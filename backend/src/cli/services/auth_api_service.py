from __future__ import annotations

from typing import Any, Dict, Optional
import os

import httpx

from auth.session import AuthError, Session


class AuthAPIService:
    """HTTP client for authentication endpoints used by the TUI."""

    def __init__(self, base_url: Optional[str] = None, timeout: float = 10.0) -> None:
        self._base_url = base_url or os.getenv("PORTFOLIO_API_URL", "http://127.0.0.1:8000")
        self._timeout = timeout

    def signup(self, email: str, password: str) -> Session:
        payload = {"email": email, "password": password}
        data = self._request("POST", "/api/auth/signup", json=payload)
        return self._to_session(data, fallback_email=email)

    def login(self, email: str, password: str) -> Session:
        payload = {"email": email, "password": password}
        data = self._request("POST", "/api/auth/login", json=payload)
        return self._to_session(data, fallback_email=email)

    def refresh_session(self, refresh_token: str) -> Session:
        if not refresh_token:
            raise AuthError("Refresh token missing. Sign in again.")
        payload = {"refresh_token": refresh_token}
        data = self._request("POST", "/api/auth/refresh", json=payload)
        return self._to_session(data, fallback_email="")

    def _request(
        self,
        method: str,
        path: str,
        *,
        json: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        try:
            with httpx.Client(base_url=self._base_url, timeout=self._timeout) as client:
                response = client.request(method, path, json=json)
        except httpx.RequestError as exc:
            raise AuthError(f"Auth API request failed: {exc}") from exc

        payload: Dict[str, Any] = {}
        try:
            result = response.json()
            if isinstance(result, dict):
                payload = result
        except ValueError:
            payload = {}

        if response.status_code >= 400:
            detail: Any = payload.get("detail", payload)
            if isinstance(detail, dict):
                message = detail.get("message") or str(detail)
            else:
                message = str(detail) if detail else response.text
            raise AuthError(message or f"Auth API error ({response.status_code}).")

        return payload

    @staticmethod
    def _to_session(payload: Dict[str, Any], fallback_email: str) -> Session:
        user_id = payload.get("user_id")
        access_token = payload.get("access_token")
        if not user_id or not access_token:
            raise AuthError("Auth API response missing session data.")
        email = payload.get("email") or fallback_email
        refresh_token = payload.get("refresh_token")
        return Session(
            user_id=user_id,
            email=email,
            access_token=access_token,
            refresh_token=refresh_token,
        )
