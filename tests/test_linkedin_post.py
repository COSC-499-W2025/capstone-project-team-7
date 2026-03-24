"""Tests for the LinkedIn post generation feature.

Covers:
- build_portfolio_post template output (linkedin_post_builder.py)
- build_project_post template output
- POST /api/portfolio/linkedin-post endpoint contract
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

PROJECT_ROOT = Path(__file__).parent.parent
BACKEND_SRC = PROJECT_ROOT / "backend" / "src"
sys.path.insert(0, str(BACKEND_SRC))
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from services.services.linkedin_post_builder import (
    build_portfolio_post,
    build_project_post,
)


# ---------------------------------------------------------------------------
# build_portfolio_post tests
# ---------------------------------------------------------------------------


def _make_project(name, langs=None, commits=0, score=0, skills=None):
    sd = {
        "languages": [{"name": l} for l in (langs or [])],
        "git_analysis": [{"commit_count": commits}] if commits else [],
        "summary": {"total_files": 10},
    }
    if skills:
        sd["skills_analysis"] = {
            "skills_by_category": {
                "all": [{"name": s} for s in skills]
            }
        }
    return {
        "project_name": name,
        "contribution_score": score,
        "scan_data": sd,
    }


class TestBuildPortfolioPost:
    def test_returns_non_empty_string(self):
        post = build_portfolio_post([], [])
        assert isinstance(post, str)
        assert len(post) > 0

    def test_includes_project_names(self):
        projects = [
            _make_project("My App", langs=["Python"], commits=50, score=80),
        ]
        post = build_portfolio_post(projects, ["Python"])
        assert "My App" in post

    def test_includes_skills(self):
        post = build_portfolio_post([], ["React", "TypeScript", "Python"])
        assert "React" in post
        assert "TypeScript" in post

    def test_includes_share_url(self):
        post = build_portfolio_post([], [], share_url="https://example.com/portfolio")
        assert "https://example.com/portfolio" in post

    def test_no_share_url_when_none(self):
        post = build_portfolio_post([], [])
        assert "Check out my portfolio" not in post

    def test_includes_hashtags(self):
        projects = [_make_project("App", langs=["Python"])]
        post = build_portfolio_post(projects, [])
        assert "#SoftwareDevelopment" in post
        assert "#Python" in post

    def test_top_3_projects_by_score(self):
        projects = [
            _make_project("Low", score=10),
            _make_project("High", score=90),
            _make_project("Mid", score=50),
            _make_project("Skip", score=5),
        ]
        post = build_portfolio_post(projects, [])
        assert "High" in post
        assert "Mid" in post
        assert "Low" in post
        # 4th project should not appear (only top 3)
        assert "Skip" not in post

    def test_truncates_skills_at_8(self):
        skills = [f"Skill{i}" for i in range(12)]
        post = build_portfolio_post([], skills)
        assert "Skill7" in post
        assert "Skill8" not in post
        assert "4 more" in post

    def test_includes_commit_count(self):
        projects = [_make_project("App", commits=142)]
        post = build_portfolio_post(projects, [])
        assert "142 commits" in post

    def test_includes_languages(self):
        projects = [_make_project("App", langs=["TypeScript", "Go"])]
        post = build_portfolio_post(projects, [])
        assert "TypeScript" in post


class TestBuildProjectPost:
    def test_returns_non_empty_string(self):
        project = _make_project("Test Project")
        post = build_project_post(project)
        assert isinstance(post, str)
        assert len(post) > 0

    def test_includes_project_name(self):
        project = _make_project("My Cool Project")
        post = build_project_post(project)
        assert "My Cool Project" in post

    def test_includes_languages(self):
        project = _make_project("App", langs=["Rust", "Python"])
        post = build_project_post(project)
        assert "Rust" in post
        assert "Python" in post

    def test_includes_skills_from_scan_data(self):
        project = _make_project("App", skills=["Error Handling", "Testing"])
        post = build_project_post(project)
        assert "Error Handling" in post
        assert "Testing" in post

    def test_includes_role_if_present(self):
        project = _make_project("App")
        project["role"] = "Lead Developer"
        post = build_project_post(project)
        assert "Lead Developer" in post

    def test_includes_hashtags(self):
        project = _make_project("App", langs=["JavaScript"])
        post = build_project_post(project)
        assert "#SoftwareDevelopment" in post
        assert "#JavaScript" in post

    def test_includes_commit_count(self):
        project = _make_project("App", commits=75)
        post = build_project_post(project)
        assert "75 commits" in post


# ---------------------------------------------------------------------------
# API endpoint tests
# ---------------------------------------------------------------------------

try:
    from fastapi.testclient import TestClient
    from main import app
    from api.dependencies import AuthContext, get_auth_context

    TEST_USER_ID = "test-user-linkedin-001"

    async def _override_auth() -> AuthContext:
        return AuthContext(user_id=TEST_USER_ID, access_token="test-token")

    # Verify TestClient works
    _test = TestClient(app)
    del _test
    _HAS_TEST_CLIENT = True
except Exception:
    _HAS_TEST_CLIENT = False


@pytest.mark.skipif(not _HAS_TEST_CLIENT, reason="TestClient unavailable")
class TestLinkedInPostEndpoint:
    @pytest.fixture(autouse=True)
    def setup(self):
        app.dependency_overrides[get_auth_context] = _override_auth
        yield
        app.dependency_overrides.clear()

    @pytest.fixture
    def client(self):
        return TestClient(app)

    def test_portfolio_post_returns_200(self, client):
        with patch("api.portfolio_routes.get_projects_service") as mock_dep:
            mock_service = MagicMock()
            mock_service.get_user_projects.return_value = [
                _make_project("Demo", langs=["Python"], commits=10, score=50),
            ]
            mock_dep.return_value = mock_service
            app.dependency_overrides[
                __import__("api.portfolio_routes", fromlist=["get_projects_service"]).get_projects_service
            ] = lambda: mock_service

            response = client.post(
                "/api/portfolio/linkedin-post",
                json={"scope": "portfolio"},
            )

        assert response.status_code == 200
        body = response.json()
        assert "post_text" in body
        assert isinstance(body["post_text"], str)
        assert len(body["post_text"]) > 0

    def test_project_post_returns_404_for_missing_project(self, client):
        with patch("api.portfolio_routes.get_projects_service") as mock_dep:
            mock_service = MagicMock()
            mock_service.get_user_projects.return_value = []
            mock_dep.return_value = mock_service
            from api.portfolio_routes import get_projects_service
            app.dependency_overrides[get_projects_service] = lambda: mock_service

            response = client.post(
                "/api/portfolio/linkedin-post",
                json={"scope": "project", "project_id": "nonexistent-id"},
            )

        assert response.status_code == 404
