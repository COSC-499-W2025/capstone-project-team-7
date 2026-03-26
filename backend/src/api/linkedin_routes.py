"""LinkedIn OAuth and direct-posting API routes."""

from __future__ import annotations

import logging
import os
import secrets
import time
from dataclasses import dataclass, field
from typing import Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from api.dependencies import AuthContext, get_auth_context

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/linkedin", tags=["LinkedIn"])

# ---------------------------------------------------------------------------
# CSRF state store (in-memory, single-server)
# ---------------------------------------------------------------------------

_STATE_TTL = 600  # 10 minutes


@dataclass
class _OAuthState:
    state: str
    created_at: float = field(default_factory=time.time)


_oauth_states: Dict[str, _OAuthState] = {}


def _cleanup_states() -> None:
    now = time.time()
    expired = [uid for uid, s in _oauth_states.items() if now - s.created_at > _STATE_TTL]
    for uid in expired:
        del _oauth_states[uid]


def _require_linkedin_config() -> None:
    if not os.getenv("LINKEDIN_CLIENT_ID") or not os.getenv("LINKEDIN_CLIENT_SECRET"):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "linkedin_not_configured", "message": "LinkedIn API credentials are not configured"},
        )


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------


class LinkedInAuthUrlResponse(BaseModel):
    auth_url: str


class LinkedInCallbackRequest(BaseModel):
    code: str
    state: str


class LinkedInConnectionStatus(BaseModel):
    connected: bool
    linkedin_name: Optional[str] = None
    expires_at: Optional[str] = None


class LinkedInDirectPostRequest(BaseModel):
    post_text: str


class LinkedInDirectPostResponse(BaseModel):
    success: bool
    post_id: Optional[str] = None
    error: Optional[str] = None


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.get("/auth-url", response_model=LinkedInAuthUrlResponse)
async def get_auth_url(auth: AuthContext = Depends(get_auth_context)):
    """Generate a LinkedIn OAuth 2.0 authorization URL."""
    _require_linkedin_config()
    _cleanup_states()

    state = secrets.token_urlsafe(32)
    _oauth_states[auth.user_id] = _OAuthState(state=state)

    from services.services.linkedin_api_service import get_authorization_url

    auth_url = get_authorization_url(state)
    return LinkedInAuthUrlResponse(auth_url=auth_url)


@router.post("/callback", response_model=LinkedInConnectionStatus)
async def oauth_callback(
    body: LinkedInCallbackRequest,
    auth: AuthContext = Depends(get_auth_context),
):
    """Exchange an OAuth authorization code for LinkedIn tokens."""
    _require_linkedin_config()
    _cleanup_states()

    stored = _oauth_states.pop(auth.user_id, None)
    if not stored or stored.state != body.state:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "invalid_state", "message": "Invalid or expired OAuth state"},
        )

    from services.services.linkedin_api_service import exchange_code

    result = await exchange_code(body.code, auth.user_id, auth.access_token)
    if not result.get("connected"):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"code": "exchange_failed", "message": result.get("error", "Token exchange failed")},
        )

    return LinkedInConnectionStatus(
        connected=True,
        linkedin_name=result.get("linkedin_name"),
        expires_at=result.get("expires_at"),
    )


@router.get("/status", response_model=LinkedInConnectionStatus)
async def connection_status(auth: AuthContext = Depends(get_auth_context)):
    """Check whether the user has a connected LinkedIn account."""
    from services.services.linkedin_api_service import get_connection_status

    result = await get_connection_status(auth.user_id, auth.access_token)
    return LinkedInConnectionStatus(**result)


@router.post("/post", response_model=LinkedInDirectPostResponse)
async def post_to_linkedin(
    body: LinkedInDirectPostRequest,
    auth: AuthContext = Depends(get_auth_context),
):
    """Post content directly to LinkedIn."""
    _require_linkedin_config()

    if not body.post_text.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "empty_post", "message": "Post text cannot be empty"},
        )

    from services.services.linkedin_api_service import create_post

    result = await create_post(auth.user_id, auth.access_token, body.post_text)
    return LinkedInDirectPostResponse(
        success=result.get("success", False),
        post_id=result.get("post_id"),
        error=result.get("error"),
    )


@router.delete("/disconnect")
async def disconnect_linkedin(auth: AuthContext = Depends(get_auth_context)):
    """Remove LinkedIn connection for the user."""
    from services.services.linkedin_api_service import disconnect

    await disconnect(auth.user_id, auth.access_token)
    return {"ok": True}
