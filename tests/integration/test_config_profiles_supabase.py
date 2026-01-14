import os
import uuid
import sys
from pathlib import Path

import pytest

# Run with:
# SUPABASE_URL=... SUPABASE_SERVICE_ROLE_KEY=... TEST_USER_ID=... pytest -m integration
# Optional auth header:
# TEST_JWT=... pytest -m integration

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
TEST_USER_ID = os.getenv("TEST_USER_ID")
TEST_JWT = os.getenv("TEST_JWT")

if SUPABASE_SERVICE_ROLE_KEY and SUPABASE_KEY != SUPABASE_SERVICE_ROLE_KEY:
    os.environ["SUPABASE_KEY"] = SUPABASE_SERVICE_ROLE_KEY

if not (SUPABASE_URL and (SUPABASE_SERVICE_ROLE_KEY or SUPABASE_KEY) and TEST_USER_ID):
    pytest.skip("Supabase integration env vars not set.", allow_module_level=True)

testclient_module = pytest.importorskip("fastapi.testclient")
TestClient = testclient_module.TestClient  # type: ignore

backend_src = Path(__file__).parents[2] / "backend" / "src"
sys.path.insert(0, str(backend_src))

from main import app  # type: ignore  # noqa: E402


@pytest.mark.integration
def test_config_profiles_persist_in_supabase():
    client = TestClient(app)
    profile_name = f"it_{uuid.uuid4().hex}"
    payload = {
        "user_id": TEST_USER_ID,
        "name": profile_name,
        "extensions": [".py", ".md"],
        "exclude_dirs": [".git"],
        "description": "Integration test profile",
    }
    headers = {}
    if TEST_JWT:
        headers["Authorization"] = f"Bearer {TEST_JWT}"

    post_res = client.post("/api/config/profiles", json=payload, headers=headers)
    assert post_res.status_code == 200
    post_body = post_res.json()
    assert post_body["name"] == profile_name
    assert post_body["profile"]["extensions"] == [".py", ".md"]

    get_res = client.get(
        "/api/config/profiles",
        params={"user_id": TEST_USER_ID},
        headers=headers,
    )
    assert get_res.status_code == 200
    get_body = get_res.json()
    assert "current_profile" in get_body
    assert "profiles" in get_body
    assert profile_name in get_body["profiles"]
    assert get_body["profiles"][profile_name]["extensions"] == [".py", ".md"]
