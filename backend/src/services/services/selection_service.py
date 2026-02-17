"""Service for managing user selection preferences."""
from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional, Any
import logging
import os

try:
    from supabase import Client, create_client
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False
    Client = None  # type: ignore
    def create_client(*args, **kwargs):  # type: ignore
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
        self.supabase_key = supabase_key or os.getenv("SUPABASE_KEY")
        
        if not self.supabase_url or not self.supabase_key:
            raise SelectionServiceError("Supabase credentials not configured.")

        try:
            self.client: Client = create_client(self.supabase_url, self.supabase_key)
        except Exception as exc:
            raise SelectionServiceError(f"Failed to initialize Supabase client: {exc}") from exc
    
    def get_user_selections(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user's selection preferences.
        
        Args:
            user_id: User's UUID
        
        Returns:
            Selection record with project/skill ordering, or None if not found
        
        Raises:
            SelectionServiceError: If database query fails
        """
        try:
            response = (
                self.client.table("user_selections")
                .select("*")
                .eq("user_id", user_id)
                .maybe_single()
                .execute()
            )
            return response.data
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
    ) -> Dict[str, Any]:
        """Save or update user's selection preferences.
        
        Args:
            user_id: User's UUID
            project_order: Ordered list of project IDs for display
            skill_order: Ordered list of skill names for display
            selected_project_ids: List of project IDs selected for showcase
            selected_skill_ids: List of skill names selected for showcase
        
        Returns:
            Saved selection record
        
        Raises:
            SelectionServiceError: If database operation fails
        """
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
                
                response = (
                    self.client.table("user_selections")
                    .insert(payload)
                    .execute()
                )
            
            if not response.data:
                raise SelectionServiceError("No data returned after save operation")
            
            return response.data[0] if isinstance(response.data, list) else response.data
            
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
