"""
Tests for DELETE /api/projects/{project_id}/insights endpoint.

Tests clearing analysis data (insights) while preserving project records.

All endpoints require JWT authentication via Bearer token.
Run with: pytest tests/test_delete_insights_api.py -v
"""

import pytest
from fastapi.testclient import TestClient
import uuid

from main import app


client = TestClient(app)

# Test JWT token (sub claim contains valid user_id: 9870edb5-2741-4c0a-b5cd-494a498f7485)
TEST_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI5ODcwZWRiNS0yNzQxLTRjMGEtYjVjZC00OTRhNDk4Zjc0ODUifQ.test"

# Sample scan data for testing
SAMPLE_SCAN_DATA = {
    "summary": {"total_files": 42, "total_lines": 5000},
    "code_analysis": {"languages": ["Python", "JavaScript"]},
    "skills_analysis": {"skills": ["FastAPI", "React"]},
    "git_analysis": [{"commit": "abc123"}],
    "contribution_metrics": {"commits": 10},
    "languages": ["Python", "JavaScript"],
    "files": [{"name": "test.py", "size": 1024}]
}


class TestDeleteProjectInsights:
    """Tests for DELETE /api/projects/{project_id}/insights"""

    def test_delete_insights_success(self):
        """Test clearing insights returns 200 with timestamp"""
        # Create a project with scan data
        create_response = client.post(
            "/api/projects",
            json={
                "project_name": f"Insights Delete Test {uuid.uuid4().hex[:8]}",
                "project_path": "/test/insights/delete",
                "scan_data": SAMPLE_SCAN_DATA,
            },
            headers={"Authorization": f"Bearer {TEST_TOKEN}"},
        )
        assert create_response.status_code == 201
        project_id = create_response.json()["id"]

        # Delete insights
        response = client.delete(
            f"/api/projects/{project_id}/insights",
            headers={"Authorization": f"Bearer {TEST_TOKEN}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "insights_deleted_at" in data
        assert data["message"] == "Insights cleared successfully"

    def test_delete_insights_preserves_project_record(self):
        """Test that project record remains after insights deletion"""
        # Create project
        project_name = f"Preserve Record Test {uuid.uuid4().hex[:8]}"
        create_response = client.post(
            "/api/projects",
            json={
                "project_name": project_name,
                "project_path": "/test/preserve",
                "scan_data": SAMPLE_SCAN_DATA,
            },
            headers={"Authorization": f"Bearer {TEST_TOKEN}"},
        )
        assert create_response.status_code == 201
        project_id = create_response.json()["id"]

        # Delete insights
        delete_response = client.delete(
            f"/api/projects/{project_id}/insights",
            headers={"Authorization": f"Bearer {TEST_TOKEN}"},
        )
        assert delete_response.status_code == 200

        # Project should still exist
        get_response = client.get(
            f"/api/projects/{project_id}",
            headers={"Authorization": f"Bearer {TEST_TOKEN}"},
        )
        assert get_response.status_code == 200
        assert get_response.json()["project_name"] == project_name

    def test_delete_insights_clears_scan_data(self):
        """Test that insights deletion clears scan_data"""
        # Create project with scan data
        create_response = client.post(
            "/api/projects",
            json={
                "project_name": f"Clear Data Test {uuid.uuid4().hex[:8]}",
                "project_path": "/test/clear",
                "scan_data": SAMPLE_SCAN_DATA,
            },
            headers={"Authorization": f"Bearer {TEST_TOKEN}"},
        )
        assert create_response.status_code == 201
        project_id = create_response.json()["id"]

        # Verify scan_data exists before deletion
        get_before = client.get(
            f"/api/projects/{project_id}",
            headers={"Authorization": f"Bearer {TEST_TOKEN}"},
        )
        assert get_before.status_code == 200
        # scan_data should have content
        assert get_before.json().get("scan_data") is not None

        # Delete insights
        client.delete(
            f"/api/projects/{project_id}/insights",
            headers={"Authorization": f"Bearer {TEST_TOKEN}"},
        )

        # Verify scan_data is cleared but project exists
        get_after = client.get(
            f"/api/projects/{project_id}",
            headers={"Authorization": f"Bearer {TEST_TOKEN}"},
        )
        assert get_after.status_code == 200
        assert get_after.json()["scan_data"] is None

    def test_delete_insights_resets_analysis_flags(self):
        """Test that all analysis flags are reset to false"""
        # Create project with analysis data
        create_response = client.post(
            "/api/projects",
            json={
                "project_name": f"Flags Reset Test {uuid.uuid4().hex[:8]}",
                "project_path": "/test/flags",
                "scan_data": SAMPLE_SCAN_DATA,
            },
            headers={"Authorization": f"Bearer {TEST_TOKEN}"},
        )
        assert create_response.status_code == 201
        project_id = create_response.json()["id"]

        # Delete insights
        client.delete(
            f"/api/projects/{project_id}/insights",
            headers={"Authorization": f"Bearer {TEST_TOKEN}"},
        )

        # Check flags are reset
        get_response = client.get(
            f"/api/projects/{project_id}",
            headers={"Authorization": f"Bearer {TEST_TOKEN}"},
        )
        assert get_response.status_code == 200
        data = get_response.json()
        assert data["has_code_analysis"] is False
        assert data["has_skills_analysis"] is False
        assert data["has_git_analysis"] is False
        assert data["has_media_analysis"] is False
        assert data["has_pdf_analysis"] is False

    def test_delete_insights_nonexistent_project_returns_404(self):
        """Test that deleting insights for nonexistent project returns 404"""
        fake_id = str(uuid.uuid4())
        response = client.delete(
            f"/api/projects/{fake_id}/insights",
            headers={"Authorization": f"Bearer {TEST_TOKEN}"},
        )
        assert response.status_code == 404

    def test_delete_insights_missing_auth_returns_401(self):
        """Test that missing Authorization header returns 401"""
        response = client.delete(f"/api/projects/{uuid.uuid4()}/insights")
        assert response.status_code == 401

    def test_delete_insights_invalid_token_returns_401(self):
        """Test that invalid Authorization token returns 401"""
        response = client.delete(
            f"/api/projects/{uuid.uuid4()}/insights",
            headers={"Authorization": "Bearer invalid_token"},
        )
        assert response.status_code == 401


class TestDeleteInsightsWorkflow:
    """Integration tests for insights workflow"""

    def test_create_clear_rescan_workflow(self):
        """Test workflow: create -> clear insights -> rescan works correctly"""
        project_name = f"Workflow Test {uuid.uuid4().hex[:8]}"

        # Create project with initial scan
        create_response = client.post(
            "/api/projects",
            json={
                "project_name": project_name,
                "project_path": "/test/workflow",
                "scan_data": SAMPLE_SCAN_DATA,
            },
            headers={"Authorization": f"Bearer {TEST_TOKEN}"},
        )
        assert create_response.status_code == 201
        project_id = create_response.json()["id"]

        # Clear insights
        clear_response = client.delete(
            f"/api/projects/{project_id}/insights",
            headers={"Authorization": f"Bearer {TEST_TOKEN}"},
        )
        assert clear_response.status_code == 200

        # Rescan (update project with new data)
        new_scan_data = {
            "summary": {"total_files": 100, "total_lines": 10000},
            "code_analysis": {"languages": ["Go", "Rust"]},
        }
        rescan_response = client.post(
            "/api/projects",
            json={
                "project_name": project_name,
                "project_path": "/test/workflow",
                "scan_data": new_scan_data,
            },
            headers={"Authorization": f"Bearer {TEST_TOKEN}"},
        )
        assert rescan_response.status_code == 201

        # Verify new data is present
        get_response = client.get(
            f"/api/projects/{project_id}",
            headers={"Authorization": f"Bearer {TEST_TOKEN}"},
        )
        assert get_response.status_code == 200
        assert get_response.json()["scan_data"] is not None
