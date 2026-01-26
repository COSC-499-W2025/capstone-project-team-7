"""
Tests for Project Overrides API endpoints.

Tests GET/PATCH/DELETE /api/projects/{project_id}/overrides

All endpoints require JWT authentication via Bearer token.
Run with: pytest tests/test_project_overrides_api.py -v
"""

import pytest
from fastapi.testclient import TestClient
import uuid

from main import app


client = TestClient(app)

# Test JWT token (sub claim contains valid user_id)
TEST_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI5ODcwZWRiNS0yNzQxLTRjMGEtYjVjZC00OTRhNDk4Zjc0ODUifQ.test"


def create_test_project() -> str:
    """Helper to create a test project and return its ID."""
    response = client.post(
        "/api/projects",
        json={
            "project_name": f"Override Test Project {uuid.uuid4().hex[:8]}",
            "project_path": "/test/overrides",
            "scan_data": {"summary": {"total_files": 10}},
        },
        headers={"Authorization": f"Bearer {TEST_TOKEN}"},
    )
    assert response.status_code == 201
    return response.json()["id"]


class TestGetProjectOverrides:
    """Tests for GET /api/projects/{project_id}/overrides"""

    def test_get_overrides_empty_for_new_project(self):
        """Test that GET returns empty overrides for project with no overrides set."""
        project_id = create_test_project()
        
        response = client.get(
            f"/api/projects/{project_id}/overrides",
            headers={"Authorization": f"Bearer {TEST_TOKEN}"},
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["project_id"] == project_id
        assert data["overrides"]["role"] is None
        assert data["overrides"]["evidence"] == []
        assert data["overrides"]["highlighted_skills"] == []
        assert data["overrides"]["start_date_override"] is None
        assert data["overrides"]["end_date_override"] is None

    def test_get_overrides_returns_set_values(self):
        """Test that GET returns previously set override values."""
        project_id = create_test_project()
        
        # First set some overrides
        client.patch(
            f"/api/projects/{project_id}/overrides",
            json={
                "role": "Lead Developer",
                "highlighted_skills": ["Python", "FastAPI"],
            },
            headers={"Authorization": f"Bearer {TEST_TOKEN}"},
        )
        
        # Then get them
        response = client.get(
            f"/api/projects/{project_id}/overrides",
            headers={"Authorization": f"Bearer {TEST_TOKEN}"},
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["overrides"]["role"] == "Lead Developer"
        assert data["overrides"]["highlighted_skills"] == ["Python", "FastAPI"]

    def test_get_overrides_nonexistent_project_returns_404(self):
        """Test that GET returns 404 for nonexistent project."""
        fake_id = str(uuid.uuid4())
        
        response = client.get(
            f"/api/projects/{fake_id}/overrides",
            headers={"Authorization": f"Bearer {TEST_TOKEN}"},
        )
        
        assert response.status_code == 404

    def test_get_overrides_missing_auth_returns_401(self):
        """Test that GET without auth returns 401."""
        fake_id = str(uuid.uuid4())
        
        response = client.get(f"/api/projects/{fake_id}/overrides")
        
        assert response.status_code == 401


class TestPatchProjectOverrides:
    """Tests for PATCH /api/projects/{project_id}/overrides"""

    def test_patch_creates_overrides(self):
        """Test that PATCH creates new overrides for project."""
        project_id = create_test_project()
        
        response = client.patch(
            f"/api/projects/{project_id}/overrides",
            json={
                "role": "Backend Engineer",
                "evidence": ["Implemented API endpoints", "Wrote unit tests"],
                "highlighted_skills": ["Python", "PostgreSQL"],
                "start_date_override": "2024-01-15",
                "end_date_override": "2024-06-30",
            },
            headers={"Authorization": f"Bearer {TEST_TOKEN}"},
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["project_id"] == project_id
        assert data["overrides"]["role"] == "Backend Engineer"
        assert data["overrides"]["evidence"] == ["Implemented API endpoints", "Wrote unit tests"]
        assert data["overrides"]["highlighted_skills"] == ["Python", "PostgreSQL"]
        assert data["overrides"]["start_date_override"] == "2024-01-15"
        assert data["overrides"]["end_date_override"] == "2024-06-30"

    def test_patch_updates_existing_overrides(self):
        """Test that PATCH updates existing overrides."""
        project_id = create_test_project()
        
        # Create initial overrides
        client.patch(
            f"/api/projects/{project_id}/overrides",
            json={"role": "Junior Developer"},
            headers={"Authorization": f"Bearer {TEST_TOKEN}"},
        )
        
        # Update role
        response = client.patch(
            f"/api/projects/{project_id}/overrides",
            json={"role": "Senior Developer"},
            headers={"Authorization": f"Bearer {TEST_TOKEN}"},
        )
        
        assert response.status_code == 200
        assert response.json()["overrides"]["role"] == "Senior Developer"

    def test_patch_partial_update(self):
        """Test that PATCH only updates provided fields."""
        project_id = create_test_project()
        
        # Create initial overrides with multiple fields
        client.patch(
            f"/api/projects/{project_id}/overrides",
            json={
                "role": "Developer",
                "highlighted_skills": ["JavaScript"],
            },
            headers={"Authorization": f"Bearer {TEST_TOKEN}"},
        )
        
        # Update only role
        response = client.patch(
            f"/api/projects/{project_id}/overrides",
            json={"role": "Senior Developer"},
            headers={"Authorization": f"Bearer {TEST_TOKEN}"},
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["overrides"]["role"] == "Senior Developer"
        # highlighted_skills should still be set
        assert data["overrides"]["highlighted_skills"] == ["JavaScript"]

    def test_patch_sets_custom_rank(self):
        """Test that PATCH can set custom_rank."""
        project_id = create_test_project()
        
        response = client.patch(
            f"/api/projects/{project_id}/overrides",
            json={"custom_rank": 85.5},
            headers={"Authorization": f"Bearer {TEST_TOKEN}"},
        )
        
        assert response.status_code == 200
        assert response.json()["overrides"]["custom_rank"] == 85.5

    def test_patch_sets_comparison_attributes(self):
        """Test that PATCH can set comparison_attributes."""
        project_id = create_test_project()
        
        response = client.patch(
            f"/api/projects/{project_id}/overrides",
            json={
                "comparison_attributes": {
                    "team_size": "5",
                    "complexity": "high",
                }
            },
            headers={"Authorization": f"Bearer {TEST_TOKEN}"},
        )
        
        assert response.status_code == 200
        attrs = response.json()["overrides"]["comparison_attributes"]
        assert attrs["team_size"] == "5"
        assert attrs["complexity"] == "high"

    def test_patch_nonexistent_project_returns_404(self):
        """Test that PATCH returns 404 for nonexistent project."""
        fake_id = str(uuid.uuid4())
        
        response = client.patch(
            f"/api/projects/{fake_id}/overrides",
            json={"role": "Test"},
            headers={"Authorization": f"Bearer {TEST_TOKEN}"},
        )
        
        assert response.status_code == 404

    def test_patch_missing_auth_returns_401(self):
        """Test that PATCH without auth returns 401."""
        fake_id = str(uuid.uuid4())
        
        response = client.patch(
            f"/api/projects/{fake_id}/overrides",
            json={"role": "Test"},
        )
        
        assert response.status_code == 401


class TestDeleteProjectOverrides:
    """Tests for DELETE /api/projects/{project_id}/overrides"""

    def test_delete_removes_overrides(self):
        """Test that DELETE removes all overrides for project."""
        project_id = create_test_project()
        
        # Create overrides
        client.patch(
            f"/api/projects/{project_id}/overrides",
            json={
                "role": "Developer",
                "highlighted_skills": ["Python"],
            },
            headers={"Authorization": f"Bearer {TEST_TOKEN}"},
        )
        
        # Delete overrides
        response = client.delete(
            f"/api/projects/{project_id}/overrides",
            headers={"Authorization": f"Bearer {TEST_TOKEN}"},
        )
        
        assert response.status_code == 200
        assert "Overrides cleared" in response.json()["message"]
        
        # Verify overrides are gone
        get_response = client.get(
            f"/api/projects/{project_id}/overrides",
            headers={"Authorization": f"Bearer {TEST_TOKEN}"},
        )
        assert get_response.status_code == 200
        assert get_response.json()["overrides"]["role"] is None

    def test_delete_returns_404_when_no_overrides(self):
        """Test that DELETE returns 404 when no overrides exist."""
        project_id = create_test_project()
        
        # Try to delete non-existent overrides
        response = client.delete(
            f"/api/projects/{project_id}/overrides",
            headers={"Authorization": f"Bearer {TEST_TOKEN}"},
        )
        
        assert response.status_code == 404

    def test_delete_nonexistent_project_returns_404(self):
        """Test that DELETE returns 404 for nonexistent project."""
        fake_id = str(uuid.uuid4())
        
        response = client.delete(
            f"/api/projects/{fake_id}/overrides",
            headers={"Authorization": f"Bearer {TEST_TOKEN}"},
        )
        
        assert response.status_code == 404

    def test_delete_missing_auth_returns_401(self):
        """Test that DELETE without auth returns 401."""
        fake_id = str(uuid.uuid4())
        
        response = client.delete(f"/api/projects/{fake_id}/overrides")
        
        assert response.status_code == 401


class TestProjectDetailWithOverrides:
    """Tests for GET /api/projects/{project_id} including user_overrides."""

    def test_get_project_includes_user_overrides(self):
        """Test that GET project detail includes user_overrides field."""
        project_id = create_test_project()
        
        # Set some overrides
        client.patch(
            f"/api/projects/{project_id}/overrides",
            json={
                "role": "Tech Lead",
                "highlighted_skills": ["Architecture", "Python"],
            },
            headers={"Authorization": f"Bearer {TEST_TOKEN}"},
        )
        
        # Get project detail
        response = client.get(
            f"/api/projects/{project_id}",
            headers={"Authorization": f"Bearer {TEST_TOKEN}"},
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "user_overrides" in data
        assert data["user_overrides"]["role"] == "Tech Lead"
        assert data["user_overrides"]["highlighted_skills"] == ["Architecture", "Python"]

    def test_get_project_returns_null_overrides_when_none_set(self):
        """Test that GET project detail returns null user_overrides when none exist."""
        project_id = create_test_project()
        
        response = client.get(
            f"/api/projects/{project_id}",
            headers={"Authorization": f"Bearer {TEST_TOKEN}"},
        )
        
        assert response.status_code == 200
        data = response.json()
        # user_overrides should be None when no overrides are set
        assert data.get("user_overrides") is None


class TestTimelineWithOverrides:
    """Tests for GET /api/projects/timeline using override dates."""

    def test_timeline_uses_end_date_override(self):
        """Test that timeline uses end_date_override when available."""
        # Create two projects
        project1_id = create_test_project()
        project2_id = create_test_project()
        
        # Set end_date_override to make project1 appear "newer"
        client.patch(
            f"/api/projects/{project1_id}/overrides",
            json={"end_date_override": "2099-12-31"},  # Far future
            headers={"Authorization": f"Bearer {TEST_TOKEN}"},
        )
        
        # Get timeline
        response = client.get(
            "/api/projects/timeline",
            headers={"Authorization": f"Bearer {TEST_TOKEN}"},
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["count"] >= 2
        
        # Find our project in timeline
        project_ids = [entry["project"]["id"] for entry in data["timeline"]]
        assert project1_id in project_ids
        
        # Project1 should be first (newest) due to override date
        first_project = data["timeline"][0]["project"]
        assert first_project["id"] == project1_id


class TestOverridesWorkflow:
    """Integration tests for complete overrides workflow."""

    def test_create_read_update_delete_workflow(self):
        """Test complete CRUD workflow for overrides."""
        project_id = create_test_project()
        
        # 1. Initially no overrides
        get_response = client.get(
            f"/api/projects/{project_id}/overrides",
            headers={"Authorization": f"Bearer {TEST_TOKEN}"},
        )
        assert get_response.status_code == 200
        assert get_response.json()["overrides"]["role"] is None
        
        # 2. Create overrides
        create_response = client.patch(
            f"/api/projects/{project_id}/overrides",
            json={
                "role": "Developer",
                "evidence": ["Initial evidence"],
            },
            headers={"Authorization": f"Bearer {TEST_TOKEN}"},
        )
        assert create_response.status_code == 200
        assert create_response.json()["overrides"]["role"] == "Developer"
        
        # 3. Update overrides
        update_response = client.patch(
            f"/api/projects/{project_id}/overrides",
            json={
                "role": "Senior Developer",
                "evidence": ["Updated evidence", "New accomplishment"],
            },
            headers={"Authorization": f"Bearer {TEST_TOKEN}"},
        )
        assert update_response.status_code == 200
        assert update_response.json()["overrides"]["role"] == "Senior Developer"
        assert len(update_response.json()["overrides"]["evidence"]) == 2
        
        # 4. Read and verify
        read_response = client.get(
            f"/api/projects/{project_id}/overrides",
            headers={"Authorization": f"Bearer {TEST_TOKEN}"},
        )
        assert read_response.status_code == 200
        assert read_response.json()["overrides"]["role"] == "Senior Developer"
        
        # 5. Delete overrides
        delete_response = client.delete(
            f"/api/projects/{project_id}/overrides",
            headers={"Authorization": f"Bearer {TEST_TOKEN}"},
        )
        assert delete_response.status_code == 200
        
        # 6. Verify deleted
        final_response = client.get(
            f"/api/projects/{project_id}/overrides",
            headers={"Authorization": f"Bearer {TEST_TOKEN}"},
        )
        assert final_response.status_code == 200
        assert final_response.json()["overrides"]["role"] is None
