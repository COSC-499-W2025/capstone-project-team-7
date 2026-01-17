"""Tests for the Scan API Client (scan_api_client.py).

These tests verify the HTTP client for the One-Shot Scan API:
- ScanApiClient initialization and configuration
- start_scan() method for POST /api/scans
- get_scan_status() method for GET /api/scans/{scan_id}
- Error handling for connection and request failures
- Response parsing and data class conversions
"""

import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

import pytest

# Ensure backend/src is on path for imports
PROJECT_ROOT = Path(__file__).parent.parent.parent
BACKEND_SRC = PROJECT_ROOT / "backend" / "src"
sys.path.insert(0, str(BACKEND_SRC))
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

# Import the module under test
from src.cli.services.scan_api_client import (
    ScanApiClient,
    ScanApiClientError,
    ScanApiConnectionError,
    ScanApiRequestError,
    ScanStatusResponse,
    ScanJobState,
    ScanProgress,
    ScanError,
)


class TestScanApiClientInit:
    """Tests for ScanApiClient initialization."""

    def test_default_base_url(self):
        """Client should use default base URL when none provided."""
        with patch.dict("os.environ", {}, clear=True):
            client = ScanApiClient()
            assert client.base_url == "http://localhost:8000"
            client.close()

    def test_custom_base_url(self):
        """Client should use provided base URL."""
        client = ScanApiClient(base_url="http://custom:9000")
        assert client.base_url == "http://custom:9000"
        client.close()

    def test_base_url_from_env(self):
        """Client should use SCAN_API_URL environment variable."""
        with patch.dict("os.environ", {"SCAN_API_URL": "http://env-url:8080"}):
            client = ScanApiClient()
            assert client.base_url == "http://env-url:8080"
            client.close()

    def test_base_url_strips_trailing_slash(self):
        """Client should strip trailing slash from base URL."""
        client = ScanApiClient(base_url="http://example.com/")
        assert client.base_url == "http://example.com"
        client.close()

    def test_custom_timeout(self):
        """Client should accept custom timeout."""
        client = ScanApiClient(timeout=60.0)
        assert client.timeout == 60.0
        client.close()

    def test_context_manager(self):
        """Client should work as context manager."""
        with ScanApiClient() as client:
            assert client.base_url == "http://localhost:8000"


class TestScanStatusResponse:
    """Tests for ScanStatusResponse data class."""

    def test_from_dict_minimal(self):
        """Should parse minimal response."""
        data = {
            "scan_id": "test-123",
            "state": "queued",
        }
        response = ScanStatusResponse.from_dict(data)
        assert response.scan_id == "test-123"
        assert response.state == ScanJobState.queued
        assert response.progress is None
        assert response.error is None
        assert response.result is None

    def test_from_dict_with_progress(self):
        """Should parse response with progress."""
        data = {
            "scan_id": "test-123",
            "state": "running",
            "progress": {"percent": 50.0, "message": "Processing files..."},
        }
        response = ScanStatusResponse.from_dict(data)
        assert response.progress is not None
        assert response.progress.percent == 50.0
        assert response.progress.message == "Processing files..."

    def test_from_dict_with_error(self):
        """Should parse response with error."""
        data = {
            "scan_id": "test-123",
            "state": "failed",
            "error": {"code": "PATH_NOT_FOUND", "message": "Path does not exist"},
        }
        response = ScanStatusResponse.from_dict(data)
        assert response.error is not None
        assert response.error.code == "PATH_NOT_FOUND"
        assert response.error.message == "Path does not exist"

    def test_from_dict_with_result(self):
        """Should parse response with result."""
        data = {
            "scan_id": "test-123",
            "state": "succeeded",
            "result": {"summary": {"total_files": 100}},
        }
        response = ScanStatusResponse.from_dict(data)
        assert response.result == {"summary": {"total_files": 100}}

    def test_is_complete_queued(self):
        """Queued state should not be complete."""
        response = ScanStatusResponse(scan_id="test", state=ScanJobState.queued)
        assert not response.is_complete

    def test_is_complete_running(self):
        """Running state should not be complete."""
        response = ScanStatusResponse(scan_id="test", state=ScanJobState.running)
        assert not response.is_complete

    def test_is_complete_succeeded(self):
        """Succeeded state should be complete."""
        response = ScanStatusResponse(scan_id="test", state=ScanJobState.succeeded)
        assert response.is_complete

    def test_is_complete_failed(self):
        """Failed state should be complete."""
        response = ScanStatusResponse(scan_id="test", state=ScanJobState.failed)
        assert response.is_complete

    def test_is_complete_canceled(self):
        """Canceled state should be complete."""
        response = ScanStatusResponse(scan_id="test", state=ScanJobState.canceled)
        assert response.is_complete

    def test_is_successful(self):
        """Only succeeded state should be successful."""
        assert ScanStatusResponse(scan_id="test", state=ScanJobState.succeeded).is_successful
        assert not ScanStatusResponse(scan_id="test", state=ScanJobState.failed).is_successful
        assert not ScanStatusResponse(scan_id="test", state=ScanJobState.running).is_successful


class TestStartScan:
    """Tests for ScanApiClient.start_scan() method."""

    @patch("src.cli.services.scan_api_client.httpx.Client")
    def test_start_scan_success(self, mock_client_class):
        """Should return scan_id on successful start."""
        mock_response = Mock()
        mock_response.status_code = 202
        mock_response.json.return_value = {"scan_id": "scan-abc-123"}

        mock_client = Mock()
        mock_client.post.return_value = mock_response
        mock_client_class.return_value = mock_client

        client = ScanApiClient()
        scan_id = client.start_scan("/path/to/project")

        assert scan_id == "scan-abc-123"
        mock_client.post.assert_called_once()
        call_args = mock_client.post.call_args
        assert call_args[0][0] == "/api/scans"
        assert call_args[1]["json"]["source_path"] == "/path/to/project"

    @patch("src.cli.services.scan_api_client.httpx.Client")
    def test_start_scan_with_options(self, mock_client_class):
        """Should pass all options to API."""
        mock_response = Mock()
        mock_response.status_code = 202
        mock_response.json.return_value = {"scan_id": "scan-123"}

        mock_client = Mock()
        mock_client.post.return_value = mock_response
        mock_client_class.return_value = mock_client

        client = ScanApiClient()
        client.start_scan(
            "/path/to/project",
            relevance_only=True,
            persist_project=False,
            profile_id="profile-123",
            use_llm=True,
        )

        call_args = mock_client.post.call_args
        payload = call_args[1]["json"]
        assert payload["relevance_only"] is True
        assert payload["persist_project"] is False
        assert payload["profile_id"] == "profile-123"
        assert payload["use_llm"] is True

    @patch("src.cli.services.scan_api_client.httpx.Client")
    def test_start_scan_with_idempotency_key(self, mock_client_class):
        """Should include idempotency key in headers."""
        mock_response = Mock()
        mock_response.status_code = 202
        mock_response.json.return_value = {"scan_id": "scan-123"}

        mock_client = Mock()
        mock_client.post.return_value = mock_response
        mock_client_class.return_value = mock_client

        client = ScanApiClient()
        client.start_scan("/path", idempotency_key="my-key-123")

        call_args = mock_client.post.call_args
        headers = call_args[1]["headers"]
        assert headers.get("idempotency-key") == "my-key-123"

    @patch("src.cli.services.scan_api_client.httpx.Client")
    def test_start_scan_with_user_id(self, mock_client_class):
        """Should include user ID in headers."""
        mock_response = Mock()
        mock_response.status_code = 202
        mock_response.json.return_value = {"scan_id": "scan-123"}

        mock_client = Mock()
        mock_client.post.return_value = mock_response
        mock_client_class.return_value = mock_client

        client = ScanApiClient()
        client.start_scan("/path", user_id="user-456")

        call_args = mock_client.post.call_args
        headers = call_args[1]["headers"]
        assert headers.get("x-user-id") == "user-456"

    @patch("src.cli.services.scan_api_client.httpx.Client")
    def test_start_scan_connection_error(self, mock_client_class):
        """Should raise ScanApiConnectionError on connection failure."""
        import httpx

        mock_client = Mock()
        mock_client.post.side_effect = httpx.ConnectError("Connection refused")
        mock_client_class.return_value = mock_client

        client = ScanApiClient()
        with pytest.raises(ScanApiConnectionError) as exc_info:
            client.start_scan("/path")

        assert "Unable to connect" in str(exc_info.value)

    @patch("src.cli.services.scan_api_client.httpx.Client")
    def test_start_scan_timeout_error(self, mock_client_class):
        """Should raise ScanApiConnectionError on timeout."""
        import httpx

        mock_client = Mock()
        mock_client.post.side_effect = httpx.TimeoutException("Request timed out")
        mock_client_class.return_value = mock_client

        client = ScanApiClient()
        with pytest.raises(ScanApiConnectionError) as exc_info:
            client.start_scan("/path")

        assert "timed out" in str(exc_info.value)

    @patch("src.cli.services.scan_api_client.httpx.Client")
    def test_start_scan_bad_request(self, mock_client_class):
        """Should raise ScanApiRequestError on 400 response."""
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.json.return_value = {"detail": "source_path is required"}

        mock_client = Mock()
        mock_client.post.return_value = mock_response
        mock_client_class.return_value = mock_client

        client = ScanApiClient()
        with pytest.raises(ScanApiRequestError) as exc_info:
            client.start_scan("/path")

        assert exc_info.value.status_code == 400
        assert exc_info.value.detail == "source_path is required"


class TestGetScanStatus:
    """Tests for ScanApiClient.get_scan_status() method."""

    @patch("src.cli.services.scan_api_client.httpx.Client")
    def test_get_scan_status_success(self, mock_client_class):
        """Should return ScanStatusResponse on success."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "scan_id": "scan-123",
            "state": "running",
            "progress": {"percent": 50.0, "message": "Processing..."},
        }

        mock_client = Mock()
        mock_client.get.return_value = mock_response
        mock_client_class.return_value = mock_client

        client = ScanApiClient()
        status = client.get_scan_status("scan-123")

        assert status.scan_id == "scan-123"
        assert status.state == ScanJobState.running
        assert status.progress.percent == 50.0

    @patch("src.cli.services.scan_api_client.httpx.Client")
    def test_get_scan_status_not_found(self, mock_client_class):
        """Should raise ScanApiRequestError with 404 for missing scan."""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.json.return_value = {"detail": "Scan not found"}

        mock_client = Mock()
        mock_client.get.return_value = mock_response
        mock_client_class.return_value = mock_client

        client = ScanApiClient()
        with pytest.raises(ScanApiRequestError) as exc_info:
            client.get_scan_status("nonexistent-scan")

        assert exc_info.value.status_code == 404
        assert "not found" in str(exc_info.value).lower()

    @patch("src.cli.services.scan_api_client.httpx.Client")
    def test_get_scan_status_with_user_id(self, mock_client_class):
        """Should include user ID in headers."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"scan_id": "scan-123", "state": "queued"}

        mock_client = Mock()
        mock_client.get.return_value = mock_response
        mock_client_class.return_value = mock_client

        client = ScanApiClient()
        client.get_scan_status("scan-123", user_id="user-456")

        call_args = mock_client.get.call_args
        headers = call_args[1]["headers"]
        assert headers.get("x-user-id") == "user-456"

    @patch("src.cli.services.scan_api_client.httpx.Client")
    def test_get_scan_status_connection_error(self, mock_client_class):
        """Should raise ScanApiConnectionError on connection failure."""
        import httpx

        mock_client = Mock()
        mock_client.get.side_effect = httpx.ConnectError("Connection refused")
        mock_client_class.return_value = mock_client

        client = ScanApiClient()
        with pytest.raises(ScanApiConnectionError):
            client.get_scan_status("scan-123")


class TestPollUntilComplete:
    """Tests for ScanApiClient.poll_until_complete() method."""

    @patch("src.cli.services.scan_api_client.httpx.Client")
    @patch("src.cli.services.scan_api_client.time.sleep")
    def test_poll_until_success(self, mock_sleep, mock_client_class):
        """Should poll until scan succeeds."""
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        # Simulate: queued -> running -> succeeded
        mock_client.get.side_effect = [
            Mock(status_code=200, json=lambda: {"scan_id": "scan-123", "state": "queued"}),
            Mock(status_code=200, json=lambda: {"scan_id": "scan-123", "state": "running", "progress": {"percent": 50.0}}),
            Mock(status_code=200, json=lambda: {"scan_id": "scan-123", "state": "succeeded", "result": {"summary": {}}}),
        ]

        client = ScanApiClient()
        result = client.poll_until_complete("scan-123", poll_interval=0.1)

        assert result.state == ScanJobState.succeeded
        assert mock_client.get.call_count == 3
        assert mock_sleep.call_count == 2

    @patch("src.cli.services.scan_api_client.httpx.Client")
    @patch("src.cli.services.scan_api_client.time.sleep")
    def test_poll_until_failure(self, mock_sleep, mock_client_class):
        """Should poll until scan fails."""
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        mock_client.get.side_effect = [
            Mock(status_code=200, json=lambda: {"scan_id": "scan-123", "state": "running"}),
            Mock(status_code=200, json=lambda: {"scan_id": "scan-123", "state": "failed", "error": {"code": "ERROR", "message": "Failed"}}),
        ]

        client = ScanApiClient()
        result = client.poll_until_complete("scan-123", poll_interval=0.1)

        assert result.state == ScanJobState.failed
        assert result.error is not None

    @patch("src.cli.services.scan_api_client.httpx.Client")
    @patch("src.cli.services.scan_api_client.time.sleep")
    def test_poll_with_progress_callback(self, mock_sleep, mock_client_class):
        """Should call progress callback on each poll."""
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        mock_client.get.side_effect = [
            Mock(status_code=200, json=lambda: {"scan_id": "scan-123", "state": "running", "progress": {"percent": 25.0}}),
            Mock(status_code=200, json=lambda: {"scan_id": "scan-123", "state": "running", "progress": {"percent": 75.0}}),
            Mock(status_code=200, json=lambda: {"scan_id": "scan-123", "state": "succeeded"}),
        ]

        callback_calls = []

        def callback(status):
            callback_calls.append(status.progress.percent if status.progress else None)

        client = ScanApiClient()
        client.poll_until_complete("scan-123", poll_interval=0.1, progress_callback=callback)

        assert len(callback_calls) == 3
        assert callback_calls[0] == 25.0
        assert callback_calls[1] == 75.0


class TestScanJobState:
    """Tests for ScanJobState enum."""

    def test_all_states_exist(self):
        """All expected states should exist."""
        assert ScanJobState.queued.value == "queued"
        assert ScanJobState.running.value == "running"
        assert ScanJobState.succeeded.value == "succeeded"
        assert ScanJobState.failed.value == "failed"
        assert ScanJobState.canceled.value == "canceled"

    def test_state_from_string(self):
        """Should create state from string value."""
        assert ScanJobState("queued") == ScanJobState.queued
        assert ScanJobState("succeeded") == ScanJobState.succeeded
