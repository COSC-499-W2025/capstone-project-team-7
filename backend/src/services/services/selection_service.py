"""Service for managing user selection preferences."""
from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional, Any
import logging
import os

from .supabase_keys import (
    apply_client_access_token,
    create_postgrest_client,
    is_jwt_like,
    resolve_supabase_api_key,
)
from . import local_store

try:
    from supabase.client import create_client
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False
    def create_client(*args: Any, **kwargs: Any) -> Any:  # type: ignore
        raise ImportError("supabase-py is not installed")


logger = logging.getLogger(__name__)


class SelectionServiceError(Exception):
    """Base error for selection service."""


class SelectionService:
    """Manage user selection preferences in Supabase."""
    
    def __init__(
        self,
        supabase_url: Optional[str] = None,
        supabase_key: Optional[str] = None,
    ):
        """Initialize SelectionService with Supabase credentials.
        
        Args:
            supabase_url: Supabase project URL (defaults to SUPABASE_URL env var)
            supabase_key: Supabase service role key (defaults to SUPABASE_KEY env var)
        
        Raises:
            SelectionServiceError: If Supabase is not available or credentials are missing
        """
        if not SUPABASE_AVAILABLE:
            raise SelectionServiceError("Supabase client not available. Install supabase-py.")
        
        # Initialize Supabase client
        self.supabase_url = supabase_url or os.getenv("SUPABASE_URL")
        self.supabase_key = resolve_supabase_api_key(
            supabase_key,
            prefer_anon_for_python_client=True,
        )
        
        if not self.supabase_url or not self.supabase_key:
            raise SelectionServiceError("Supabase credentials not configured.")

        self.supabase_url = str(self.supabase_url)
        self.supabase_key = str(self.supabase_key)

        self._use_local_store = os.getenv("CAPSTONE_LOCAL_STORE") == "1"

        self.client: Any = None
        self._requires_user_token_client = False

        if self._use_local_store:
            return

        try:
            self.client = create_client(self.supabase_url, self.supabase_key)
        except Exception as exc:
            if (self.supabase_key or "").startswith("sb_publishable_"):
                self._requires_user_token_client = True
                try:
                    self.client = create_postgrest_client(str(self.supabase_url), str(self.supabase_key))
                    self._requires_user_token_client = False
                except Exception:
                    self.client = None
            else:
                raise SelectionServiceError(f"Failed to initialize Supabase client: {exc}") from exc

    def apply_access_token(self, token: Optional[str]) -> None:
        if token and not is_jwt_like(token) and self.client is not None:
            return

        if self.client is None and token and is_jwt_like(token):
            try:
                self.client = create_client(self.supabase_url, token)
            except Exception as exc:
                try:
                    self.client = create_postgrest_client(str(self.supabase_url), str(self.supabase_key))
                except Exception:
                    raise SelectionServiceError(f"Failed to initialize user-scoped Supabase client: {exc}") from exc

        if self.client is None and token and not is_jwt_like(token) and self._requires_user_token_client:
            raise SelectionServiceError("JWT access token is required for Supabase operations.")

        if self.client is None and self._requires_user_token_client:
            raise SelectionServiceError("Authenticated user token is required for Supabase operations.")

        if self._use_local_store:
            return

        apply_client_access_token(self.client, token)
    
    def get_user_selections(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user's selection preferences.
        
        Args:
            user_id: User's UUID
        
        Returns:
            Selection record with project/skill ordering, or None if not found
        
        Raises:
            SelectionServiceError: If database query fails
        """
        if self._use_local_store:
            return local_store.get_selection(user_id)

        try:
            response = (
                self.client.table("user_selections")
                .select("*")
                .eq("user_id", user_id)
                .limit(1)
                .execute()
            )
            if response is None:
                return None

            data = getattr(response, "data", None)
            if not data:
                return None

            if isinstance(data, list):
                return data[0] if data else None
            return data
        except Exception as exc:
            logger.error(f"Failed to retrieve selections for user {user_id}: {exc}")
            raise SelectionServiceError(f"Failed to retrieve selections: {exc}") from exc
    
    def save_user_selections(
        self,
        user_id: str,
        project_order: Optional[List[str]] = None,
        skill_order: Optional[List[str]] = None,
        selected_project_ids: Optional[List[str]] = None,
        selected_skill_ids: Optional[List[str]] = None,
        sort_mode: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Save or update user's selection preferences.
        
        Args:
            user_id: User's UUID
            project_order: Ordered list of project IDs for display
            skill_order: Ordered list of skill names for display
            selected_project_ids: List of project IDs selected for showcase
            selected_skill_ids: List of skill names selected for showcase
            sort_mode: Projects ranking mode preference (contribution or recency)
        
        Returns:
            Saved selection record
        
        Raises:
            SelectionServiceError: If database operation fails
        """
        if self._use_local_store:
            payload: Dict[str, Any] = {}
            if project_order is not None:
                payload["project_order"] = project_order
            if skill_order is not None:
                payload["skill_order"] = skill_order
            if selected_project_ids is not None:
                payload["selected_project_ids"] = selected_project_ids
            if selected_skill_ids is not None:
                payload["selected_skill_ids"] = selected_skill_ids
            if sort_mode is not None:
                payload["sort_mode"] = sort_mode
            return local_store.upsert_selection(user_id, payload)

        try:
            # Build payload with only provided fields
            payload: Dict[str, Any] = {"user_id": user_id}
            
            if project_order is not None:
                payload["project_order"] = project_order
            if skill_order is not None:
                payload["skill_order"] = skill_order
            if selected_project_ids is not None:
                payload["selected_project_ids"] = selected_project_ids
            if selected_skill_ids is not None:
                payload["selected_skill_ids"] = selected_skill_ids
            if sort_mode is not None:
                payload["sort_mode"] = sort_mode
            
            # Try to get existing record
            existing = self.get_user_selections(user_id)
            
            if existing:
                # Update existing record
                response = (
                    self.client.table("user_selections")
                    .update(payload)
                    .eq("user_id", user_id)
                    .execute()
                )
            else:
                # Insert new record with defaults for missing fields
                if "project_order" not in payload:
                    payload["project_order"] = []
                if "skill_order" not in payload:
                    payload["skill_order"] = []
                if "selected_project_ids" not in payload:
                    payload["selected_project_ids"] = []
                if "selected_skill_ids" not in payload:
                    payload["selected_skill_ids"] = []
                if "sort_mode" not in payload:
                    payload["sort_mode"] = "recency"
                
                response = (
                    self.client.table("user_selections")
                    .insert(payload)
                    .execute()
                )

            if response is None:
                raise SelectionServiceError("No data returned after save operation")

            response_data = getattr(response, "data", None)
            if not response_data:
                raise SelectionServiceError("No data returned after save operation")

            return response_data[0] if isinstance(response_data, list) else response_data
            
        except SelectionServiceError:
            raise
        except Exception as exc:
            logger.error(f"Failed to save selections for user {user_id}: {exc}")
            raise SelectionServiceError(f"Failed to save selections: {exc}") from exc
    
    def delete_user_selections(self, user_id: str) -> bool:
        """Delete user's selection preferences.
        
        Args:
            user_id: User's UUID
        
        Returns:
            True if deleted, False if no record existed
        
        Raises:
            SelectionServiceError: If database operation fails
        """
        if self._use_local_store:
            return local_store.delete_selection(user_id)

        try:
            # Check if record exists
            existing = self.get_user_selections(user_id)
            if not existing:
                return False
            
            self.client.table("user_selections").delete().eq("user_id", user_id).execute()
            return True
            
        except SelectionServiceError:
            raise
        except Exception as exc:
            logger.error(f"Failed to delete selections for user {user_id}: {exc}")
            raise SelectionServiceError(f"Failed to delete selections: {exc}") from exc
