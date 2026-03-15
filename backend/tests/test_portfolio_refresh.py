"""Tests for POST /api/portfolio/refresh endpoint."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import api.portfolio_routes as portfolio_mod
from api.dependencies import AuthContext, get_auth_context
from services.services.projects_service import ProjectsServiceError


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def mock_projects_service():
    """Return a mock ProjectsService."""
    return MagicMock()


@pytest.fixture()
def client(mock_projects_service):
    """TestClient with auth and ProjectsService mocked."""
    app = FastAPI()
    app.include_router(portfolio_mod.router)

    fake_ctx = AuthContext(
        user_id="user-123", access_token="tok-abc", email="user@example.com"
    )
    app.dependency_overrides[get_auth_context] = lambda: fake_ctx
    app.dependency_overrides[portfolio_mod.get_projects_service] = lambda: mock_projects_service

    with TestClient(app) as c:
        yield c


@pytest.fixture()
def unauthenticated_client():
    """TestClient with no auth override."""
    app = FastAPI()
    app.include_router(portfolio_mod.router)
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_project(project_id: str, name: str = "My Project") -> dict:
    return {"id": project_id, "project_name": name}


def _make_cached_files(*entries: tuple[str, str, int]) -> dict:
    """Build a cached-files dict from (rel_path, sha256, size_bytes) tuples."""
    return {
        path: {"sha256": sha256, "size_bytes": size}
        for path, sha256, size in entries
    }


# ---------------------------------------------------------------------------
# Happy-path tests
# ---------------------------------------------------------------------------

class TestRefreshPortfolioSuccess:
    def test_returns_200(self, client, mock_projects_service):
        mock_projects_service.get_user_projects.return_value = []
        resp = client.post("/api/portfolio/refresh")
        assert resp.status_code == 200

    def test_response_has_required_fields(self, client, mock_projects_service):
        mock_projects_service.get_user_projects.return_value = []
        data = client.post("/api/portfolio/refresh").json()
        assert "status" in data
        assert "projects_scanned" in data
        assert "total_files" in data
        assert "total_size_bytes" in data

    def test_status_is_completed(self, client, mock_projects_service):
        mock_projects_service.get_user_projects.return_value = []
        data = client.post("/api/portfolio/refresh").json()
        assert data["status"] == "completed"

    def test_projects_scanned_count(self, client, mock_projects_service):
        mock_projects_service.get_user_projects.return_value = [
            _make_project("p1"), _make_project("p2"), _make_project("p3"),
        ]
        mock_projects_service.get_cached_files.return_value = {}
        data = client.post("/api/portfolio/refresh").json()
        assert data["projects_scanned"] == 3

    def test_zero_projects(self, client, mock_projects_service):
        mock_projects_service.get_user_projects.return_value = []
        data = client.post("/api/portfolio/refresh").json()
        assert data["projects_scanned"] == 0
        assert data["total_files"] == 0
        assert data["total_size_bytes"] == 0

    def test_total_files_aggregated_across_projects(self, client, mock_projects_service):
        mock_projects_service.get_user_projects.return_value = [
            _make_project("p1"), _make_project("p2"),
        ]
        mock_projects_service.get_cached_files.side_effect = [
            _make_cached_files(("a.py", "hash1", 100), ("b.py", "hash2", 200)),
            _make_cached_files(("c.py", "hash3", 50)),
        ]
        data = client.post("/api/portfolio/refresh").json()
        assert data["total_files"] == 3

    def test_total_size_bytes_aggregated_across_projects(self, client, mock_projects_service):
        mock_projects_service.get_user_projects.return_value = [
            _make_project("p1"), _make_project("p2"),
        ]
        mock_projects_service.get_cached_files.side_effect = [
            _make_cached_files(("a.py", "hash1", 100), ("b.py", "hash2", 200)),
            _make_cached_files(("c.py", "hash3", 50)),
        ]
        data = client.post("/api/portfolio/refresh").json()
        assert data["total_size_bytes"] == 350

    def test_dedup_report_included_by_default(self, client, mock_projects_service):
        mock_projects_service.get_user_projects.return_value = []
        data = client.post("/api/portfolio/refresh").json()
        assert "dedup_report" in data

    def test_dedup_report_omitted_when_include_duplicates_false(self, client, mock_projects_service):
        mock_projects_service.get_user_projects.return_value = []
        data = client.post("/api/portfolio/refresh", json={"include_duplicates": False}).json()
        assert data["dedup_report"] is None


# ---------------------------------------------------------------------------
# Deduplication logic tests
# ---------------------------------------------------------------------------

class TestDeduplication:
    def test_no_duplicates_when_all_files_unique(self, client, mock_projects_service):
        mock_projects_service.get_user_projects.return_value = [
            _make_project("p1"), _make_project("p2"),
        ]
        mock_projects_service.get_cached_files.side_effect = [
            _make_cached_files(("a.py", "aaa", 100)),
            _make_cached_files(("b.py", "bbb", 200)),
        ]
        data = client.post("/api/portfolio/refresh").json()
        assert data["dedup_report"]["summary"]["duplicate_groups_count"] == 0
        assert data["dedup_report"]["summary"]["total_wasted_bytes"] == 0
        assert data["dedup_report"]["duplicate_groups"] == []

    def test_detects_cross_project_duplicate(self, client, mock_projects_service):
        shared_hash = "deadbeef" * 8
        mock_projects_service.get_user_projects.return_value = [
            _make_project("p1", "Alpha"), _make_project("p2", "Beta"),
        ]
        mock_projects_service.get_cached_files.side_effect = [
            _make_cached_files(("lib/utils.py", shared_hash, 1024)),
            _make_cached_files(("helpers/utils.py", shared_hash, 1024)),
        ]
        data = client.post("/api/portfolio/refresh").json()
        assert data["dedup_report"]["summary"]["duplicate_groups_count"] == 1
        group = data["dedup_report"]["duplicate_groups"][0]
        assert group["sha256"] == shared_hash
        assert group["file_count"] == 2

    def test_wasted_bytes_calculated_correctly(self, client, mock_projects_service):
        """Wasted bytes = (file_count - 1) * file_size."""
        shared_hash = "cafebabe" * 8
        mock_projects_service.get_user_projects.return_value = [
            _make_project("p1"), _make_project("p2"), _make_project("p3"),
        ]
        mock_projects_service.get_cached_files.side_effect = [
            _make_cached_files(("x.py", shared_hash, 2048)),
            _make_cached_files(("x.py", shared_hash, 2048)),
            _make_cached_files(("x.py", shared_hash, 2048)),
        ]
        data = client.post("/api/portfolio/refresh").json()
        group = data["dedup_report"]["duplicate_groups"][0]
        # 3 copies, file_size=2048 → wasted = (3-1)*2048 = 4096
        assert group["wasted_bytes"] == 4096
        assert data["dedup_report"]["summary"]["total_wasted_bytes"] == 4096

    def test_does_not_flag_same_project_duplicates(self, client, mock_projects_service):
        """Two files with the same hash in the same project are NOT cross-project duplicates."""
        shared_hash = "11223344" * 8
        mock_projects_service.get_user_projects.return_value = [_make_project("p1")]
        mock_projects_service.get_cached_files.return_value = _make_cached_files(
            ("a/file.py", shared_hash, 512),
            ("b/file.py", shared_hash, 512),
        )
        data = client.post("/api/portfolio/refresh").json()
        assert data["dedup_report"]["summary"]["duplicate_groups_count"] == 0

    def test_multiple_duplicate_groups(self, client, mock_projects_service):
        hash_a = "aaaa" * 16
        hash_b = "bbbb" * 16
        mock_projects_service.get_user_projects.return_value = [
            _make_project("p1"), _make_project("p2"),
        ]
        mock_projects_service.get_cached_files.side_effect = [
            _make_cached_files(("a.py", hash_a, 100), ("b.py", hash_b, 200)),
            _make_cached_files(("a_copy.py", hash_a, 100), ("b_copy.py", hash_b, 200)),
        ]
        data = client.post("/api/portfolio/refresh").json()
        assert data["dedup_report"]["summary"]["duplicate_groups_count"] == 2

    def test_duplicate_groups_sorted_by_wasted_bytes_descending(self, client, mock_projects_service):
        hash_small = "1111" * 16
        hash_large = "2222" * 16
        mock_projects_service.get_user_projects.return_value = [
            _make_project("p1"), _make_project("p2"),
        ]
        mock_projects_service.get_cached_files.side_effect = [
            _make_cached_files(("small.py", hash_small, 50), ("large.py", hash_large, 5000)),
            _make_cached_files(("small2.py", hash_small, 50), ("large2.py", hash_large, 5000)),
        ]
        data = client.post("/api/portfolio/refresh").json()
        groups = data["dedup_report"]["duplicate_groups"]
        assert groups[0]["wasted_bytes"] >= groups[1]["wasted_bytes"]

    def test_duplicate_group_contains_file_paths_and_project_names(self, client, mock_projects_service):
        shared_hash = "feedface" * 8
        mock_projects_service.get_user_projects.return_value = [
            _make_project("p1", "Frontend"), _make_project("p2", "Backend"),
        ]
        mock_projects_service.get_cached_files.side_effect = [
            _make_cached_files(("src/util.py", shared_hash, 256)),
            _make_cached_files(("lib/util.py", shared_hash, 256)),
        ]
        data = client.post("/api/portfolio/refresh").json()
        group = data["dedup_report"]["duplicate_groups"][0]
        paths = {f["path"] for f in group["files"]}
        project_names = {f["project_name"] for f in group["files"]}
        assert "src/util.py" in paths
        assert "lib/util.py" in paths
        assert "Frontend" in project_names
        assert "Backend" in project_names

    def test_files_without_sha256_are_counted_but_not_deduplicated(self, client, mock_projects_service):
        mock_projects_service.get_user_projects.return_value = [
            _make_project("p1"), _make_project("p2"),
        ]
        # Files with no sha256 key
        mock_projects_service.get_cached_files.side_effect = [
            {"a.py": {"size_bytes": 100}},
            {"b.py": {"size_bytes": 200}},
        ]
        data = client.post("/api/portfolio/refresh").json()
        assert data["total_files"] == 2
        assert data["dedup_report"]["summary"]["duplicate_groups_count"] == 0


# ---------------------------------------------------------------------------
# Resilience tests
# ---------------------------------------------------------------------------

class TestRefreshResilience:
    def test_continues_when_one_project_cached_files_fails(self, client, mock_projects_service):
        """A single project failing to load cached files should not abort the whole refresh."""
        mock_projects_service.get_user_projects.return_value = [
            _make_project("p1"), _make_project("p2"),
        ]
        mock_projects_service.get_cached_files.side_effect = [
            Exception("storage unavailable"),
            _make_cached_files(("ok.py", "abc123", 512)),
        ]
        data = client.post("/api/portfolio/refresh").json()
        assert data["status"] == "completed"
        assert data["projects_scanned"] == 2
        assert data["total_files"] == 1

    def test_returns_500_on_projects_service_error(self, client, mock_projects_service):
        mock_projects_service.get_user_projects.side_effect = ProjectsServiceError("DB down")
        resp = client.post("/api/portfolio/refresh")
        assert resp.status_code == 500
        assert resp.json()["detail"]["code"] == "refresh_error"

    def test_returns_500_on_unexpected_exception(self, client, mock_projects_service):
        mock_projects_service.get_user_projects.side_effect = RuntimeError("unexpected")
        resp = client.post("/api/portfolio/refresh")
        assert resp.status_code == 500
        assert resp.json()["detail"]["code"] == "refresh_error"

    def test_error_detail_contains_message(self, client, mock_projects_service):
        mock_projects_service.get_user_projects.side_effect = ProjectsServiceError("connection refused")
        data = client.post("/api/portfolio/refresh").json()
        assert "message" in data["detail"]
        assert "connection refused" in data["detail"]["message"]

    def test_unauthenticated_returns_error(self, unauthenticated_client):
        resp = unauthenticated_client.post("/api/portfolio/refresh")
        assert resp.status_code in (401, 403, 422, 500)
