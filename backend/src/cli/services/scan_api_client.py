"""HTTP client for the One-Shot Scan API.

This service provides methods to interact with the scan API endpoints:
- POST /api/scans - Start a new scan job
- GET /api/scans/{scan_id} - Poll scan status

The API runs scans in the background and returns immediately with a scan_id
that can be polled for progress and results.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)


class ScanJobState(str, Enum):
    """Possible states for a scan job."""
    queued = "queued"
    running = "running"
    succeeded = "succeeded"
    failed = "failed"
    canceled = "canceled"


@dataclass
class ScanProgress:
    """Progress information for a running scan."""
    percent: float
    message: Optional[str] = None


@dataclass
class ScanError:
    """Error information for a failed scan."""
    code: str
    message: str
    details: Optional[Dict[str, Any]] = None


@dataclass
class ScanStatusResponse:
    """Response from GET /api/scans/{scan_id}."""
    scan_id: str
    state: ScanJobState
    progress: Optional[ScanProgress] = None
    error: Optional[ScanError] = None
    result: Optional[Dict[str, Any]] = None
    project_id: Optional[str] = None
    upload_id: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ScanStatusResponse":
        """Create from API response dictionary."""
        progress = None
        if data.get("progress"):
            progress = ScanProgress(
                percent=data["progress"].get("percent", 0.0),
                message=data["progress"].get("message"),
            )

        error = None
        if data.get("error"):
            error = ScanError(
                code=data["error"].get("code", "UNKNOWN"),
                message=data["error"].get("message", "Unknown error"),
                details=data["error"].get("details"),
            )

        return cls(
            scan_id=data["scan_id"],
            state=ScanJobState(data["state"]),
            progress=progress,
            error=error,
            result=data.get("result"),
            project_id=data.get("project_id"),
            upload_id=data.get("upload_id"),
        )

    @property
    def is_complete(self) -> bool:
        """Check if the scan has finished (succeeded or failed)."""
        return self.state in (ScanJobState.succeeded, ScanJobState.failed, ScanJobState.canceled)

    @property
    def is_successful(self) -> bool:
        """Check if the scan completed successfully."""
        return self.state == ScanJobState.succeeded


class ScanApiClientError(Exception):
    """Base exception for scan API client errors."""
    pass


class ScanApiConnectionError(ScanApiClientError):
    """Raised when unable to connect to the API."""
    pass


class ScanApiRequestError(ScanApiClientError):
    """Raised when the API returns an error response."""
    def __init__(self, message: str, status_code: int, detail: Optional[str] = None):
        super().__init__(message)
        self.status_code = status_code
        self.detail = detail


class ScanApiClient:
    """HTTP client for the One-Shot Scan API.

    Example usage:
        client = ScanApiClient("http://localhost:8000")

        # Start a scan
        scan_id = client.start_scan("/path/to/project", relevance_only=True)

        # Poll for completion
        while True:
            status = client.get_scan_status(scan_id)
            if status.is_complete:
                break
            time.sleep(0.5)

        if status.is_successful:
            print(status.result)
    """

    DEFAULT_TIMEOUT = 30.0  # seconds

    def __init__(
        self,
        base_url: Optional[str] = None,
        timeout: float = DEFAULT_TIMEOUT,
    ):
        """Initialize the scan API client.

        Args:
            base_url: Base URL of the API server. Defaults to SCAN_API_URL env var
                     or http://localhost:8000.
            timeout: Request timeout in seconds.
        """
        self.base_url = (
            base_url
            or os.environ.get("SCAN_API_URL")
            or "http://localhost:8000"
        ).rstrip("/")
        self.timeout = timeout
        self._client: Optional[httpx.Client] = None

    def _get_client(self) -> httpx.Client:
        """Get or create the HTTP client."""
        if self._client is None:
            self._client = httpx.Client(
                base_url=self.base_url,
                timeout=self.timeout,
            )
        return self._client

    def close(self) -> None:
        """Close the HTTP client."""
        if self._client is not None:
            self._client.close()
            self._client = None

    def __enter__(self) -> "ScanApiClient":
        return self

    def __exit__(self, *args) -> None:
        self.close()

    def start_scan(
        self,
        source_path: str,
        *,
        relevance_only: bool = False,
        persist_project: bool = True,
        profile_id: Optional[str] = None,
        use_llm: bool = False,
        llm_media: bool = False,
        idempotency_key: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> str:
        """Start a new scan job.

        Args:
            source_path: Path to the directory or file to scan.
            relevance_only: If True, only scan relevant files based on profile.
            persist_project: If True, save the scan results to the database.
            profile_id: Optional profile ID for scan preferences.
            use_llm: If True, use LLM for enhanced analysis.
            llm_media: If True, use LLM for media file analysis.
            idempotency_key: Optional key for idempotent requests.
            user_id: Optional user ID for user isolation.

        Returns:
            The scan_id for polling status.

        Raises:
            ScanApiConnectionError: If unable to connect to the API.
            ScanApiRequestError: If the API returns an error response.
        """
        payload = {
            "source_path": source_path,
            "relevance_only": relevance_only,
            "persist_project": persist_project,
            "use_llm": use_llm,
            "llm_media": llm_media,
        }
        if profile_id:
            payload["profile_id"] = profile_id

        headers = {}
        if idempotency_key:
            headers["idempotency-key"] = idempotency_key
        if user_id:
            headers["x-user-id"] = user_id

        try:
            response = self._get_client().post(
                "/api/scans",
                json=payload,
                headers=headers,
            )
        except httpx.ConnectError as exc:
            raise ScanApiConnectionError(
                f"Unable to connect to scan API at {self.base_url}: {exc}"
            ) from exc
        except httpx.TimeoutException as exc:
            raise ScanApiConnectionError(
                f"Request to scan API timed out: {exc}"
            ) from exc

        if response.status_code == 202:
            data = response.json()
            return data["scan_id"]

        # Handle error responses
        detail = None
        try:
            error_data = response.json()
            detail = error_data.get("detail")
        except Exception:
            pass

        raise ScanApiRequestError(
            f"Failed to start scan: HTTP {response.status_code}",
            status_code=response.status_code,
            detail=detail,
        )

    def get_scan_status(self, scan_id: str, user_id: Optional[str] = None) -> ScanStatusResponse:
        """Get the current status of a scan job.

        Args:
            scan_id: The scan ID returned from start_scan().
            user_id: Optional user ID for user isolation.

        Returns:
            ScanStatusResponse with current state, progress, and results.

        Raises:
            ScanApiConnectionError: If unable to connect to the API.
            ScanApiRequestError: If the API returns an error response.
        """
        headers = {}
        if user_id:
            headers["x-user-id"] = user_id

        try:
            response = self._get_client().get(
                f"/api/scans/{scan_id}",
                headers=headers,
            )
        except httpx.ConnectError as exc:
            raise ScanApiConnectionError(
                f"Unable to connect to scan API at {self.base_url}: {exc}"
            ) from exc
        except httpx.TimeoutException as exc:
            raise ScanApiConnectionError(
                f"Request to scan API timed out: {exc}"
            ) from exc

        if response.status_code == 200:
            return ScanStatusResponse.from_dict(response.json())

        if response.status_code == 404:
            raise ScanApiRequestError(
                f"Scan not found: {scan_id}",
                status_code=404,
            )

        # Handle other error responses
        detail = None
        try:
            error_data = response.json()
            detail = error_data.get("detail")
        except Exception:
            pass

        raise ScanApiRequestError(
            f"Failed to get scan status: HTTP {response.status_code}",
            status_code=response.status_code,
            detail=detail,
        )

    def poll_until_complete(
        self,
        scan_id: str,
        *,
        poll_interval: float = 0.5,
        progress_callback: Optional[Callable[[ScanStatusResponse], None]] = None,
        user_id: Optional[str] = None,
    ) -> ScanStatusResponse:
        """Poll the scan status until it completes.

        Args:
            scan_id: The scan ID to poll.
            poll_interval: Time in seconds between polls.
            progress_callback: Optional callback called on each poll with current status.
            user_id: Optional user ID for user isolation.

        Returns:
            Final ScanStatusResponse when scan completes.
        """
        import time

        while True:
            status = self.get_scan_status(scan_id, user_id=user_id)

            if progress_callback:
                try:
                    progress_callback(status)
                except Exception:
                    pass

            if status.is_complete:
                return status

            time.sleep(poll_interval)
