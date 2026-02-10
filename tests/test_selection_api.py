"""Tests for selection API endpoints."""
import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, patch
from fastapi.testclient import TestClient
from datetime import datetime

# Add backend/src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend" / "src"))

from main import app
from api.dependencies import AuthContext, get_auth_context
from services.selection_service import SelectionService, SelectionServiceError


client = TestClient(app)


async def _override_auth() -> AuthContext:
    """Mock auth context for testing."""
    return AuthContext(user_id="test-user-123", access_token="test-token")


@pytest.fixture(autouse=True)
def override_auth_context():
    """Override auth dependency for all tests."""
    app.dependency_overrides[get_auth_context] = _override_auth
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def mock_selection_service():
    """Mock SelectionService for testing."""
    from api.selection_routes import get_selection_service
    
    service = Mock(spec=SelectionService)
    
    def _override_get_service():
        return service
    
    # Set override AFTER auth override (since autouse runs first)
    app.dependency_overrides[get_selection_service] = _override_get_service
    yield service
    # Don't clear here - let override_auth_context handle it


class TestPostSelection:
    """Tests for POST /api/selection endpoint."""
    
    def test_save_new_selection(self, mock_selection_service):
        """Test saving selection preferences for the first time."""
        mock_selection_service.save_user_selections.return_value = {
            "user_id": "test-user-123",
            "project_order": ["proj-1", "proj-2"],
            "skill_order": ["Python", "JavaScript"],
            "selected_project_ids": ["proj-1"],
            "selected_skill_ids": ["Python"],
            "created_at": datetime(2026, 1, 15, 10, 0, 0),
            "updated_at": datetime(2026, 1, 15, 10, 0, 0),
        }
        
        response = client.post(
            "/api/selection",
            json={
                "project_order": ["proj-1", "proj-2"],
                "skill_order": ["Python", "JavaScript"],
                "selected_project_ids": ["proj-1"],
                "selected_skill_ids": ["Python"],
            },
        )
        
        assert response.status_code == 200
        payload = response.json()
        assert payload["user_id"] == "test-user-123"
        assert payload["project_order"] == ["proj-1", "proj-2"]
        assert payload["skill_order"] == ["Python", "JavaScript"]
        assert payload["selected_project_ids"] == ["proj-1"]
        assert payload["selected_skill_ids"] == ["Python"]
        
        # Verify service was called correctly
        mock_selection_service.save_user_selections.assert_called_once_with(
            user_id="test-user-123",
            project_order=["proj-1", "proj-2"],
            skill_order=["Python", "JavaScript"],
            selected_project_ids=["proj-1"],
            selected_skill_ids=["Python"],
        )
    
    def test_save_partial_selection(self, mock_selection_service):
        """Test saving only some fields (partial update)."""
        mock_selection_service.save_user_selections.return_value = {
            "user_id": "test-user-123",
            "project_order": ["proj-3", "proj-1"],
            "skill_order": [],
            "selected_project_ids": [],
            "selected_skill_ids": [],
            "created_at": datetime(2026, 1, 15, 10, 0, 0),
            "updated_at": datetime(2026, 1, 15, 11, 0, 0),
        }
        
        response = client.post(
            "/api/selection",
            json={"project_order": ["proj-3", "proj-1"]},
        )
        
        assert response.status_code == 200
        payload = response.json()
        assert payload["project_order"] == ["proj-3", "proj-1"]
        
        # Verify only project_order was passed to service
        mock_selection_service.save_user_selections.assert_called_once_with(
            user_id="test-user-123",
            project_order=["proj-3", "proj-1"],
            skill_order=None,
            selected_project_ids=None,
            selected_skill_ids=None,
        )
    
    def test_save_empty_arrays(self, mock_selection_service):
        """Test saving empty arrays (clearing selections)."""
        mock_selection_service.save_user_selections.return_value = {
            "user_id": "test-user-123",
            "project_order": [],
            "skill_order": [],
            "selected_project_ids": [],
            "selected_skill_ids": [],
            "created_at": datetime(2026, 1, 15, 10, 0, 0),
            "updated_at": datetime(2026, 1, 15, 12, 0, 0),
        }
        
        response = client.post(
            "/api/selection",
            json={
                "project_order": [],
                "skill_order": [],
                "selected_project_ids": [],
                "selected_skill_ids": [],
            },
        )
        
        assert response.status_code == 200
        payload = response.json()
        assert payload["project_order"] == []
        assert payload["skill_order"] == []
        assert payload["selected_project_ids"] == []
        assert payload["selected_skill_ids"] == []
    
    def test_save_selection_service_error(self, mock_selection_service):
        """Test error handling when service fails."""
        mock_selection_service.save_user_selections.side_effect = SelectionServiceError(
            "Database connection failed"
        )
        
        response = client.post(
            "/api/selection",
            json={"project_order": ["proj-1"]},
        )
        
        assert response.status_code == 500
        payload = response.json()
        assert payload["detail"]["code"] == "save_failed"
    
    def test_save_selection_without_auth(self):
        """Test that endpoint requires authentication."""
        app.dependency_overrides.clear()
        
        response = client.post(
            "/api/selection",
            json={"project_order": ["proj-1"]},
        )
        
        assert response.status_code == 401
        payload = response.json()
        assert payload["detail"]["code"] == "unauthorized"


class TestGetSelection:
    """Tests for GET /api/selection endpoint."""
    
    def test_get_existing_selection(self, mock_selection_service):
        """Test retrieving existing selection preferences."""
        mock_selection_service.get_user_selections.return_value = {
            "user_id": "test-user-123",
            "project_order": ["proj-2", "proj-1"],
            "skill_order": ["Python", "Go"],
            "selected_project_ids": ["proj-2"],
            "selected_skill_ids": ["Python", "Go"],
            "created_at": datetime(2026, 1, 15, 10, 0, 0),
            "updated_at": datetime(2026, 1, 15, 14, 0, 0),
        }
        
        response = client.get("/api/selection")
        
        assert response.status_code == 200
        payload = response.json()
        assert payload["user_id"] == "test-user-123"
        assert payload["project_order"] == ["proj-2", "proj-1"]
        assert payload["skill_order"] == ["Python", "Go"]
        assert payload["selected_project_ids"] == ["proj-2"]
        assert payload["selected_skill_ids"] == ["Python", "Go"]
        
        mock_selection_service.get_user_selections.assert_called_once_with("test-user-123")
    
    def test_get_nonexistent_selection(self, mock_selection_service):
        """Test retrieving selection when none exists (returns defaults)."""
        mock_selection_service.get_user_selections.return_value = None
        
        response = client.get("/api/selection")
        
        assert response.status_code == 200
        payload = response.json()
        assert payload["user_id"] == "test-user-123"
        assert payload["project_order"] == []
        assert payload["skill_order"] == []
        assert payload["selected_project_ids"] == []
        assert payload["selected_skill_ids"] == []
    
    def test_get_selection_with_null_arrays(self, mock_selection_service):
        """Test handling of null values in database response."""
        mock_selection_service.get_user_selections.return_value = {
            "user_id": "test-user-123",
            "project_order": None,
            "skill_order": None,
            "selected_project_ids": None,
            "selected_skill_ids": None,
            "created_at": datetime(2026, 1, 15, 10, 0, 0),
            "updated_at": datetime(2026, 1, 15, 10, 0, 0),
        }
        
        response = client.get("/api/selection")
        
        assert response.status_code == 200
        payload = response.json()
        assert payload["project_order"] == []
        assert payload["skill_order"] == []
        assert payload["selected_project_ids"] == []
        assert payload["selected_skill_ids"] == []
    
    def test_get_selection_service_error(self, mock_selection_service):
        """Test error handling when service fails."""
        mock_selection_service.get_user_selections.side_effect = SelectionServiceError(
            "Database query failed"
        )
        
        response = client.get("/api/selection")
        
        assert response.status_code == 500
        payload = response.json()
        assert payload["detail"]["code"] == "retrieval_failed"
    
    def test_get_selection_without_auth(self):
        """Test that endpoint requires authentication."""
        app.dependency_overrides.clear()
        
        response = client.get("/api/selection")
        
        assert response.status_code == 401
        payload = response.json()
        assert payload["detail"]["code"] == "unauthorized"


class TestDeleteSelection:
    """Tests for DELETE /api/selection endpoint."""
    
    def test_delete_existing_selection(self, mock_selection_service):
        """Test deleting existing selection preferences."""
        mock_selection_service.delete_user_selections.return_value = True
        
        response = client.delete("/api/selection")
        
        assert response.status_code == 204
        assert response.content == b""
        
        mock_selection_service.delete_user_selections.assert_called_once_with("test-user-123")
    
    def test_delete_nonexistent_selection(self, mock_selection_service):
        """Test deleting when no selection exists (should still succeed)."""
        mock_selection_service.delete_user_selections.return_value = False
        
        response = client.delete("/api/selection")
        
        assert response.status_code == 204
    
    def test_delete_selection_service_error(self, mock_selection_service):
        """Test error handling when service fails."""
        mock_selection_service.delete_user_selections.side_effect = SelectionServiceError(
            "Database deletion failed"
        )
        
        response = client.delete("/api/selection")
        
        assert response.status_code == 500
        payload = response.json()
        assert payload["detail"]["code"] == "deletion_failed"
    
    def test_delete_selection_without_auth(self):
        """Test that endpoint requires authentication."""
        app.dependency_overrides.clear()
        
        response = client.delete("/api/selection")
        
        assert response.status_code == 401
        payload = response.json()
        assert payload["detail"]["code"] == "unauthorized"


class TestSelectionIntegration:
    """Integration tests for selection workflow."""
    
    def test_save_retrieve_delete_workflow(self, mock_selection_service):
        """Test complete workflow: save -> retrieve -> delete."""
        # Step 1: Save selection
        save_data = {
            "user_id": "test-user-123",
            "project_order": ["proj-1", "proj-2"],
            "skill_order": ["Python"],
            "selected_project_ids": ["proj-1"],
            "selected_skill_ids": ["Python"],
            "created_at": datetime(2026, 1, 15, 10, 0, 0),
            "updated_at": datetime(2026, 1, 15, 10, 0, 0),
        }
        mock_selection_service.save_user_selections.return_value = save_data
        
        save_response = client.post(
            "/api/selection",
            json={
                "project_order": ["proj-1", "proj-2"],
                "skill_order": ["Python"],
                "selected_project_ids": ["proj-1"],
                "selected_skill_ids": ["Python"],
            },
        )
        assert save_response.status_code == 200
        
        # Step 2: Retrieve selection
        mock_selection_service.get_user_selections.return_value = save_data
        
        get_response = client.get("/api/selection")
        assert get_response.status_code == 200
        get_payload = get_response.json()
        assert get_payload["project_order"] == ["proj-1", "proj-2"]
        
        # Step 3: Delete selection
        mock_selection_service.delete_user_selections.return_value = True
        
        delete_response = client.delete("/api/selection")
        assert delete_response.status_code == 204
        
        # Step 4: Verify deletion
        mock_selection_service.get_user_selections.return_value = None
        
        verify_response = client.get("/api/selection")
        assert verify_response.status_code == 200
        verify_payload = verify_response.json()
        assert verify_payload["project_order"] == []
