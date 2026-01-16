"""
Tests for GET /api/dedup endpoint.

Validates dedup report generation and authentication.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Ensure backend/src is on path for imports
PROJECT_ROOT = Path(__file__).parent.parent
BACKEND_SRC = PROJECT_ROOT / "backend" / "src"
sys.path.insert(0, str(BACKEND_SRC))
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

fastapi = pytest.importorskip("fastapi")
from fastapi.testclient import TestClient

from backend.src.main import app
from api.dependencies import AuthContext, get_auth_context
from api import spec_routes


TEST_USER_ID = "test-user-123"
TEST_ACCESS_TOKEN = "test-token"
TEST_PROJECT_ID = "proj-123"


async def _override_auth() -> AuthContext:
    return AuthContext(user_id=TEST_USER_ID, access_token=TEST_ACCESS_TOKEN)


class FakeProjectsService:
    def __init__(self, project: dict) -> None:
        self._project = project

    def get_project_scan(self, user_id: str, project_id: str):
        if user_id != TEST_USER_ID:
            return None
        if project_id != self._project.get("id"):
            return None
        return self._project


@pytest.fixture
def client(monkeypatch):
    app.dependency_overrides[get_auth_context] = _override_auth

    project = {
        "id": TEST_PROJECT_ID,
        "scan_data": {
            "files": [
                {
                    "path": "dup-a.txt",
                    "size_bytes": 100,
                    "mime_type": "text/plain",
                    "file_hash": "hash-1",
                },
                {
                    "path": "dup-b.txt",
                    "size_bytes": 100,
                    "mime_type": "text/plain",
                    "file_hash": "hash-1",
                },
                {
                    "path": "unique.txt",
                    "size_bytes": 50,
                    "mime_type": "text/plain",
                    "file_hash": "hash-2",
                },
            ]
        },
    }
    fake_service = FakeProjectsService(project)
    monkeypatch.setattr(spec_routes, "_get_projects_service", lambda: fake_service)

    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def unauthenticated_client():
    app.dependency_overrides.clear()
    return TestClient(app)


def test_dedup_report_returns_groups(client):
    response = client.get("/api/dedup", params={"project_id": TEST_PROJECT_ID})
    assert response.status_code == 200
    body = response.json()

    summary = body["summary"]
    assert summary["total_files_analyzed"] == 3
    assert summary["files_with_hash"] == 3
    assert summary["duplicate_groups_count"] == 1
    assert summary["total_duplicate_files"] == 2
    assert summary["total_wasted_bytes"] == 100
    assert summary["space_savings_percent"] == 50.0

    groups = body["duplicate_groups"]
    assert len(groups) == 1
    assert groups[0]["hash"] == "hash-1"
    assert groups[0]["file_count"] == 2
    assert groups[0]["wasted_bytes"] == 100


def test_dedup_missing_project_returns_404(client):
    response = client.get("/api/dedup", params={"project_id": "missing"})
    assert response.status_code == 404


def test_dedup_requires_auth(unauthenticated_client):
    response = unauthenticated_client.get("/api/dedup", params={"project_id": TEST_PROJECT_ID})
    assert response.status_code == 401
