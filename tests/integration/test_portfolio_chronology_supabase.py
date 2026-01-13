import os
import sys
import types
import uuid
from pathlib import Path

import pytest

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
TEST_USER_ID = os.getenv("TEST_USER_ID")
TEST_USER_ID_2 = os.getenv("TEST_USER_ID_2")
TEST_JWT = os.getenv("TEST_JWT")

if SUPABASE_SERVICE_ROLE_KEY and SUPABASE_KEY != SUPABASE_SERVICE_ROLE_KEY:
    os.environ["SUPABASE_KEY"] = SUPABASE_SERVICE_ROLE_KEY

if not (SUPABASE_URL and (SUPABASE_SERVICE_ROLE_KEY or SUPABASE_KEY) and TEST_USER_ID and TEST_USER_ID_2 and TEST_JWT):
    pytest.skip("Supabase integration env vars not set.", allow_module_level=True)

testclient_module = pytest.importorskip("fastapi.testclient")
TestClient = testclient_module.TestClient  # type: ignore

backend_src = Path(__file__).parents[2] / "backend" / "src"
sys.path.insert(0, str(backend_src))
sys.modules["cli"] = types.ModuleType("cli")
sys.modules["cli"].__path__ = [str(backend_src / "cli")]

from main import app  # type: ignore  # noqa: E402
from cli.services.projects_service import ProjectsService  # type: ignore  # noqa: E402
from supabase import create_client  # type: ignore  # noqa: E402


def _cleanup_project(client, user_id: str, project_name: str) -> None:
    client.table("projects").delete().eq("user_id", user_id).eq("project_name", project_name).execute()


@pytest.mark.integration
def test_portfolio_chronology_scoped_to_user():
    client = TestClient(app)
    service = ProjectsService()
    supabase = create_client(SUPABASE_URL, os.environ["SUPABASE_KEY"])

    project_name_user1 = f"it_user1_{uuid.uuid4().hex}"
    project_name_user2 = f"it_user2_{uuid.uuid4().hex}"
    scan_data_user1 = {
        "skills_progress": {
            "timeline": [
                {"period_label": "2024-01", "commits": 2, "top_skills": ["Python"]}
            ]
        }
    }
    scan_data_user2 = {
        "skills_progress": {
            "timeline": [
                {"period_label": "2024-02", "commits": 4, "top_skills": ["Rust"]}
            ]
        }
    }

    service.save_scan(TEST_USER_ID, project_name_user1, "/tmp/user1", scan_data_user1)
    service.save_scan(TEST_USER_ID_2, project_name_user2, "/tmp/user2", scan_data_user2)

    try:
        headers = {"Authorization": f"Bearer {TEST_JWT}"}
        skills_res = client.get("/api/skills/timeline", headers=headers)
        assert skills_res.status_code == 200
        skills_payload = skills_res.json()
        assert any("Python" in item["skills"] for item in skills_payload["items"])
        assert all("Rust" not in item["skills"] for item in skills_payload["items"])

        chronology_res = client.get("/api/portfolio/chronology", headers=headers)
        assert chronology_res.status_code == 200
        chronology_payload = chronology_res.json()
        assert any(item["name"] == project_name_user1 for item in chronology_payload["projects"])
        assert all(item["name"] != project_name_user2 for item in chronology_payload["projects"])
    finally:
        _cleanup_project(supabase, TEST_USER_ID, project_name_user1)
        _cleanup_project(supabase, TEST_USER_ID_2, project_name_user2)


@pytest.mark.integration
def test_portfolio_chronology_auth_validation():
    client = TestClient(app)

    missing_res = client.get("/api/skills/timeline")
    assert missing_res.status_code == 401

    invalid_res = client.get("/api/skills/timeline", headers={"Authorization": "Bearer invalid"})
    assert invalid_res.status_code == 401
