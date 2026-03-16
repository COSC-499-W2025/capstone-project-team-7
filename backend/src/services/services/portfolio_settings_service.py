"""Service for managing portfolio display settings and public sharing."""
from __future__ import annotations

import logging
import os
import secrets
from typing import Any, Dict, Optional

from .supabase_keys import (
    apply_client_access_token,
    create_postgrest_client,
    is_jwt_like,
    resolve_supabase_api_key,
)
try:
    from supabase.client import create_client
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False
    def create_client(*args: Any, **kwargs: Any) -> Any:  # type: ignore
        raise ImportError("supabase-py is not installed")


logger = logging.getLogger(__name__)

TABLE = "portfolio_settings"


class PortfolioSettingsError(Exception):
    """Base error for portfolio settings service."""


class PortfolioSettingsService:
    """Manage portfolio display settings and public sharing in Supabase."""

    def __init__(
        self,
        supabase_url: Optional[str] = None,
        supabase_key: Optional[str] = None,
    ):
        if not SUPABASE_AVAILABLE:
            raise PortfolioSettingsError("Supabase client not available.")

        self.supabase_url = supabase_url or os.getenv("SUPABASE_URL")
        self.supabase_key = resolve_supabase_api_key(
            supabase_key, prefer_anon_for_python_client=True,
        )

        if not self.supabase_url or not self.supabase_key:
            raise PortfolioSettingsError("Supabase credentials not configured.")

        self.supabase_url = str(self.supabase_url)
        self.supabase_key = str(self.supabase_key)

        self._use_local_store = (
            os.getenv("CAPSTONE_LOCAL_STORE") == "1"
            or bool(os.getenv("PYTEST_CURRENT_TEST"))
        )

        self.client: Any = None
        self._requires_user_token_client = False
        try:
            self.client = create_client(self.supabase_url, self.supabase_key)
        except Exception as exc:
            if (self.supabase_key or "").startswith("sb_publishable_"):
                self._requires_user_token_client = True
                try:
                    self.client = create_postgrest_client(self.supabase_url, self.supabase_key)
                    self._requires_user_token_client = False
                except Exception:
                    self.client = None
            else:
                raise PortfolioSettingsError(f"Failed to init Supabase client: {exc}") from exc

    def apply_access_token(self, token: Optional[str]) -> None:
        if token and not is_jwt_like(token) and self.client is not None:
            return
        if self.client is None and token and is_jwt_like(token):
            try:
                self.client = create_client(self.supabase_url, token)
            except Exception as exc:
                try:
                    self.client = create_postgrest_client(self.supabase_url, self.supabase_key)
                except Exception:
                    raise PortfolioSettingsError(f"Failed to init user-scoped client: {exc}") from exc
        if self.client is None and self._requires_user_token_client:
            raise PortfolioSettingsError("JWT access token required.")
        if self._use_local_store:
            return
        apply_client_access_token(self.client, token)

    # ── Read ────────────────────────────────────────────────────────────

    def get_settings(self, user_id: str) -> Optional[Dict[str, Any]]:
        if self._use_local_store:
            return None  # local store not supported for settings
        try:
            resp = (
                self.client.table(TABLE)
                .select("*")
                .eq("user_id", user_id)
                .limit(1)
                .execute()
            )
            data = getattr(resp, "data", None)
            if not data:
                return None
            return data[0] if isinstance(data, list) else data
        except Exception as exc:
            logger.error("Failed to get portfolio settings for %s: %s", user_id, exc)
            raise PortfolioSettingsError(f"Failed to get settings: {exc}") from exc

    def get_by_share_token(self, share_token: str) -> Optional[Dict[str, Any]]:
        """Fetch settings by share_token. Used for public access (no auth)."""
        if self._use_local_store:
            return None
        try:
            resp = (
                self.client.table(TABLE)
                .select("*")
                .eq("share_token", share_token)
                .eq("is_public", True)
                .limit(1)
                .execute()
            )
            data = getattr(resp, "data", None)
            if not data:
                return None
            return data[0] if isinstance(data, list) else data
        except Exception as exc:
            logger.error("Failed to get portfolio by token: %s", exc)
            raise PortfolioSettingsError(f"Failed to get by token: {exc}") from exc

    # ── Upsert ──────────────────────────────────────────────────────────

    def upsert_settings(self, user_id: str, **kwargs: Any) -> Dict[str, Any]:
        allowed = {
            "is_public", "share_token", "display_name", "bio",
            "show_heatmap", "show_skills_timeline", "show_top_projects",
            "show_all_skills", "showcase_count",
        }
        payload: Dict[str, Any] = {
            k: v for k, v in kwargs.items() if k in allowed and v is not None
        }

        if self._use_local_store:
            return {"user_id": user_id, **payload}

        try:
            existing = self.get_settings(user_id)
            if existing:
                resp = (
                    self.client.table(TABLE)
                    .update(payload)
                    .eq("user_id", user_id)
                    .execute()
                )
            else:
                payload["user_id"] = user_id
                resp = self.client.table(TABLE).insert(payload).execute()

            data = getattr(resp, "data", None)
            if not data:
                raise PortfolioSettingsError("No data returned after upsert")
            return data[0] if isinstance(data, list) else data
        except PortfolioSettingsError:
            raise
        except Exception as exc:
            logger.error("Failed to upsert portfolio settings for %s: %s", user_id, exc)
            raise PortfolioSettingsError(f"Failed to save settings: {exc}") from exc

    # ── Publish / Unpublish ─────────────────────────────────────────────

    def toggle_public(self, user_id: str, is_public: bool) -> Dict[str, Any]:
        kwargs: Dict[str, Any] = {"is_public": is_public}
        if is_public:
            existing = self.get_settings(user_id)
            if not existing or not existing.get("share_token"):
                kwargs["share_token"] = secrets.token_urlsafe(16)
        return self.upsert_settings(user_id, **kwargs)

    # ── Profile (for public portfolio) ──────────────────────────────────

    def get_user_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Fetch basic profile data for a user. Used by the public endpoint."""
        if self._use_local_store:
            return None
        try:
            resp = (
                self.client.table("profiles")
                .select("id,full_name,career_title,education,avatar_url")
                .eq("id", user_id)
                .limit(1)
                .execute()
            )
            data = getattr(resp, "data", None)
            if not data:
                return None
            return data[0] if isinstance(data, list) else data
        except Exception as exc:
            logger.warning("Failed to fetch profile for user %s: %s", user_id, exc)
            return None
