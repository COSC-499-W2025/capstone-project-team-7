"""Service for managing project scan storage and retrieval."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
import json
import logging
import os
import uuid
import io

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
        
        # Lazy-load overrides service
        self._overrides_service = None
        
        try:
            self.client: Client = create_client(self.supabase_url, self.supabase_key)
        except Exception as exc:
            raise ProjectsServiceError(f"Failed to initialize Supabase client: {exc}") from exc
    
    def _get_overrides_service(self):
        """Get or create the ProjectOverridesService (lazy-loaded)."""
        if self._overrides_service is None:
            try:
                from .project_overrides_service import ProjectOverridesService
                self._overrides_service = ProjectOverridesService(
                    supabase_url=self.supabase_url,
                    supabase_key=self.supabase_key,
                    encryption_service=self._encryption,
                    encryption_required=False,
                )
            except Exception as exc:
                logging.getLogger(__name__).warning(f"Could not initialize overrides service: {exc}")
                self._overrides_service = False  # Cache the failure with a sentinel value
                return None
        
        # Check if it's the sentinel "failed" value
        if self._overrides_service is False:
            return None  # Skip re-initialization attempts
        
        return self._overrides_service
    
    @staticmethod
    def infer_role_from_contribution(scan_data: Dict[str, Any]) -> str:
        """
        Infer user's role based on contribution metrics.
        
        Returns:
            'author' if user has >= 80% of commits, otherwise 'contributor'
        """
        user_commit_share = scan_data.get("contribution_ranking", {}).get("user_commit_share")
        if user_commit_share is None:
            # Check contribution_metrics as fallback
            contribution_metrics = scan_data.get("contribution_metrics", {})
            if contribution_metrics:
                # Try to compute share from primary_contributor
                primary = contribution_metrics.get("primary_contributor")
                total_commits = contribution_metrics.get("total_commits", 0)
                if isinstance(primary, dict) and total_commits > 0:
                    primary_commits = primary.get("commits", 0)
                    user_commit_share = primary_commits / total_commits
        
        if user_commit_share is not None and user_commit_share >= 0.80:
            return "author"
        return "contributor"
    
    def save_scan(
        self,
        user_id: str,
        project_name: str,
        project_path: str,
        scan_data: Dict[str, Any],
        role: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Save or update a project scan.
        
        Args:
            user_id: User's UUID
            project_name: Name/identifier for this project
            project_path: Filesystem path that was scanned
            scan_data: Complete JSON export payload
            role: User's role in the project (optional - auto-inferred if not provided)
        
        Returns:
            Saved project record (includes 'role' field from overrides if available)
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
            
            saved_project = response.data[0]
            project_id = saved_project.get("id")
            
            # Auto-infer and save role to project_overrides if not already set
            if project_id:
                overrides_service = self._get_overrides_service()
                if overrides_service:
                    try:
                        # Check existing overrides
                        existing_overrides = overrides_service.get_overrides(user_id, project_id)
                        existing_role = existing_overrides.get("role") if existing_overrides else None
                        
                        # Determine role to save
                        role_to_save = role  # Use explicit role if provided
                        if not role_to_save and not existing_role:
                            # Auto-infer role only for new projects without existing role
                            role_to_save = self.infer_role_from_contribution(scan_data)
                        
                        if role_to_save:
                            overrides_service.upsert_overrides(
                                user_id=user_id,
                                project_id=project_id,
                                role=role_to_save,
                            )
                            saved_project["role"] = role_to_save
                        elif existing_role:
                            saved_project["role"] = existing_role
                    except Exception as role_exc:
                        # Don't fail the entire save if role update fails
                        logging.getLogger(__name__).warning(f"Failed to save role for project {project_id}: {role_exc}")
            
            return saved_project
            
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
                "primary_contributor, project_end_date, has_skills_progress, has_skills_analysis, has_document_analysis, "
                "thumbnail_url, created_at"
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
                    "primary_contributor, project_end_date, thumbnail_url, "
                    "created_at"
                ).eq("user_id", user_id).order("scan_timestamp", desc=True).execute()
                # Ensure callers can safely read the flag even if absent
                projects = response.data or []
                for project in projects:
                    project.setdefault("has_skills_progress", False)
                return projects
            raise ProjectsServiceError(f"Failed to get projects: {exc}") from exc
    
    def get_user_projects_with_roles(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Get all projects for a user with role information from overrides.
        
        Returns:
            List of project records including 'role' field from project_overrides
        """
        projects = self.get_user_projects(user_id)
        if not projects:
            return projects
        
        # Get all project IDs
        project_ids = [p.get("id") for p in projects if p.get("id")]
        
        # Fetch overrides for all projects in one query
        overrides_service = self._get_overrides_service()
        if overrides_service and project_ids:
            try:
                overrides_map = overrides_service.get_overrides_for_projects(user_id, project_ids)
                for project in projects:
                    pid = project.get("id")
                    if pid and pid in overrides_map:
                        project["role"] = overrides_map[pid].get("role")
                    else:
                        project["role"] = None
            except Exception as exc:
                logging.getLogger(__name__).warning(f"Failed to fetch overrides: {exc}")
                # Set role to None for all projects if overrides fetch fails
                for project in projects:
                    project["role"] = None
        else:
            for project in projects:
                project["role"] = None
        
        return projects

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
            Complete project record with scan_data and role, or None if not found
        """
        try:
            response = self.client.table("projects").select("*").eq(
                "user_id", user_id
            ).eq("id", project_id).execute()
            
            if not response.data:
                return None
            
            record = response.data[0]
            record["scan_data"] = self._decrypt_scan_data(record.get("scan_data"))
            
            # Fetch role from overrides
            overrides_service = self._get_overrides_service()
            if overrides_service:
                try:
                    overrides = overrides_service.get_overrides(user_id, project_id)
                    record["role"] = overrides.get("role") if overrides else None
                except Exception:
                    record["role"] = None
            else:
                record["role"] = None
            
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

    # --- Thumbnail management -------------------------------------------------

    def upload_thumbnail(self, image_path: str, project_id: str) -> Tuple[Optional[str], Optional[str]]:
        """Upload an image as a project thumbnail to Supabase storage.
        
        Args:
            image_path: Path to the local image file
            project_id: ID of the project to associate the thumbnail with
            
        Returns:
            Tuple of (public_url, error_message). If successful, public_url is set and error_message is None.
            If failed, public_url is None and error_message contains the error.
        """
        try:
            # Validate file size (5MB max to prevent DoS)
            MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB
            file_size = os.path.getsize(image_path)
            if file_size > MAX_FILE_SIZE:
                return None, f"File size exceeds 5MB limit (got {file_size / 1024 / 1024:.2f}MB)"
            
            # Use configurable bucket name from environment
            bucket_name = os.getenv("THUMBNAIL_BUCKET", "thumbnails")
            
            # Delete old thumbnail before uploading new one
            self._delete_old_thumbnail(project_id, bucket_name)
            
            # Convert image to JPG format
            file_name = f"public/{project_id}_{uuid.uuid4().hex[:8]}.jpg"
            jpg_data = self._convert_image_to_jpg(image_path)
            
            if jpg_data is None:
                return None, "Failed to convert image to JPG format"
            
            # Upload to Supabase storage
            file_options = {"content-type": "image/jpg", "upsert": "false"}
            result = self.client.storage.from_(bucket_name).upload(
                path=file_name,
                file=jpg_data,
                file_options=file_options
            )
            
            # Get the public URL
            public_url = self._get_thumbnail_public_url(bucket_name, file_name)
            
            return public_url, None
            
        except Exception as exc:
            error = f"{type(exc).__name__}: {exc}"
            logging.error(f"Thumbnail upload error: {error}")
            return None, error
    
    def update_project_thumbnail_url(self, project_id: str, thumbnail_url: str) -> Tuple[bool, Optional[str]]:
        """Update a project's thumbnail_url in the database.
        
        Args:
            project_id: ID of the project to update
            thumbnail_url: Public URL of the uploaded thumbnail
            
        Returns:
            Tuple of (success, error_message). If successful, (True, None).
            If failed, (False, error_message).
        """
        try:
            result = self.client.table("projects").update({
                "thumbnail_url": thumbnail_url
            }).eq("id", project_id).execute()
            
            return True, None
            
        except Exception as exc:
            error = f"{type(exc).__name__}: {exc}"
            logging.error(f"Database update error: {error}")
            return False, error
    
    def _convert_image_to_jpg(self, image_path: str) -> Optional[bytes]:
        """Convert an image file to JPG format.
        
        Args:
            image_path: Path to the image file
            
        Returns:
            JPG image data as bytes, or None if conversion failed
        """
        try:
            from PIL import Image
            
            img = Image.open(image_path)
            
            # Validate dimensions (4096x4096 max to prevent DoS)
            MAX_DIMENSION = 4096
            width, height = img.size
            if width > MAX_DIMENSION or height > MAX_DIMENSION:
                logging.error(f"Image dimensions exceed {MAX_DIMENSION}x{MAX_DIMENSION} (got {width}x{height})")
                return None
            
            # Convert to RGB if necessary
            if img.mode in ('RGBA', 'LA', 'P'):
                # Convert RGBA/LA/P to RGB
                background = Image.new('RGB', img.size, (255, 255, 255))
                if img.mode == 'P':
                    img = img.convert('RGBA')
                background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                img = background
            elif img.mode != 'RGB':
                img = img.convert('RGB')
            
            # Save as JPG to bytes
            jpg_buffer = io.BytesIO()
            img.save(jpg_buffer, format='JPEG', quality=85)
            return jpg_buffer.getvalue()
            
        except Exception as e:
            logging.error(f"Error converting image: {e}")
            return None
    
    def _get_thumbnail_public_url(self, bucket_name: str, file_name: str) -> str:
        """Get the public URL for an uploaded file.
        
        Args:
            bucket_name: Name of the storage bucket
            file_name: Name/path of the file in storage
            
        Returns:
            Public URL for the file
        """
        try:
            public_url_response = self.client.storage.from_(bucket_name).get_public_url(file_name)
            return public_url_response
        except Exception as url_exc:
            logging.warning(f"Error getting public URL: {url_exc}")
            # Fallback to manual construction with URL encoding
            from urllib.parse import quote
            encoded_bucket = quote(bucket_name)
            encoded_file = quote(file_name)
            return f"{self.supabase_url}/storage/v1/object/public/{encoded_bucket}/{encoded_file}"
    
    def _delete_old_thumbnail(self, project_id: str, bucket_name: str) -> None:
        """Delete existing thumbnail for a project before uploading a new one.
        
        Args:
            project_id: ID of the project
            bucket_name: Name of the storage bucket
        """
        try:
            # Get current thumbnail URL from database
            result = self.client.table("projects").select("thumbnail_url").eq("id", project_id).execute()
            
            if not result.data or not result.data[0].get("thumbnail_url"):
                return  # No existing thumbnail to delete
            
            thumbnail_url = result.data[0]["thumbnail_url"]
            
            # Extract file path from URL (format: .../storage/v1/object/public/bucket_name/file_path)
            if "/storage/v1/object/public/" in thumbnail_url:
                parts = thumbnail_url.split("/storage/v1/object/public/", 1)
                if len(parts) == 2:
                    # Remove bucket name prefix to get just the file path
                    path_with_bucket = parts[1]
                    if "/" in path_with_bucket:
                        file_path = path_with_bucket.split("/", 1)[1]
                        
                        # Delete the old thumbnail from storage
                        self.client.storage.from_(bucket_name).remove([file_path])
                        logging.info(f"Deleted old thumbnail: {file_path}")
        except Exception as exc:
            # Log but don't fail the upload if cleanup fails
            logging.warning(f"Failed to delete old thumbnail: {exc}")
