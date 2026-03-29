"""Settings endpoints -- manage user-scoped secrets (API keys) stored encrypted at rest."""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from api.dependencies import AuthContext, get_auth_context
from api.llm_routes import get_user_client, set_user_client, remove_user_client
from analyzer.llm.client import LLMClient, InvalidAPIKeyError, LLMError
from auth.consent_validator import ConsentValidator
from services.services.encryption import EncryptionService, EncryptionError

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/settings", tags=["settings"])

_SECRETS_TABLE = "user_secrets"
_ALLOWED_SECRET_KEYS = {"openai_api_key", "apify_api_token"}

# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------


class SecretStatusItem(BaseModel):
    secret_key: str
    has_value: bool
    provider: Optional[str] = None
    metadata: Optional[dict] = None
    updated_at: Optional[str] = None


class SecretStatusResponse(BaseModel):
    secrets: list[SecretStatusItem]


class SaveSecretRequest(BaseModel):
    secret_key: str
    value: str
    provider: Optional[str] = None
    metadata: Optional[dict] = None


class SaveSecretResponse(BaseModel):
    secret_key: str
    has_value: bool = True
    provider: Optional[str] = None
    updated_at: Optional[str] = None


class DeleteSecretRequest(BaseModel):
    secret_key: str


class VerifyStoredKeyResponse(BaseModel):
    valid: bool
    message: str


# ---------------------------------------------------------------------------
# Supabase helpers (same pattern as profile_routes)
# ---------------------------------------------------------------------------


def _supabase_headers(access_token: str) -> dict[str, str]:
    key = (
        os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        or os.getenv("SUPABASE_KEY")
        or os.getenv("SUPABASE_ANON_KEY", "")
    )
    return {
        "Authorization": f"Bearer {access_token}",
        "apikey": key,
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }


def _supabase_rest_url() -> str:
    base = os.getenv("SUPABASE_URL", "")
    if not base:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "configuration_error", "message": "SUPABASE_URL not set"},
        )
    return f"{base}/rest/v1"


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.get("/secrets", response_model=SecretStatusResponse)
async def get_secrets_status(auth: AuthContext = Depends(get_auth_context)):
    """Return metadata for all stored secrets -- never returns raw values."""
    rest = _supabase_rest_url()
    url = f"{rest}/{_SECRETS_TABLE}?user_id=eq.{auth.user_id}&select=secret_key,provider,metadata,updated_at"

    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(url, headers=_supabase_headers(auth.access_token))

    if resp.status_code >= 400:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"code": "upstream_error", "message": "Failed to fetch secrets status"},
        )

    rows = resp.json()
    secrets = [
        SecretStatusItem(
            secret_key=row["secret_key"],
            has_value=True,
            provider=row.get("provider"),
            metadata=row.get("metadata"),
            updated_at=row.get("updated_at"),
        )
        for row in rows
    ]
    return SecretStatusResponse(secrets=secrets)


@router.put("/secrets", response_model=SaveSecretResponse)
async def save_secret(
    body: SaveSecretRequest,
    auth: AuthContext = Depends(get_auth_context),
):
    """Encrypt and upsert a secret value."""
    if body.secret_key not in _ALLOWED_SECRET_KEYS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "invalid_secret_key",
                "message": f"Allowed keys: {', '.join(sorted(_ALLOWED_SECRET_KEYS))}",
            },
        )

    if not body.value or not body.value.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "empty_value", "message": "Secret value cannot be empty"},
        )

    try:
        enc = EncryptionService()
        envelope = enc.encrypt_json(body.value)
    except EncryptionError as exc:
        logger.error(f"Encryption failed: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "encryption_error", "message": "Failed to encrypt secret"},
        )

    now = datetime.now(timezone.utc).isoformat()
    payload = {
        "user_id": auth.user_id,
        "secret_key": body.secret_key,
        "encrypted_value": envelope.to_dict(),
        "provider": body.provider or _provider_for_key(body.secret_key),
        "metadata": body.metadata or {},
        "updated_at": now,
    }

    rest = _supabase_rest_url()
    url = f"{rest}/{_SECRETS_TABLE}?on_conflict=user_id,secret_key"
    headers = _supabase_headers(auth.access_token)
    headers["Prefer"] = "return=representation,resolution=merge-duplicates"

    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.post(url, json=payload, headers=headers)

    if resp.status_code >= 400:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"code": "upstream_error", "message": "Failed to save secret"},
        )

    rows = resp.json()
    row = rows[0] if rows else payload
    return SaveSecretResponse(
        secret_key=body.secret_key,
        has_value=True,
        provider=row.get("provider"),
        updated_at=row.get("updated_at", now),
    )


@router.delete("/secrets")
async def delete_secret(
    body: DeleteSecretRequest,
    auth: AuthContext = Depends(get_auth_context),
):
    """Delete a stored secret and evict any in-memory LLM client."""
    rest = _supabase_rest_url()
    url = f"{rest}/{_SECRETS_TABLE}?user_id=eq.{auth.user_id}&secret_key=eq.{body.secret_key}"

    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.delete(url, headers=_supabase_headers(auth.access_token))

    if resp.status_code >= 400:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"code": "upstream_error", "message": "Failed to delete secret"},
        )

    remove_user_client(auth.user_id)
    return {"ok": True, "message": "Secret removed"}


@router.post("/secrets/verify", response_model=VerifyStoredKeyResponse)
async def verify_stored_key(auth: AuthContext = Depends(get_auth_context)):
    """Decrypt the stored OpenAI key, verify it with OpenAI, and cache the client."""
    # Check consent
    try:
        consent_validator = ConsentValidator()
        has_consent = consent_validator.validate_external_services_consent(auth.user_id)
        if not has_consent:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="External services consent not granted. Enable it in Privacy & Consent.",
            )
    except HTTPException:
        raise
    except Exception as exc:
        logger.warning(f"Consent check failed: {exc}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Consent check failed.",
        )

    # Fetch encrypted key from DB
    api_key = await _fetch_and_decrypt_secret(auth.user_id, "openai_api_key", auth.access_token)
    if api_key is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No stored API key found. Save one first.",
        )

    # Verify with OpenAI
    try:
        llm_client = LLMClient(api_key=api_key)
        is_valid = llm_client.verify_api_key()
    except InvalidAPIKeyError as exc:
        logger.info(f"Invalid API key for user {auth.user_id}: {exc}")
        return VerifyStoredKeyResponse(valid=False, message="The API key is invalid or has been revoked.")
    except LLMError as exc:
        logger.warning(f"LLM service error during key verification for user {auth.user_id}: {exc}")
        return VerifyStoredKeyResponse(valid=False, message=f"Could not verify key: {exc}")
    except Exception as exc:
        logger.error(f"Unexpected error during key verification for user {auth.user_id}: {exc}", exc_info=True)
        return VerifyStoredKeyResponse(valid=False, message="An unexpected error occurred while verifying the key. Please try again.")

    if is_valid:
        set_user_client(auth.user_id, llm_client)
        return VerifyStoredKeyResponse(valid=True, message="API key verified successfully")

    return VerifyStoredKeyResponse(valid=False, message="API key verification failed")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _provider_for_key(secret_key: str) -> str:
    mapping = {"openai_api_key": "openai", "apify_api_token": "apify"}
    return mapping.get(secret_key, "unknown")


async def _fetch_and_decrypt_secret(
    user_id: str,
    secret_key: str,
    access_token: str,
) -> Optional[str]:
    """Fetch an encrypted secret from the DB and decrypt it. Returns None if not found."""
    rest = _supabase_rest_url()
    url = (
        f"{rest}/{_SECRETS_TABLE}"
        f"?user_id=eq.{user_id}&secret_key=eq.{secret_key}"
        f"&select=encrypted_value"
    )

    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(url, headers=_supabase_headers(access_token))

    if resp.status_code >= 400:
        logger.warning(
            f"Supabase error fetching secret {secret_key} for user {user_id}: "
            f"status={resp.status_code}, body={resp.text}"
        )
        return None

    rows = resp.json()
    if not rows:
        return None

    try:
        enc = EncryptionService()
        return enc.decrypt_json(rows[0]["encrypted_value"])
    except EncryptionError as exc:
        logger.error(f"Failed to decrypt secret {secret_key}: {exc}")
        return None


async def get_or_hydrate_llm_client(
    user_id: str,
    access_token: str,
) -> Optional[LLMClient]:
    """Check in-memory cache first; on miss, hydrate from DB."""
    client = get_user_client(user_id)
    if client is not None:
        return client

    api_key = await _fetch_and_decrypt_secret(user_id, "openai_api_key", access_token)
    if api_key is None:
        return None

    try:
        llm_client = LLMClient(api_key=api_key)
        set_user_client(user_id, llm_client)
        return llm_client
    except Exception as exc:
        logger.warning(f"Failed to create LLM client from stored key: {exc}")
        return None
