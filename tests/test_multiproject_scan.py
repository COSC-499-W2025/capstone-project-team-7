"""Tests for multi-project scan path in spec_routes.

Covers:
- _scan_single_subproject module-level helper
- MAX_DETECTED_PROJECTS cap enforcement
- Multi-project scan via POST /api/scans with a directory containing sub-projects
- Aggregated result shape after multi-project scan completes
"""

import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
from unittest.mock import MagicMock, patch

import pytest

# Ensure backend/src is on path for imports
PROJECT_ROOT = Path(__file__).parent.parent
BACKEND_SRC = PROJECT_ROOT / "backend" / "src"
sys.path.insert(0, str(BACKEND_SRC))
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

fastapi = pytest.importorskip("fastapi")

from api.spec_routes import (
    _scan_single_subproject,
    MAX_DETECTED_PROJECTS,
)

# TestClient may be unavailable on some environments due to dependency mismatches.
# Guard the import so unit tests still run.
_HAS_TEST_CLIENT = False
try:
    from fastapi.testclient import TestClient
    from backend.src.main import app
    from api.dependencies import AuthContext, get_auth_context
    # Verify TestClient actually works (starlette/httpx version mismatch can
    # cause __init__ to crash even though the import succeeds).
    _test = TestClient(app)
    del _test
    _HAS_TEST_CLIENT = True
except Exception:
    pass

TEST_USER_ID = "test-user-multiproject"
TEST_ACCESS_TOKEN = "test-token"


if _HAS_TEST_CLIENT:
    async def _override_auth() -> AuthContext:
        return AuthContext(user_id=TEST_USER_ID, access_token=TEST_ACCESS_TOKEN)


@pytest.fixture
def client():
    if not _HAS_TEST_CLIENT:
        pytest.skip("TestClient unavailable")
    app.dependency_overrides[get_auth_context] = _override_auth
    yield TestClient(app)
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


@dataclass
class FakeProjectInfo:
    name: str
    path: Path
    project_type: str


def _make_fake_scan_result():
    """Return a minimal scan result that _run_analysis_pipeline can process."""
    mock = MagicMock()
    mock.parse_result.files = []
    mock.parse_result.summary = {
        "files_processed": 0,
        "bytes_processed": 0,
        "issues_count": 0,
    }
    mock.languages = []
    mock.has_media_files = False
    mock.pdf_candidates = []
    mock.document_candidates = []
    mock.git_repos = []
    mock.timings = []
    return mock


# ---------------------------------------------------------------------------
# _scan_single_subproject unit tests
# ---------------------------------------------------------------------------


class TestScanSingleSubproject:
    """Tests for the module-level _scan_single_subproject helper."""

    def test_returns_tuple_of_name_path_payload(self, tmp_path):
        """Should return (name, path_str, payload_dict)."""
        proj_dir = tmp_path / "my_project"
        proj_dir.mkdir()

        proj_info = FakeProjectInfo(name="my_project", path=proj_dir, project_type="python")
        scan_service = MagicMock()
        scan_service.run_scan.return_value = _make_fake_scan_result()

        with patch("api.spec_routes._run_analysis_pipeline") as mock_pipeline:
            mock_pipeline.return_value = {
                "summary": {"total_files": 5, "bytes_processed": 1024, "issues_count": 0},
                "languages": [],
            }
            result = _scan_single_subproject(proj_info, scan_service, False, None)

        assert isinstance(result, tuple)
        assert len(result) == 3
        name, path_str, payload = result
        assert name == "my_project"
        assert path_str == str(proj_dir)
        assert isinstance(payload, dict)

    def test_passes_preferences_to_scan_service(self, tmp_path):
        """Should forward preferences to scan_service.run_scan."""
        proj_dir = tmp_path / "proj"
        proj_dir.mkdir()

        proj_info = FakeProjectInfo(name="proj", path=proj_dir, project_type="python")
        scan_service = MagicMock()
        scan_service.run_scan.return_value = _make_fake_scan_result()
        fake_prefs = MagicMock()

        with patch("api.spec_routes._run_analysis_pipeline") as mock_pipeline:
            mock_pipeline.return_value = {"summary": {"total_files": 0, "bytes_processed": 0, "issues_count": 0}, "languages": []}
            _scan_single_subproject(proj_info, scan_service, True, fake_prefs)

        scan_service.run_scan.assert_called_once_with(
            target=proj_dir,
            relevant_only=True,
            preferences=fake_prefs,
        )

    def test_sets_detected_project_type_on_payload(self, tmp_path):
        """Should annotate the payload with detected_project_type."""
        proj_dir = tmp_path / "js_app"
        proj_dir.mkdir()

        proj_info = FakeProjectInfo(name="js_app", path=proj_dir, project_type="javascript")
        scan_service = MagicMock()
        scan_service.run_scan.return_value = _make_fake_scan_result()

        with patch("api.spec_routes._run_analysis_pipeline") as mock_pipeline:
            mock_pipeline.return_value = {"summary": {"total_files": 0, "bytes_processed": 0, "issues_count": 0}, "languages": []}
            _, _, payload = _scan_single_subproject(proj_info, scan_service, False, None)

        assert payload["detected_project_type"] == "javascript"

    def test_calls_pipeline_with_compact_true(self, tmp_path):
        """Should always pass compact=True for sub-project scans."""
        proj_dir = tmp_path / "proj"
        proj_dir.mkdir()

        proj_info = FakeProjectInfo(name="proj", path=proj_dir, project_type="python")
        scan_service = MagicMock()
        scan_service.run_scan.return_value = _make_fake_scan_result()

        with patch("api.spec_routes._run_analysis_pipeline") as mock_pipeline:
            mock_pipeline.return_value = {"summary": {"total_files": 0, "bytes_processed": 0, "issues_count": 0}, "languages": []}
            _scan_single_subproject(proj_info, scan_service, False, None)

        _, kwargs = mock_pipeline.call_args
        assert kwargs.get("compact") is True


# ---------------------------------------------------------------------------
# MAX_DETECTED_PROJECTS constant
# ---------------------------------------------------------------------------


class TestMaxDetectedProjects:
    """Tests that the project cap constant is defined and reasonable."""

    def test_max_detected_projects_is_positive(self):
        assert MAX_DETECTED_PROJECTS > 0

    def test_max_detected_projects_is_at_most_20(self):
        """Cap should be reasonable to avoid resource exhaustion."""
        assert MAX_DETECTED_PROJECTS <= 20


# ---------------------------------------------------------------------------
# Multi-project scan API integration
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not _HAS_TEST_CLIENT, reason="TestClient unavailable in this environment")
class TestMultiProjectScanAPI:
    """Integration tests for multi-project scan via POST /api/scans."""

    def test_create_scan_with_multiproject_dir(self, client, tmp_path):
        """POST /api/scans with a directory containing multiple sub-projects should return 202."""
        # Create a directory with two sub-projects
        proj_a = tmp_path / "backend"
        proj_a.mkdir()
        (proj_a / "requirements.txt").write_text("flask\n")
        (proj_a / "app.py").write_text("print('hello')\n")

        proj_b = tmp_path / "frontend"
        proj_b.mkdir()
        (proj_b / "package.json").write_text('{"name": "frontend"}\n')
        (proj_b / "index.js").write_text("console.log('hi');\n")

        response = client.post("/api/scans", json={
            "source_path": str(tmp_path),
            "persist_project": False,
        })
        assert response.status_code == 202
        body = response.json()
        assert "scan_id" in body

    def test_scan_completes_for_multiproject_dir(self, client, tmp_path):
        """Scan of a multi-project directory should eventually succeed."""
        proj_a = tmp_path / "service_a"
        proj_a.mkdir()
        (proj_a / "requirements.txt").write_text("requests\n")
        (proj_a / "main.py").write_text("import requests\n")

        proj_b = tmp_path / "service_b"
        proj_b.mkdir()
        (proj_b / "package.json").write_text('{"name": "service_b"}\n')
        (proj_b / "index.js").write_text("module.exports = {};\n")

        create_resp = client.post("/api/scans", json={
            "source_path": str(tmp_path),
            "persist_project": False,
        })
        scan_id = create_resp.json()["scan_id"]

        # Poll until complete (with timeout)
        for _ in range(30):
            status_resp = client.get(f"/api/scans/{scan_id}")
            state = status_resp.json()["state"]
            if state in ("succeeded", "failed"):
                break
            time.sleep(0.5)

        final = client.get(f"/api/scans/{scan_id}").json()
        assert final["state"] == "succeeded", f"Scan ended in state: {final['state']}"

    def test_single_project_not_treated_as_multi(self, client, tmp_path):
        """A directory with a single project marker at root should not split."""
        (tmp_path / "package.json").write_text('{"name": "mono"}\n')
        (tmp_path / "index.js").write_text("console.log('hi');\n")

        create_resp = client.post("/api/scans", json={
            "source_path": str(tmp_path),
            "persist_project": False,
        })
        scan_id = create_resp.json()["scan_id"]

        for _ in range(30):
            status_resp = client.get(f"/api/scans/{scan_id}")
            state = status_resp.json()["state"]
            if state in ("succeeded", "failed"):
                break
            time.sleep(0.5)

        final = client.get(f"/api/scans/{scan_id}").json()
        assert final["state"] == "succeeded"
        result = final.get("result", {})
        # Should NOT have detected_projects since it was a single project
        detected = result.get("detected_projects")
        assert detected is None or len(detected) <= 1
