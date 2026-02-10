from __future__ import annotations

from typing import Any, Dict

from services.preferences_service import PreferencesService


def test_load_preferences_returns_fallback_without_user() -> None:
    service = PreferencesService(media_extensions=(".jpg", ".png"))

    summary, profiles, config, error = service.load_preferences("")

    assert error is None
    assert summary["current_profile"] == "sample"
    assert "sample" in profiles
    assert config["max_file_size_mb"] == 10


def test_preferences_from_config_includes_media_for_all_profile() -> None:
    service = PreferencesService(media_extensions=(".jpg",))
    config = {
        "scan_profiles": {
            "all": {
                "description": "",
                "extensions": [".py"],
                "exclude_dirs": [],
            }
        },
        "current_profile": "all",
        "max_file_size_mb": 5,
        "follow_symlinks": False,
    }

    prefs = service.preferences_from_config(config, "all")

    assert ".py" in prefs.allowed_extensions
    assert ".jpg" in prefs.allowed_extensions


def test_execute_action_delegates_to_manager_factory() -> None:
    captured: Dict[str, Any] = {}

    class FakeManager:
        def __init__(self, user_id: str) -> None:
            self.user_id = user_id

        def set_current_profile(self, name: str) -> bool:
            captured["profile"] = name
            return True

    service = PreferencesService(media_extensions=(), manager_factory=lambda uid: FakeManager(uid))
    success, message = service.execute_action("user-1", "set_active", {"name": "dev"})

    assert success is True
    assert message == "Active profile set to dev."
    assert captured["profile"] == "dev"
