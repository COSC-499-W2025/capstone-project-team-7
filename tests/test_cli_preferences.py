import os
from contextlib import contextmanager

import pytest

from src.cli import parse_zip as cli_parse_zip
from src.scanner.models import ScanPreferences


def test_preferences_from_config_populates_fields():
    config = {
        "scan_profiles": {
            "python_only": {
                "extensions": [".PY", ".py"],
                "exclude_dirs": ["venv", "__pycache__"],
            }
        },
        "current_profile": "python_only",
        "max_file_size_mb": 4,
        "follow_symlinks": True,
    }

    prefs = cli_parse_zip._preferences_from_config(config, None)

    assert isinstance(prefs, ScanPreferences)
    assert prefs.allowed_extensions == [".py", ".py"]
    assert prefs.excluded_dirs == ["venv", "__pycache__"]
    assert prefs.max_file_size_bytes == 4 * 1024 * 1024
    assert prefs.follow_symlinks is True


def test_preferences_from_config_handles_missing_profile():
    config = {
        "scan_profiles": {},
        "current_profile": "python_only",
        "max_file_size_mb": None,
        "follow_symlinks": False,
    }

    prefs = cli_parse_zip._preferences_from_config(config, None)

    assert prefs.allowed_extensions is None
    assert prefs.excluded_dirs is None
    assert prefs.max_file_size_bytes is None
    assert prefs.follow_symlinks is False


def test_load_preferences_respects_environment(monkeypatch):
    dummy_config = {
        "scan_profiles": {
            "all": {
                "extensions": [".md"],
                "exclude_dirs": ["docs"],
            }
        },
        "current_profile": "all",
        "max_file_size_mb": 1,
        "follow_symlinks": False,
    }

    class DummyManager:
        def __init__(self, user_id):
            self.user_id = user_id
            self.config = dummy_config

        def get_current_profile(self):
            return self.config["current_profile"]

    monkeypatch.setenv(cli_parse_zip.USER_ID_ENV, "user-123")
    monkeypatch.setattr(cli_parse_zip, "_get_config_manager", lambda user_id: DummyManager(user_id))

    prefs = cli_parse_zip.load_preferences(profile_name=None)

    assert isinstance(prefs, ScanPreferences)
    assert prefs.allowed_extensions == [".md"]
    assert prefs.excluded_dirs == ["docs"]
    assert prefs.max_file_size_bytes == 1 * 1024 * 1024
    assert prefs.follow_symlinks is False


def test_load_preferences_returns_none_when_env_missing(monkeypatch):
    monkeypatch.delenv(cli_parse_zip.USER_ID_ENV, raising=False)
    assert cli_parse_zip.load_preferences(profile_name=None) is None
