"""Service for managing project scan storage and retrieval."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
import json
import logging

try:
    from supabase import Client, create_client
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False
    Client = None  # type: ignore
    def create_client(*args, **kwargs):  # type: ignore
        raise ImportError("supabase-py is not installed")


class ProjectsServiceError(Exception):
    """Base error for projects service."""


class ProjectsService:
    """Manage project scan storage in Supabase."""
    
    def __init__(
        self,
        supabase_url: Optional[str] = None,
        supabase_key: Optional[str] = None,
        *,
        encryption_service=None,
        encryption_required: bool = False,
    ):
        if not SUPABASE_AVAILABLE and not callable(create_client):
            raise ProjectsServiceError("Supabase client not available. Install supabase-py.")
        
        # Initialize Supabase client
        import os
        self.supabase_url = supabase_url or os.getenv("SUPABASE_URL")
        self.supabase_key = (
            supabase_key
            or os.getenv("SUPABASE_KEY")
            or os.getenv("SUPABASE_SERVICE_ROLE_KEY")
            or os.getenv("SUPABASE_ANON_KEY")
        )
        
        if not self.supabase_url or not self.supabase_key:
            raise ProjectsServiceError("Supabase credentials not configured.")

        self._encryption = encryption_service
        if self._encryption is None:
            try:
                from .encryption import EncryptionService  # local import to avoid hard dependency at import time
                self._encryption = EncryptionService()
            except Exception as exc:
                if encryption_required:
                    raise ProjectsServiceError(f"Encryption unavailable: {exc}") from exc
                self._encryption = None
        
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
                    for lang in lang_data:
                        if isinstance(lang, dict):
                            name = lang.get("name") or lang.get("language") or "Unknown"
                            if name and name != "Unknown":
                                languages.append(name)
                        elif isinstance(lang, str):
                            languages.append(lang)
                elif isinstance(lang_data, dict):
                    languages = list(lang_data.keys())
                
            record = {
                "user_id": user_id,
                "project_name": project_name,
                "project_path": project_path,
                "scan_data": self._encrypt_scan_data(scan_data),
                "scan_timestamp": datetime.now().isoformat(),
                "total_files": summary.get("files_processed", 0),
                "total_lines": scan_data.get("code_analysis", {}).get("metrics", {}).get("total_lines", 0),
                "languages": languages,
                "has_media_analysis": "media_analysis" in scan_data,
                "has_pdf_analysis": "pdf_analysis" in scan_data,
                "has_code_analysis": "code_analysis" in scan_data,
                "has_skills_analysis": "skills_analysis" in scan_data and scan_data.get("skills_analysis", {}).get("success"),
                "has_document_analysis": "document_analysis" in scan_data,
                "has_git_analysis": "git_analysis" in scan_data,
                "has_contribution_metrics": "contribution_metrics" in scan_data,
                "contribution_score": scan_data.get("contribution_ranking", {}).get("score"),
                "user_commit_share": scan_data.get("contribution_ranking", {}).get("user_commit_share"),
                "total_commits": scan_data.get("contribution_metrics", {}).get("total_commits"),
                "primary_contributor": (
                    (scan_data.get("contribution_metrics", {}).get("primary_contributor") or {}).get("name")
                    if isinstance(scan_data.get("contribution_metrics", {}).get("primary_contributor"), dict)
                    else None
                ),
                "project_end_date": scan_data.get("contribution_metrics", {}).get("project_end_date"),
                "has_skills_progress": bool(scan_data.get("skills_progress")),
            }
            
            # Upsert (insert or update if exists)
            try:
                response = self.client.table("projects").upsert(
                    record,
                    on_conflict="user_id,project_name"
                ).execute()
            except Exception as exc:
                # Backward compatibility: some databases may not have the has_skills_progress column yet.
                if "has_skills_progress" in str(exc):
                    record.pop("has_skills_progress", None)
                    response = self.client.table("projects").upsert(
                        record,
                        on_conflict="user_id,project_name"
                    ).execute()
                else:
                    raise
            
            if not response.data:
                raise ProjectsServiceError("Failed to save project scan")
            
            return response.data[0]
            
        except Exception as exc:
            raise ProjectsServiceError(f"Failed to save scan: {exc}") from exc
    
    def update_project_score(
        self,
        user_id: str,
        project_id: str,
        contribution_score: float,
        user_commit_share: float,
    ) -> Dict[str, Any]:
        """
        Update the contribution score for a project.
        
        Args:
            user_id: User's UUID
            project_id: Project's UUID
            contribution_score: Computed ranking score (0-100)
            user_commit_share: User's percentage of total commits
        
        Returns:
            Updated project record
        """
        try:
            response = self.client.table("projects").update({
                "contribution_score": contribution_score,
                "user_commit_share": user_commit_share,
            }).eq("id", project_id).eq("user_id", user_id).execute()
            
            if not response.data:
                raise ProjectsServiceError(f"Project {project_id} not found or not owned by user")
            
            return response.data[0]
            
        except Exception as exc:
            raise ProjectsServiceError(f"Failed to update project score: {exc}") from exc
    
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
                "has_contribution_metrics, contribution_score, user_commit_share, total_commits, "
                "primary_contributor, project_end_date, has_skills_progress, has_skills_analysis, has_document_analysis,"
                "created_at"
            ).eq("user_id", user_id).order("scan_timestamp", desc=True).execute()
            
            return response.data or []
            
        except Exception as exc:
            # Fall back if older schema does not include has_skills_progress
            if "has_skills_progress" in str(exc):
                response = self.client.table("projects").select(
                    "id, project_name, project_path, scan_timestamp, "
                    "total_files, total_lines, languages, "
                    "has_media_analysis, has_pdf_analysis, has_code_analysis, has_git_analysis, "
                    "has_contribution_metrics, contribution_score, user_commit_share, total_commits, "
                    "primary_contributor, project_end_date, "
                    "created_at"
                ).eq("user_id", user_id).order("scan_timestamp", desc=True).execute()
                # Ensure callers can safely read the flag even if absent
                projects = response.data or []
                for project in projects:
                    project.setdefault("has_skills_progress", False)
                return projects
            raise ProjectsServiceError(f"Failed to get projects: {exc}") from exc

    def get_user_projects_with_scan_data(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Get all projects for a user, including decrypted scan_data.

        Returns:
            List of project records with scan_data field.
        """
        try:
            response = (
                self.client.table("projects")
                .select("id, project_name, scan_timestamp, project_end_date, created_at, scan_data")
                .eq("user_id", user_id)
                .execute()
            )
        except Exception as exc:
            raise ProjectsServiceError(f"Failed to get projects with scan data: {exc}") from exc

        projects = response.data or []
        for project in projects:
            project["scan_data"] = self._decrypt_scan_data(project.get("scan_data"))
        return projects
    
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
            
            record = response.data[0]
            record["scan_data"] = self._decrypt_scan_data(record.get("scan_data"))
            return record
            
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
                "scan_data": {},
                "scan_timestamp": None,
                "total_files": 0,
                "total_lines": 0,
                "languages": [],
                "has_media_analysis": False,
                "has_pdf_analysis": False,
                "has_code_analysis": False,
                "has_skills_analysis": False,
                "has_document_analysis": False,
                "has_git_analysis": False,
                "has_contribution_metrics": False,
                "contribution_score": None,
                "user_commit_share": None,
                "total_commits": None,
                "primary_contributor": None,
                "project_end_date": None,
                "has_skills_progress": False,
                "insights_deleted_at": timestamp,
            }
            try:
                response = (
                    self.client.table("projects")
                    .update(update_fields)
                    .eq("user_id", user_id)
                    .eq("id", project_id)
                    .execute()
                )
            except Exception as exc:
                if "has_skills_progress" not in str(exc):
                    raise ProjectsServiceError(f"Failed to delete insights: {exc}") from exc
                # Retry without the missing column for backward compatibility
                update_fields.pop("has_skills_progress", None)
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
            # scan_files table may not exist in all environments (e.g., test database)
            # Log and continue rather than failing the whole operation
            logging.warning("Could not prune cached files (table may not exist): %s", exc)

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
        if not data:
            return None
        record = data[0]
        record["scan_data"] = self._decrypt_scan_data(record.get("scan_data"))
        return record

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
                "metadata": self._decrypt_cached_metadata(row.get("metadata")),
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
                    "metadata": self._encrypt_cached_metadata(entry.get("metadata")),
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

    # --- Encryption helpers -------------------------------------------------

    def _encrypt_scan_data(self, scan_data: Dict[str, Any]) -> Any:
        """Encrypt full scan payload when encryption is available."""
        if not self._encryption:
            return scan_data
        try:
            envelope = self._encryption.encrypt_json(scan_data)
            return envelope.to_dict()
        except Exception as exc:
            raise ProjectsServiceError(f"Failed to encrypt scan data: {exc}") from exc

    def _decrypt_scan_data(self, scan_data: Any) -> Any:
        """Attempt to decrypt scan_data; fall back to original on failure."""
        if not scan_data or not self._encryption:
            return scan_data
        if isinstance(scan_data, dict) and {"v", "iv", "ct"} <= set(scan_data.keys()):
            try:
                return self._encryption.decrypt_json(scan_data)
            except Exception as exc:
                logging.warning(
                    "Failed to decrypt scan_data for project, returning as-is: %s", exc
                )
                return scan_data
        return scan_data

    def _encrypt_cached_metadata(self, metadata: Optional[Dict[str, Any]]) -> Any:
        """Encrypt cached file metadata when available."""
        meta = metadata or {}
        if not self._encryption:
            return meta
        try:
            return self._encryption.encrypt_json(meta).to_dict()
        except Exception as exc:
            raise ProjectsServiceError(f"Failed to encrypt cached file metadata: {exc}") from exc

    def _decrypt_cached_metadata(self, metadata: Any) -> Dict[str, Any]:
        """Decrypt cached metadata envelope back into a dict."""
        if metadata is None:
            return {}
        if not self._encryption:
            return metadata if isinstance(metadata, dict) else {}
        if isinstance(metadata, dict) and {"v", "iv", "ct"} <= set(metadata.keys()):
            try:
                return self._encryption.decrypt_json(metadata) or {}
            except Exception as exc:
                logging.warning(
                    "Failed to decrypt cached file metadata, returning empty dict: %s", exc
                )
                return {}
        return metadata if isinstance(metadata, dict) else {}
