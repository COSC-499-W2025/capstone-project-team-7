"""User Resume Service - manages full resume documents stored in Supabase."""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, cast
from uuid import UUID

try:
    from supabase import Client, create_client
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False
    Client = None  # type: ignore[assignment]

from services.services.supabase_keys import (
    apply_client_access_token,
    create_postgrest_client,
    is_jwt_like,
    resolve_supabase_api_key,
)

logger = logging.getLogger(__name__)


class UserResumeServiceError(Exception):
    """Raised when user resume operations fail."""


class UserResumeService:
    """Service for managing user resume documents in Supabase."""

    VALID_TEMPLATES = {"jake", "classic", "modern", "minimal", "custom"}

    def __init__(
        self,
        supabase_url: Optional[str] = None,
        supabase_key: Optional[str] = None,
    ) -> None:
        if not SUPABASE_AVAILABLE:
            raise UserResumeServiceError("Supabase client not available. Install supabase-py.")

        self.supabase_url = supabase_url or os.getenv("SUPABASE_URL")
        self.supabase_key = resolve_supabase_api_key(
            supabase_key,
            prefer_anon_for_python_client=True,
        )

        if not self.supabase_url or not self.supabase_key:
            raise UserResumeServiceError("Supabase credentials not configured.")

        self._access_token: Optional[str] = None
        self.client: Any = None
        self._requires_user_token_client = False

        try:
            self.client = create_client(cast(str, self.supabase_url), cast(str, self.supabase_key))
        except Exception as exc:
            if (self.supabase_key or "").startswith("sb_publishable_"):
                self._requires_user_token_client = True
                try:
                    self.client = create_postgrest_client(
                        cast(str, self.supabase_url),
                        cast(str, self.supabase_key),
                    )
                    self._requires_user_token_client = False
                except Exception:
                    self.client = None
            else:
                raise UserResumeServiceError(f"Failed to initialize Supabase client: {exc}") from exc

    def apply_access_token(self, token: Optional[str]) -> None:
        """Apply user's access token for RLS-scoped queries."""
        self._access_token = token

        if token and not is_jwt_like(token) and self.client is not None:
            return

        if self.client is None and token and is_jwt_like(token):
            try:
                self.client = create_client(cast(str, self.supabase_url), token)
            except Exception as exc:
                try:
                    self.client = create_postgrest_client(
                        cast(str, self.supabase_url),
                        cast(str, self.supabase_key),
                    )
                except Exception:
                    raise UserResumeServiceError(
                        f"Failed to initialize user-scoped Supabase client: {exc}"
                    ) from exc

        if self.client is None and token and not is_jwt_like(token) and self._requires_user_token_client:
            raise UserResumeServiceError("JWT access token is required for Supabase operations.")

        if self.client is None and self._requires_user_token_client:
            raise UserResumeServiceError("Authenticated user token is required for Supabase operations.")

        apply_client_access_token(self.client, token)

    def _handle_response(self, response: Any) -> List[Dict[str, Any]]:
        """Extract data from Supabase response."""
        if response is not None:
            return response
        raise UserResumeServiceError("Supabase operation returned None")

    def list_resumes(
        self, user_id: str, *, limit: int = 20, offset: int = 0
    ) -> tuple[List[Dict[str, Any]], int]:
        """List resumes for a user with pagination.
        
        Returns:
            Tuple of (records, total_count) for the requested page.
        """
        if not user_id:
            return [], 0

        try:
            # Get total count first
            count_response = (
                self.client.table("user_resumes")
                .select("id", count="exact")
                .eq("user_id", user_id)
                .execute()
            )
            total = count_response.count if hasattr(count_response, 'count') and count_response.count is not None else 0

            # Get paginated records
            response = (
                self.client.table("user_resumes")
                .select("id, name, template, is_latex_mode, metadata, created_at, updated_at")
                .eq("user_id", user_id)
                .order("updated_at", desc=True)
                .range(offset, offset + limit - 1)
                .execute()
            )
            records = self._handle_response(response.data)
            return records, total
        except Exception as exc:
            raise UserResumeServiceError(f"Failed to list resumes: {exc}") from exc

    def get_resume(self, user_id: str, resume_id: str) -> Optional[Dict[str, Any]]:
        """Fetch a single resume with full content."""
        if not user_id or not resume_id:
            return None

        try:
            response = (
                self.client.table("user_resumes")
                .select("*")
                .eq("user_id", user_id)
                .eq("id", resume_id)
                .limit(1)
                .execute()
            )
            data = self._handle_response(response.data)
            return data[0] if data else None
        except Exception as exc:
            raise UserResumeServiceError(f"Failed to fetch resume: {exc}") from exc

    def create_resume(
        self,
        user_id: str,
        *,
        name: str = "Untitled Resume",
        template: str = "jake",
        latex_content: Optional[str] = None,
        structured_data: Optional[Dict[str, Any]] = None,
        is_latex_mode: bool = True,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Create a new resume document."""
        if not user_id:
            raise UserResumeServiceError("User ID is required to create a resume.")

        if template not in self.VALID_TEMPLATES:
            raise UserResumeServiceError(f"Invalid template: {template}. Must be one of {self.VALID_TEMPLATES}")

        payload = {
            "user_id": user_id,
            "name": name,
            "template": template,
            "latex_content": latex_content,
            "structured_data": structured_data or {},
            "is_latex_mode": is_latex_mode,
            "metadata": metadata or {},
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

        try:
            response = self.client.table("user_resumes").insert(payload).execute()
            data = self._handle_response(response.data)
            if not data:
                raise UserResumeServiceError("Supabase did not return created resume.")
            return data[0]
        except UserResumeServiceError:
            raise
        except Exception as exc:
            raise UserResumeServiceError(f"Failed to create resume: {exc}") from exc

    def update_resume(
        self,
        user_id: str,
        resume_id: str,
        *,
        name: Optional[str] = None,
        template: Optional[str] = None,
        latex_content: Optional[str] = None,
        structured_data: Optional[Dict[str, Any]] = None,
        is_latex_mode: Optional[bool] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        """Update an existing resume."""
        if not user_id or not resume_id:
            return None

        # Check resume exists
        existing = self.get_resume(user_id, resume_id)
        if not existing:
            return None

        if template is not None and template not in self.VALID_TEMPLATES:
            raise UserResumeServiceError(f"Invalid template: {template}. Must be one of {self.VALID_TEMPLATES}")

        payload: Dict[str, Any] = {}
        if name is not None:
            payload["name"] = name
        if template is not None:
            payload["template"] = template
        if latex_content is not None:
            payload["latex_content"] = latex_content
        if structured_data is not None:
            payload["structured_data"] = structured_data
        if is_latex_mode is not None:
            payload["is_latex_mode"] = is_latex_mode
        if metadata is not None:
            # Merge with existing metadata
            existing_metadata = existing.get("metadata") or {}
            payload["metadata"] = {**existing_metadata, **metadata}

        if not payload:
            return existing  # Nothing to update

        try:
            response = (
                self.client.table("user_resumes")
                .update(payload)
                .eq("user_id", user_id)
                .eq("id", resume_id)
                .execute()
            )
            data = self._handle_response(response.data)
            return data[0] if data else None
        except Exception as exc:
            raise UserResumeServiceError(f"Failed to update resume: {exc}") from exc

    def delete_resume(self, user_id: str, resume_id: str) -> bool:
        """Delete a resume."""
        if not user_id or not resume_id:
            return False

        try:
            response = (
                self.client.table("user_resumes")
                .delete()
                .eq("user_id", user_id)
                .eq("id", resume_id)
                .execute()
            )
            data = self._handle_response(response.data)
            return bool(data)
        except Exception as exc:
            raise UserResumeServiceError(f"Failed to delete resume: {exc}") from exc

    def duplicate_resume(self, user_id: str, resume_id: str, new_name: Optional[str] = None) -> Dict[str, Any]:
        """Duplicate an existing resume."""
        existing = self.get_resume(user_id, resume_id)
        if not existing:
            raise UserResumeServiceError("Resume not found.")

        return self.create_resume(
            user_id,
            name=new_name or f"{existing.get('name', 'Resume')} (Copy)",
            template=existing.get("template", "jake"),
            latex_content=existing.get("latex_content"),
            structured_data=existing.get("structured_data"),
            is_latex_mode=existing.get("is_latex_mode", True),
            metadata={"duplicated_from": resume_id},
        )
