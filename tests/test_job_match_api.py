"""
Job Match API tests.

Tests for:
- POST /api/jobs/search  — basic job search
- POST /api/jobs/match   — search + scoring
- POST /api/jobs/explain — AI explanation
- _keyword_score helper logic
- Consent enforcement on external-calling endpoints
"""

import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
from fastapi.testclient import TestClient

backend_src = Path(__file__).parent.parent / "backend" / "src"
sys.path.insert(0, str(backend_src))

from main import app

client = TestClient(app)

TEST_TOKEN = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
    ".eyJzdWIiOiI5ODcwZWRiNS0yNzQxLTRjMGEtYjVjZC00OTRhNDk4Zjc0ODUifQ"
    ".test"
)
AUTH_HEADER = {"Authorization": f"Bearer {TEST_TOKEN}"}

# All endpoint tests that hit external services need consent mocked to True.
_CONSENT_PATCH = "api.job_match_routes.ConsentValidator"


def _mock_consent(allowed: bool = True):
    """Return a patcher that stubs ConsentValidator."""
    mock_cls = MagicMock()
    mock_cls.return_value.validate_external_services_consent.return_value = allowed
    return patch(_CONSENT_PATCH, mock_cls)


# =============================================================================
# Search endpoint
# =============================================================================

class TestJobSearch:
    """Tests for POST /api/jobs/search."""

    def test_search_returns_200(self, project_test_auth_override):
        with _mock_consent(True):
            response = client.post(
                "/api/jobs/search",
                json={"keywords": "python", "location": "", "results_per_page": 5, "country": "ca"},
                headers=AUTH_HEADER,
            )
        assert response.status_code == 200

    def test_search_returns_list(self, project_test_auth_override):
        with _mock_consent(True):
            response = client.post(
                "/api/jobs/search",
                json={"keywords": "developer", "results_per_page": 10, "country": "ca"},
                headers=AUTH_HEADER,
            )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        if data:
            assert "title" in data[0]
            assert "company" in data[0]
            assert "id" in data[0]

    def test_search_requires_auth(self):
        response = client.post(
            "/api/jobs/search",
            json={"keywords": "python"},
        )
        assert response.status_code == 401

    def test_search_without_consent_returns_403(self, project_test_auth_override):
        with _mock_consent(False):
            response = client.post(
                "/api/jobs/search",
                json={"keywords": "python", "results_per_page": 5, "country": "ca"},
                headers=AUTH_HEADER,
            )
        assert response.status_code == 403

    def test_search_empty_keywords_returns_empty(self, project_test_auth_override):
        with _mock_consent(True):
            response = client.post(
                "/api/jobs/search",
                json={"keywords": "", "results_per_page": 5, "country": "ca"},
                headers=AUTH_HEADER,
            )
        assert response.status_code == 200
        assert response.json() == []


# =============================================================================
# Match endpoint
# =============================================================================

class TestJobMatch:
    """Tests for POST /api/jobs/match."""

    def test_match_returns_200(self, project_test_auth_override):
        with _mock_consent(True):
            response = client.post(
                "/api/jobs/match",
                json={
                    "search": {"keywords": "python", "results_per_page": 5, "country": "ca"},
                    "profile": {
                        "skills": ["Python", "FastAPI"],
                        "job_titles": ["Backend Engineer"],
                        "experience_summary": "",
                        "education": "",
                    },
                },
                headers=AUTH_HEADER,
            )
        assert response.status_code == 200

    def test_match_response_shape(self, project_test_auth_override):
        with _mock_consent(True):
            response = client.post(
                "/api/jobs/match",
                json={
                    "search": {"keywords": "react", "results_per_page": 5, "country": "ca"},
                    "profile": {
                        "skills": ["React", "TypeScript"],
                        "job_titles": ["Front-End Developer"],
                    },
                },
                headers=AUTH_HEADER,
            )
        data = response.json()
        assert "jobs" in data
        assert "total" in data
        assert isinstance(data["jobs"], list)
        if data["jobs"]:
            job_entry = data["jobs"][0]
            assert "job" in job_entry
            assert "score" in job_entry
            assert "match_reasons" in job_entry

    def test_match_jobs_sorted_descending(self, project_test_auth_override):
        with _mock_consent(True):
            response = client.post(
                "/api/jobs/match",
                json={
                    "search": {"keywords": "", "results_per_page": 10, "country": "ca"},
                    "profile": {
                        "skills": ["Python", "React", "SQL"],
                        "job_titles": ["Full-Stack Developer"],
                    },
                },
                headers=AUTH_HEADER,
            )
        data = response.json()
        scores = [j["score"] for j in data["jobs"]]
        assert scores == sorted(scores, reverse=True)

    def test_match_without_consent_returns_403(self, project_test_auth_override):
        with _mock_consent(False):
            response = client.post(
                "/api/jobs/match",
                json={
                    "search": {"keywords": "python", "results_per_page": 5, "country": "ca"},
                    "profile": {"skills": ["Python"]},
                },
                headers=AUTH_HEADER,
            )
        assert response.status_code == 403

    def test_match_requires_auth(self):
        response = client.post(
            "/api/jobs/match",
            json={
                "search": {"keywords": "python"},
                "profile": {"skills": ["Python"]},
            },
        )
        assert response.status_code == 401


# =============================================================================
# Explain endpoint
# =============================================================================

class TestJobExplain:
    """Tests for POST /api/jobs/explain."""

    def test_explain_without_llm_returns_503(self, project_test_auth_override):
        """Without a configured LLM client, explain should fail gracefully."""
        with _mock_consent(True):
            response = client.post(
                "/api/jobs/explain",
                json={
                    "job": {
                        "id": "mock-1",
                        "title": "Developer",
                        "company": "Acme",
                        "location": "Remote",
                        "description": "Build stuff",
                    },
                    "profile": {"skills": ["Python"]},
                },
                headers=AUTH_HEADER,
            )
        # 503 because no LLM key is configured in test environment
        assert response.status_code == 503

    def test_explain_without_consent_returns_403(self, project_test_auth_override):
        with _mock_consent(False):
            response = client.post(
                "/api/jobs/explain",
                json={
                    "job": {"id": "1", "title": "Dev", "company": "X", "location": "R", "description": "D"},
                    "profile": {"skills": []},
                },
                headers=AUTH_HEADER,
            )
        assert response.status_code == 403

    def test_explain_requires_auth(self):
        response = client.post(
            "/api/jobs/explain",
            json={
                "job": {"id": "1", "title": "Dev"},
                "profile": {"skills": []},
            },
        )
        assert response.status_code == 401


# =============================================================================
# Keyword score unit tests
# =============================================================================

class TestKeywordScore:
    """Unit tests for the _keyword_score helper."""

    def test_no_profile_returns_50(self):
        from api.job_match_routes import _keyword_score, UserProfile
        from services.job_search_client import JobListing

        job = JobListing(
            id="1", title="Dev", company="Acme", location="Remote",
            description="Python developer wanted",
        )
        profile = UserProfile(skills=[], job_titles=[])
        score, reasons = _keyword_score(job, profile)
        assert score == 50.0
        assert len(reasons) == 1

    def test_matching_skill_increases_score(self):
        from api.job_match_routes import _keyword_score, UserProfile
        from services.job_search_client import JobListing

        job = JobListing(
            id="1", title="Python Developer", company="Acme",
            location="Remote", description="We need Python and FastAPI skills",
        )
        profile = UserProfile(skills=["Python", "FastAPI"], job_titles=[])
        score, reasons = _keyword_score(job, profile)
        assert score > 0
        assert any("Python" in r for r in reasons)

    def test_no_overlap_scores_zero(self):
        from api.job_match_routes import _keyword_score, UserProfile
        from services.job_search_client import JobListing

        job = JobListing(
            id="1", title="Chef", company="Restaurant",
            location="Kitchen", description="Cooking and baking",
        )
        profile = UserProfile(skills=["Rust", "Haskell"], job_titles=["Compiler Engineer"])
        score, reasons = _keyword_score(job, profile)
        assert score == 0.0
        assert len(reasons) == 0

    def test_matching_job_title_adds_reason(self):
        from api.job_match_routes import _keyword_score, UserProfile
        from services.job_search_client import JobListing

        job = JobListing(
            id="1", title="Full-Stack Developer", company="TechCo",
            location="Vancouver", description="Build web applications",
        )
        profile = UserProfile(
            skills=[], job_titles=["Full-Stack Developer"],
        )
        score, reasons = _keyword_score(job, profile)
        assert score > 0
        assert any("Full-Stack Developer" in r for r in reasons)
