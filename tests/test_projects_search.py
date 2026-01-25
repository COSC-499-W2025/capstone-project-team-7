import base64
import json
import uuid

import pytest
from fastapi.testclient import TestClient

from main import app


def _make_token(sub: str) -> str:
    def b64u(obj: str) -> str:
        return base64.urlsafe_b64encode(obj.encode()).decode().rstrip("=")

    header = b64u(json.dumps({"alg": "HS256", "typ": "JWT"}))
    payload = b64u(json.dumps({"sub": sub}))
    return f"{header}.{payload}.sig"


class FakeProjectsService:
    def __init__(self):
        self.project_id = str(uuid.uuid4())
        self.project = {
            "id": self.project_id,
            "project_name": "budgetTracker",
            "scan_data": {
                "files": [
                    {
                        "path": "budgetTracker/backend/src/config/upstash.js",
                        "mime_type": "application/javascript",
                        "size_bytes": 1234,
                    }
                ]
            },
        }

    def get_user_projects_with_scan_data(self, user_id: str):
        return [self.project]

    def get_project_scan(self, user_id: str, project_id: str):
        if project_id == self.project_id:
            return self.project
        return None


@pytest.fixture(autouse=True)
def patch_projects_service(monkeypatch):
    """Replace the projects service singleton with a fake one for tests."""
    import api.project_routes as project_routes

    fake = FakeProjectsService()
    monkeypatch.setattr(project_routes, "_projects_service", fake)
    return fake


def test_search_files_returns_matches(patch_projects_service):
    token = _make_token("test-user")
    client = TestClient(app)

    resp = client.get(
        "/api/projects/search",
        params={"q": "upstash"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert data["page"]["total"] == 1
    assert len(data["items"]) == 1
    item = data["items"][0]
    assert item["path"].endswith("upstash.js")


def test_search_empty_query_returns_empty(patch_projects_service):
    token = _make_token("test-user")
    client = TestClient(app)

    resp = client.get(
        "/api/projects/search",
        params={"q": ""},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["items"] == []
    assert data["page"]["total"] == 0
