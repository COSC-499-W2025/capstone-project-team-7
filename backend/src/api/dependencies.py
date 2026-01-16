from __future__ import annotations

from dataclasses import dataclass
import os
from typing import Any, Dict, Optional

import httpx
from fastapi import Header, HTTPException, status


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
    supabase_key = (
        os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        or os.getenv("SUPABASE_KEY")
        or os.getenv("SUPABASE_ANON_KEY")
    )
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

    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        _raise_auth_error("Authorization header must be Bearer token")

    access_token = parts[1].strip()
    if not access_token:
        _raise_auth_error("Access token missing")

    user = await get_user_profile(access_token)
    return AuthContext(
        user_id=user["id"],
        access_token=access_token,
        email=user.get("email"),
    )
