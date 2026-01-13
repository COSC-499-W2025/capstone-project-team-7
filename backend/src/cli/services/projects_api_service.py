"""Service for interacting with project ranking API endpoints."""
from __future__ import annotations

import os
import logging
from typing import Dict, List, Optional, Any
import httpx

logger = logging.getLogger(__name__)


class ProjectsAPIServiceError(Exception):
    """Base error for projects API service."""


class ProjectsAPIService:
    """Client for project ranking API endpoints."""
    
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
            raise ProjectsAPIServiceError("Authentication token is required")
        
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
            ProjectsAPIServiceError: If API call fails
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
            raise ProjectsAPIServiceError(
                f"Failed to rank project {project_id}: {exc.response.status_code} - {error_detail}"
            ) from exc
        except httpx.RequestError as exc:
            raise ProjectsAPIServiceError(
                f"Network error ranking project {project_id}: {exc}"
            ) from exc
        except Exception as exc:
            raise ProjectsAPIServiceError(
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
            ProjectsAPIServiceError: If API call fails
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
            raise ProjectsAPIServiceError(
                f"Failed to fetch top projects: {exc.response.status_code} - {error_detail}"
            ) from exc
        except httpx.RequestError as exc:
            raise ProjectsAPIServiceError(
                f"Network error fetching top projects: {exc}"
            ) from exc
        except Exception as exc:
            raise ProjectsAPIServiceError(
                f"Unexpected error fetching top projects: {exc}"
            ) from exc
    
    def get_project_timeline(self) -> Dict[str, Any]:
        """
        Get projects ordered chronologically by activity date.
        
        Returns:
            Dict with count and timeline entries (sorted by display_date)
            
        Raises:
            ProjectsAPIServiceError: If API call fails
        """
        url = f"{self.base_url}/api/projects/timeline"
        
        try:
            with httpx.Client(timeout=30.0) as client:
                response = client.get(url, headers=self.headers)
                response.raise_for_status()
                return response.json()
        except httpx.HTTPStatusError as exc:
            error_detail = exc.response.text
            raise ProjectsAPIServiceError(
                f"Failed to fetch project timeline: {exc.response.status_code} - {error_detail}"
            ) from exc
        except httpx.RequestError as exc:
            raise ProjectsAPIServiceError(
                f"Network error fetching project timeline: {exc}"
            ) from exc
        except Exception as exc:
            raise ProjectsAPIServiceError(
                f"Unexpected error fetching project timeline: {exc}"
            ) from exc
