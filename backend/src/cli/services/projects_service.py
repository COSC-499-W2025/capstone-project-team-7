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
            response = self.client.table("projects").delete().eq(
                "user_id", user_id
            ).eq("id", project_id).execute()
            
            return len(response.data) > 0
            
        except Exception as exc:
            raise ProjectsServiceError(f"Failed to delete project: {exc}") from exc