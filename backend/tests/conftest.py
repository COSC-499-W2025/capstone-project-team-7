"""Shared fixtures for backend tests."""

from __future__ import annotations

import importlib
import importlib.util
import os
import sys
from pathlib import Path
from types import ModuleType
from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

# Ensure the backend src directory is on sys.path so imports resolve.
_src = Path(__file__).resolve().parent.parent / "src"
if str(_src) not in sys.path:
    sys.path.insert(0, str(_src))

# Set required env vars BEFORE importing so config checks pass.
os.environ.setdefault("SUPABASE_URL", "https://test.supabase.co")
os.environ.setdefault("SUPABASE_KEY", "test-service-role-key")


def _import_file(name: str, path: Path):
    """Import a single .py file as a module, bypassing package __init__.py."""
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


# Register a stub `api` package so that `import api.profile_routes` doesn't
# trigger the real api/__init__.py (which imports every route + heavy deps).
_api_dir = _src / "api"
if "api" not in sys.modules:
    _api_pkg = ModuleType("api")
    _api_pkg.__path__ = [str(_api_dir)]
    _api_pkg.__package__ = "api"
    sys.modules["api"] = _api_pkg

_deps_mod = _import_file("api.dependencies", _api_dir / "dependencies.py")
_profile_mod = _import_file("api.profile_routes", _api_dir / "profile_routes.py")

# Re-export so tests can do `from api.dependencies import AuthContext` etc.
AUTH_CONTEXT_CLS = _deps_mod.AuthContext


@pytest.fixture()
def client():
    """Return a TestClient with auth overridden to a fake user."""
    app = FastAPI()
    app.include_router(_profile_mod.router)

    fake_ctx = AUTH_CONTEXT_CLS(
        user_id="user-123", access_token="tok-abc", email="user@example.com"
    )
    app.dependency_overrides[_deps_mod.get_auth_context] = lambda: fake_ctx

    with TestClient(app) as c:
        yield c
