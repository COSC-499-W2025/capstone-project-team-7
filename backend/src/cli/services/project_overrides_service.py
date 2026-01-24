"""Service for managing project override preferences."""
from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional, Any
import json
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

# Allowed user roles for projects
# Used for validation in API endpoints, CLI screens, and database constraints
ALLOWED_ROLES = ["author", "contributor", "lead", "maintainer", "reviewer"]


class ProjectOverridesServiceError(Exception):
    """Base error for project overrides service."""


class ProjectOverridesService:
    """Manage project override preferences in Supabase.
    
    Handles user-defined overrides for:
    - Chronology corrections (start_date_override, end_date_override)
    - Role and evidence (encrypted)
    - Display customization (thumbnail_url, highlighted_skills)
    - Comparison attributes (flexible key-value pairs)
    - Custom ranking
    """
    
    # Fields that should be encrypted for privacy
    # Note: evidence is NOT encrypted because it's stored as text[] in PostgreSQL
    # and encrypting would require storing as text/jsonb instead
    ENCRYPTED_FIELDS = {"role", "comparison_attributes"}
    
    def __init__(
        self,
        supabase_url: Optional[str] = None,
        supabase_key: Optional[str] = None,
        *,
        encryption_service=None,
        encryption_required: bool = False,
    ):
        """Initialize ProjectOverridesService with Supabase credentials.
        
        Args:
            supabase_url: Supabase project URL (defaults to SUPABASE_URL env var)
            supabase_key: Supabase service role key (defaults to SUPABASE_KEY env var)
            encryption_service: Optional EncryptionService instance for encrypting sensitive fields
            encryption_required: If True, raise error when encryption is unavailable
        
        Raises:
            ProjectOverridesServiceError: If Supabase is not available or credentials are missing
        """
        if not SUPABASE_AVAILABLE:
            raise ProjectOverridesServiceError("Supabase client not available. Install supabase-py.")
        
        # Initialize Supabase client
        self.supabase_url = supabase_url or os.getenv("SUPABASE_URL")
        self.supabase_key = (
            supabase_key
            or os.getenv("SUPABASE_KEY")
            or os.getenv("SUPABASE_SERVICE_ROLE_KEY")
            or os.getenv("SUPABASE_ANON_KEY")
        )
        
        if not self.supabase_url or not self.supabase_key:
            raise ProjectOverridesServiceError("Supabase credentials not configured.")
        
        # Initialize encryption service
        self._encryption = encryption_service
        if self._encryption is None:
            try:
                from .encryption import EncryptionService
                self._encryption = EncryptionService()
            except Exception as exc:
                if encryption_required:
                    raise ProjectOverridesServiceError(f"Encryption unavailable: {exc}") from exc
                logger.warning(f"Encryption unavailable, sensitive fields will be stored unencrypted: {exc}")
                self._encryption = None

        try:
            self.client: Client = create_client(self.supabase_url, self.supabase_key)
        except Exception as exc:
            raise ProjectOverridesServiceError(f"Failed to initialize Supabase client: {exc}") from exc
    
    def get_overrides(self, user_id: str, project_id: str) -> Optional[Dict[str, Any]]:
        """Get overrides for a specific project.
        
        Args:
            user_id: User's UUID
            project_id: Project's UUID
        
        Returns:
            Override record with decrypted fields, or None if not found
        
        Raises:
            ProjectOverridesServiceError: If database query fails
        """
        try:
            # Don't use maybe_single() as it returns None directly when no rows found
            # which makes it hard to distinguish from errors. Use limit(1) instead.
            response = (
                self.client.table("project_overrides")
                .select("*")
                .eq("user_id", user_id)
                .eq("project_id", project_id)
                .limit(1)
                .execute()
            )
            
            if not response.data:
                return None
            
            return self._decrypt_record(response.data[0])
            
        except Exception as exc:
            logger.error(f"Failed to retrieve overrides for project {project_id}: {exc}")
            raise ProjectOverridesServiceError(f"Failed to retrieve overrides: {exc}") from exc
    
    def get_overrides_for_projects(self, user_id: str, project_ids: List[str]) -> Dict[str, Dict[str, Any]]:
        """Get overrides for multiple projects in a single query.
        
        Args:
            user_id: User's UUID
            project_ids: List of project UUIDs
        
        Returns:
            Dict mapping project_id to override record (decrypted)
        
        Raises:
            ProjectOverridesServiceError: If database query fails
        """
        if not project_ids:
            return {}
        
        try:
            response = (
                self.client.table("project_overrides")
                .select("*")
                .eq("user_id", user_id)
                .in_("project_id", project_ids)
                .execute()
            )
            
            result = {}
            for record in response.data or []:
                project_id = record.get("project_id")
                if project_id:
                    result[project_id] = self._decrypt_record(record)
            
            return result
            
        except Exception as exc:
            logger.error(f"Failed to retrieve overrides for projects: {exc}")
            raise ProjectOverridesServiceError(f"Failed to retrieve overrides: {exc}") from exc
    
    def upsert_overrides(
        self,
        user_id: str,
        project_id: str,
        *,
        role: Optional[str] = None,
        evidence: Optional[List[str]] = None,
        thumbnail_url: Optional[str] = None,
        custom_rank: Optional[float] = None,
        start_date_override: Optional[str] = None,
        end_date_override: Optional[str] = None,
        comparison_attributes: Optional[Dict[str, str]] = None,
        highlighted_skills: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Create or update overrides for a project.
        
        Only provided (non-None) fields are updated. Pass empty string/list/dict
        to explicitly clear a field.
        
        Args:
            user_id: User's UUID
            project_id: Project's UUID
            role: User's role/title for this project
            evidence: List of accomplishment bullet points
            thumbnail_url: Custom thumbnail URL
            custom_rank: Manual ranking override (0-100)
            start_date_override: Override for project start date (ISO date string)
            end_date_override: Override for project end date (ISO date string)
            comparison_attributes: Custom key-value pairs for comparisons
            highlighted_skills: Skills to highlight for this project
        
        Returns:
            Updated override record (decrypted)
        
        Raises:
            ProjectOverridesServiceError: If database operation fails
        """
        try:
            # Build payload with only provided fields
            payload: Dict[str, Any] = {
                "user_id": user_id,
                "project_id": project_id,
            }
            
            # Add provided fields (None means "don't update", explicit value means "set this")
            if role is not None:
                payload["role"] = self._encrypt_field("role", role) if role else role
            if evidence is not None:
                payload["evidence"] = self._encrypt_field("evidence", evidence) if evidence else evidence
            if thumbnail_url is not None:
                payload["thumbnail_url"] = thumbnail_url
            if custom_rank is not None:
                payload["custom_rank"] = custom_rank
            if start_date_override is not None:
                payload["start_date_override"] = start_date_override if start_date_override else None
            if end_date_override is not None:
                payload["end_date_override"] = end_date_override if end_date_override else None
            if comparison_attributes is not None:
                payload["comparison_attributes"] = (
                    self._encrypt_field("comparison_attributes", comparison_attributes)
                    if comparison_attributes else comparison_attributes
                )
            if highlighted_skills is not None:
                payload["highlighted_skills"] = highlighted_skills
            
            # Check if record exists
            existing = self.get_overrides(user_id, project_id)
            
            if existing:
                # Update existing record - merge with existing data
                update_payload = {k: v for k, v in payload.items() if k not in ("user_id", "project_id")}
                if not update_payload:
                    return existing  # Nothing to update
                
                response = (
                    self.client.table("project_overrides")
                    .update(update_payload)
                    .eq("user_id", user_id)
                    .eq("project_id", project_id)
                    .execute()
                )
            else:
                # Insert new record with defaults for missing fields
                if "role" not in payload:
                    payload["role"] = None
                if "evidence" not in payload:
                    payload["evidence"] = []
                if "thumbnail_url" not in payload:
                    payload["thumbnail_url"] = None
                if "custom_rank" not in payload:
                    payload["custom_rank"] = None
                if "start_date_override" not in payload:
                    payload["start_date_override"] = None
                if "end_date_override" not in payload:
                    payload["end_date_override"] = None
                if "comparison_attributes" not in payload:
                    payload["comparison_attributes"] = {}
                if "highlighted_skills" not in payload:
                    payload["highlighted_skills"] = []
                
                response = (
                    self.client.table("project_overrides")
                    .insert(payload)
                    .execute()
                )
            
            if not response.data:
                raise ProjectOverridesServiceError("No data returned after save operation")
            
            record = response.data[0] if isinstance(response.data, list) else response.data
            return self._decrypt_record(record)
            
        except ProjectOverridesServiceError:
            raise
        except Exception as exc:
            logger.error(f"Failed to save overrides for project {project_id}: {exc}")
            raise ProjectOverridesServiceError(f"Failed to save overrides: {exc}") from exc
    
    def delete_overrides(self, user_id: str, project_id: str) -> bool:
        """Delete all overrides for a project.
        
        Args:
            user_id: User's UUID
            project_id: Project's UUID
        
        Returns:
            True if deleted, False if no record existed
        
        Raises:
            ProjectOverridesServiceError: If database operation fails
        """
        try:
            # Check if record exists
            existing = self.get_overrides(user_id, project_id)
            if not existing:
                return False
            
            self.client.table("project_overrides").delete().eq("user_id", user_id).eq("project_id", project_id).execute()
            return True
            
        except ProjectOverridesServiceError:
            raise
        except Exception as exc:
            logger.error(f"Failed to delete overrides for project {project_id}: {exc}")
            raise ProjectOverridesServiceError(f"Failed to delete overrides: {exc}") from exc
    
    # --- Encryption helpers ---
    
    def _encrypt_field(self, field_name: str, value: Any) -> Any:
        """Encrypt a field value if encryption is available and field should be encrypted."""
        if field_name not in self.ENCRYPTED_FIELDS:
            return value
        if not self._encryption:
            return value
        if not value:  # Don't encrypt empty values
            return value
        
        try:
            envelope = self._encryption.encrypt_json(value)
            # Return as JSON string for storage in text columns
            return json.dumps(envelope.to_dict())
        except Exception as exc:
            logger.warning(f"Failed to encrypt field {field_name}, storing unencrypted: {exc}")
            return value
    
    def _decrypt_field(self, field_name: str, value: Any) -> Any:
        """Decrypt a field value if it appears to be encrypted."""
        if field_name not in self.ENCRYPTED_FIELDS:
            return value
        if not value or not self._encryption:
            return value
        
        # Try to parse JSON string if needed (data stored in text columns comes back as string)
        envelope = value
        if isinstance(value, str):
            try:
                envelope = json.loads(value)
            except (json.JSONDecodeError, TypeError):
                # Not valid JSON, return as-is
                return value
        
        # Check if value is an encryption envelope
        if isinstance(envelope, dict) and {"v", "iv", "ct"} <= set(envelope.keys()):
            try:
                return self._encryption.decrypt_json(envelope)
            except Exception as exc:
                logger.warning(f"Failed to decrypt field {field_name}, returning as-is: {exc}")
                return value
        
        return value
    
    def _decrypt_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Decrypt all encrypted fields in a record."""
        result = dict(record)
        for field in self.ENCRYPTED_FIELDS:
            if field in result:
                result[field] = self._decrypt_field(field, result[field])
        return result
