"""LinkedIn API service for OAuth and direct posting.

Handles the three-legged OAuth 2.0 flow, encrypted token storage in the
existing ``user_secrets`` table, and posting to the LinkedIn Posts API.
"""

from __future__ import annotations

import logging
import os
import urllib.parse
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, Optional

import httpx

from services.services.encryption import EncryptionService, EncryptionError

logger = logging.getLogger(__name__)

_SECRETS_TABLE = "user_secrets"
_LINKEDIN_AUTH_URL = "https://www.linkedin.com/oauth/v2/authorization"
_LINKEDIN_TOKEN_URL = "https://www.linkedin.com/oauth/v2/accessToken"
_LINKEDIN_USERINFO_URL = "https://api.linkedin.com/v2/userinfo"
_LINKEDIN_POSTS_URL = "https://api.linkedin.com/rest/posts"

# ---------------------------------------------------------------------------
# Supabase helpers (same pattern as settings_routes.py)
# ---------------------------------------------------------------------------


def _supabase_headers(access_token: str) -> Dict[str, str]:
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
        raise RuntimeError("SUPABASE_URL not set")
    return f"{base}/rest/v1"


# ---------------------------------------------------------------------------
# Token helpers
# ---------------------------------------------------------------------------


async def _store_secret(
    user_id: str,
    access_token: str,
    secret_key: str,
    value: str,
    metadata: Optional[Dict[str, Any]] = None,
) -> None:
    enc = EncryptionService()
    envelope = enc.encrypt_json(value)
    now = datetime.now(timezone.utc).isoformat()
    payload = {
        "user_id": user_id,
        "secret_key": secret_key,
        "encrypted_value": envelope.to_dict(),
        "provider": "linkedin",
        "metadata": metadata or {},
        "updated_at": now,
    }
    rest = _supabase_rest_url()
    url = f"{rest}/{_SECRETS_TABLE}?on_conflict=user_id,secret_key"
    headers = _supabase_headers(access_token)
    headers["Prefer"] = "return=representation,resolution=merge-duplicates"
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.post(url, json=payload, headers=headers)
    if resp.status_code >= 400:
        logger.error("Failed to store secret %s: %s", secret_key, resp.text)


async def _fetch_secret(
    user_id: str,
    access_token: str,
    secret_key: str,
) -> Optional[str]:
    rest = _supabase_rest_url()
    url = (
        f"{rest}/{_SECRETS_TABLE}"
        f"?user_id=eq.{user_id}&secret_key=eq.{secret_key}"
        f"&select=encrypted_value"
    )
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(url, headers=_supabase_headers(access_token))
    if resp.status_code >= 400:
        return None
    rows = resp.json()
    if not rows:
        return None
    try:
        enc = EncryptionService()
        return enc.decrypt_json(rows[0]["encrypted_value"])
    except EncryptionError as exc:
        logger.error("Failed to decrypt %s: %s", secret_key, exc)
        return None


async def _fetch_secret_metadata(
    user_id: str,
    access_token: str,
    secret_key: str,
) -> Optional[Dict[str, Any]]:
    rest = _supabase_rest_url()
    url = (
        f"{rest}/{_SECRETS_TABLE}"
        f"?user_id=eq.{user_id}&secret_key=eq.{secret_key}"
        f"&select=metadata"
    )
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(url, headers=_supabase_headers(access_token))
    if resp.status_code >= 400 or not resp.json():
        return None
    return resp.json()[0].get("metadata")


async def _delete_secret(
    user_id: str,
    access_token: str,
    secret_key: str,
) -> None:
    rest = _supabase_rest_url()
    url = f"{rest}/{_SECRETS_TABLE}?user_id=eq.{user_id}&secret_key=eq.{secret_key}"
    async with httpx.AsyncClient(timeout=10) as client:
        await client.delete(url, headers=_supabase_headers(access_token))


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def get_authorization_url(state: str) -> str:
    """Build the LinkedIn OAuth 2.0 authorization URL."""
    client_id = os.getenv("LINKEDIN_CLIENT_ID", "")
    redirect_uri = os.getenv("LINKEDIN_REDIRECT_URI", "")
    params = urllib.parse.urlencode({
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "state": state,
        "scope": "openid profile w_member_social",
    })
    return f"{_LINKEDIN_AUTH_URL}?{params}"


async def exchange_code(
    code: str,
    user_id: str,
    access_token: str,
) -> Dict[str, Any]:
    """Exchange an authorization code for tokens and store them."""
    client_id = os.getenv("LINKEDIN_CLIENT_ID", "")
    client_secret = os.getenv("LINKEDIN_CLIENT_SECRET", "")
    redirect_uri = os.getenv("LINKEDIN_REDIRECT_URI", "")

    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(
            _LINKEDIN_TOKEN_URL,
            data={
                "grant_type": "authorization_code",
                "code": code,
                "client_id": client_id,
                "client_secret": client_secret,
                "redirect_uri": redirect_uri,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

    if resp.status_code != 200:
        logger.error("LinkedIn token exchange failed: %s", resp.text)
        return {"connected": False, "error": "Token exchange failed"}

    data = resp.json()
    li_access_token = data.get("access_token", "")
    li_refresh_token = data.get("refresh_token", "")
    expires_in = data.get("expires_in", 5184000)  # default 60 days
    refresh_expires_in = data.get("refresh_token_expires_in", 31536000)

    # Fetch LinkedIn profile
    member_id = ""
    member_name = ""
    async with httpx.AsyncClient(timeout=10) as client:
        profile_resp = await client.get(
            _LINKEDIN_USERINFO_URL,
            headers={"Authorization": f"Bearer {li_access_token}"},
        )
    if profile_resp.status_code == 200:
        profile = profile_resp.json()
        member_id = profile.get("sub", "")
        member_name = profile.get("name", "")

    expires_at = (datetime.now(timezone.utc) + timedelta(seconds=expires_in)).isoformat()
    refresh_expires_at = (datetime.now(timezone.utc) + timedelta(seconds=refresh_expires_in)).isoformat()

    await _store_secret(
        user_id, access_token, "linkedin_access_token", li_access_token,
        metadata={"expires_at": expires_at, "member_id": member_id, "name": member_name},
    )
    if li_refresh_token:
        await _store_secret(
            user_id, access_token, "linkedin_refresh_token", li_refresh_token,
            metadata={"expires_at": refresh_expires_at},
        )

    return {
        "connected": True,
        "linkedin_name": member_name,
        "expires_at": expires_at,
    }


async def get_connection_status(
    user_id: str,
    access_token: str,
) -> Dict[str, Any]:
    """Check whether the user has a valid LinkedIn connection."""
    meta = await _fetch_secret_metadata(user_id, access_token, "linkedin_access_token")
    if not meta:
        return {"connected": False, "linkedin_name": None, "expires_at": None}

    expires_at = meta.get("expires_at")
    if expires_at:
        try:
            exp = datetime.fromisoformat(expires_at)
            if exp < datetime.now(timezone.utc):
                return {"connected": False, "linkedin_name": None, "expires_at": None}
        except ValueError:
            pass

    return {
        "connected": True,
        "linkedin_name": meta.get("name"),
        "expires_at": expires_at,
    }


async def create_post(
    user_id: str,
    access_token: str,
    post_text: str,
) -> Dict[str, Any]:
    """Post content to LinkedIn on behalf of the user."""
    li_token = await _fetch_secret(user_id, access_token, "linkedin_access_token")
    if not li_token:
        return {"success": False, "error": "LinkedIn not connected"}

    meta = await _fetch_secret_metadata(user_id, access_token, "linkedin_access_token")
    member_id = (meta or {}).get("member_id", "")
    if not member_id:
        return {"success": False, "error": "LinkedIn member ID not found"}

    result = await _do_post(li_token, member_id, post_text)

    # If 401, try refreshing the token and retry once
    if result.get("status") == 401:
        refreshed = await _refresh_token(user_id, access_token)
        if refreshed:
            li_token = await _fetch_secret(user_id, access_token, "linkedin_access_token")
            if li_token:
                result = await _do_post(li_token, member_id, post_text)

    return result


async def _do_post(
    li_token: str,
    member_id: str,
    post_text: str,
) -> Dict[str, Any]:
    body = {
        "author": f"urn:li:person:{member_id}",
        "commentary": post_text,
        "visibility": "PUBLIC",
        "distribution": {
            "feedDistribution": "MAIN_FEED",
            "targetEntities": [],
            "thirdPartyDistributionChannels": [],
        },
        "lifecycleState": "PUBLISHED",
        "isReshareDisabledByAuthor": False,
    }
    headers = {
        "Authorization": f"Bearer {li_token}",
        "LinkedIn-Version": "202501",
        "X-Restli-Protocol-Version": "2.0.0",
        "Content-Type": "application/json",
    }
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(_LINKEDIN_POSTS_URL, json=body, headers=headers)

    if resp.status_code == 401:
        return {"success": False, "status": 401, "error": "Token expired"}
    if resp.status_code >= 400:
        logger.error("LinkedIn post failed: %s %s", resp.status_code, resp.text)
        return {"success": False, "error": f"LinkedIn API error ({resp.status_code})"}

    post_id = resp.headers.get("x-restli-id", "")
    return {"success": True, "post_id": post_id}


async def _refresh_token(user_id: str, access_token: str) -> bool:
    """Attempt to refresh the LinkedIn access token."""
    refresh_token = await _fetch_secret(user_id, access_token, "linkedin_refresh_token")
    if not refresh_token:
        return False

    client_id = os.getenv("LINKEDIN_CLIENT_ID", "")
    client_secret = os.getenv("LINKEDIN_CLIENT_SECRET", "")

    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(
            _LINKEDIN_TOKEN_URL,
            data={
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
                "client_id": client_id,
                "client_secret": client_secret,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

    if resp.status_code != 200:
        logger.error("LinkedIn token refresh failed: %s", resp.text)
        return False

    data = resp.json()
    new_token = data.get("access_token", "")
    expires_in = data.get("expires_in", 5184000)
    expires_at = (datetime.now(timezone.utc) + timedelta(seconds=expires_in)).isoformat()

    # Preserve existing metadata
    meta = await _fetch_secret_metadata(user_id, access_token, "linkedin_access_token") or {}
    meta["expires_at"] = expires_at

    await _store_secret(user_id, access_token, "linkedin_access_token", new_token, metadata=meta)

    new_refresh = data.get("refresh_token")
    if new_refresh:
        refresh_expires_in = data.get("refresh_token_expires_in", 31536000)
        refresh_expires_at = (datetime.now(timezone.utc) + timedelta(seconds=refresh_expires_in)).isoformat()
        await _store_secret(
            user_id, access_token, "linkedin_refresh_token", new_refresh,
            metadata={"expires_at": refresh_expires_at},
        )

    return True


async def disconnect(user_id: str, access_token: str) -> None:
    """Remove all LinkedIn tokens for a user."""
    await _delete_secret(user_id, access_token, "linkedin_access_token")
    await _delete_secret(user_id, access_token, "linkedin_refresh_token")
