"""LinkedIn OAuth and direct-posting API routes."""

from __future__ import annotations

import logging
import os
import secrets
import time
from dataclasses import dataclass, field
from typing import Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from api.dependencies import AuthContext, get_auth_context

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/linkedin", tags=["LinkedIn"])

# ---------------------------------------------------------------------------
# CSRF state store (in-memory, single-server)
# Stores the Supabase access_token alongside so the backend GET callback
# can exchange the LinkedIn code without the browser needing auth.
# ---------------------------------------------------------------------------

_STATE_TTL = 600  # 10 minutes


@dataclass
class _OAuthState:
    state: str
    user_id: str
    access_token: str
    created_at: float = field(default_factory=time.time)


_oauth_states: Dict[str, _OAuthState] = {}  # keyed by state value


def _cleanup_states() -> None:
    now = time.time()
    expired = [k for k, s in _oauth_states.items() if now - s.created_at > _STATE_TTL]
    for k in expired:
        del _oauth_states[k]


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


_CALLBACK_SUCCESS_HTML = """<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>LinkedIn Connected</title>
<style>
body {{ font-family: -apple-system, sans-serif; display: flex; align-items: center;
       justify-content: center; min-height: 100vh; margin: 0; background: #f8fafc; }}
.card {{ text-align: center; padding: 2.5rem; border-radius: 1rem;
         border: 1px solid #e2e8f0; background: #fff; max-width: 24rem; box-shadow: 0 4px 12px rgba(0,0,0,0.06); }}
.icon {{ font-size: 2rem; margin-bottom: 0.75rem; }}
h2 {{ margin: 0 0 0.25rem; font-size: 1rem; color: #1a202c; }}
p {{ margin: 0; font-size: 0.8rem; color: #64748b; }}
</style></head>
<body><div class="card">
<div class="icon">&#9989;</div>
<h2>Connected as {name}</h2>
<p>You can close this window and return to the app.</p>
</div></body></html>"""

_CALLBACK_ERROR_HTML = """<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>LinkedIn Error</title>
<style>
body {{ font-family: -apple-system, sans-serif; display: flex; align-items: center;
       justify-content: center; min-height: 100vh; margin: 0; background: #f8fafc; }}
.card {{ text-align: center; padding: 2.5rem; border-radius: 1rem;
         border: 1px solid #e2e8f0; background: #fff; max-width: 24rem; box-shadow: 0 4px 12px rgba(0,0,0,0.06); }}
.icon {{ font-size: 2rem; margin-bottom: 0.75rem; }}
h2 {{ margin: 0 0 0.25rem; font-size: 1rem; color: #1a202c; }}
p {{ margin: 0; font-size: 0.8rem; color: #ef4444; }}
</style></head>
<body><div class="card">
<div class="icon">&#10060;</div>
<h2>Connection Failed</h2>
<p>{error}</p>
</div></body></html>"""


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.get("/auth-url", response_model=LinkedInAuthUrlResponse)
async def get_auth_url(auth: AuthContext = Depends(get_auth_context)):
    """Generate a LinkedIn OAuth 2.0 authorization URL."""
    _require_linkedin_config()
    _cleanup_states()

    state = secrets.token_urlsafe(32)
    _oauth_states[state] = _OAuthState(
        state=state,
        user_id=auth.user_id,
        access_token=auth.access_token,
    )

    from services.services.linkedin_api_service import get_authorization_url

    auth_url = get_authorization_url(state)
    return LinkedInAuthUrlResponse(auth_url=auth_url)


@router.get("/oauth/callback", response_class=HTMLResponse)
async def oauth_callback_get(code: str = "", state: str = "", error: str = ""):
    """Backend-handled OAuth callback. LinkedIn redirects here directly.

    This is a GET endpoint so it works in the system browser without needing
    the user's auth token (which lives in Electron's localStorage).
    """
    if error:
        return HTMLResponse(_CALLBACK_ERROR_HTML.format(error=error))

    _cleanup_states()

    stored = _oauth_states.pop(state, None)
    if not stored:
        return HTMLResponse(_CALLBACK_ERROR_HTML.format(error="Invalid or expired OAuth state. Please try again."))

    from services.services.linkedin_api_service import exchange_code

    result = await exchange_code(code, stored.user_id, stored.access_token)
    if not result.get("connected"):
        return HTMLResponse(_CALLBACK_ERROR_HTML.format(error=result.get("error", "Token exchange failed")))

    name = result.get("linkedin_name", "LinkedIn user")
    return HTMLResponse(_CALLBACK_SUCCESS_HTML.format(name=name))


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
