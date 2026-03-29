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


pytestmark = pytest.mark.usefixtures("project_test_auth_override")


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

    def test_get_overrides_for_new_project(self):
        """Test that GET returns overrides for a new project.

        New projects automatically get an inferred role ('author' or 'contributor')
        based on contribution metrics. Evidence and other user-set fields start empty.
        """
        project_id = create_test_project()

        response = client.get(
            f"/api/projects/{project_id}/overrides",
            headers={"Authorization": f"Bearer {TEST_TOKEN}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["project_id"] == project_id
        # Role is auto-inferred on project creation (defaults to 'contributor' when no git data)
        assert data["overrides"]["role"] in (None, "author", "contributor")
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
                "role": "lead",
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
        assert data["overrides"]["role"] == "lead"
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
                "role": "author",
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
        assert data["overrides"]["role"] == "author"
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
            json={"role": "contributor"},
            headers={"Authorization": f"Bearer {TEST_TOKEN}"},
        )

        # Update role
        response = client.patch(
            f"/api/projects/{project_id}/overrides",
            json={"role": "lead"},
            headers={"Authorization": f"Bearer {TEST_TOKEN}"},
        )

        assert response.status_code == 200
        assert response.json()["overrides"]["role"] == "lead"

    def test_patch_partial_update(self):
        """Test that PATCH only updates provided fields."""
        project_id = create_test_project()
        
        # Create initial overrides with multiple fields
        client.patch(
            f"/api/projects/{project_id}/overrides",
            json={
                "role": "contributor",
                "highlighted_skills": ["JavaScript"],
            },
            headers={"Authorization": f"Bearer {TEST_TOKEN}"},
        )

        # Update only role
        response = client.patch(
            f"/api/projects/{project_id}/overrides",
            json={"role": "lead"},
            headers={"Authorization": f"Bearer {TEST_TOKEN}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["overrides"]["role"] == "lead"
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

    def test_delete_returns_404_on_second_delete(self):
        """Test that DELETE returns 404 when overrides have already been deleted."""
        project_id = create_test_project()

        # First delete succeeds (new projects have auto-inferred overrides)
        client.delete(
            f"/api/projects/{project_id}/overrides",
            headers={"Authorization": f"Bearer {TEST_TOKEN}"},
        )

        # Second delete should return 404 — nothing left to delete
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
                "role": "lead",
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
        assert data["user_overrides"]["role"] == "lead"
        assert data["user_overrides"]["highlighted_skills"] == ["Architecture", "Python"]

    def test_get_project_includes_user_overrides_with_inferred_role(self):
        """Test that GET project detail includes user_overrides with the auto-inferred role.

        New projects automatically get an inferred role via save_scan, so user_overrides
        is always populated (never None) after project creation.
        """
        project_id = create_test_project()

        response = client.get(
            f"/api/projects/{project_id}",
            headers={"Authorization": f"Bearer {TEST_TOKEN}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "user_overrides" in data
        overrides = data["user_overrides"]
        # Auto-inferred role is set; evidence and highlights start empty
        assert overrides is not None
        assert overrides.get("role") in ("author", "contributor")
        assert overrides.get("evidence") == []
        assert overrides.get("highlighted_skills") == []


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
        
        # 1. New project has auto-inferred role (author or contributor)
        get_response = client.get(
            f"/api/projects/{project_id}/overrides",
            headers={"Authorization": f"Bearer {TEST_TOKEN}"},
        )
        assert get_response.status_code == 200
        assert get_response.json()["overrides"]["role"] in (None, "author", "contributor")
        
        # 2. Update overrides (project already has auto-inferred 'contributor' role)
        create_response = client.patch(
            f"/api/projects/{project_id}/overrides",
            json={
                "role": "contributor",
                "evidence": ["Initial evidence"],
            },
            headers={"Authorization": f"Bearer {TEST_TOKEN}"},
        )
        assert create_response.status_code == 200
        assert create_response.json()["overrides"]["role"] == "contributor"

        # 3. Update overrides
        update_response = client.patch(
            f"/api/projects/{project_id}/overrides",
            json={
                "role": "lead",
                "evidence": ["Updated evidence", "New accomplishment"],
            },
            headers={"Authorization": f"Bearer {TEST_TOKEN}"},
        )
        assert update_response.status_code == 200
        assert update_response.json()["overrides"]["role"] == "lead"
        assert len(update_response.json()["overrides"]["evidence"]) == 2

        # 4. Read and verify
        read_response = client.get(
            f"/api/projects/{project_id}/overrides",
            headers={"Authorization": f"Bearer {TEST_TOKEN}"},
        )
        assert read_response.status_code == 200
        assert read_response.json()["overrides"]["role"] == "lead"
        
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


class TestEvidenceOverrides:
    """Tests for evidence of success CRUD via project overrides."""

    def test_set_evidence_bullets(self):
        """PATCH overrides with evidence stores and returns the bullets."""
        project_id = create_test_project()

        bullets = ["Throughput improved 35%", "Led 3-person team", "Zero downtime deployment"]
        response = client.patch(
            f"/api/projects/{project_id}/overrides",
            json={"evidence": bullets},
            headers={"Authorization": f"Bearer {TEST_TOKEN}"},
        )

        assert response.status_code == 200
        assert response.json()["overrides"]["evidence"] == bullets

        # Confirm persisted via GET
        get_response = client.get(
            f"/api/projects/{project_id}/overrides",
            headers={"Authorization": f"Bearer {TEST_TOKEN}"},
        )
        assert get_response.status_code == 200
        assert get_response.json()["overrides"]["evidence"] == bullets

    def test_evidence_survives_role_only_patch(self):
        """PATCHing only role does not erase existing evidence."""
        project_id = create_test_project()

        # Set evidence first
        client.patch(
            f"/api/projects/{project_id}/overrides",
            json={"evidence": ["Received positive client feedback"]},
            headers={"Authorization": f"Bearer {TEST_TOKEN}"},
        )

        # Update only role — evidence should be untouched
        client.patch(
            f"/api/projects/{project_id}/overrides",
            json={"role": "lead"},
            headers={"Authorization": f"Bearer {TEST_TOKEN}"},
        )

        get_response = client.get(
            f"/api/projects/{project_id}/overrides",
            headers={"Authorization": f"Bearer {TEST_TOKEN}"},
        )
        assert get_response.status_code == 200
        overrides = get_response.json()["overrides"]
        assert overrides["role"] == "lead"
        assert overrides["evidence"] == ["Received positive client feedback"]

    def test_clear_evidence_with_empty_list(self):
        """Passing evidence=[] clears all bullets."""
        project_id = create_test_project()

        # Set evidence
        client.patch(
            f"/api/projects/{project_id}/overrides",
            json={"evidence": ["Passed all evaluations"]},
            headers={"Authorization": f"Bearer {TEST_TOKEN}"},
        )

        # Clear with empty list
        response = client.patch(
            f"/api/projects/{project_id}/overrides",
            json={"evidence": []},
            headers={"Authorization": f"Bearer {TEST_TOKEN}"},
        )

        assert response.status_code == 200
        assert response.json()["overrides"]["evidence"] == []
