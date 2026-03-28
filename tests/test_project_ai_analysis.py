"""
Tests for the AI analysis feature in project_routes.py.

Covers:
  - _build_categorized_ai_prompt output shape
  - run_project_ai_analysis cached-result early return path
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

# Make backend/src importable (mirrors conftest.py convention)
sys.path.insert(0, str(Path(__file__).parent.parent / "backend" / "src"))

from main import app
from api.project_routes import _build_categorized_ai_prompt, verify_auth_token

# ---------------------------------------------------------------------------
# Shared test data
# ---------------------------------------------------------------------------

TEST_USER_ID = "test-user-ai-analysis-abc123"

SAMPLE_SCAN_DATA = {
    "summary": {"total_files": 20, "total_lines": 1500},
    "languages": [{"name": "Python"}, {"name": "JavaScript"}],
    "code_analysis": {
        "total_files": 20,
        "total_lines": 1500,
        "functions": 45,
        "classes": 8,
        "avg_complexity": 3.2,
        "magic_values": 2,
        "naming_issues": 1,
        "dead_code": {"total": 3, "unused_functions": 1, "unused_imports": 2},
        "languages": {"Python": 12, "JavaScript": 8},
    },
    "skills_analysis": {
        "skills_by_category": {
            "frameworks": [{"name": "FastAPI"}, {"name": "React"}],
            "databases": [{"name": "PostgreSQL"}],
        }
    },
}

SAMPLE_ACTIVE_CATEGORIES = [
    ("code_analysis", "Code Analysis"),
    ("skills_analysis", "Skills Analysis"),
]

SAMPLE_FILE_SNIPPETS = [
    {"path": "src/main.py", "content": "def main():\n    pass"},
    {"path": "src/app.js", "content": "const x = 1;"},
]

# ---------------------------------------------------------------------------
# _build_categorized_ai_prompt tests
# ---------------------------------------------------------------------------


class TestBuildCategorizedAiPrompt:
    """Unit tests for the pure prompt-builder function."""

    def test_returns_nonempty_string(self):
        result = _build_categorized_ai_prompt(
            "My Project", SAMPLE_SCAN_DATA, SAMPLE_FILE_SNIPPETS, SAMPLE_ACTIVE_CATEGORIES
        )
        assert isinstance(result, str)
        assert len(result) > 0

    def test_contains_project_name(self):
        result = _build_categorized_ai_prompt(
            "PortfolioApp", SAMPLE_SCAN_DATA, SAMPLE_FILE_SNIPPETS, SAMPLE_ACTIVE_CATEGORIES
        )
        assert "PortfolioApp" in result

    def test_contains_category_labels(self):
        result = _build_categorized_ai_prompt(
            "My Project", SAMPLE_SCAN_DATA, SAMPLE_FILE_SNIPPETS, SAMPLE_ACTIVE_CATEGORIES
        )
        assert "CODE ANALYSIS" in result.upper()
        assert "SKILLS ANALYSIS" in result.upper()

    def test_contains_file_snippet_paths(self):
        result = _build_categorized_ai_prompt(
            "My Project", SAMPLE_SCAN_DATA, SAMPLE_FILE_SNIPPETS, SAMPLE_ACTIVE_CATEGORIES
        )
        assert "src/main.py" in result
        assert "src/app.js" in result

    def test_json_output_keys_in_prompt(self):
        """The task section must request overall_summary and per-category keys."""
        result = _build_categorized_ai_prompt(
            "My Project", SAMPLE_SCAN_DATA, SAMPLE_FILE_SNIPPETS, SAMPLE_ACTIVE_CATEGORIES
        )
        assert "overall_summary" in result
        assert "code_analysis" in result
        assert "skills_analysis" in result

    def test_no_file_snippets(self):
        """Should not crash and should still produce a valid prompt with no files."""
        result = _build_categorized_ai_prompt(
            "My Project", SAMPLE_SCAN_DATA, [], SAMPLE_ACTIVE_CATEGORIES
        )
        assert isinstance(result, str)
        assert "My Project" in result

    def test_empty_active_categories(self):
        """Zero categories → prompt still has output key doc (empty)."""
        result = _build_categorized_ai_prompt(
            "My Project", SAMPLE_SCAN_DATA, SAMPLE_FILE_SNIPPETS, []
        )
        assert isinstance(result, str)
        assert "overall_summary" in result

    def test_language_list_appears(self):
        result = _build_categorized_ai_prompt(
            "My Project", SAMPLE_SCAN_DATA, SAMPLE_FILE_SNIPPETS, SAMPLE_ACTIVE_CATEGORIES
        )
        assert "Python" in result or "JavaScript" in result


# ---------------------------------------------------------------------------
# run_project_ai_analysis – cached-result early-return tests
# ---------------------------------------------------------------------------

# Override auth for the entire test module
async def _mock_verify_auth():
    return TEST_USER_ID


@pytest.fixture(autouse=True)
def _override_auth_for_module():
    app.dependency_overrides[verify_auth_token] = _mock_verify_auth
    yield
    app.dependency_overrides.clear()

client = TestClient(app)


class TestRunProjectAiAnalysisCachedReturn:
    """Tests for the cached-result early-return branch of the AI analysis endpoint."""

    def _make_project_with_ai_analysis(self, ai_analysis: dict) -> dict:
        return {
            "project_id": "proj-cached-001",
            "project_name": "Cached Project",
            "scan_data": {
                "summary": {"total_files": 5},
                "ai_analysis": ai_analysis,
            },
        }

    @patch("api.project_routes.get_projects_service")
    def test_returns_cached_result_when_force_false(self, mock_get_service):
        """If ai_analysis exists in scan_data and force=False, the endpoint must
        return the cached data with llm_status='used:cached' without calling the LLM."""
        ai_analysis = {
            "overall_summary": "Stored portfolio summary.",
            "categories": [{"category": "code_analysis", "label": "Code Analysis",
                            "summary": "Good code.", "insights": ["Fast"]}],
        }
        mock_service = MagicMock()
        mock_service.get_project_scan.return_value = self._make_project_with_ai_analysis(ai_analysis)
        mock_get_service.return_value = mock_service

        response = client.post(
            "/api/projects/proj-cached-001/ai-analysis",
            headers={"Authorization": "Bearer test-token"},
        )

        assert response.status_code == 200
        body = response.json()
        assert body["llm_status"] == "used:cached"
        assert body["cached"] is True
        assert body["result"]["overall_summary"] == "Stored portfolio summary."

    @patch("api.project_routes.get_projects_service")
    def test_cached_result_does_not_call_llm(self, mock_get_service):
        """The LLM client must NOT be invoked when a cached result is returned."""
        ai_analysis = {"overall_summary": "Cached.", "categories": []}
        mock_service = MagicMock()
        mock_service.get_project_scan.return_value = self._make_project_with_ai_analysis(ai_analysis)
        mock_get_service.return_value = mock_service

        with patch("api.project_routes.get_or_hydrate_llm_client") as mock_llm:
            response = client.post("/api/projects/proj-cached-001/ai-analysis")
            mock_llm.assert_not_called()

        assert response.status_code == 200
        assert response.json()["llm_status"] == "used:cached"

    @patch("api.project_routes.get_projects_service")
    def test_force_true_bypasses_cache(self, mock_get_service):
        """With force=True the cached value should be skipped (consent check or LLM path taken)."""
        ai_analysis = {"overall_summary": "Old summary.", "categories": []}
        mock_service = MagicMock()
        mock_service.get_project_scan.return_value = self._make_project_with_ai_analysis(ai_analysis)
        mock_get_service.return_value = mock_service

        # The endpoint will proceed past the cache check; mock downstream so it
        # short-circuits at the consent stage with a predictable status.
        with patch("api.project_routes.ConsentValidator") as MockCV:
            instance = MockCV.return_value
            instance.validate_external_services_consent.return_value = False

            response = client.post(
                "/api/projects/proj-cached-001/ai-analysis?force=true"
            )

        assert response.status_code == 403
        assert response.json()["detail"] == "External services consent not granted."

    @patch("api.project_routes.get_projects_service")
    def test_no_existing_ai_analysis_skips_cache(self, mock_get_service):
        """When scan_data has no ai_analysis key, the cache branch is skipped entirely."""
        mock_service = MagicMock()
        mock_service.get_project_scan.return_value = {
            "project_id": "proj-fresh-001",
            "project_name": "Fresh Project",
            "scan_data": {"summary": {"total_files": 1}},
        }
        mock_get_service.return_value = mock_service

        with patch("api.project_routes.ConsentValidator") as MockCV:
            instance = MockCV.return_value
            instance.validate_external_services_consent.return_value = False

            response = client.post("/api/projects/proj-fresh-001/ai-analysis")

        assert response.status_code == 403
        assert response.json()["detail"] == "External services consent not granted."
