import uuid

from fastapi.testclient import TestClient

import api.project_routes as project_routes
from main import app


TEST_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI5ODcwZWRiNS0yNzQxLTRjMGEtYjVjZC00OTRhNDk4Zjc0ODUifQ.test"
TEST_USER_ID = "9870edb5-2741-4c0a-b5cd-494a498f7485"


class _FakeProjectsService:
    def __init__(self, *, project_exists: bool = True, delete_ok: bool = True, delete_error: str | None = None):
        self.project_exists = project_exists
        self.delete_ok = delete_ok
        self.delete_error = delete_error
        self.delete_called_with: str | None = None
        self.scan_called_with: tuple[str, str] | None = None

    def get_project_scan(self, user_id: str, project_id: str):
        self.scan_called_with = (user_id, project_id)
        if not self.project_exists:
            return None
        return {"id": project_id, "user_id": user_id}

    def delete_project_thumbnail(self, project_id: str):
        self.delete_called_with = project_id
        return self.delete_ok, self.delete_error


client = TestClient(app)


def test_delete_thumbnail_success(monkeypatch):
    project_id = str(uuid.uuid4())
    fake = _FakeProjectsService(project_exists=True, delete_ok=True)
    monkeypatch.setattr(project_routes, "get_projects_service", lambda: fake)

    response = client.delete(
        f"/api/projects/{project_id}/thumbnail",
        headers={"Authorization": f"Bearer {TEST_TOKEN}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True
    assert data["message"] == "Thumbnail removed successfully"
    assert fake.scan_called_with == (TEST_USER_ID, project_id)
    assert fake.delete_called_with == project_id


def test_delete_thumbnail_not_found(monkeypatch):
    project_id = str(uuid.uuid4())
    fake = _FakeProjectsService(project_exists=False)
    monkeypatch.setattr(project_routes, "get_projects_service", lambda: fake)

    response = client.delete(
        f"/api/projects/{project_id}/thumbnail",
        headers={"Authorization": f"Bearer {TEST_TOKEN}"},
    )

    assert response.status_code == 404
    assert f"Project {project_id} not found" in response.json()["detail"]


def test_delete_thumbnail_service_error(monkeypatch):
    project_id = str(uuid.uuid4())
    fake = _FakeProjectsService(project_exists=True, delete_ok=False, delete_error="storage failure")
    monkeypatch.setattr(project_routes, "get_projects_service", lambda: fake)

    response = client.delete(
        f"/api/projects/{project_id}/thumbnail",
        headers={"Authorization": f"Bearer {TEST_TOKEN}"},
    )

    assert response.status_code == 500
    assert "Failed to delete thumbnail: storage failure" in response.json()["detail"]


def test_delete_thumbnail_requires_auth(monkeypatch):
    fake = _FakeProjectsService(project_exists=True, delete_ok=True)
    monkeypatch.setattr(project_routes, "get_projects_service", lambda: fake)

    response = client.delete(f"/api/projects/{uuid.uuid4()}/thumbnail")

    assert response.status_code == 401
