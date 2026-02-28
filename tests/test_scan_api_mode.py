from __future__ import annotations

import importlib
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Ensure backend/src is importable
backend_src = Path(__file__).parent.parent / "backend" / "src"
if str(backend_src) not in sys.path:
    sys.path.insert(0, str(backend_src))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _reload_spec_routes():
    """Re-import spec_routes so module-level _use_api_mode is re-evaluated."""
    import api.spec_routes as mod
    importlib.reload(mod)
    return mod


# ---------------------------------------------------------------------------
# 1. _get_scan_service respects USE_API_MODE env var
# ---------------------------------------------------------------------------

class TestGetScanServiceApiMode:
    def setup_method(self):
        # Reset the cached singleton before each test
        import api.spec_routes as mod
        mod._scan_service = None

    def test_default_mode_is_local(self, monkeypatch):
        """Without USE_API_MODE set, ScanService should use local mode."""
        monkeypatch.delenv("USE_API_MODE", raising=False)
        mod = _reload_spec_routes()
        mod._scan_service = None  # ensure fresh

        with patch("api.spec_routes._use_api_mode", False):
            with patch("services.services.scan_service.ScanService") as MockScan:
                MockScan.return_value = MagicMock(use_api=False)
                mod._scan_service = None
                svc = mod._get_scan_service()
                MockScan.assert_called_once_with(use_api=False)

    def test_api_mode_enabled_via_env(self, monkeypatch):
        """With USE_API_MODE=true, ScanService should be created with use_api=True."""
        monkeypatch.setenv("USE_API_MODE", "true")
        mod = _reload_spec_routes()
        mod._scan_service = None

        assert mod._use_api_mode is True

        with patch("services.services.scan_service.ScanService") as MockScan:
            MockScan.return_value = MagicMock(use_api=True)
            mod._get_scan_service()
            MockScan.assert_called_once_with(use_api=True)

    def test_api_mode_disabled_when_false(self, monkeypatch):
        """With USE_API_MODE=false, _use_api_mode should be False."""
        monkeypatch.setenv("USE_API_MODE", "false")
        mod = _reload_spec_routes()
        assert mod._use_api_mode is False

    def test_api_mode_enabled_with_1(self, monkeypatch):
        """USE_API_MODE=1 should also enable api mode."""
        monkeypatch.setenv("USE_API_MODE", "1")
        mod = _reload_spec_routes()
        assert mod._use_api_mode is True


# ---------------------------------------------------------------------------
# 2. _run_scan_background forwards auth token in API mode
# ---------------------------------------------------------------------------

class TestRunScanBackgroundAuthToken:
    def test_per_scan_service_created_with_token_in_api_mode(self, monkeypatch, tmp_path):
        """In API mode, a per-scan ScanService should be created with the auth token set."""
        # Create a real target directory so path-exists check passes
        target_dir = tmp_path / "project"
        target_dir.mkdir()

        import api.spec_routes as mod
        monkeypatch.setattr(mod, "_use_api_mode", True)

        mock_scan_result = MagicMock()
        mock_scan_result.parse_result = MagicMock()
        mock_scan_result.parse_result.summary = {}
        mock_scan_result.parse_result.files = []
        mock_scan_result.languages = []
        mock_scan_result.has_media_files = False
        mock_scan_result.pdf_candidates = []
        mock_scan_result.document_candidates = []
        mock_scan_result.git_repos = []
        mock_scan_result.timings = []

        mock_service_instance = MagicMock()
        mock_service_instance.run_scan.return_value = mock_scan_result

        scan_id = "test-scan-id"
        # Pre-populate scan store so status updates don't fail
        from api.spec_routes import JobState, Progress, ScanStatus
        mod._scan_store[scan_id] = ScanStatus(
            scan_id=scan_id,
            user_id="user-1",
            project_id=None,
            upload_id=None,
            state=JobState.queued,
            progress=Progress(percent=0.0),
            error=None,
            result=None,
        )

        with patch("services.services.scan_service.ScanService", return_value=mock_service_instance) as MockScan:
            mod._run_scan_background(
                scan_id=scan_id,
                source_path=str(target_dir),
                relevance_only=False,
                persist_project=False,
                profile_id=None,
                access_token="test-token-123",
            )
            MockScan.assert_called_once_with(use_api=True)
            mock_service_instance.set_auth_token.assert_called_once_with("test-token-123")

    def test_singleton_used_when_no_token_in_api_mode(self, monkeypatch, tmp_path):
        """In API mode but without a token, the singleton is used (no per-scan instance)."""
        target_dir = tmp_path / "project2"
        target_dir.mkdir()

        import api.spec_routes as mod
        monkeypatch.setattr(mod, "_use_api_mode", True)

        mock_scan_result = MagicMock()
        mock_scan_result.parse_result = MagicMock()
        mock_scan_result.parse_result.summary = {}
        mock_scan_result.parse_result.files = []
        mock_scan_result.languages = []
        mock_scan_result.has_media_files = False
        mock_scan_result.pdf_candidates = []
        mock_scan_result.document_candidates = []
        mock_scan_result.git_repos = []
        mock_scan_result.timings = []

        mock_singleton = MagicMock()
        mock_singleton.run_scan.return_value = mock_scan_result

        scan_id = "test-scan-id-2"
        from api.spec_routes import JobState, Progress, ScanStatus
        mod._scan_store[scan_id] = ScanStatus(
            scan_id=scan_id,
            user_id="user-2",
            project_id=None,
            upload_id=None,
            state=JobState.queued,
            progress=Progress(percent=0.0),
            error=None,
            result=None,
        )

        with patch.object(mod, "_get_scan_service", return_value=mock_singleton) as mock_get:
            mod._run_scan_background(
                scan_id=scan_id,
                source_path=str(target_dir),
                relevance_only=False,
                persist_project=False,
                profile_id=None,
                access_token=None,
            )
            mock_get.assert_called_once()


# ---------------------------------------------------------------------------
# 3. POST /api/uploads stub is removed from spec_router
# ---------------------------------------------------------------------------

class TestUploadRouteNotInSpecRouter:
    def test_spec_router_has_no_post_uploads_route(self):
        """The stub POST /api/uploads must not be registered in spec_routes router."""
        import api.spec_routes as mod
        routes_in_spec = [
            (route.path, list(route.methods))
            for route in mod.router.routes
            if hasattr(route, "methods")
        ]
        post_uploads = [
            path for path, methods in routes_in_spec
            if path in ("/api/uploads", "/api/uploads/") and "POST" in methods
        ]
        assert post_uploads == [], (
            f"spec_routes.router still has POST /api/uploads: {post_uploads}. "
            "This stub shadows the real implementation in upload_routes.py."
        )
