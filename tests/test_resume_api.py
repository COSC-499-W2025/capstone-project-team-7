"""Tests for resume API endpoints."""
import sys
from pathlib import Path
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).parent.parent / "backend" / "src"))

from main import app
from api.dependencies import AuthContext, get_auth_context
from api.resume_routes import get_resume_service
from cli.services.resume_storage_service import ResumeStorageError, ResumeStorageService

client = TestClient(app)


async def _override_auth() -> AuthContext:
    return AuthContext(user_id="test-user-123", access_token="test-token")


@pytest.fixture(autouse=True)
def override_auth_context():
    app.dependency_overrides[get_auth_context] = _override_auth
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def mock_resume_service():
    service = Mock(spec=ResumeStorageService)
    service.apply_access_token = Mock()
    service._decrypt_record.side_effect = lambda record: record

    def _override_get_service():
        return service

    app.dependency_overrides[get_resume_service] = _override_get_service
    yield service


class TestListResumeItems:
    def test_list_resume_items_success(self, mock_resume_service):
        mock_resume_service.get_user_resumes.return_value = [
            {
                "id": "resume-1",
                "project_name": "Project One",
                "start_date": "2024-01",
                "end_date": "2024-06",
                "created_at": "2026-01-10T10:00:00Z",
                "metadata": {"source": "scan"},
            },
            {
                "id": "resume-2",
                "project_name": "Project Two",
                "start_date": None,
                "end_date": None,
                "created_at": "2026-01-11T10:00:00Z",
                "metadata": {},
            },
        ]

        response = client.get("/api/resume/items")

        assert response.status_code == 200
        payload = response.json()
        assert payload["page"]["total"] == 2
        assert len(payload["items"]) == 2
        assert payload["items"][0]["id"] == "resume-1"

        mock_resume_service.apply_access_token.assert_called_once_with("test-token")
        mock_resume_service.get_user_resumes.assert_called_once_with("test-user-123")

    def test_list_resume_items_service_error(self, mock_resume_service):
        mock_resume_service.get_user_resumes.side_effect = ResumeStorageError("Boom")

        response = client.get("/api/resume/items")

        assert response.status_code == 500
        payload = response.json()
        assert payload["detail"]["code"] == "resume_list_error"


class TestCreateResumeItem:
    def test_create_resume_item_success(self, mock_resume_service):
        record = {
            "id": "resume-123",
            "project_name": "Resume Project",
            "start_date": "2024-01",
            "end_date": "2024-06",
            "content": "Resume Project - 2024-01 - 2024-06\n- Built X",
            "bullets": ["Built X"],
            "metadata": {"ai_generated": False},
            "source_path": "/tmp/resume.md",
            "created_at": "2026-01-12T10:00:00Z",
        }
        mock_resume_service.save_resume_record.return_value = record

        response = client.post(
            "/api/resume/items",
            json={
                "project_name": "Resume Project",
                "start_date": "2024-01",
                "end_date": "2024-06",
                "overview": "Worked on the thing.",
                "bullets": ["Built X"],
                "metadata": {"ai_generated": False},
                "source_path": "/tmp/resume.md",
            },
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["id"] == "resume-123"
        assert payload["project_name"] == "Resume Project"
        assert payload["bullets"] == ["Built X"]

        mock_resume_service.apply_access_token.assert_called_once_with("test-token")
        assert mock_resume_service.save_resume_record.call_count == 1
        _, kwargs = mock_resume_service.save_resume_record.call_args
        assert kwargs["project_name"] == "Resume Project"
        assert "Resume Project - 2024-01 - 2024-06" in kwargs["content"]

    def test_create_resume_item_service_error(self, mock_resume_service):
        mock_resume_service.save_resume_record.side_effect = ResumeStorageError("Nope")

        response = client.post(
            "/api/resume/items",
            json={"project_name": "Resume Project"},
        )

        assert response.status_code == 500
        payload = response.json()
        assert payload["detail"]["code"] == "resume_save_error"


class TestGetResumeItem:
    def test_get_resume_item_success(self, mock_resume_service):
        mock_resume_service.get_resume_item.return_value = {
            "id": "resume-123",
            "project_name": "Resume Project",
            "start_date": "2024-01",
            "end_date": None,
            "content": "Resume Project - 2024-01\n- Built X",
            "bullets": ["Built X"],
            "metadata": {},
            "source_path": None,
            "created_at": "2026-01-12T10:00:00Z",
        }

        response = client.get("/api/resume/items/resume-123")

        assert response.status_code == 200
        payload = response.json()
        assert payload["id"] == "resume-123"
        assert payload["project_name"] == "Resume Project"

        mock_resume_service.apply_access_token.assert_called_once_with("test-token")
        mock_resume_service.get_resume_item.assert_called_once_with("test-user-123", "resume-123")

    def test_get_resume_item_not_found(self, mock_resume_service):
        mock_resume_service.get_resume_item.return_value = None

        response = client.get("/api/resume/items/missing")

        assert response.status_code == 404
        payload = response.json()
        assert payload["detail"]["code"] == "resume_not_found"

    def test_get_resume_item_service_error(self, mock_resume_service):
        mock_resume_service.get_resume_item.side_effect = ResumeStorageError("Nope")

        response = client.get("/api/resume/items/resume-123")

        assert response.status_code == 500
        payload = response.json()
        assert payload["detail"]["code"] == "resume_fetch_error"


class TestUpdateResumeItem:
    def test_update_resume_item_success(self, mock_resume_service):
        mock_resume_service.update_resume_item.return_value = {
            "id": "resume-123",
            "project_name": "Updated Project",
            "start_date": "2024-01",
            "end_date": "2024-06",
            "content": "Updated content",
            "bullets": ["Updated bullet"],
            "metadata": {"edited": True},
            "source_path": "/tmp/resume.md",
            "created_at": "2026-01-12T10:00:00Z",
        }

        response = client.patch(
            "/api/resume/items/resume-123",
            json={"content": "Updated content", "bullets": ["Updated bullet"]},
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["content"] == "Updated content"
        assert payload["bullets"] == ["Updated bullet"]

        mock_resume_service.apply_access_token.assert_called_once_with("test-token")
        mock_resume_service.update_resume_item.assert_called_once_with(
            "test-user-123",
            "resume-123",
            project_name=None,
            start_date=None,
            end_date=None,
            content="Updated content",
            bullets=["Updated bullet"],
            metadata=None,
            source_path=None,
        )

    def test_update_resume_item_no_fields(self, mock_resume_service):
        response = client.patch("/api/resume/items/resume-123", json={})

        assert response.status_code == 422
        payload = response.json()
        assert payload["detail"]["code"] == "invalid_payload"

    def test_update_resume_item_not_found(self, mock_resume_service):
        mock_resume_service.update_resume_item.return_value = None

        response = client.patch(
            "/api/resume/items/resume-123",
            json={"content": "Updated content"},
        )

        assert response.status_code == 404
        payload = response.json()
        assert payload["detail"]["code"] == "resume_not_found"

    def test_update_resume_item_service_error(self, mock_resume_service):
        mock_resume_service.update_resume_item.side_effect = ResumeStorageError("Nope")

        response = client.patch(
            "/api/resume/items/resume-123",
            json={"content": "Updated content"},
        )

        assert response.status_code == 500
        payload = response.json()
        assert payload["detail"]["code"] == "resume_update_error"


class TestDeleteResumeItem:
    def test_delete_resume_item_success(self, mock_resume_service):
        mock_resume_service.delete_resume_item.return_value = True

        response = client.delete("/api/resume/items/resume-123")

        assert response.status_code == 204
        mock_resume_service.apply_access_token.assert_called_once_with("test-token")
        mock_resume_service.delete_resume_item.assert_called_once_with("test-user-123", "resume-123")

    def test_delete_resume_item_not_found(self, mock_resume_service):
        mock_resume_service.delete_resume_item.return_value = False

        response = client.delete("/api/resume/items/resume-123")

        assert response.status_code == 404
        payload = response.json()
        assert payload["detail"]["code"] == "resume_not_found"

    def test_delete_resume_item_service_error(self, mock_resume_service):
        mock_resume_service.delete_resume_item.side_effect = ResumeStorageError("Nope")

        response = client.delete("/api/resume/items/resume-123")

        assert response.status_code == 500
        payload = response.json()
        assert payload["detail"]["code"] == "resume_delete_error"


class TestResumeAuth:
    def test_resume_requires_auth(self):
        app.dependency_overrides.clear()

        response = client.get("/api/resume/items")

        assert response.status_code == 401
        payload = response.json()
        assert payload["detail"]["code"] == "unauthorized"
