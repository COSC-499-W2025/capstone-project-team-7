"""API-based service for resume item CRUD."""
from __future__ import annotations

from typing import Any, Dict, List, Optional
import logging
import os

try:
    import httpx
    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False
    httpx = None  # type: ignore

from .resume_storage_service import ResumeStorageError

try:
    from .resume_generation_service import ResumeItem
except Exception:  # pragma: no cover - typing/optional imports
    ResumeItem = Any  # type: ignore


class ResumeAPIService:
    """Manage resume items via FastAPI endpoints."""

    def __init__(
        self,
        api_base_url: Optional[str] = None,
        access_token: Optional[str] = None,
    ) -> None:
        if not HTTPX_AVAILABLE:
            raise ResumeStorageError(
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

        try:
            response = self.client.get(f"{self.api_base_url}/health", timeout=5.0)
            if response.status_code != 200:
                self.logger.warning("API server health check failed: %s", response.status_code)
        except Exception as exc:
            raise ResumeStorageError(
                f"Cannot connect to API server at {self.api_base_url}. "
                f"Ensure FastAPI server is running. Error: {exc}"
            ) from exc

    def set_access_token(self, token: Optional[str]) -> None:
        """Update the JWT access token for authenticated requests."""
        self._access_token = token

    def apply_access_token(self, token: Optional[str]) -> None:
        """Alias used by the Supabase-backed service."""
        self.set_access_token(token)

    def _get_headers(self) -> Dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self._access_token:
            headers["Authorization"] = f"Bearer {self._access_token}"
        return headers

    def _handle_error_response(self, response: httpx.Response, operation: str) -> None:
        try:
            error_data = response.json()
            detail = error_data.get("detail", error_data)
            if isinstance(detail, dict):
                message = detail.get("message", response.text)
                code = detail.get("code", "unknown_error")
            else:
                message = str(detail) or response.text
                code = "unknown_error"
        except Exception:
            message = response.text or f"HTTP {response.status_code}"
            code = "unknown_error"

        if response.status_code == 401:
            raise ResumeStorageError(
                f"Authentication failed for {operation}: {message}"
            )
        if response.status_code in (400, 422):
            raise ResumeStorageError(
                f"Invalid request for {operation} ({code}): {message}"
            )
        if response.status_code == 404:
            raise ResumeStorageError(f"Resource not found for {operation}: {message}")
        raise ResumeStorageError(
            f"API error during {operation} (HTTP {response.status_code}): {message}"
        )

    def save_resume_item(
        self,
        user_id: str,
        resume_item: "ResumeItem",
        *,
        metadata: Optional[Dict[str, Any]] = None,
        target_path: Optional[Any] = None,
    ) -> Dict[str, Any]:
        if not user_id:
            raise ResumeStorageError("User ID is required to save a resume.")

        source_path = None
        if target_path is not None:
            source_path = str(target_path)
        elif getattr(resume_item, "output_path", None) is not None:
            source_path = str(resume_item.output_path)

        payload = {
            "project_name": resume_item.project_name,
            "start_date": resume_item.start_date,
            "end_date": resume_item.end_date,
            "overview": resume_item.overview,
            "content": resume_item.to_markdown(),
            "bullets": list(resume_item.bullets),
            "metadata": {
                **(metadata or {}),
                "ai_generated": getattr(resume_item, "ai_generated", False),
            },
            "source_path": source_path,
        }

        try:
            response = self.client.post(
                f"{self.api_base_url}/api/resume/items",
                json=payload,
                headers=self._get_headers(),
            )
            if response.status_code == 200:
                return response.json()
            self._handle_error_response(response, "save_resume_item")
        except ResumeStorageError:
            raise
        except httpx.HTTPError as exc:
            raise ResumeStorageError(f"Network error saving resume: {exc}") from exc
        except Exception as exc:
            raise ResumeStorageError(f"Failed to save resume: {exc}") from exc

    def save_resume_record(
        self,
        user_id: str,
        *,
        project_name: str,
        start_date: Optional[str],
        end_date: Optional[str],
        content: str,
        bullets: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        source_path: Optional[str] = None,
        overview: Optional[str] = None,
    ) -> Dict[str, Any]:
        if not user_id:
            raise ResumeStorageError("User ID is required to save a resume.")
        if not project_name:
            raise ResumeStorageError("Project name is required to save a resume.")
        if not content:
            raise ResumeStorageError("Resume content is required to save a resume.")

        payload = {
            "project_name": project_name,
            "start_date": start_date,
            "end_date": end_date,
            "overview": overview,
            "content": content,
            "bullets": bullets or [],
            "metadata": metadata or {},
            "source_path": source_path,
        }

        try:
            response = self.client.post(
                f"{self.api_base_url}/api/resume/items",
                json=payload,
                headers=self._get_headers(),
            )
            if response.status_code == 200:
                return response.json()
            self._handle_error_response(response, "save_resume_record")
        except ResumeStorageError:
            raise
        except httpx.HTTPError as exc:
            raise ResumeStorageError(f"Network error saving resume: {exc}") from exc
        except Exception as exc:
            raise ResumeStorageError(f"Failed to save resume: {exc}") from exc

    def get_user_resumes(self, user_id: str) -> List[Dict[str, Any]]:
        if not user_id:
            raise ResumeStorageError("User ID is required to load resumes.")

        try:
            response = self.client.get(
                f"{self.api_base_url}/api/resume/items",
                headers=self._get_headers(),
            )
            if response.status_code == 200:
                data = response.json()
                return data.get("items", [])
            self._handle_error_response(response, "get_user_resumes")
        except ResumeStorageError:
            raise
        except httpx.HTTPError as exc:
            raise ResumeStorageError(f"Network error loading resumes: {exc}") from exc
        except Exception as exc:
            raise ResumeStorageError(f"Failed to load resumes: {exc}") from exc

    def get_resume_item(self, user_id: str, resume_id: str) -> Optional[Dict[str, Any]]:
        if not user_id or not resume_id:
            raise ResumeStorageError("User ID and resume ID are required to load resumes.")

        try:
            response = self.client.get(
                f"{self.api_base_url}/api/resume/items/{resume_id}",
                headers=self._get_headers(),
            )
            if response.status_code == 200:
                return response.json()
            if response.status_code == 404:
                return None
            self._handle_error_response(response, "get_resume_item")
        except ResumeStorageError:
            raise
        except httpx.HTTPError as exc:
            raise ResumeStorageError(f"Network error loading resume: {exc}") from exc
        except Exception as exc:
            raise ResumeStorageError(f"Failed to load resume: {exc}") from exc
        return None

    def delete_resume_item(self, user_id: str, resume_id: str) -> bool:
        if not user_id or not resume_id:
            raise ResumeStorageError("User ID and resume ID are required to delete resumes.")

        try:
            response = self.client.delete(
                f"{self.api_base_url}/api/resume/items/{resume_id}",
                headers=self._get_headers(),
            )
            if response.status_code == 204:
                return True
            if response.status_code == 404:
                return False
            self._handle_error_response(response, "delete_resume_item")
        except ResumeStorageError:
            raise
        except httpx.HTTPError as exc:
            raise ResumeStorageError(f"Network error deleting resume: {exc}") from exc
        except Exception as exc:
            raise ResumeStorageError(f"Failed to delete resume: {exc}") from exc
        return False

    def update_resume_item(
        self,
        user_id: str,
        resume_id: str,
        *,
        project_name: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        content: Optional[str] = None,
        bullets: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        source_path: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        if not user_id or not resume_id:
            raise ResumeStorageError("User ID and resume ID are required to update resumes.")

        payload: Dict[str, Any] = {
            "project_name": project_name,
            "start_date": start_date,
            "end_date": end_date,
            "content": content,
            "bullets": bullets,
            "metadata": metadata,
            "source_path": source_path,
        }
        payload = {key: value for key, value in payload.items() if value is not None}

        try:
            response = self.client.patch(
                f"{self.api_base_url}/api/resume/items/{resume_id}",
                json=payload,
                headers=self._get_headers(),
            )
            if response.status_code == 200:
                return response.json()
            if response.status_code == 404:
                return None
            self._handle_error_response(response, "update_resume_item")
        except ResumeStorageError:
            raise
        except httpx.HTTPError as exc:
            raise ResumeStorageError(f"Network error updating resume: {exc}") from exc
        except Exception as exc:
            raise ResumeStorageError(f"Failed to update resume: {exc}") from exc
        return None
