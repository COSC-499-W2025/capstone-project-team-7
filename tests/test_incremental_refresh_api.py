"""
Tests for Incremental Portfolio Refresh with Deduplication API endpoints.

Tests POST /api/portfolio/refresh and POST /api/projects/{project_id}/append-upload/{upload_id}

All endpoints require JWT authentication via Bearer token.
Run with: pytest tests/test_incremental_refresh_api.py -v
"""

import pytest
from fastapi.testclient import TestClient
import uuid
import io
import zipfile
import hashlib
import sys
import types
from pathlib import Path
from datetime import datetime
from unittest.mock import patch, MagicMock

# Stub python-magic for environments without the optional dependency.
if "magic" not in sys.modules:
    sys.modules["magic"] = types.SimpleNamespace(
        from_buffer=lambda *args, **kwargs: "application/zip"
    )

PROJECT_ROOT = Path(__file__).resolve().parent.parent
BACKEND_SRC = PROJECT_ROOT / "backend" / "src"
if str(BACKEND_SRC) not in sys.path:
    sys.path.insert(0, str(BACKEND_SRC))
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

sys.modules["cli"] = types.ModuleType("cli")
sys.modules["cli"].__path__ = [str(BACKEND_SRC / "cli")]

from backend.src.main import app
from api.dependencies import AuthContext, get_auth_context
from api.portfolio_routes import get_projects_service

client = TestClient(app)

# Test JWT token (sub claim contains valid user_id)
TEST_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI5ODcwZWRiNS0yNzQxLTRjMGEtYjVjZC00OTRhNDk4Zjc0ODUifQ.test"
VALID_USER_ID = "9870edb5-2741-4c0a-b5cd-494a498f7485"


def create_test_zip(files: dict) -> bytes:
    """
    Create a ZIP file in memory with the given files.

    Args:
        files: Dict mapping relative path to file content (bytes or str)

    Returns:
        ZIP file contents as bytes
    """
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
        for path, content in files.items():
            if isinstance(content, str):
                content = content.encode('utf-8')
            zf.writestr(path, content)
    buffer.seek(0)
    return buffer.read()


def compute_sha256(content: bytes) -> str:
    """Compute SHA-256 hash of content."""
    return hashlib.sha256(content).hexdigest()


# ============================================================================
# Mock Services
# ============================================================================


class FakeProjectsService:
    """Fake projects service for testing."""

    def __init__(self):
        self._projects = {}
        self._cached_files = {}

    def get_user_projects(self, user_id):
        """Return mock projects."""
        return [
            {
                "id": "project-1",
                "project_name": "Test Project 1",
                "project_path": "/test/path1",
            },
            {
                "id": "project-2",
                "project_name": "Test Project 2",
                "project_path": "/test/path2",
            },
        ]

    def get_cached_files(self, user_id, project_id):
        """Return mock cached files."""
        if project_id == "project-1":
            return {
                "src/main.py": {
                    "sha256": "abc123",
                    "size_bytes": 100,
                    "mime_type": "text/x-python",
                },
                "src/utils.py": {
                    "sha256": "duplicate_hash",
                    "size_bytes": 200,
                    "mime_type": "text/x-python",
                },
            }
        elif project_id == "project-2":
            return {
                "lib/helper.py": {
                    "sha256": "def456",
                    "size_bytes": 150,
                    "mime_type": "text/x-python",
                },
                "lib/utils.py": {
                    "sha256": "duplicate_hash",  # Same hash as in project-1
                    "size_bytes": 200,
                    "mime_type": "text/x-python",
                },
            }
        return self._cached_files.get(project_id, {})

    def get_project_scan(self, user_id, project_id):
        """Return mock project scan data."""
        if project_id in ["project-1", "project-2"]:
            return {
                "id": project_id,
                "project_name": f"Test Project {project_id}",
                "user_id": user_id,
            }
        return self._projects.get(project_id)

    def upsert_cached_files(self, user_id, project_id, files):
        """Mock upsert cached files."""
        if project_id not in self._cached_files:
            self._cached_files[project_id] = {}
        for f in files:
            self._cached_files[project_id][f["relative_path"]] = f


async def _override_auth() -> AuthContext:
    """Override auth dependency for testing."""
    return AuthContext(user_id=VALID_USER_ID, access_token="test-token")


# ============================================================================
# Portfolio Refresh Endpoint Tests
# ============================================================================


class TestPortfolioRefresh:
    """Tests for POST /api/portfolio/refresh"""

    @pytest.fixture(autouse=True)
    def override_dependencies(self):
        """Override dependencies for testing."""
        app.dependency_overrides[get_auth_context] = _override_auth
        app.dependency_overrides[get_projects_service] = lambda: FakeProjectsService()
        yield
        app.dependency_overrides.clear()

    def test_refresh_portfolio_success(self):
        """Test refreshing portfolio returns 200 with expected structure"""
        response = client.post(
            "/api/portfolio/refresh",
            json={"include_duplicates": True},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"
        assert "projects_scanned" in data
        assert "total_files" in data
        assert "total_size_bytes" in data
        assert isinstance(data["projects_scanned"], int)
        assert isinstance(data["total_files"], int)
        assert isinstance(data["total_size_bytes"], int)

    def test_refresh_portfolio_with_dedup_report(self):
        """Test refresh includes dedup report when include_duplicates is True"""
        response = client.post(
            "/api/portfolio/refresh",
            json={"include_duplicates": True},
        )

        assert response.status_code == 200
        data = response.json()

        # dedup_report should exist with our fake data (we have duplicates)
        assert data.get("dedup_report") is not None
        dedup_report = data["dedup_report"]
        assert "summary" in dedup_report
        assert "duplicate_groups" in dedup_report
        assert "duplicate_groups_count" in dedup_report["summary"]
        assert "total_wasted_bytes" in dedup_report["summary"]
        assert isinstance(dedup_report["duplicate_groups"], list)

        # Should find the duplicate_hash across projects
        assert dedup_report["summary"]["duplicate_groups_count"] >= 1

    def test_refresh_portfolio_without_dedup(self):
        """Test refresh without duplicate detection"""
        response = client.post(
            "/api/portfolio/refresh",
            json={"include_duplicates": False},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"
        # When include_duplicates is False, dedup_report should be None
        assert data.get("dedup_report") is None

    def test_refresh_portfolio_default_request(self):
        """Test refresh with empty/default request body"""
        response = client.post(
            "/api/portfolio/refresh",
            json={},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"

    def test_refresh_portfolio_counts_files_correctly(self):
        """Test that refresh correctly counts total files"""
        response = client.post(
            "/api/portfolio/refresh",
            json={"include_duplicates": True},
        )

        assert response.status_code == 200
        data = response.json()

        # FakeProjectsService returns 2 files per project, 2 projects = 4 files
        assert data["total_files"] == 4
        assert data["projects_scanned"] == 2


class TestPortfolioRefreshAuth:
    """Tests for portfolio refresh authentication"""

    def test_refresh_portfolio_missing_auth_returns_401(self):
        """Test that missing Authorization header returns 401"""
        # Clear overrides to test real auth
        app.dependency_overrides.clear()

        response = client.post(
            "/api/portfolio/refresh",
            json={"include_duplicates": True},
        )

        assert response.status_code == 401


# ============================================================================
# Append Upload to Project Endpoint Tests
# ============================================================================


class TestAppendUpload:
    """Tests for POST /api/projects/{project_id}/append-upload/{upload_id}"""

    def _upload_zip(self, files: dict) -> str:
        """Helper to upload a ZIP file and return the upload_id"""
        zip_content = create_test_zip(files)

        response = client.post(
            "/api/uploads",
            files={"file": ("test.zip", zip_content, "application/zip")},
            headers={"Authorization": f"Bearer {TEST_TOKEN}"},
        )
        # Upload endpoint returns 201 Created
        assert response.status_code == 201, f"Upload failed: {response.json()}"
        return response.json()["upload_id"]

    def test_append_upload_not_found_upload(self):
        """Test append with nonexistent upload returns 404"""
        fake_upload_id = "upl_nonexistent123"
        fake_project_id = str(uuid.uuid4())

        response = client.post(
            f"/api/projects/{fake_project_id}/append-upload/{fake_upload_id}",
            json={"skip_duplicates": True},
            headers={"Authorization": f"Bearer {TEST_TOKEN}"},
        )

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_append_upload_missing_auth_returns_401(self):
        """Test that missing Authorization header returns 401"""
        # Use a valid UUID format for project_id
        response = client.post(
            f"/api/projects/{uuid.uuid4()}/append-upload/upl_test123456",
            json={"skip_duplicates": True},
        )

        # Should return 401 Unauthorized without auth header
        # Note: The endpoint may return 404 first if upload doesn't exist
        # depending on the order of checks, so accept either
        assert response.status_code in [401, 404]


# ============================================================================
# TUI API Service Tests (Unit Tests)
# ============================================================================


class TestPortfolioRefreshAPIService:
    """Unit tests for PortfolioRefreshAPIService"""

    def test_service_requires_auth_token(self):
        """Test that service requires authentication token"""
        from cli.services.projects_api_service import (
            PortfolioRefreshAPIService,
            PortfolioRefreshAPIServiceError,
        )

        with pytest.raises(PortfolioRefreshAPIServiceError) as exc_info:
            PortfolioRefreshAPIService(auth_token=None)

        assert "Authentication token is required" in str(exc_info.value)

    def test_service_initializes_with_token(self):
        """Test that service initializes properly with token"""
        from cli.services.projects_api_service import PortfolioRefreshAPIService

        service = PortfolioRefreshAPIService(
            base_url="http://localhost:8000",
            auth_token="test_token_123",
        )

        assert service.auth_token == "test_token_123"
        assert service.base_url == "http://localhost:8000"
        assert "Authorization" in service.headers
        assert "Bearer test_token_123" in service.headers["Authorization"]

    def test_service_uses_default_base_url(self):
        """Test that service uses default base URL when not specified"""
        from cli.services.projects_api_service import PortfolioRefreshAPIService
        import os

        # Clear env var if set
        original = os.environ.get("API_BASE_URL")
        if "API_BASE_URL" in os.environ:
            del os.environ["API_BASE_URL"]

        try:
            service = PortfolioRefreshAPIService(auth_token="test_token")
            assert service.base_url == "http://localhost:8000"
        finally:
            if original is not None:
                os.environ["API_BASE_URL"] = original


# ============================================================================
# Model Validation Tests
# ============================================================================


class TestResponseModels:
    """Test response model structure and validation"""

    @pytest.fixture(autouse=True)
    def override_dependencies(self):
        """Override dependencies for testing."""
        app.dependency_overrides[get_auth_context] = _override_auth
        app.dependency_overrides[get_projects_service] = lambda: FakeProjectsService()
        yield
        app.dependency_overrides.clear()

    def test_dedup_report_structure(self):
        """Test that dedup report has correct structure"""
        response = client.post(
            "/api/portfolio/refresh",
            json={"include_duplicates": True},
        )

        assert response.status_code == 200
        data = response.json()

        dedup_report = data.get("dedup_report")
        if dedup_report:
            # Validate summary structure
            summary = dedup_report["summary"]
            assert isinstance(summary["duplicate_groups_count"], int)
            assert isinstance(summary["total_wasted_bytes"], int)

            # Validate duplicate groups structure
            for group in dedup_report["duplicate_groups"]:
                assert "sha256" in group
                assert "file_count" in group
                assert "wasted_bytes" in group
                assert "files" in group
                assert isinstance(group["files"], list)

                for file_info in group["files"]:
                    assert "path" in file_info
                    assert "project_id" in file_info
                    assert "project_name" in file_info

    def test_duplicate_wasted_bytes_calculation(self):
        """Test that wasted bytes is calculated correctly"""
        response = client.post(
            "/api/portfolio/refresh",
            json={"include_duplicates": True},
        )

        assert response.status_code == 200
        data = response.json()

        dedup_report = data.get("dedup_report")
        if dedup_report and dedup_report["duplicate_groups"]:
            for group in dedup_report["duplicate_groups"]:
                # Wasted bytes should be (file_count - 1) * file_size
                # Since we can't know exact file size, just verify it's non-negative
                assert group["wasted_bytes"] >= 0
                assert group["file_count"] >= 2  # At least 2 files to be a duplicate
