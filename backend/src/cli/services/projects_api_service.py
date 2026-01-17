"""API-based service for managing project scan storage and retrieval."""
from __future__ import annotations

from typing import Dict, List, Optional, Any
import os
import logging

try:
    import httpx
    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False
    httpx = None  # type: ignore


class ProjectsServiceError(Exception):
    """Base error for projects service."""


class ProjectsAPIService:
    """
    Manage project scan storage via FastAPI REST endpoints.
    
    This service communicates with the FastAPI backend instead of directly
    accessing Supabase. It provides the same interface as ProjectsService
    for drop-in replacement.
    
    Usage:
        # In textual_app.py, replace:
        # self._projects_service = ProjectsService()
        # with:
        # self._projects_service = ProjectsAPIService()
    """
    
    def __init__(
        self,
        api_base_url: Optional[str] = None,
        access_token: Optional[str] = None,
        *,
        encryption_service=None,
        encryption_required: bool = False,
    ):
        """
        Initialize API-based projects service.
        
        Args:
            api_base_url: Base URL of FastAPI server (e.g., "http://127.0.0.1:8000")
                         Defaults to PORTFOLIO_API_URL env var or http://127.0.0.1:8000
            access_token: JWT access token for authentication
            encryption_service: Not used in API mode (server handles encryption)
            encryption_required: Not used in API mode
        """
        if not HTTPX_AVAILABLE:
            raise ProjectsServiceError(
                "httpx is required for API mode. Install with: pip install httpx"
            )
        
        self.api_base_url = (
            api_base_url 
            or os.getenv("PORTFOLIO_API_URL") 
            or "http://127.0.0.1:8000"
        ).rstrip("/")
        
        self._access_token = access_token
        self.client = httpx.Client(timeout=30.0)
        self.logger = logging.getLogger(__name__)
        
        # Test connection on initialization
        try:
            response = self.client.get(f"{self.api_base_url}/health", timeout=5.0)
            if response.status_code != 200:
                self.logger.warning(f"API server health check failed: {response.status_code}")
        except Exception as exc:
            raise ProjectsServiceError(
                f"Cannot connect to API server at {self.api_base_url}. "
                f"Ensure FastAPI server is running. Error: {exc}"
            ) from exc
    
    def set_access_token(self, token: Optional[str]) -> None:
        """Update the JWT access token for authenticated requests."""
        self._access_token = token
    
    def _get_headers(self) -> Dict[str, str]:
        """Build request headers with authentication."""
        headers = {"Content-Type": "application/json"}
        if self._access_token:
            headers["Authorization"] = f"Bearer {self._access_token}"
        return headers
    
    def _handle_error_response(self, response: httpx.Response, operation: str) -> None:
        """Parse and raise appropriate errors from API responses."""
        try:
            error_data = response.json()
            detail = error_data.get("detail", response.text)
        except Exception:
            detail = response.text or f"HTTP {response.status_code}"
        
        if response.status_code == 401:
            raise ProjectsServiceError(
                f"Authentication failed for {operation}. "
                f"Token may be expired or invalid: {detail}"
            )
        elif response.status_code == 404:
            raise ProjectsServiceError(f"Resource not found for {operation}: {detail}")
        elif response.status_code == 400:
            raise ProjectsServiceError(f"Invalid request for {operation}: {detail}")
        else:
            raise ProjectsServiceError(
                f"API error during {operation} (HTTP {response.status_code}): {detail}"
            )
    
    def save_scan(
        self,
        user_id: str,
        project_name: str,
        project_path: str,
        scan_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Save or update a project scan via API.
        
        Args:
            user_id: User's UUID (extracted from JWT by API, but kept for interface compatibility)
            project_name: Name/identifier for this project
            project_path: Filesystem path that was scanned
            scan_data: Complete JSON export payload
        
        Returns:
            Saved project record
        """
        try:
            payload = {
                "project_name": project_name,
                "project_path": project_path,
                "scan_data": scan_data,
            }
            
            response = self.client.post(
                f"{self.api_base_url}/api/projects",
                json=payload,
                headers=self._get_headers(),
            )
            
            if response.status_code == 201:
                result = response.json()
                # Return format compatible with Supabase version
                return {
                    "id": result.get("id"),
                    "project_name": result.get("project_name"),
                    "scan_timestamp": result.get("scan_timestamp"),
                }
            else:
                self._handle_error_response(response, "save_scan")
                
        except httpx.HTTPError as exc:
            raise ProjectsServiceError(f"Network error saving scan: {exc}") from exc
        except ProjectsServiceError:
            raise
        except Exception as exc:
            raise ProjectsServiceError(f"Failed to save scan: {exc}") from exc
    
    def get_user_projects(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Get all projects for authenticated user via API.
        
        Args:
            user_id: User's UUID (extracted from JWT by API, kept for interface compatibility)
        
        Returns:
            List of project records (without full scan_data)
        """
        try:
            response = self.client.get(
                f"{self.api_base_url}/api/projects",
                headers=self._get_headers(),
            )
            
            if response.status_code == 200:
                data = response.json()
                # API returns {"count": N, "projects": [...]}
                projects = data.get("projects", [])
                return projects
            else:
                self._handle_error_response(response, "get_user_projects")
                
        except httpx.HTTPError as exc:
            raise ProjectsServiceError(f"Network error getting projects: {exc}") from exc
        except ProjectsServiceError:
            raise
        except Exception as exc:
            raise ProjectsServiceError(f"Failed to get projects: {exc}") from exc
    
    def get_project_scan(self, user_id: str, project_id: str) -> Optional[Dict[str, Any]]:
        """
        Get full scan data for a specific project via API.
        
        Args:
            user_id: User's UUID (extracted from JWT by API, kept for interface compatibility)
            project_id: Project's UUID
        
        Returns:
            Complete project record with scan_data, or None if not found
        """
        try:
            response = self.client.get(
                f"{self.api_base_url}/api/projects/{project_id}",
                headers=self._get_headers(),
            )
            
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 404:
                return None
            else:
                self._handle_error_response(response, "get_project_scan")
                
        except httpx.HTTPError as exc:
            raise ProjectsServiceError(f"Network error getting project: {exc}") from exc
        except ProjectsServiceError:
            raise
        except Exception as exc:
            raise ProjectsServiceError(f"Failed to get project scan: {exc}") from exc
    
    def get_dedup_report(self, project_id: str) -> Dict[str, Any]:
        """Fetch the deduplication report for a project via API."""
        try:
            response = self.client.get(
                f"{self.api_base_url}/api/dedup",
                params={"project_id": project_id},
                headers=self._get_headers(),
            )

            if response.status_code == 200:
                data = response.json()
                return data if isinstance(data, dict) else {}
            else:
                self._handle_error_response(response, "get_dedup_report")

        except httpx.HTTPError as exc:
            raise ProjectsServiceError(f"Network error getting dedup report: {exc}") from exc
        except ProjectsServiceError:
            raise
        except Exception as exc:
            raise ProjectsServiceError(f"Failed to get dedup report: {exc}") from exc

    def delete_project(self, user_id: str, project_id: str) -> bool:
        """
        Delete a project scan via API.
        
        Args:
            user_id: User's UUID (extracted from JWT by API, kept for interface compatibility)
            project_id: Project's UUID
        
        Returns:
            True if deleted successfully, False if not found
        """
        try:
            response = self.client.delete(
                f"{self.api_base_url}/api/projects/{project_id}",
                headers=self._get_headers(),
            )
            
            if response.status_code == 204:
                return True
            elif response.status_code == 404:
                return False
            else:
                self._handle_error_response(response, "delete_project")
                
        except httpx.HTTPError as exc:
            raise ProjectsServiceError(f"Network error deleting project: {exc}") from exc
        except ProjectsServiceError:
            raise
        except Exception as exc:
            raise ProjectsServiceError(f"Failed to delete project: {exc}") from exc
    
    def delete_project_insights(self, user_id: str, project_id: str) -> bool:
        """
        Clear stored scan insights for a project via API.

        Args:
            user_id: User's UUID (extracted from JWT by API, kept for interface compatibility)
            project_id: Project's UUID

        Returns:
            True if insights cleared successfully, False if project not found
        """
        try:
            response = self.client.delete(
                f"{self.api_base_url}/api/projects/{project_id}/insights",
                headers=self._get_headers(),
            )

            if response.status_code == 200:
                return True
            elif response.status_code == 404:
                return False
            else:
                self._handle_error_response(response, "delete_project_insights")
                return False

        except httpx.HTTPError as exc:
            raise ProjectsServiceError(f"Network error clearing insights: {exc}") from exc
        except ProjectsServiceError:
            raise
        except Exception as exc:
            raise ProjectsServiceError(f"Failed to clear project insights: {exc}") from exc
    
    def get_project_by_name(self, user_id: str, project_name: str) -> Optional[Dict[str, Any]]:
        """
        Fetch an existing project by name.
        
        Note: This requires fetching all projects and filtering client-side
        since the API doesn't have a by-name endpoint yet.
        Consider adding GET /api/projects?name=... query parameter.
        """
        try:
            projects = self.get_user_projects(user_id)
            for project in projects:
                if project.get("project_name") == project_name:
                    # Fetch full details
                    return self.get_project_scan(user_id, project["id"])
            return None
        except Exception as exc:
            raise ProjectsServiceError(f"Failed to get project by name: {exc}") from exc
    
    def upload_thumbnail(self, image_path: str, project_id: str) -> tuple[Optional[str], Optional[str]]:
        """
        Upload a thumbnail image for a project via API.
        
        Args:
            image_path: Local filesystem path to the image file
            project_id: Project's UUID
        
        Returns:
            Tuple of (thumbnail_url, error_message)
            On success: (url, None)
            On failure: (None, error_message)
        """
        try:
            # Open the image file
            with open(image_path, 'rb') as f:
                files = {'file': (os.path.basename(image_path), f, 'image/*')}
                
                # Build headers without Content-Type (httpx sets it automatically for multipart)
                headers = {}
                if self._access_token:
                    headers["Authorization"] = f"Bearer {self._access_token}"
                
                # POST multipart/form-data to thumbnail upload endpoint
                response = self.client.post(
                    f"{self.api_base_url}/api/projects/{project_id}/thumbnail",
                    files=files,
                    headers=headers,
                )
            
            if response.status_code == 200:
                result = response.json()
                return result.get("thumbnail_url"), None
            else:
                self._handle_error_response(response, "upload_thumbnail")
                
        except FileNotFoundError:
            return None, f"Image file not found: {image_path}"
        except httpx.HTTPError as exc:
            return None, f"Network error uploading thumbnail: {exc}"
        except ProjectsServiceError as exc:
            return None, str(exc)
        except Exception as exc:
            return None, f"Failed to upload thumbnail: {exc}"
    
    def update_project_thumbnail_url(self, project_id: str, thumbnail_url: str) -> tuple[bool, Optional[str]]:
        """
        Update the thumbnail URL for a project via API.
        
        Args:
            project_id: Project's UUID
            thumbnail_url: Public URL of the thumbnail image
        
        Returns:
            Tuple of (success, error_message)
            On success: (True, None)
            On failure: (False, error_message)
        """
        try:
            payload = {"thumbnail_url": thumbnail_url}
            
            response = self.client.patch(
                f"{self.api_base_url}/api/projects/{project_id}/thumbnail",
                json=payload,
                headers=self._get_headers(),
            )
            
            if response.status_code == 200:
                return True, None
            else:
                self._handle_error_response(response, "update_thumbnail_url")
                
        except httpx.HTTPError as exc:
            return False, f"Network error updating thumbnail URL: {exc}"
        except ProjectsServiceError as exc:
            return False, str(exc)
        except Exception as exc:
            return False, f"Failed to update thumbnail URL: {exc}"
    
    def close(self) -> None:
        """Close the HTTP client."""
        if self.client:
            self.client.close()
    
    def __del__(self):
        """Cleanup on deletion."""
        try:
            self.close()
        except Exception:
            pass


# ============================================================================
# Project Ranking API Service
# ============================================================================

class ProjectsRankingAPIServiceError(Exception):
    """Base error for projects ranking API service."""


class ProjectsRankingAPIService:
    """Client for project ranking API endpoints (rank, top, timeline)."""
    
    def __init__(
        self,
        base_url: Optional[str] = None,
        auth_token: Optional[str] = None,
    ):
        """
        Initialize the API service client.
        
        Args:
            base_url: Base URL for the API (e.g., "http://localhost:8000")
            auth_token: JWT Bearer token for authentication
        """
        self.base_url = base_url or os.getenv("API_BASE_URL", "http://localhost:8000")
        self.auth_token = auth_token
        
        if not self.auth_token:
            raise ProjectsRankingAPIServiceError("Authentication token is required")
        
        self.headers = {
            "Authorization": f"Bearer {self.auth_token}",
            "Content-Type": "application/json",
        }
    
    def rank_project(
        self,
        project_id: str,
        user_email: Optional[str] = None,
        user_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Calculate ranking score for a specific project.
        
        Args:
            project_id: UUID of the project to rank
            user_email: Optional user email for contribution matching
            user_name: Optional user name for contribution matching
        
        Returns:
            Dict with score, components, and ranking reasons
            
        Raises:
            ProjectsRankingAPIServiceError: If API call fails
        """
        url = f"{self.base_url}/api/projects/{project_id}/rank"
        
        payload = {}
        if user_email:
            payload["user_email"] = user_email
        if user_name:
            payload["user_name"] = user_name
        
        logger.info(f"Calling rank API: POST {url}")
        logger.info(f"Token present: {bool(self.auth_token)}, Token length: {len(self.auth_token) if self.auth_token else 0}")
        
        try:
            with httpx.Client(timeout=30.0) as client:
                response = client.post(url, json=payload, headers=self.headers)
                response.raise_for_status()
                return response.json()
        except httpx.HTTPStatusError as exc:
            error_detail = exc.response.text
            logger.error(f"Rank API failed: {exc.response.status_code} - {error_detail}")
            raise ProjectsRankingAPIServiceError(
                f"Failed to rank project {project_id}: {exc.response.status_code} - {error_detail}"
            ) from exc
        except httpx.RequestError as exc:
            raise ProjectsRankingAPIServiceError(
                f"Network error ranking project {project_id}: {exc}"
            ) from exc
        except Exception as exc:
            raise ProjectsRankingAPIServiceError(
                f"Unexpected error ranking project {project_id}: {exc}"
            ) from exc
    
    def get_top_projects(self, limit: int = 10) -> Dict[str, Any]:
        """
        Get top-ranked projects sorted by contribution score.
        
        Args:
            limit: Maximum number of projects to return (default: 10)
        
        Returns:
            Dict with count and list of top projects
            
        Raises:
            ProjectsRankingAPIServiceError: If API call fails
        """
        url = f"{self.base_url}/api/projects/top"
        params = {"limit": limit}
        
        try:
            with httpx.Client(timeout=30.0) as client:
                response = client.get(url, params=params, headers=self.headers)
                response.raise_for_status()
                return response.json()
        except httpx.HTTPStatusError as exc:
            error_detail = exc.response.text
            raise ProjectsRankingAPIServiceError(
                f"Failed to fetch top projects: {exc.response.status_code} - {error_detail}"
            ) from exc
        except httpx.RequestError as exc:
            raise ProjectsRankingAPIServiceError(
                f"Network error fetching top projects: {exc}"
            ) from exc
        except Exception as exc:
            raise ProjectsRankingAPIServiceError(
                f"Unexpected error fetching top projects: {exc}"
            ) from exc
    
    def get_project_timeline(self) -> Dict[str, Any]:
        """
        Get projects ordered chronologically by activity date.
        
        Returns:
            Dict with count and timeline entries (sorted by display_date)
            
        Raises:
            ProjectsRankingAPIServiceError: If API call fails
        """
        url = f"{self.base_url}/api/projects/timeline"
        
        try:
            with httpx.Client(timeout=30.0) as client:
                response = client.get(url, headers=self.headers)
                response.raise_for_status()
                return response.json()
        except httpx.HTTPStatusError as exc:
            error_detail = exc.response.text
            raise ProjectsRankingAPIServiceError(
                f"Failed to fetch project timeline: {exc.response.status_code} - {error_detail}"
            ) from exc
        except httpx.RequestError as exc:
            raise ProjectsRankingAPIServiceError(
                f"Network error fetching project timeline: {exc}"
            ) from exc
        except Exception as exc:
            raise ProjectsRankingAPIServiceError(
                f"Unexpected error fetching project timeline: {exc}"
            ) from exc
