"""
Tests for skill progress timeline helper.
"""

from pathlib import Path
import sys
import types

# Add backend/src to path so backend.src.* imports resolve
backend_src_path = Path(__file__).parent.parent / "backend" / "src"
sys.path.insert(0, str(backend_src_path))

# Stub pypdf dependency to keep imports lightweight in this test environment
if "pypdf" not in sys.modules:  # pragma: no cover - test harness shim
    errors_module = types.SimpleNamespace(PdfReadError=Exception)
    sys.modules["pypdf"] = types.SimpleNamespace(PdfReader=lambda *args, **kwargs: None, errors=errors_module)
    sys.modules["pypdf.errors"] = errors_module

from backend.src.local_analysis.skill_progress_timeline import SkillProgression, build_skill_progression
from backend.src.local_analysis.contribution_analyzer import ActivityBreakdown, ProjectContributionMetrics
from backend.src.cli.services.skills_analysis_service import SkillsAnalysisService


def _make_metrics() -> ProjectContributionMetrics:
    metrics = ProjectContributionMetrics(
        project_path="proj",
        project_type="individual",
        total_commits=10,
        total_contributors=1,
        overall_activity_breakdown=ActivityBreakdown(),
    )
    metrics.timeline = [
        {"month": "2024-01", "commits": 4},
        {"month": "2024-02", "commits": 6},
    ]
    metrics.languages_detected = {"Python", "JavaScript"}
    return metrics


def test_build_skill_progression_merges_skills_and_commits():
    chronological = [
        {
            "period": "2024-01",
            "skills_exercised": ["Testing", "API Design"],
            "skill_count": 2,
            "evidence_count": 3,
            "details": [
                {"file_path": "tests/test_app.py"},
                {"file_path": "src/app.py"},
            ],
        },
        {
            "period": "2024-02",
            "skills_exercised": ["Refactoring"],
            "skill_count": 1,
            "evidence_count": 1,
            "details": [],
        },
    ]
    progression: SkillProgression = build_skill_progression(chronological, _make_metrics())

    assert len(progression.timeline) == 2
    jan, feb = progression.timeline

    assert jan.period_label == "2024-01"
    assert jan.commits == 4
    assert jan.tests_changed == 1  # one test file in details
    assert jan.skill_count == 2
    assert jan.evidence_count == 3
    assert jan.top_skills == ["Testing", "API Design"]
    assert set(jan.languages.keys()) == {"JavaScript", "Python"}

    assert feb.period_label == "2024-02"
    assert feb.commits == 6
    assert feb.tests_changed == 0
    assert feb.top_skills == ["Refactoring"]


def test_build_skill_progression_handles_missing_contributions():
    chronological = [
        {"period": "2024-03", "skills_exercised": ["Docs"], "skill_count": 1, "evidence_count": 1}
    ]
    progression = build_skill_progression(chronological, contribution_metrics=None)

    assert len(progression.timeline) == 1
    period = progression.timeline[0]
    assert period.period_label == "2024-03"
    assert period.commits == 0
    assert period.languages == {}


def test_skills_service_builds_progression(monkeypatch):
    service = SkillsAnalysisService()
    chronological = [
        {
            "period": "2024-01",
            "skills_exercised": ["Testing"],
            "skill_count": 1,
            "evidence_count": 2,
            "details": [{"file_path": "tests/test_app.py"}],
        }
    ]
    monkeypatch.setattr(service, "get_chronological_overview", lambda: chronological)

    result = service.build_skill_progression(contribution_metrics=None)

    assert result is not None
    assert "timeline" in result
    assert result["timeline"][0]["period_label"] == "2024-01"
