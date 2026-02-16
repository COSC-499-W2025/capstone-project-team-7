"""Authentication API routes backed by Supabase auth."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from api.dependencies import AuthContext, get_auth_context
from auth.session import AuthError, Session, SupabaseAuth


router = APIRouter(prefix="/api/auth", tags=["Auth"])


class AuthCredentials(BaseModel):
    email: str = Field(..., description="User email address")
    password: str = Field(..., description="User password")


class RefreshRequest(BaseModel):
    refresh_token: str = Field(..., description="Supabase refresh token")


class AuthSessionResponse(BaseModel):
    user_id: str
    email: str
    access_token: str
    refresh_token: Optional[str] = None


class AuthSessionInfo(BaseModel):
    user_id: str
    email: Optional[str] = None


class PasswordResetRequest(BaseModel):
    email: str = Field(..., description="User email address")
    redirect_to: Optional[str] = Field(None, description="Redirect URL after reset")


class PasswordResetConfirm(BaseModel):
    token: str = Field(..., description="Supabase recovery token")
    new_password: str = Field(..., description="New user password")


def _to_session_response(session: Session) -> AuthSessionResponse:
    return AuthSessionResponse(
        user_id=session.user_id,
        email=session.email,
        access_token=session.access_token,
        refresh_token=session.refresh_token,
    )


def _raise_auth_error(error: AuthError) -> HTTPException:
    message = str(error)
    message_lower = message.lower()
    if "credentials missing" in message_lower:
        status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        code = "configuration_error"
    elif "refresh token missing" in message_lower:
        status_code = status.HTTP_400_BAD_REQUEST
        code = "validation_error"
    else:
        status_code = status.HTTP_401_UNAUTHORIZED
        code = "authentication_failed"
    return HTTPException(
        status_code=status_code,
        detail={"code": code, "message": message},
    )


@router.post("/signup", response_model=AuthSessionResponse, status_code=status.HTTP_200_OK)
def signup(payload: AuthCredentials) -> AuthSessionResponse:
    try:
        session = SupabaseAuth().signup(payload.email, payload.password)
        return _to_session_response(session)
    except AuthError as exc:
        raise _raise_auth_error(exc)


@router.post("/login", response_model=AuthSessionResponse, status_code=status.HTTP_200_OK)
def login(payload: AuthCredentials) -> AuthSessionResponse:
    try:
        session = SupabaseAuth().login(payload.email, payload.password)
        return _to_session_response(session)
    except AuthError as exc:
        raise _raise_auth_error(exc)


@router.post("/refresh", response_model=AuthSessionResponse, status_code=status.HTTP_200_OK)
def refresh_session(payload: RefreshRequest) -> AuthSessionResponse:
    try:
        session = SupabaseAuth().refresh_session(payload.refresh_token)
        return _to_session_response(session)
    except AuthError as exc:
        raise _raise_auth_error(exc)


@router.post("/request-reset", status_code=status.HTTP_200_OK)
def request_password_reset(payload: PasswordResetRequest) -> dict:
    try:
        SupabaseAuth().request_password_reset(payload.email, payload.redirect_to)
        return {"ok": True, "message": "Password reset email sent."}
    except AuthError as exc:
        raise _raise_auth_error(exc)


@router.post("/reset-password", status_code=status.HTTP_200_OK)
def reset_password(payload: PasswordResetConfirm) -> dict:
    try:
        SupabaseAuth().reset_password(payload.token, payload.new_password)
        return {"ok": True, "message": "Password has been reset."}
    except AuthError as exc:
        raise _raise_auth_error(exc)


@router.get("/session", response_model=AuthSessionInfo, status_code=status.HTTP_200_OK)
async def get_session(auth: AuthContext = Depends(get_auth_context)) -> AuthSessionInfo:
    return AuthSessionInfo(user_id=auth.user_id, email=auth.email)
