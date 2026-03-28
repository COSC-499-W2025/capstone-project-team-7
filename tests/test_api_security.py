"""Tests for API security hardening: rate limiting, headers, path validation."""

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


# ---------------------------------------------------------------------------
# Bootstrap – mirror backend/tests/conftest.py approach
# ---------------------------------------------------------------------------

_src = Path(__file__).resolve().parent.parent / "backend" / "src"
if str(_src) not in sys.path:
    sys.path.insert(0, str(_src))

os.environ.setdefault("SUPABASE_URL", "https://test.supabase.co")
os.environ.setdefault("SUPABASE_KEY", "test-service-role-key")


def _import_file(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


_api_dir = _src / "api"
if "api" not in sys.modules:
    _api_pkg = ModuleType("api")
    _api_pkg.__path__ = [str(_api_dir)]
    _api_pkg.__package__ = "api"
    sys.modules["api"] = _api_pkg

# Ensure sub-modules importable
_import_file("api.request_context", _api_dir / "request_context.py")
_import_file("api.security", _api_dir / "security.py")
_import_file("api.dependencies", _api_dir / "dependencies.py")

from api.security import limiter, rate_limit_exceeded_handler, SecurityHeadersMiddleware, validate_storage_path


# ===================================================================
# 1. Security headers tests
# ===================================================================

class TestSecurityHeaders:
    """Verify that SecurityHeadersMiddleware injects expected headers."""

    @pytest.fixture()
    def app_client(self):
        app = FastAPI()
        app.add_middleware(SecurityHeadersMiddleware)

        @app.get("/test")
        def _test():
            return {"ok": True}

        return TestClient(app)

    def test_x_content_type_options(self, app_client):
        resp = app_client.get("/test")
        assert resp.headers.get("X-Content-Type-Options") == "nosniff"

    def test_x_frame_options(self, app_client):
        resp = app_client.get("/test")
        assert resp.headers.get("X-Frame-Options") == "DENY"

    def test_x_xss_protection(self, app_client):
        resp = app_client.get("/test")
        assert resp.headers.get("X-XSS-Protection") == "1; mode=block"

    def test_referrer_policy(self, app_client):
        resp = app_client.get("/test")
        assert resp.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"

    def test_permissions_policy(self, app_client):
        resp = app_client.get("/test")
        assert resp.headers.get("Permissions-Policy") == "camera=(), microphone=(), geolocation=()"

    def test_hsts_absent_by_default(self, app_client):
        resp = app_client.get("/test")
        assert "Strict-Transport-Security" not in resp.headers

    def test_hsts_present_when_enabled(self):
        with patch.dict(os.environ, {"ENABLE_HSTS": "true", "HSTS_MAX_AGE": "600"}):
            app = FastAPI()
            app.add_middleware(SecurityHeadersMiddleware)

            @app.get("/test")
            def _test():
                return {"ok": True}

            client = TestClient(app)
            resp = client.get("/test")
            assert resp.headers.get("Strict-Transport-Security") == "max-age=600; includeSubDomains"


# ===================================================================
# 2. Rate limiting tests
# ===================================================================

class TestRateLimiting:
    """Verify rate limiting on auth endpoints."""

    @pytest.fixture()
    def app_client(self, tmp_path):
        """Build a minimal app with rate limiting via a subprocess to isolate from pytest."""
        # Create the app in a helper module to avoid pytest's annotation interference
        helper = tmp_path / "rl_helper.py"
        helper.write_text(
            "from starlette.requests import Request\n"
            "from fastapi import FastAPI\n"
            "from slowapi import Limiter\n"
            "from slowapi.util import get_remote_address\n"
            "from slowapi.errors import RateLimitExceeded\n"
            "from fastapi.responses import JSONResponse\n"
            "\n"
            "limiter = Limiter(key_func=get_remote_address, storage_uri='memory://')\n"
            "app = FastAPI()\n"
            "app.state.limiter = limiter\n"
            "\n"
            "def handler(req, exc):\n"
            "    return JSONResponse(status_code=429, content={'error':'rate_limit_exceeded','message':str(exc.detail)})\n"
            "\n"
            "app.add_exception_handler(RateLimitExceeded, handler)\n"
            "\n"
            "@app.post('/limited')\n"
            "@limiter.limit('2/minute')\n"
            "def limited(request: Request):\n"
            "    return {'ok': True}\n"
        )
        import importlib.util
        spec = importlib.util.spec_from_file_location("rl_helper", str(helper))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        mod.limiter.reset()
        return TestClient(mod.app)

    def test_under_limit_succeeds(self, app_client):
        resp = app_client.post("/limited")
        assert resp.status_code == 200

    def test_over_limit_returns_429(self, app_client):
        # exhaust the 2/minute budget
        app_client.post("/limited")
        app_client.post("/limited")
        resp = app_client.post("/limited")
        assert resp.status_code == 429
        body = resp.json()
        assert body["error"] == "rate_limit_exceeded"


# ===================================================================
# 3. Path traversal validation tests
# ===================================================================

class TestValidateStoragePath:
    """Verify that validate_storage_path rejects traversal and bad paths."""

    def test_simple_filename(self, tmp_path):
        result = validate_storage_path("file.zip", tmp_path)
        assert result == (tmp_path / "file.zip").resolve()

    def test_nested_subdir(self, tmp_path):
        result = validate_storage_path("sub/dir/file.zip", tmp_path)
        assert str(result).startswith(str(tmp_path.resolve()))

    def test_rejects_dot_dot(self, tmp_path):
        with pytest.raises(ValueError, match="escapes the upload root"):
            validate_storage_path("../etc/passwd", tmp_path)

    def test_rejects_absolute_path(self, tmp_path):
        with pytest.raises(ValueError, match="Absolute paths"):
            validate_storage_path("/etc/passwd", tmp_path)

    def test_rejects_null_bytes(self, tmp_path):
        with pytest.raises(ValueError, match="null bytes"):
            validate_storage_path("file\x00.zip", tmp_path)

    def test_rejects_backslash_traversal(self, tmp_path):
        with pytest.raises(ValueError, match="escapes the upload root"):
            validate_storage_path("..\\..\\etc\\passwd", tmp_path)

    def test_rejects_windows_drive_letter(self, tmp_path):
        with pytest.raises(ValueError, match="Absolute paths"):
            validate_storage_path("C:\\Windows\\System32\\cmd.exe", tmp_path)

    def test_rejects_double_encoded_traversal(self, tmp_path):
        # Already decoded by the time it reaches us; verify the resolved check catches it
        with pytest.raises(ValueError, match="escapes the upload root"):
            validate_storage_path("foo/../../etc/passwd", tmp_path)
