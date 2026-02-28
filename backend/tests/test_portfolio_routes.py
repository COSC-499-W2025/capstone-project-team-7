"""Tests for GET /api/skills endpoint."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import api.portfolio_routes as portfolio_mod
from api.dependencies import AuthContext, get_auth_context
from services.services.portfolio_timeline_service import PortfolioTimelineServiceError


@pytest.fixture()
def mock_timeline_service():
    """Create a mock PortfolioTimelineService."""
    return MagicMock()


@pytest.fixture()
def client(mock_timeline_service):
    """Return a TestClient with auth and service mocked."""
    app = FastAPI()
    app.include_router(portfolio_mod.router)

    fake_ctx = AuthContext(
        user_id="user-123", access_token="tok-abc", email="user@example.com"
    )
    app.dependency_overrides[get_auth_context] = lambda: fake_ctx
    app.dependency_overrides[portfolio_mod.get_portfolio_timeline_service] = lambda: mock_timeline_service

    with TestClient(app) as c:
        yield c


@pytest.fixture()
def unauthenticated_client():
    """Return a TestClient without auth override."""
    app = FastAPI()
    app.include_router(portfolio_mod.router)

    with TestClient(app, raise_server_exceptions=False) as c:
        yield c


class TestGetAllSkills:
    def test_returns_unique_skills_sorted(self, client, mock_timeline_service):
        """GET /api/skills returns unique skills sorted alphabetically."""
        mock_timeline_service.get_skills_timeline.return_value = [
            {"skills": ["Python", "Docker", "FastAPI"], "period_label": "2025-01"},
            {"skills": ["Python", "React", "TypeScript"], "period_label": "2025-02"},
            {"skills": ["Docker", "AWS"], "period_label": "2025-03"},
        ]

        resp = client.get("/api/skills")

        assert resp.status_code == 200
        data = resp.json()
        assert "skills" in data
        # Should be unique and sorted (case-insensitive)
        assert data["skills"] == ["AWS", "Docker", "FastAPI", "Python", "React", "TypeScript"]

    def test_returns_empty_list_when_no_skills(self, client, mock_timeline_service):
        """GET /api/skills returns empty list when user has no projects."""
        mock_timeline_service.get_skills_timeline.return_value = []

        resp = client.get("/api/skills")

        assert resp.status_code == 200
        data = resp.json()
        assert data["skills"] == []

    def test_returns_empty_list_when_timeline_has_no_skills(self, client, mock_timeline_service):
        """GET /api/skills returns empty list when timeline items have no skills."""
        mock_timeline_service.get_skills_timeline.return_value = [
            {"skills": [], "period_label": "2025-01"},
            {"period_label": "2025-02"},  # Missing skills key
        ]

        resp = client.get("/api/skills")

        assert resp.status_code == 200
        data = resp.json()
        assert data["skills"] == []

    def test_service_error_returns_500(self, client, mock_timeline_service):
        """GET /api/skills returns 500 when service raises an error."""
        mock_timeline_service.get_skills_timeline.side_effect = PortfolioTimelineServiceError(
            "Database connection failed"
        )

        resp = client.get("/api/skills")

        assert resp.status_code == 500
        data = resp.json()
        assert data["detail"]["code"] == "skills_error"

    def test_unauthenticated_returns_error(self, unauthenticated_client):
        """GET /api/skills returns error when not authenticated."""
        resp = unauthenticated_client.get("/api/skills")
        # Should fail auth - exact code depends on how get_auth_context handles missing auth
        assert resp.status_code in (401, 403, 422, 500)

    def test_handles_case_insensitive_sorting(self, client, mock_timeline_service):
        """GET /api/skills sorts case-insensitively."""
        mock_timeline_service.get_skills_timeline.return_value = [
            {"skills": ["react", "AWS", "docker", "Python"], "period_label": "2025-01"},
        ]

        resp = client.get("/api/skills")

        assert resp.status_code == 200
        data = resp.json()
        # Case-insensitive sort: AWS, docker, Python, react
        assert data["skills"] == ["AWS", "docker", "Python", "react"]
