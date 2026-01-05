"""Smoke tests for stubbed API scaffold.

These tests validate that the new API router is mounted and returns the
expected shapes per docs/api-spec.yaml. They exercise only the stubbed
in-memory logic to guide future implementation.
"""

import sys
from pathlib import Path

import pytest

fastapi = pytest.importorskip("fastapi")
TestClient = fastapi.testclient.TestClient  # type: ignore

# Ensure backend/src is on path for imports
backend_src = Path(__file__).parent.parent / "backend" / "src"
sys.path.insert(0, str(backend_src))

from main import app  # type: ignore


client = TestClient(app)


def test_health():
    res = client.get("/health")
    assert res.status_code == 200
    body = res.json()
    assert body.get("status") in {"ok", "healthy"}


def test_scans_stub():
    payload = {"source_path": "~/example", "use_llm": False}
    res = client.post("/api/scans", json=payload)
    assert res.status_code == 202
    body = res.json()
    assert body["state"] in {"queued", "running", "succeeded"}
    assert "scan_id" in body
    # Fetch status
    status_res = client.get(f"/api/scans/{body['scan_id']}")
    assert status_res.status_code == 200
    status_body = status_res.json()
    assert status_body["scan_id"] == body["scan_id"]


def test_projects_stub():
    create = client.post("/api/projects", json={"name": "demo"})
    assert create.status_code == 200
    proj = create.json()
    assert proj["name"] == "demo"
    project_id = proj["project_id"]

    detail = client.get(f"/api/projects/{project_id}")
    assert detail.status_code == 200
    detail_body = detail.json()
    assert detail_body["project_id"] == project_id

    # timeline should include it
    timeline = client.get("/api/projects/timeline").json()
    assert any(item["project_id"] == project_id for item in timeline)
