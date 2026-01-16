"""
Tests for Portfolio Refresh and Append Upload API endpoints.

Tests:
- POST /api/portfolio/refresh
- POST /api/projects/{project_id}/append-upload/{upload_id}

Run with: pytest tests/test_portfolio_refresh_api.py -v
"""

import io
import zipfile
import sys
from pathlib import Path
import uuid

import pytest
from fastapi.testclient import TestClient

# Add backend/src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend" / "src"))

from main import app
from api.upload_routes import verify_auth_token as upload_verify_auth
from api.project_routes import verify_auth_token as project_verify_auth
from api.portfolio_routes import verify_auth_token as portfolio_verify_auth


client = TestClient(app)

# Test user ID for mocked auth
TEST_USER_ID = "test-user-portfolio-123"

# Test JWT token (sub claim contains valid user_id)
TEST_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0ZXN0LXVzZXItcG9ydGZvbGlvLTEyMyJ9.test"


# Mock authentication for testing
async def mock_verify_auth_token():
    """Mock auth function that returns test user ID"""
    return TEST_USER_ID


# Override auth dependencies for tests
app.dependency_overrides[upload_verify_auth] = mock_verify_auth_token
app.dependency_overrides[project_verify_auth] = mock_verify_auth_token
app.dependency_overrides[portfolio_verify_auth] = mock_verify_auth_token


@pytest.fixture
def valid_zip_bytes():
    """Create a valid ZIP file in memory"""
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("src/main.py", "print('Hello World')\n")
        zf.writestr("src/utils.py", "def helper(): pass\n")
        zf.writestr("README.md", "# Test Project\n")
    zip_buffer.seek(0)
    return zip_buffer.getvalue()


@pytest.fixture
def valid_zip_bytes_updated():
    """Create a different ZIP file for merge testing"""
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
        # Same file with different content (should trigger conflict)
        zf.writestr("src/main.py", "print('Updated Hello World')\n")
        # New file
        zf.writestr("src/new_module.py", "class NewClass: pass\n")
        zf.writestr("tests/test_main.py", "def test_main(): pass\n")
    zip_buffer.seek(0)
    return zip_buffer.getvalue()


@pytest.fixture
def cleanup_uploads():
    """Cleanup uploaded files after tests"""
    yield
    upload_dir = Path("data/uploads")
    if upload_dir.exists():
        for file in upload_dir.glob("upl_*.zip"):
            try:
                file.unlink()
            except Exception:
                pass


class TestPortfolioRefresh:
    """Tests for POST /api/portfolio/refresh"""

    def test_refresh_empty_portfolio(self):
        """Test refreshing empty portfolio returns 200 with empty results"""
        response = client.post(
            "/api/portfolio/refresh",
            json={},
            headers={"Authorization": f"Bearer {TEST_TOKEN}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "refreshed_projects" in data
        assert "summary" in data
        assert isinstance(data["refreshed_projects"], list)
        assert "total_projects_refreshed" in data["summary"]
        assert "duration_ms" in data["summary"]

    def test_refresh_all_projects(self):
        """Test refreshing all projects without specifying IDs"""
        # First create a project
        create_response = client.post(
            "/api/projects",
            json={
                "project_name": "Refresh All Test",
                "project_path": "/test/refresh-all",
                "scan_data": {"summary": {"total_files": 5}},
            },
            headers={"Authorization": f"Bearer {TEST_TOKEN}"},
        )
        assert create_response.status_code == 201

        # Refresh all
        response = client.post(
            "/api/portfolio/refresh",
            json={},
            headers={"Authorization": f"Bearer {TEST_TOKEN}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["summary"]["total_projects_refreshed"] >= 1

    def test_refresh_specific_project(self):
        """Test refreshing specific project by ID"""
        # Create a project
        create_response = client.post(
            "/api/projects",
            json={
                "project_name": "Refresh Specific Test",
                "project_path": "/test/refresh-specific",
                "scan_data": {},
            },
            headers={"Authorization": f"Bearer {TEST_TOKEN}"},
        )
        project_id = create_response.json()["id"]

        # Refresh specific project
        response = client.post(
            "/api/portfolio/refresh",
            json={"project_ids": [project_id]},
            headers={"Authorization": f"Bearer {TEST_TOKEN}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["refreshed_projects"]) == 1
        assert data["refreshed_projects"][0]["project_id"] == project_id

    def test_refresh_nonexistent_project_returns_404(self):
        """Test refreshing nonexistent project returns 404"""
        fake_id = str(uuid.uuid4())
        response = client.post(
            "/api/portfolio/refresh",
            json={"project_ids": [fake_id]},
            headers={"Authorization": f"Bearer {TEST_TOKEN}"},
        )

        assert response.status_code == 404

    def test_refresh_missing_auth_returns_401(self):
        """Test missing auth returns 401"""
        response = client.post("/api/portfolio/refresh", json={})
        assert response.status_code == 401

    def test_refresh_response_structure(self):
        """Test refresh response has correct structure"""
        # Create a project
        create_response = client.post(
            "/api/projects",
            json={
                "project_name": "Structure Test",
                "project_path": "/test/structure",
                "scan_data": {},
            },
            headers={"Authorization": f"Bearer {TEST_TOKEN}"},
        )
        project_id = create_response.json()["id"]

        response = client.post(
            "/api/portfolio/refresh",
            json={"project_ids": [project_id]},
            headers={"Authorization": f"Bearer {TEST_TOKEN}"},
        )

        data = response.json()
        project_info = data["refreshed_projects"][0]

        assert "project_id" in project_info
        assert "project_name" in project_info
        assert "files_unchanged" in project_info
        assert "files_updated" in project_info
        assert "files_removed" in project_info
        assert "new_total_files" in project_info
        assert "refresh_timestamp" in project_info


class TestAppendUpload:
    """Tests for POST /api/projects/{project_id}/append-upload/{upload_id}"""

    def test_append_upload_success(self, valid_zip_bytes, cleanup_uploads):
        """Test successfully appending upload to project"""
        # Create a project
        create_response = client.post(
            "/api/projects",
            json={
                "project_name": "Append Test Project",
                "project_path": "/test/append",
                "scan_data": {},
            },
            headers={"Authorization": f"Bearer {TEST_TOKEN}"},
        )
        project_id = create_response.json()["id"]

        # Upload a ZIP file
        upload_response = client.post(
            "/api/uploads",
            files={"file": ("test.zip", valid_zip_bytes, "application/zip")},
            headers={"Authorization": f"Bearer {TEST_TOKEN}"},
        )
        upload_id = upload_response.json()["upload_id"]

        # Append upload to project
        response = client.post(
            f"/api/projects/{project_id}/append-upload/{upload_id}",
            json={"deduplication_strategy": "hash"},
            headers={"Authorization": f"Bearer {TEST_TOKEN}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["project_id"] == project_id
        assert data["upload_id"] == upload_id
        assert "merge_result" in data
        assert data["merge_result"]["files_added"] >= 0
        assert "merge_timestamp" in data

    def test_append_upload_dry_run(self, valid_zip_bytes, cleanup_uploads):
        """Test dry run returns preview without applying changes"""
        # Create project and upload
        create_response = client.post(
            "/api/projects",
            json={
                "project_name": "Dry Run Test",
                "project_path": "/test/dryrun",
                "scan_data": {},
            },
            headers={"Authorization": f"Bearer {TEST_TOKEN}"},
        )
        project_id = create_response.json()["id"]

        upload_response = client.post(
            "/api/uploads",
            files={"file": ("test.zip", valid_zip_bytes, "application/zip")},
            headers={"Authorization": f"Bearer {TEST_TOKEN}"},
        )
        upload_id = upload_response.json()["upload_id"]

        # Dry run
        response = client.post(
            f"/api/projects/{project_id}/append-upload/{upload_id}",
            json={"dry_run": True},
            headers={"Authorization": f"Bearer {TEST_TOKEN}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["dry_run"] is True
        assert "merge_result" in data

    def test_append_upload_deduplication_by_hash(
        self, valid_zip_bytes, cleanup_uploads
    ):
        """Test that files with identical hashes are deduplicated"""
        # Create project
        create_response = client.post(
            "/api/projects",
            json={
                "project_name": "Hash Dedup Test",
                "project_path": "/test/hashdedup",
                "scan_data": {},
            },
            headers={"Authorization": f"Bearer {TEST_TOKEN}"},
        )
        project_id = create_response.json()["id"]

        # First upload
        upload1_response = client.post(
            "/api/uploads",
            files={"file": ("test1.zip", valid_zip_bytes, "application/zip")},
            headers={"Authorization": f"Bearer {TEST_TOKEN}"},
        )
        upload1_id = upload1_response.json()["upload_id"]

        # Append first upload
        response1 = client.post(
            f"/api/projects/{project_id}/append-upload/{upload1_id}",
            json={"deduplication_strategy": "hash"},
            headers={"Authorization": f"Bearer {TEST_TOKEN}"},
        )
        assert response1.status_code == 200
        files_added_first = response1.json()["merge_result"]["files_added"]

        # Second upload with same content
        upload2_response = client.post(
            "/api/uploads",
            files={"file": ("test2.zip", valid_zip_bytes, "application/zip")},
            headers={"Authorization": f"Bearer {TEST_TOKEN}"},
        )
        upload2_id = upload2_response.json()["upload_id"]

        # Append second upload - should detect duplicates
        response2 = client.post(
            f"/api/projects/{project_id}/append-upload/{upload2_id}",
            json={"deduplication_strategy": "hash"},
            headers={"Authorization": f"Bearer {TEST_TOKEN}"},
        )
        assert response2.status_code == 200
        data = response2.json()

        # All files should be duplicates
        assert data["merge_result"]["duplicates_skipped"] > 0
        assert data["merge_result"]["files_added"] == 0

    def test_append_upload_invalid_strategy_returns_400(
        self, valid_zip_bytes, cleanup_uploads
    ):
        """Test invalid deduplication strategy returns 400"""
        # Create project and upload
        create_response = client.post(
            "/api/projects",
            json={
                "project_name": "Invalid Strategy Test",
                "project_path": "/test/invalid",
                "scan_data": {},
            },
            headers={"Authorization": f"Bearer {TEST_TOKEN}"},
        )
        project_id = create_response.json()["id"]

        upload_response = client.post(
            "/api/uploads",
            files={"file": ("test.zip", valid_zip_bytes, "application/zip")},
            headers={"Authorization": f"Bearer {TEST_TOKEN}"},
        )
        upload_id = upload_response.json()["upload_id"]

        response = client.post(
            f"/api/projects/{project_id}/append-upload/{upload_id}",
            json={"deduplication_strategy": "invalid_strategy"},
            headers={"Authorization": f"Bearer {TEST_TOKEN}"},
        )

        assert response.status_code == 400

    def test_append_upload_invalid_resolution_returns_400(
        self, valid_zip_bytes, cleanup_uploads
    ):
        """Test invalid conflict resolution returns 400"""
        create_response = client.post(
            "/api/projects",
            json={
                "project_name": "Invalid Resolution Test",
                "project_path": "/test/invalid-res",
                "scan_data": {},
            },
            headers={"Authorization": f"Bearer {TEST_TOKEN}"},
        )
        project_id = create_response.json()["id"]

        upload_response = client.post(
            "/api/uploads",
            files={"file": ("test.zip", valid_zip_bytes, "application/zip")},
            headers={"Authorization": f"Bearer {TEST_TOKEN}"},
        )
        upload_id = upload_response.json()["upload_id"]

        response = client.post(
            f"/api/projects/{project_id}/append-upload/{upload_id}",
            json={"conflict_resolution": "invalid_resolution"},
            headers={"Authorization": f"Bearer {TEST_TOKEN}"},
        )

        assert response.status_code == 400

    def test_append_upload_missing_auth_returns_401(self):
        """Test missing auth returns 401"""
        response = client.post(
            f"/api/projects/{uuid.uuid4()}/append-upload/upl_test",
            json={},
        )
        assert response.status_code == 401

    def test_append_upload_nonexistent_project_returns_404(
        self, valid_zip_bytes, cleanup_uploads
    ):
        """Test appending to nonexistent project returns 404"""
        # Create an upload
        upload_response = client.post(
            "/api/uploads",
            files={"file": ("test.zip", valid_zip_bytes, "application/zip")},
            headers={"Authorization": f"Bearer {TEST_TOKEN}"},
        )
        upload_id = upload_response.json()["upload_id"]

        fake_project_id = str(uuid.uuid4())
        response = client.post(
            f"/api/projects/{fake_project_id}/append-upload/{upload_id}",
            json={},
            headers={"Authorization": f"Bearer {TEST_TOKEN}"},
        )

        assert response.status_code == 404

    def test_append_upload_nonexistent_upload_returns_404(self):
        """Test appending nonexistent upload returns 404"""
        # Create a project
        create_response = client.post(
            "/api/projects",
            json={
                "project_name": "Missing Upload Test",
                "project_path": "/test/missing-upload",
                "scan_data": {},
            },
            headers={"Authorization": f"Bearer {TEST_TOKEN}"},
        )
        project_id = create_response.json()["id"]

        response = client.post(
            f"/api/projects/{project_id}/append-upload/upl_nonexistent",
            json={},
            headers={"Authorization": f"Bearer {TEST_TOKEN}"},
        )

        assert response.status_code == 404

    def test_append_upload_response_structure(
        self, valid_zip_bytes, cleanup_uploads
    ):
        """Test append upload response has correct structure"""
        create_response = client.post(
            "/api/projects",
            json={
                "project_name": "Response Structure Test",
                "project_path": "/test/response",
                "scan_data": {},
            },
            headers={"Authorization": f"Bearer {TEST_TOKEN}"},
        )
        project_id = create_response.json()["id"]

        upload_response = client.post(
            "/api/uploads",
            files={"file": ("test.zip", valid_zip_bytes, "application/zip")},
            headers={"Authorization": f"Bearer {TEST_TOKEN}"},
        )
        upload_id = upload_response.json()["upload_id"]

        response = client.post(
            f"/api/projects/{project_id}/append-upload/{upload_id}",
            json={},
            headers={"Authorization": f"Bearer {TEST_TOKEN}"},
        )

        data = response.json()

        # Check top-level fields
        assert "project_id" in data
        assert "upload_id" in data
        assert "merge_result" in data
        assert "duplicate_details" in data
        assert "merge_timestamp" in data
        assert "dry_run" in data

        # Check merge_result structure
        merge_result = data["merge_result"]
        assert "files_added" in merge_result
        assert "files_updated" in merge_result
        assert "duplicates_skipped" in merge_result
        assert "total_project_files" in merge_result


class TestAppendUploadDeduplicationStrategies:
    """Tests for different deduplication strategies"""

    def test_strategy_hash(self, valid_zip_bytes, cleanup_uploads):
        """Test deduplication by hash strategy"""
        create_response = client.post(
            "/api/projects",
            json={
                "project_name": "Strategy Hash Test",
                "project_path": "/test/strategy-hash",
                "scan_data": {},
            },
            headers={"Authorization": f"Bearer {TEST_TOKEN}"},
        )
        project_id = create_response.json()["id"]

        upload_response = client.post(
            "/api/uploads",
            files={"file": ("test.zip", valid_zip_bytes, "application/zip")},
            headers={"Authorization": f"Bearer {TEST_TOKEN}"},
        )
        upload_id = upload_response.json()["upload_id"]

        response = client.post(
            f"/api/projects/{project_id}/append-upload/{upload_id}",
            json={"deduplication_strategy": "hash"},
            headers={"Authorization": f"Bearer {TEST_TOKEN}"},
        )

        assert response.status_code == 200

    def test_strategy_path(self, valid_zip_bytes, cleanup_uploads):
        """Test deduplication by path strategy"""
        create_response = client.post(
            "/api/projects",
            json={
                "project_name": "Strategy Path Test",
                "project_path": "/test/strategy-path",
                "scan_data": {},
            },
            headers={"Authorization": f"Bearer {TEST_TOKEN}"},
        )
        project_id = create_response.json()["id"]

        upload_response = client.post(
            "/api/uploads",
            files={"file": ("test.zip", valid_zip_bytes, "application/zip")},
            headers={"Authorization": f"Bearer {TEST_TOKEN}"},
        )
        upload_id = upload_response.json()["upload_id"]

        response = client.post(
            f"/api/projects/{project_id}/append-upload/{upload_id}",
            json={"deduplication_strategy": "path"},
            headers={"Authorization": f"Bearer {TEST_TOKEN}"},
        )

        assert response.status_code == 200

    def test_strategy_both(self, valid_zip_bytes, cleanup_uploads):
        """Test deduplication by both hash and path"""
        create_response = client.post(
            "/api/projects",
            json={
                "project_name": "Strategy Both Test",
                "project_path": "/test/strategy-both",
                "scan_data": {},
            },
            headers={"Authorization": f"Bearer {TEST_TOKEN}"},
        )
        project_id = create_response.json()["id"]

        upload_response = client.post(
            "/api/uploads",
            files={"file": ("test.zip", valid_zip_bytes, "application/zip")},
            headers={"Authorization": f"Bearer {TEST_TOKEN}"},
        )
        upload_id = upload_response.json()["upload_id"]

        response = client.post(
            f"/api/projects/{project_id}/append-upload/{upload_id}",
            json={"deduplication_strategy": "both"},
            headers={"Authorization": f"Bearer {TEST_TOKEN}"},
        )

        assert response.status_code == 200


class TestAppendUploadConflictResolution:
    """Tests for different conflict resolution strategies"""

    def test_resolution_newer(self, valid_zip_bytes, cleanup_uploads):
        """Test conflict resolution with 'newer' strategy"""
        create_response = client.post(
            "/api/projects",
            json={
                "project_name": "Resolution Newer Test",
                "project_path": "/test/resolution-newer",
                "scan_data": {},
            },
            headers={"Authorization": f"Bearer {TEST_TOKEN}"},
        )
        project_id = create_response.json()["id"]

        upload_response = client.post(
            "/api/uploads",
            files={"file": ("test.zip", valid_zip_bytes, "application/zip")},
            headers={"Authorization": f"Bearer {TEST_TOKEN}"},
        )
        upload_id = upload_response.json()["upload_id"]

        response = client.post(
            f"/api/projects/{project_id}/append-upload/{upload_id}",
            json={"conflict_resolution": "newer"},
            headers={"Authorization": f"Bearer {TEST_TOKEN}"},
        )

        assert response.status_code == 200

    def test_resolution_keep_existing(self, valid_zip_bytes, cleanup_uploads):
        """Test conflict resolution with 'keep_existing' strategy"""
        create_response = client.post(
            "/api/projects",
            json={
                "project_name": "Resolution Keep Test",
                "project_path": "/test/resolution-keep",
                "scan_data": {},
            },
            headers={"Authorization": f"Bearer {TEST_TOKEN}"},
        )
        project_id = create_response.json()["id"]

        upload_response = client.post(
            "/api/uploads",
            files={"file": ("test.zip", valid_zip_bytes, "application/zip")},
            headers={"Authorization": f"Bearer {TEST_TOKEN}"},
        )
        upload_id = upload_response.json()["upload_id"]

        response = client.post(
            f"/api/projects/{project_id}/append-upload/{upload_id}",
            json={"conflict_resolution": "keep_existing"},
            headers={"Authorization": f"Bearer {TEST_TOKEN}"},
        )

        assert response.status_code == 200

    def test_resolution_replace(self, valid_zip_bytes, cleanup_uploads):
        """Test conflict resolution with 'replace' strategy"""
        create_response = client.post(
            "/api/projects",
            json={
                "project_name": "Resolution Replace Test",
                "project_path": "/test/resolution-replace",
                "scan_data": {},
            },
            headers={"Authorization": f"Bearer {TEST_TOKEN}"},
        )
        project_id = create_response.json()["id"]

        upload_response = client.post(
            "/api/uploads",
            files={"file": ("test.zip", valid_zip_bytes, "application/zip")},
            headers={"Authorization": f"Bearer {TEST_TOKEN}"},
        )
        upload_id = upload_response.json()["upload_id"]

        response = client.post(
            f"/api/projects/{project_id}/append-upload/{upload_id}",
            json={"conflict_resolution": "replace"},
            headers={"Authorization": f"Bearer {TEST_TOKEN}"},
        )

        assert response.status_code == 200
