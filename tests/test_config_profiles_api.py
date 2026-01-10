import sys
from pathlib import Path

import pytest

testclient_module = pytest.importorskip("fastapi.testclient")
TestClient = testclient_module.TestClient  # type: ignore

backend_src = Path(__file__).parent.parent / "backend" / "src"
sys.path.insert(0, str(backend_src))

from main import app  # type: ignore
from api import spec_routes  # type: ignore


class FakeConfigManager:
    def __init__(self) -> None:
        self.config = {
            "scan_profiles": {
                "sample": {
                    "extensions": [".py"],
                    "exclude_dirs": [".git"],
                    "description": "Sample profile",
                }
            },
            "current_profile": "sample",
        }

    def get_current_profile(self) -> str:
        return self.config.get("current_profile", "sample")

    def create_custom_profile(
        self,
        name: str,
        extensions: list,
        exclude_dirs: list = None,
        description: str = "Custom profile",
    ) -> bool:
        if name in self.config["scan_profiles"]:
            return False
        self.config["scan_profiles"][name] = {
            "extensions": extensions or [],
            "exclude_dirs": exclude_dirs or [],
            "description": description,
        }
        return True

    def update_profile(
        self,
        name: str,
        extensions: list = None,
        exclude_dirs: list = None,
        description: str = None,
    ) -> bool:
        if name not in self.config["scan_profiles"]:
            return False
        profile = self.config["scan_profiles"][name]
        if extensions is not None:
            profile["extensions"] = extensions
        if exclude_dirs is not None:
            profile["exclude_dirs"] = exclude_dirs
        if description is not None:
            profile["description"] = description
        return True


def test_get_config_profiles_returns_single_json_object(monkeypatch):
    manager = FakeConfigManager()
    monkeypatch.setattr(spec_routes, "_get_config_manager", lambda user_id: manager)

    client = TestClient(app)
    res = client.get("/api/config/profiles", params={"user_id": "test-user"})

    assert res.status_code == 200
    assert res.headers.get("content-type", "").startswith("application/json")

    body = res.json()  # fails hard if response is not valid single JSON
    assert isinstance(body, dict)
    assert isinstance(body.get("current_profile"), str)
    assert isinstance(body.get("profiles"), dict)

    assert "sample" in body["profiles"]
    assert set(body["profiles"]["sample"].keys()) >= {"extensions", "exclude_dirs", "description"}


def test_post_config_profiles_returns_single_json_object_and_persists(monkeypatch):
    manager = FakeConfigManager()
    monkeypatch.setattr(spec_routes, "_get_config_manager", lambda user_id: manager)

    client = TestClient(app)
    payload = {
        "user_id": "test-user",
        "name": "my_profile",
        "extensions": [".py", ".md"],
        "exclude_dirs": [".git"],
        "description": "Python + docs",
    }

    res = client.post("/api/config/profiles", json=payload)

    assert res.status_code == 200
    assert res.headers.get("content-type", "").startswith("application/json")

    body = res.json()
    assert body["name"] == "my_profile"
    assert isinstance(body.get("profile"), dict)
    assert isinstance(body.get("current_profile"), str)

    # Persistence check (AC: Profiles persist)
    assert "my_profile" in manager.config["scan_profiles"]
    assert manager.config["scan_profiles"]["my_profile"]["extensions"] == [".py", ".md"]

    # GET reflects POST (end-to-end manage profiles)
    res2 = client.get("/api/config/profiles", params={"user_id": "test-user"})
    body2 = res2.json()
    assert "my_profile" in body2["profiles"]
