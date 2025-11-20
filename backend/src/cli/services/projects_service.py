"""Service for managing project scan storage and retrieval."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
import json

try:
    from supabase import Client, create_client
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False
    Client = None  # type: ignore


class ProjectsServiceError(Exception):
    """Base error for projects service."""


class ProjectsService:
    """Manage project scan storage in Supabase."""
    
    def __init__(self, supabase_url: Optional[str] = None, supabase_key: Optional[str] = None):
        if not SUPABASE_AVAILABLE:
            raise ProjectsServiceError("Supabase client not available. Install supabase-py.")
        
        # Initialize Supabase client
        import os
        self.supabase_url = supabase_url or os.getenv("SUPABASE_URL")
        self.supabase_key = supabase_key or os.getenv("SUPABASE_KEY")
        
        if not self.supabase_url or not self.supabase_key:
            raise ProjectsServiceError("Supabase credentials not configured.")
        
        try:
            self.client: Client = create_client(self.supabase_url, self.supabase_key)
        except Exception as exc:
            raise ProjectsServiceError(f"Failed to initialize Supabase client: {exc}") from exc
    
    def save_scan(
        self,
        user_id: str,
        project_name: str,
        project_path: str,
        scan_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Save or update a project scan.
        
        Args:
            user_id: User's UUID
            project_name: Name/identifier for this project
            project_path: Filesystem path that was scanned
            scan_data: Complete JSON export payload
        
        Returns:
            Saved project record
        """
        try:
            # Extract metadata from scan_data
            summary = scan_data.get("summary", {})
            
            languages = []
            if "languages" in summary:
                lang_data = summary["languages"]
                if isinstance(lang_data, list):
                    languages = [lang.get("name") for lang in lang_data if isinstance(lang, dict)]
                elif isinstance(lang_data, dict):
                    languages = list(lang_data.keys())
            
            record = {
                "user_id": user_id,
                "project_name": project_name,
                "project_path": project_path,
                "scan_data": scan_data,
                "scan_timestamp": datetime.now().isoformat(),
                "total_files": summary.get("files_processed", 0),
                "total_lines": scan_data.get("code_analysis", {}).get("metrics", {}).get("total_lines", 0),
                "languages": languages,
                "has_media_analysis": "media_analysis" in scan_data,
                "has_pdf_analysis": "pdf_analysis" in scan_data,
                "has_code_analysis": "code_analysis" in scan_data,
                "has_git_analysis": "git_analysis" in scan_data,
            }
            
            # Upsert (insert or update if exists)
            response = self.client.table("projects").upsert(
                record,
                on_conflict="user_id,project_name"
            ).execute()
            
            if not response.data:
                raise ProjectsServiceError("Failed to save project scan")
            
            return response.data[0]
            
        except Exception as exc:
            raise ProjectsServiceError(f"Failed to save scan: {exc}") from exc
    
    def get_user_projects(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Get all projects for a user, ordered by most recent first.
        
        Returns:
            List of project records (without full scan_data)
        """
        try:
            response = self.client.table("projects").select(
                "id, project_name, project_path, scan_timestamp, "
                "total_files, total_lines, languages, "
                "has_media_analysis, has_pdf_analysis, has_code_analysis, has_git_analysis, "
                "created_at"
            ).eq("user_id", user_id).order("scan_timestamp", desc=True).execute()
            
            return response.data or []
            
        except Exception as exc:
            raise ProjectsServiceError(f"Failed to get projects: {exc}") from exc
    
    def get_project_scan(self, user_id: str, project_id: str) -> Optional[Dict[str, Any]]:
        """
        Get full scan data for a specific project.
        
        Args:
            user_id: User's UUID
            project_id: Project's UUID
        
        Returns:
            Complete project record with scan_data, or None if not found
        """
        try:
            response = self.client.table("projects").select("*").eq(
                "user_id", user_id
            ).eq("id", project_id).execute()
            
            if not response.data:
                return None
            
            return response.data[0]
            
        except Exception as exc:
            raise ProjectsServiceError(f"Failed to get project scan: {exc}") from exc
    
    def delete_project(self, user_id: str, project_id: str) -> bool:
        """
        Delete a project scan.
        
        Returns:
            True if deleted successfully
        """
        try:
            response = (
                self.client.table("projects")
                .delete()
                .eq("user_id", user_id)
                .eq("id", project_id)
                .execute()
            )
        except Exception as exc:
            raise ProjectsServiceError(f"Failed to delete project: {exc}") from exc

        return len(response.data) > 0

    def delete_project_insights(self, user_id: str, project_id: str) -> bool:
        """
        Remove stored scan insights for a project while keeping user uploads intact.

        This clears `scan_data` and all cached per-file metadata so the user can
        re-run analysis later without losing shared artifacts.
        """
        try:
            timestamp = datetime.now().isoformat()
            update_fields = {
                "scan_data": None,
                "scan_timestamp": None,
                "total_files": 0,
                "total_lines": 0,
                "languages": [],
                "has_media_analysis": False,
                "has_pdf_analysis": False,
                "has_code_analysis": False,
                "has_git_analysis": False,
                "insights_deleted_at": timestamp,
            }
            response = (
                self.client.table("projects")
                .update(update_fields)
                .eq("user_id", user_id)
                .eq("id", project_id)
                .execute()
            )
        except Exception as exc:
            raise ProjectsServiceError(f"Failed to delete insights: {exc}") from exc

        if not response.data:
            return False

        try:
            (
                self.client.table("scan_files")
                .delete()
                .eq("owner", user_id)
                .eq("project_id", project_id)
                .execute()
            )
        except Exception as exc:
            raise ProjectsServiceError(f"Failed to prune cached files: {exc}") from exc

        return True

    def get_project_by_name(self, user_id: str, project_name: str) -> Optional[Dict[str, Any]]:
        """
        Fetch an existing project row by name.

        Returns the project record or None if not found.
        """
        try:
            response = (
                self.client.table("projects")
                .select("*")
                .eq("user_id", user_id)
                .eq("project_name", project_name)
                .limit(1)
                .execute()
            )
        except Exception as exc:
            raise ProjectsServiceError(f"Failed to load project: {exc}") from exc

        data = response.data or []
        return data[0] if data else None

    # --- Cached file metadata helpers -------------------------------------------------

    def get_cached_files(self, user_id: str, project_id: str) -> Dict[str, Dict[str, Any]]:
        """
        Return cached metadata for previously scanned files.

        The payload is a mapping of relative_path -> metadata dict so callers can
        decide whether a file needs to be reprocessed.
        """
        try:
            response = (
                self.client.table("scan_files")
                .select(
                    "relative_path, size_bytes, mime_type, sha256, metadata,"
                    " last_seen_modified_at, last_scanned_at"
                )
                .eq("owner", user_id)
                .eq("project_id", project_id)
                .execute()
            )
        except Exception as exc:
            raise ProjectsServiceError(f"Failed to load cached files: {exc}") from exc

        cached: Dict[str, Dict[str, Any]] = {}
        for row in response.data or []:
            path = row.get("relative_path")
            if not path:
                continue
            normalized = str(path).replace("\\", "/")
            cached[normalized] = {
                "size_bytes": row.get("size_bytes"),
                "mime_type": row.get("mime_type"),
                "sha256": row.get("sha256"),
                "metadata": row.get("metadata") or {},
                "last_seen_modified_at": row.get("last_seen_modified_at"),
                "last_scanned_at": row.get("last_scanned_at"),
            }
        return cached

    def upsert_cached_files(
        self,
        user_id: str,
        project_id: str,
        files: List[Dict[str, Any]],
    ) -> None:
        """
        Persist cached metadata for all files included in a scan.

        Args:
            user_id: Owner of the project
            project_id: Project identifier
            files: List of dictionaries with keys:
                - relative_path (str)
                - size_bytes (int)
                - mime_type (str)
                - sha256 (str | None)
                - metadata (dict)
                - last_seen_modified_at (datetime ISO string)
                - last_scanned_at (datetime ISO string)
        """
        if not files:
            return

        payload = []
        for entry in files:
            path = entry.get("relative_path")
            modified = entry.get("last_seen_modified_at")
            scanned = entry.get("last_scanned_at")
            if not path or not modified or not scanned:
                continue
            payload.append(
                {
                    "owner": user_id,
                    "project_id": project_id,
                    "relative_path": path,
                    "size_bytes": entry.get("size_bytes"),
                    "mime_type": entry.get("mime_type"),
                    "sha256": entry.get("sha256"),
                    "metadata": entry.get("metadata") or {},
                    "last_seen_modified_at": modified,
                    "last_scanned_at": scanned,
                }
            )

        if not payload:
            return

        try:
            self.client.table("scan_files").upsert(
                payload,
                on_conflict="project_id,relative_path",
            ).execute()
        except Exception as exc:
            raise ProjectsServiceError(f"Failed to upsert cached files: {exc}") from exc

    def delete_cached_files(
        self,
        user_id: str,
        project_id: str,
        relative_paths: List[str],
    ) -> None:
        """Delete cached file rows for a project."""
        if not relative_paths:
            return
        try:
            (
                self.client.table("scan_files")
                .delete()
                .eq("owner", user_id)
                .eq("project_id", project_id)
                .in_("relative_path", relative_paths)
                .execute()
            )
        except Exception as exc:
            raise ProjectsServiceError(f"Failed to delete cached files: {exc}") from exc
