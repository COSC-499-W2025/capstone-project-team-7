"""Tests for the One-Shot Scan API (POST /api/scans and GET /api/scans/{scan_id}).

These tests verify the scan API implementation for PR #195:
- POST /api/scans starts a scan and returns scan_id
- GET /api/scans/{scan_id} returns scan status for polling
- Proper error handling for invalid inputs
- Idempotency support via headers
"""

import sys
import time
from pathlib import Path

import pytest

# Ensure backend/src is on path for imports
PROJECT_ROOT = Path(__file__).parent.parent
BACKEND_SRC = PROJECT_ROOT / "backend" / "src"
sys.path.insert(0, str(BACKEND_SRC))
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

fastapi = pytest.importorskip("fastapi")
from fastapi.testclient import TestClient

from main import app


@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)


@pytest.fixture
def fixtures_path():
    """Path to test fixtures directory."""
    return str(PROJECT_ROOT / "tests" / "fixtures")


class TestPostApiScans:
    """Tests for POST /api/scans endpoint."""

    def test_create_scan_returns_202(self, client, fixtures_path):
        """POST /api/scans should return HTTP 202 Accepted."""
        response = client.post("/api/scans", json={"source_path": fixtures_path})
        assert response.status_code == 202

    def test_create_scan_returns_scan_id(self, client, fixtures_path):
        """POST /api/scans should return a scan_id."""
        response = client.post("/api/scans", json={"source_path": fixtures_path})
        body = response.json()
        assert "scan_id" in body
        assert isinstance(body["scan_id"], str)
        assert len(body["scan_id"]) > 0

    def test_create_scan_initial_state_is_queued(self, client, fixtures_path):
        """POST /api/scans should return state as 'queued' initially."""
        response = client.post("/api/scans", json={"source_path": fixtures_path})
        body = response.json()
        # State should be queued or running (depending on how fast the background task starts)
        assert body["state"] in ("queued", "running", "succeeded")

    def test_create_scan_returns_progress(self, client, fixtures_path):
        """POST /api/scans should include progress information."""
        response = client.post("/api/scans", json={"source_path": fixtures_path})
        body = response.json()
        assert "progress" in body
        assert "percent" in body["progress"]

    def test_create_scan_missing_source_path_returns_400(self, client):
        """POST /api/scans without source_path or upload_id should return 400."""
        response = client.post("/api/scans", json={"use_llm": False})
        assert response.status_code == 400
        assert "source_path" in response.json()["detail"].lower() or "upload_id" in response.json()["detail"].lower()

    def test_create_scan_with_upload_id_only_returns_501(self, client):
        """POST /api/scans with only upload_id (not implemented) should return 501."""
        response = client.post("/api/scans", json={"upload_id": "some-upload-id"})
        assert response.status_code == 501

    def test_create_scan_idempotency_key(self, client, fixtures_path):
        """Same idempotency key should return the same scan."""
        idempotency_key = "test-idempotency-key-12345"

        response1 = client.post(
            "/api/scans",
            json={"source_path": fixtures_path},
            headers={"idempotency-key": idempotency_key}
        )
        response2 = client.post(
            "/api/scans",
            json={"source_path": fixtures_path},
            headers={"idempotency-key": idempotency_key}
        )

        assert response1.json()["scan_id"] == response2.json()["scan_id"]

    def test_create_scan_different_requests_get_different_ids(self, client, fixtures_path):
        """Different scan requests should get different scan_ids."""
        response1 = client.post("/api/scans", json={"source_path": fixtures_path})
        response2 = client.post("/api/scans", json={"source_path": fixtures_path})

        assert response1.json()["scan_id"] != response2.json()["scan_id"]


class TestGetApiScans:
    """Tests for GET /api/scans/{scan_id} endpoint."""

    def test_get_scan_returns_200(self, client, fixtures_path):
        """GET /api/scans/{scan_id} should return 200 for existing scan."""
        create_response = client.post("/api/scans", json={"source_path": fixtures_path})
        scan_id = create_response.json()["scan_id"]

        response = client.get(f"/api/scans/{scan_id}")
        assert response.status_code == 200

    def test_get_scan_returns_scan_id(self, client, fixtures_path):
        """GET /api/scans/{scan_id} should return the correct scan_id."""
        create_response = client.post("/api/scans", json={"source_path": fixtures_path})
        scan_id = create_response.json()["scan_id"]

        response = client.get(f"/api/scans/{scan_id}")
        assert response.json()["scan_id"] == scan_id

    def test_get_scan_nonexistent_returns_404(self, client):
        """GET /api/scans/{scan_id} for non-existent scan should return 404."""
        response = client.get("/api/scans/nonexistent-scan-id")
        assert response.status_code == 404

    def test_get_scan_returns_state(self, client, fixtures_path):
        """GET /api/scans/{scan_id} should include state field."""
        create_response = client.post("/api/scans", json={"source_path": fixtures_path})
        scan_id = create_response.json()["scan_id"]

        response = client.get(f"/api/scans/{scan_id}")
        body = response.json()
        assert "state" in body
        assert body["state"] in ("queued", "running", "succeeded", "failed", "canceled")

    def test_get_scan_returns_progress(self, client, fixtures_path):
        """GET /api/scans/{scan_id} should include progress field."""
        create_response = client.post("/api/scans", json={"source_path": fixtures_path})
        scan_id = create_response.json()["scan_id"]

        response = client.get(f"/api/scans/{scan_id}")
        body = response.json()
        assert "progress" in body


class TestScanCompletion:
    """Tests for scan completion and results."""

    def test_scan_completes_successfully(self, client, fixtures_path):
        """Scan should complete with 'succeeded' state for valid path."""
        create_response = client.post("/api/scans", json={"source_path": fixtures_path})
        scan_id = create_response.json()["scan_id"]

        # Poll until complete (max 30 seconds)
        for _ in range(60):
            response = client.get(f"/api/scans/{scan_id}")
            state = response.json()["state"]
            if state in ("succeeded", "failed"):
                break
            time.sleep(0.5)

        assert response.json()["state"] == "succeeded"

    def test_scan_result_contains_summary(self, client, fixtures_path):
        """Completed scan should have result with summary."""
        create_response = client.post("/api/scans", json={"source_path": fixtures_path})
        scan_id = create_response.json()["scan_id"]

        # Poll until complete
        for _ in range(60):
            response = client.get(f"/api/scans/{scan_id}")
            if response.json()["state"] == "succeeded":
                break
            time.sleep(0.5)

        result = response.json().get("result", {})
        assert "summary" in result
        assert "total_files" in result["summary"]

    def test_scan_result_contains_languages(self, client, fixtures_path):
        """Completed scan should have result with languages."""
        create_response = client.post("/api/scans", json={"source_path": fixtures_path})
        scan_id = create_response.json()["scan_id"]

        # Poll until complete
        for _ in range(60):
            response = client.get(f"/api/scans/{scan_id}")
            if response.json()["state"] == "succeeded":
                break
            time.sleep(0.5)

        result = response.json().get("result", {})
        assert "languages" in result
        assert isinstance(result["languages"], list)

    def test_scan_progress_increases(self, client, fixtures_path):
        """Scan progress should increase over time."""
        create_response = client.post("/api/scans", json={"source_path": fixtures_path})
        scan_id = create_response.json()["scan_id"]

        initial_progress = create_response.json()["progress"]["percent"]

        # Poll until complete
        max_progress = initial_progress
        for _ in range(60):
            response = client.get(f"/api/scans/{scan_id}")
            body = response.json()
            current_progress = body["progress"]["percent"]
            max_progress = max(max_progress, current_progress)
            if body["state"] in ("succeeded", "failed"):
                break
            time.sleep(0.5)

        # Progress should have reached 100% on success
        if response.json()["state"] == "succeeded":
            assert max_progress == 100.0


class TestScanErrorHandling:
    """Tests for scan error handling."""

    def test_scan_nonexistent_path_fails(self, client):
        """Scan of non-existent path should fail with PATH_NOT_FOUND."""
        create_response = client.post("/api/scans", json={"source_path": "/nonexistent/path/12345"})
        scan_id = create_response.json()["scan_id"]

        # Poll until complete
        for _ in range(20):
            response = client.get(f"/api/scans/{scan_id}")
            if response.json()["state"] in ("succeeded", "failed"):
                break
            time.sleep(0.5)

        body = response.json()
        assert body["state"] == "failed"
        assert body["error"] is not None
        assert body["error"]["code"] == "PATH_NOT_FOUND"

    def test_scan_error_includes_message(self, client):
        """Failed scan should include error message."""
        create_response = client.post("/api/scans", json={"source_path": "/nonexistent/path"})
        scan_id = create_response.json()["scan_id"]

        # Poll until complete
        for _ in range(20):
            response = client.get(f"/api/scans/{scan_id}")
            if response.json()["state"] == "failed":
                break
            time.sleep(0.5)

        error = response.json().get("error", {})
        assert "message" in error
        assert len(error["message"]) > 0


class TestScanRequestOptions:
    """Tests for scan request options."""

    def test_scan_with_relevance_only_option(self, client, fixtures_path):
        """Scan should accept relevance_only option."""
        response = client.post("/api/scans", json={
            "source_path": fixtures_path,
            "relevance_only": True
        })
        assert response.status_code == 202

    def test_scan_with_use_llm_option(self, client, fixtures_path):
        """Scan should accept use_llm option."""
        response = client.post("/api/scans", json={
            "source_path": fixtures_path,
            "use_llm": False
        })
        assert response.status_code == 202

    def test_scan_with_persist_project_false(self, client, fixtures_path):
        """Scan should accept persist_project option."""
        response = client.post("/api/scans", json={
            "source_path": fixtures_path,
            "persist_project": False
        })
        assert response.status_code == 202
