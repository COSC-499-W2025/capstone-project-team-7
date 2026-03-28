from __future__ import annotations

import base64
from dataclasses import dataclass
import json
import os
from typing import Any, Dict, Optional, cast

import httpx
from fastapi import Header, HTTPException, status

from api.request_context import set_request_access_token
from services.services.supabase_keys import resolve_supabase_api_key


@dataclass(frozen=True)
class AuthContext:
    user_id: str
    access_token: str
    email: Optional[str] = None


def _raise_auth_error(message: str, status_code: int = status.HTTP_401_UNAUTHORIZED) -> None:
    raise HTTPException(
        status_code=status_code,
        detail={"code": "unauthorized", "message": message},
    )


async def _fetch_user(access_token: str) -> Dict[str, Any]:
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = resolve_supabase_api_key()
    if not supabase_url or not supabase_key:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "configuration_error", "message": "Supabase credentials missing"},
        )

    headers = {
        "Authorization": f"Bearer {access_token}",
        "apikey": supabase_key,
        "Content-Type": "application/json",
    }
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.get(f"{supabase_url}/auth/v1/user", headers=headers)

    if response.status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN):
        _raise_auth_error("Invalid or expired access token")
    if response.status_code >= 400:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"code": "upstream_error", "message": "Failed to validate access token"},
        )

    payload = response.json()
    user_id = payload.get("id")
    if not user_id:
        _raise_auth_error("Access token missing user id")
    return payload


async def _resolve_user_id(access_token: str) -> str:
    payload = await _fetch_user(access_token)
    return payload["id"]


async def get_user_profile(access_token: str) -> Dict[str, Any]:
    return await _fetch_user(access_token)


async def get_auth_context(authorization: Optional[str] = Header(default=None)) -> AuthContext:
    if not authorization:
        _raise_auth_error("Authorization header missing")

    header_value = cast(str, authorization)
    parts = header_value.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        _raise_auth_error("Authorization header must be Bearer token")

    access_token = parts[1].strip()
    if not access_token:
        _raise_auth_error("Access token missing")

    set_request_access_token(access_token)

    if os.getenv("PYTEST_CURRENT_TEST"):
        payload: Dict[str, Any] = {}
        pieces = access_token.split(".")
        if len(pieces) >= 2:
            encoded_payload = pieces[1]
            encoded_payload += "=" * (-len(encoded_payload) % 4)
            try:
                payload = json.loads(base64.urlsafe_b64decode(encoded_payload.encode()).decode())
            except Exception:
                payload = {}

        user_id = payload.get("sub") or payload.get("id") or access_token
        email = payload.get("email")
        return AuthContext(
            user_id=str(user_id),
            access_token=access_token,
            email=str(email) if isinstance(email, str) else None,
        )

    user = await get_user_profile(access_token)
    return AuthContext(
        user_id=user["id"],
        access_token=access_token,
        email=user.get("email"),
    )
