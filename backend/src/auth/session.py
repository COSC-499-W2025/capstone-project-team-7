from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any, Dict, Optional

try:  # pragma: no cover
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover
    def load_dotenv():  # type: ignore
        return None

try:  # pragma: no cover - handled in tests via FakeAuth
    import requests
except ImportError:  # pragma: no cover
    requests = None


AUTH_SIGNUP_PATH = "/auth/v1/signup"
AUTH_TOKEN_PATH = "/auth/v1/token?grant_type=password"

load_dotenv()


class AuthError(Exception):
    """Raised when authentication with Supabase fails."""


@dataclass
class Session:
    """Represents an authenticated Supabase session."""

    user_id: str
    email: str
    access_token: str


class SupabaseAuth:
    """Thin wrapper around Supabase REST auth endpoints."""

    def __init__(self, *, url: Optional[str] = None, anon_key: Optional[str] = None):
        self.base_url = url or os.getenv("SUPABASE_URL")
        self.anon_key = anon_key or os.getenv("SUPABASE_ANON_KEY") or os.getenv("SUPABASE_KEY")
        if not self.base_url or not self.anon_key:
            raise AuthError("Supabase credentials missing. Set SUPABASE_URL and SUPABASE_ANON_KEY.")

    def signup(self, email: str, password: str) -> Session:
        """Create a new user account and return a valid session."""
        self._post(AUTH_SIGNUP_PATH, {"email": email, "password": password})
        # Supabase may not auto-return a session after signup, so perform a login.
        return self.login(email, password)

    def login(self, email: str, password: str) -> Session:
        """Authenticate a user and return a session."""
        payload = self._post(AUTH_TOKEN_PATH, {"email": email, "password": password})
        access_token = payload.get("access_token")
        user = payload.get("user") or {}
        user_id = user.get("id")
        if not access_token or not user_id:
            raise AuthError("Incomplete response from Supabase during login.")
        return Session(user_id=user_id, email=user.get("email", email), access_token=access_token)

    def _post(self, path: str, data: Dict[str, Any]) -> Dict[str, Any]:
        if requests is None:
            raise AuthError("The 'requests' package is required for Supabase authentication.")
        headers = {
            "apikey": self.anon_key,
            "Content-Type": "application/json",
        }
        response = requests.post(
            f"{self.base_url}{path}",
            headers=headers,
            data=json.dumps(data),
            timeout=20,
        )
        if response.status_code >= 400:
            try:
                details = response.json()
            except ValueError:
                details = response.text
            raise AuthError(f"Supabase error {response.status_code}: {details}")
        if not response.text:
            return {}
        return response.json()
