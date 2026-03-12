"""Tests for User Resume API routes."""

from unittest.mock import MagicMock, patch
import pytest
from fastapi.testclient import TestClient

from backend.src.main import app
from api.dependencies import AuthContext, get_auth_context
from api.user_resume_routes import get_user_resume_service
from services.services.user_resume_service import UserResumeService, UserResumeServiceError


client = TestClient(app)


async def _override_auth() -> AuthContext:
    return AuthContext(user_id="user-123", access_token="test-token")


@pytest.fixture
def mock_service():
    """Create a mock UserResumeService."""
    service = MagicMock(spec=UserResumeService)
    service.apply_access_token = MagicMock()
    return service


@pytest.fixture(autouse=True)
def override_auth_context():
    """Override auth context for all tests."""
    app.dependency_overrides[get_auth_context] = _override_auth
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def override_service(mock_service):
    """Override the resume service dependency."""
    app.dependency_overrides[get_user_resume_service] = lambda: mock_service
    yield mock_service
    if get_user_resume_service in app.dependency_overrides:
        del app.dependency_overrides[get_user_resume_service]


# ============================================================================
# Template List Tests
# ============================================================================


def test_list_templates_returns_available_templates():
    """Test that list templates returns all available templates."""
    response = client.get("/api/user-resumes/templates")
    assert response.status_code == 200
    payload = response.json()
    assert "templates" in payload
    assert len(payload["templates"]) >= 1
    
    template_ids = [t["id"] for t in payload["templates"]]
    assert "jake" in template_ids
    assert "classic" in template_ids
    assert "modern" in template_ids


# ============================================================================
# List Resumes Tests
# ============================================================================


def test_list_resumes_returns_empty_list(override_service):
    """Test listing resumes when user has none."""
    override_service.list_resumes.return_value = ([], 0)
    
    response = client.get("/api/user-resumes")
    assert response.status_code == 200
    payload = response.json()
    assert payload["items"] == []
    assert payload["page"]["total"] == 0
    assert payload["page"]["limit"] == 20
    assert payload["page"]["offset"] == 0


def test_list_resumes_returns_user_resumes(override_service):
    """Test listing resumes returns user's resumes."""
    mock_resumes = [
        {
            "id": "resume-1",
            "name": "My Resume",
            "template": "jake",
            "is_latex_mode": True,
            "metadata": {},
            "created_at": "2026-03-11T10:00:00Z",
            "updated_at": "2026-03-11T10:00:00Z",
        },
        {
            "id": "resume-2",
            "name": "Second Resume",
            "template": "modern",
            "is_latex_mode": False,
            "metadata": {},
            "created_at": "2026-03-10T10:00:00Z",
            "updated_at": "2026-03-10T10:00:00Z",
        },
    ]
    override_service.list_resumes.return_value = (mock_resumes, 2)
    
    response = client.get("/api/user-resumes")
    assert response.status_code == 200
    payload = response.json()
    assert len(payload["items"]) == 2
    assert payload["page"]["total"] == 2
    assert payload["items"][0]["name"] == "My Resume"
    assert payload["items"][1]["name"] == "Second Resume"


def test_list_resumes_with_pagination(override_service):
    """Test listing resumes with pagination parameters."""
    override_service.list_resumes.return_value = ([], 50)
    
    response = client.get("/api/user-resumes?limit=10&offset=20")
    assert response.status_code == 200
    payload = response.json()
    assert payload["page"]["limit"] == 10
    assert payload["page"]["offset"] == 20
    assert payload["page"]["total"] == 50
    
    override_service.list_resumes.assert_called_once_with("user-123", limit=10, offset=20)


def test_list_resumes_handles_service_error(override_service):
    """Test that service errors are handled properly."""
    override_service.list_resumes.side_effect = UserResumeServiceError("Database error")
    
    response = client.get("/api/user-resumes")
    assert response.status_code == 500
    payload = response.json()
    assert payload["detail"]["code"] == "resume_list_error"


# ============================================================================
# Create Resume Tests
# ============================================================================


def test_create_resume_with_defaults(override_service):
    """Test creating a resume with default values."""
    override_service.create_resume.return_value = {
        "id": "new-resume-id",
        "name": "Untitled Resume",
        "template": "jake",
        "is_latex_mode": True,
        "metadata": {},
        "latex_content": None,
        "structured_data": {},
        "created_at": "2026-03-11T10:00:00Z",
        "updated_at": "2026-03-11T10:00:00Z",
    }
    
    response = client.post("/api/user-resumes", json={})
    assert response.status_code == 201
    payload = response.json()
    assert payload["id"] == "new-resume-id"
    assert payload["name"] == "Untitled Resume"
    assert payload["template"] == "jake"


def test_create_resume_with_custom_values(override_service):
    """Test creating a resume with custom values."""
    override_service.create_resume.return_value = {
        "id": "new-resume-id",
        "name": "Software Engineer Resume",
        "template": "modern",
        "is_latex_mode": False,
        "metadata": {"job_target": "SWE"},
        "latex_content": None,
        "structured_data": {"contact": {"full_name": "John Doe"}},
        "created_at": "2026-03-11T10:00:00Z",
        "updated_at": "2026-03-11T10:00:00Z",
    }
    
    response = client.post(
        "/api/user-resumes",
        json={
            "name": "Software Engineer Resume",
            "template": "modern",
            "is_latex_mode": False,
            "metadata": {"job_target": "SWE"},
            "structured_data": {"contact": {"full_name": "John Doe"}},
        },
    )
    assert response.status_code == 201
    payload = response.json()
    assert payload["name"] == "Software Engineer Resume"
    assert payload["template"] == "modern"
    assert payload["is_latex_mode"] is False


def test_create_resume_rejects_invalid_template(override_service):
    """Test that invalid templates are rejected."""
    override_service.create_resume.side_effect = UserResumeServiceError(
        "Invalid template: bad_template"
    )
    
    response = client.post(
        "/api/user-resumes",
        json={"template": "bad_template"},
    )
    assert response.status_code == 422
    payload = response.json()
    assert payload["detail"]["code"] == "invalid_template"


# ============================================================================
# Get Resume Tests
# ============================================================================


def test_get_resume_returns_full_record(override_service):
    """Test getting a single resume with full content."""
    override_service.get_resume.return_value = {
        "id": "resume-1",
        "name": "My Resume",
        "template": "jake",
        "is_latex_mode": True,
        "metadata": {},
        "latex_content": "\\documentclass{article}",
        "structured_data": {"contact": {"full_name": "John Doe"}},
        "created_at": "2026-03-11T10:00:00Z",
        "updated_at": "2026-03-11T10:00:00Z",
    }
    
    response = client.get("/api/user-resumes/resume-1")
    assert response.status_code == 200
    payload = response.json()
    assert payload["id"] == "resume-1"
    assert payload["latex_content"] == "\\documentclass{article}"
    assert payload["structured_data"]["contact"]["full_name"] == "John Doe"


def test_get_resume_not_found(override_service):
    """Test getting a non-existent resume."""
    override_service.get_resume.return_value = None
    
    response = client.get("/api/user-resumes/nonexistent")
    assert response.status_code == 404
    payload = response.json()
    assert payload["detail"]["code"] == "resume_not_found"


# ============================================================================
# Update Resume Tests
# ============================================================================


def test_update_resume_partial_update(override_service):
    """Test updating a resume with partial data."""
    override_service.update_resume.return_value = {
        "id": "resume-1",
        "name": "Updated Name",
        "template": "jake",
        "is_latex_mode": True,
        "metadata": {},
        "latex_content": None,
        "structured_data": {},
        "created_at": "2026-03-11T10:00:00Z",
        "updated_at": "2026-03-11T11:00:00Z",
    }
    
    response = client.patch(
        "/api/user-resumes/resume-1",
        json={"name": "Updated Name"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["name"] == "Updated Name"


def test_update_resume_rejects_empty_payload(override_service):
    """Test that empty update payloads are rejected."""
    response = client.patch("/api/user-resumes/resume-1", json={})
    assert response.status_code == 422
    payload = response.json()
    assert payload["detail"]["code"] == "invalid_payload"


def test_update_resume_not_found(override_service):
    """Test updating a non-existent resume."""
    override_service.update_resume.return_value = None
    
    response = client.patch(
        "/api/user-resumes/nonexistent",
        json={"name": "New Name"},
    )
    assert response.status_code == 404


# ============================================================================
# Delete Resume Tests
# ============================================================================


def test_delete_resume_success(override_service):
    """Test deleting a resume successfully."""
    override_service.delete_resume.return_value = True
    
    response = client.delete("/api/user-resumes/resume-1")
    assert response.status_code == 204


def test_delete_resume_not_found(override_service):
    """Test deleting a non-existent resume."""
    override_service.delete_resume.return_value = False
    
    response = client.delete("/api/user-resumes/nonexistent")
    assert response.status_code == 404


# ============================================================================
# Duplicate Resume Tests
# ============================================================================


def test_duplicate_resume_success(override_service):
    """Test duplicating a resume successfully."""
    override_service.duplicate_resume.return_value = {
        "id": "new-resume-id",
        "name": "My Resume (Copy)",
        "template": "jake",
        "is_latex_mode": True,
        "metadata": {"duplicated_from": "resume-1"},
        "latex_content": "\\documentclass{article}",
        "structured_data": {},
        "created_at": "2026-03-11T11:00:00Z",
        "updated_at": "2026-03-11T11:00:00Z",
    }
    
    response = client.post("/api/user-resumes/resume-1/duplicate", json={})
    assert response.status_code == 201
    payload = response.json()
    assert payload["name"] == "My Resume (Copy)"
    assert payload["metadata"]["duplicated_from"] == "resume-1"


def test_duplicate_resume_with_custom_name(override_service):
    """Test duplicating a resume with a custom name."""
    override_service.duplicate_resume.return_value = {
        "id": "new-resume-id",
        "name": "Custom Copy Name",
        "template": "jake",
        "is_latex_mode": True,
        "metadata": {"duplicated_from": "resume-1"},
        "latex_content": None,
        "structured_data": {},
        "created_at": "2026-03-11T11:00:00Z",
        "updated_at": "2026-03-11T11:00:00Z",
    }
    
    response = client.post(
        "/api/user-resumes/resume-1/duplicate",
        json={"new_name": "Custom Copy Name"},
    )
    assert response.status_code == 201
    payload = response.json()
    assert payload["name"] == "Custom Copy Name"


def test_duplicate_resume_not_found(override_service):
    """Test duplicating a non-existent resume."""
    override_service.duplicate_resume.side_effect = UserResumeServiceError(
        "Resume not found."
    )
    
    response = client.post("/api/user-resumes/nonexistent/duplicate", json={})
    assert response.status_code == 404


# ============================================================================
# Auth Tests
# ============================================================================


def test_missing_auth_returns_401():
    """Test that missing auth returns 401."""
    app.dependency_overrides.clear()
    
    response = client.get("/api/user-resumes")
    assert response.status_code == 401
    payload = response.json()
    assert payload["detail"]["code"] == "unauthorized"
