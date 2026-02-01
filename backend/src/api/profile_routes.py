"""Profile endpoints – GET, PATCH, avatar upload, and password change."""

from __future__ import annotations

import base64
import os
import uuid
from datetime import datetime, timezone
from typing import Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from pydantic import BaseModel, Field

from api.dependencies import AuthContext, get_auth_context

router = APIRouter(prefix="/api/profile", tags=["profile"])

_ALLOWED_AVATAR_TYPES = {"image/png", "image/jpeg", "image/gif", "image/webp"}
_MAX_AVATAR_BYTES = 5 * 1024 * 1024  # 5 MB

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


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=6)


class AvatarUploadResponse(BaseModel):
    avatar_url: str


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


@router.post("/avatar", response_model=AvatarUploadResponse)
async def upload_avatar(
    file: UploadFile = File(...),
    auth: AuthContext = Depends(get_auth_context),
):
    """Upload an avatar image to Supabase Storage and update the profile.

    Accepts PNG, JPEG, GIF, or WebP up to 5 MB.  The file is stored in the
    ``avatars`` bucket under ``<user_id>/avatar.<ext>``.
    """
    if file.content_type not in _ALLOWED_AVATAR_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "invalid_file_type",
                "message": f"Allowed types: {', '.join(_ALLOWED_AVATAR_TYPES)}",
            },
        )

    contents = await file.read()
    if len(contents) > _MAX_AVATAR_BYTES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "file_too_large", "message": "Avatar must be under 5 MB"},
        )

    # Use a fixed filename so upsert always overwrites the same path,
    # preventing orphaned files when the user changes image format.
    storage_path = f"{auth.user_id}/avatar"

    base_url = os.getenv("SUPABASE_URL", "")
    key = (
        os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        or os.getenv("SUPABASE_KEY")
        or os.getenv("SUPABASE_ANON_KEY", "")
    )

    upload_url = f"{base_url}/storage/v1/object/avatars/{storage_path}"
    headers = {
        "Authorization": f"Bearer {auth.access_token}",
        "apikey": key,
        "Content-Type": file.content_type or "application/octet-stream",
        "x-upsert": "true",
    }

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.put(upload_url, content=contents, headers=headers)

    if resp.status_code >= 400:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={
                "code": "storage_error",
                "message": f"Failed to upload avatar: {resp.text}",
            },
        )

    public_url = f"{base_url}/storage/v1/object/public/avatars/{storage_path}"

    # Persist the URL in the profiles table
    await update_profile(
        UpdateProfileRequest(avatar_url=public_url),
        auth,
    )

    return AvatarUploadResponse(avatar_url=public_url)


@router.delete("/avatar")
async def delete_avatar(auth: AuthContext = Depends(get_auth_context)):
    """Delete the avatar file from Supabase Storage and clear the profile URL."""
    storage_path = f"{auth.user_id}/avatar"

    base_url = os.getenv("SUPABASE_URL", "")
    key = (
        os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        or os.getenv("SUPABASE_KEY")
        or os.getenv("SUPABASE_ANON_KEY", "")
    )

    delete_url = f"{base_url}/storage/v1/object/avatars/{storage_path}"
    headers = {
        "Authorization": f"Bearer {auth.access_token}",
        "apikey": key,
    }

    async with httpx.AsyncClient(timeout=10) as client:
        await client.delete(delete_url, headers=headers)

    # Clear the URL in the profiles table regardless of storage result
    await update_profile(UpdateProfileRequest(avatar_url=""), auth)

    return {"ok": True, "message": "Avatar removed"}


@router.post("/password")
async def change_password(
    body: ChangePasswordRequest,
    auth: AuthContext = Depends(get_auth_context),
):
    """Change the authenticated user's password via the Supabase Auth API.

    Verifies the current password first by attempting a sign-in, then
    updates to the new password.
    """
    base_url = os.getenv("SUPABASE_URL", "")
    key = (
        os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        or os.getenv("SUPABASE_KEY")
        or os.getenv("SUPABASE_ANON_KEY", "")
    )

    # --- Step 1: verify current password via sign-in ---
    verify_url = f"{base_url}/auth/v1/token?grant_type=password"
    verify_headers = {
        "apikey": key,
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=10) as client:
        verify_resp = await client.post(
            verify_url,
            json={"email": auth.email, "password": body.current_password},
            headers=verify_headers,
        )

    if verify_resp.status_code >= 400:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "invalid_current_password",
                "message": "Current password is incorrect.",
            },
        )

    # --- Step 2: update to the new password ---
    url = f"{base_url}/auth/v1/user"
    headers = {
        "Authorization": f"Bearer {auth.access_token}",
        "apikey": key,
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.put(
            url,
            json={"password": body.new_password},
            headers=headers,
        )

    if resp.status_code >= 400:
        detail = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {}
        raise HTTPException(
            status_code=resp.status_code if resp.status_code < 500 else status.HTTP_502_BAD_GATEWAY,
            detail={
                "code": "password_change_failed",
                "message": detail.get("msg") or detail.get("message") or "Password change failed",
            },
        )

    return {"ok": True, "message": "Password updated successfully"}
