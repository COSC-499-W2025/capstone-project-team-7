"""Profile endpoints – GET and PATCH the authenticated user's profile."""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from api.dependencies import AuthContext, get_auth_context

router = APIRouter(prefix="/api/profile", tags=["profile"])

# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class UserProfile(BaseModel):
    user_id: str
    display_name: Optional[str] = None
    email: Optional[str] = None
    education: Optional[str] = None
    career_title: Optional[str] = None
    avatar_url: Optional[str] = None
    schema_url: Optional[str] = None
    drive_url: Optional[str] = None
    updated_at: Optional[str] = None


class UpdateProfileRequest(BaseModel):
    display_name: Optional[str] = None
    education: Optional[str] = None
    career_title: Optional[str] = None
    avatar_url: Optional[str] = None
    schema_url: Optional[str] = None
    drive_url: Optional[str] = None


# ---------------------------------------------------------------------------
# Supabase helpers
# ---------------------------------------------------------------------------

_PROFILE_TABLE = "profiles"


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

@router.get("", response_model=UserProfile)
async def get_profile(auth: AuthContext = Depends(get_auth_context)):
    """Return the profile for the currently authenticated user.

    If no profile row exists yet, an empty skeleton is returned so the
    frontend always has a valid shape to work with.
    """
    rest = _supabase_rest_url()
    url = f"{rest}/{_PROFILE_TABLE}?id=eq.{auth.user_id}&select=*"

    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(url, headers=_supabase_headers(auth.access_token))

    if resp.status_code >= 400:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"code": "upstream_error", "message": "Failed to fetch profile"},
        )

    rows = resp.json()
    if rows:
        row = rows[0]
        return UserProfile(
            user_id=row.get("id", auth.user_id),
            display_name=row.get("full_name") or row.get("display_name"),
            email=auth.email or row.get("email"),
            education=row.get("education"),
            career_title=row.get("career_title"),
            avatar_url=row.get("avatar_url"),
            schema_url=row.get("schema_url"),
            drive_url=row.get("drive_url"),
            updated_at=row.get("updated_at"),
        )

    # No row yet – return skeleton
    return UserProfile(user_id=auth.user_id, email=auth.email)


@router.patch("", response_model=UserProfile)
async def update_profile(
    body: UpdateProfileRequest,
    auth: AuthContext = Depends(get_auth_context),
):
    """Upsert profile fields for the authenticated user."""
    rest = _supabase_rest_url()
    url = f"{rest}/{_PROFILE_TABLE}?id=eq.{auth.user_id}"

    payload: dict = {}
    if body.display_name is not None:
        payload["full_name"] = body.display_name
    if body.education is not None:
        payload["education"] = body.education
    if body.career_title is not None:
        payload["career_title"] = body.career_title
    if body.avatar_url is not None:
        payload["avatar_url"] = body.avatar_url
    if body.schema_url is not None:
        payload["schema_url"] = body.schema_url
    if body.drive_url is not None:
        payload["drive_url"] = body.drive_url

    if not payload:
        return await get_profile(auth)

    payload["updated_at"] = datetime.now(timezone.utc).isoformat()

    headers = _supabase_headers(auth.access_token)

    async with httpx.AsyncClient(timeout=10) as client:
        # Try PATCH first (row exists)
        resp = await client.patch(url, json=payload, headers=headers)

        rows = resp.json() if resp.status_code < 400 else []
        if not rows:
            # Row doesn't exist yet – INSERT
            payload["id"] = auth.user_id
            payload["email"] = auth.email
            insert_url = f"{rest}/{_PROFILE_TABLE}"
            resp = await client.post(insert_url, json=payload, headers=headers)
            if resp.status_code >= 400:
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail={"code": "upstream_error", "message": "Failed to create profile"},
                )
            rows = resp.json()

    if not rows:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"code": "upstream_error", "message": "Profile update returned empty"},
        )

    row = rows[0]
    return UserProfile(
        user_id=row.get("id", auth.user_id),
        display_name=row.get("full_name") or row.get("display_name"),
        email=auth.email or row.get("email"),
        education=row.get("education"),
        career_title=row.get("career_title"),
        avatar_url=row.get("avatar_url"),
        schema_url=row.get("schema_url"),
        drive_url=row.get("drive_url"),
        updated_at=row.get("updated_at"),
    )
