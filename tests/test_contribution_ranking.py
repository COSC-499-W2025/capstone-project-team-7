import sys
import types
import pytest
from datetime import datetime, timedelta, timezone

# Stub optional dependencies pulled in by local_analysis import chain
sys.modules.setdefault("pypdf", types.SimpleNamespace(PdfReader=object))

from services.contribution_analysis_service import ContributionAnalysisService
from backend.src.local_analysis.contribution_analyzer import (
    ProjectContributionMetrics,
    ContributorMetrics,
    ActivityBreakdown,
)


def _sample_metrics(end_date: datetime) -> ProjectContributionMetrics:
    return ProjectContributionMetrics(
        project_path=".",
        project_type="collaborative",
        total_commits=100,
        total_contributors=2,
        project_duration_days=180,
        project_start_date=(end_date - timedelta(days=180)).isoformat(),
        project_end_date=end_date.isoformat(),
        contributors=[
            ContributorMetrics(name="You", email="you@example.com", commits=60, commit_percentage=60.0),
            ContributorMetrics(name="Teammate", email="teammate@example.com", commits=40, commit_percentage=40.0),
        ],
        overall_activity_breakdown=ActivityBreakdown(
            code_lines=8000,
            test_lines=1500,
            documentation_lines=500,
            design_lines=0,
            config_lines=300,
        ),
        commit_frequency=1.1,
    )


def test_user_share_boosts_score():
    now = datetime(2025, 1, 1, tzinfo=timezone.utc)
    metrics = _sample_metrics(now)
    service = ContributionAnalysisService()

    score_with_user = service.compute_contribution_score(
        metrics, user_email="you@example.com", now=now
    )
    score_without_user = service.compute_contribution_score(
        metrics, user_email="other@example.com", now=now
    )

    assert pytest.approx(score_with_user["user_commit_share"], rel=1e-3) == 0.6
    assert score_with_user["score"] > score_without_user["score"]


def test_recency_influences_score():
    service = ContributionAnalysisService()
    ref = datetime(2025, 1, 1, tzinfo=timezone.utc)
    recent_metrics = _sample_metrics(ref)
    old_metrics = _sample_metrics(ref - timedelta(days=730))  # ~2 years old

    recent_score = service.compute_contribution_score(recent_metrics, user_email="you@example.com", now=ref)["score"]
    old_score = service.compute_contribution_score(old_metrics, user_email="you@example.com", now=ref)["score"]

    assert recent_score > old_score


def test_metrics_from_dict_round_trip():
    service = ContributionAnalysisService()
    payload = {
        "project_path": ".",
        "project_type": "individual",
        "total_commits": 10,
        "total_contributors": 1,
        "project_end_date": "2024-12-31T00:00:00Z",
        "overall_activity_breakdown": {
            "lines": {"code": 1000, "test": 200, "documentation": 100, "design": 0, "config": 50},
            "percentages": {},
        },
        "contributors": [
            {
                "name": "Solo",
                "email": "solo@example.com",
                "commits": 10,
                "commit_percentage": 100.0,
                "active_days": 10,
                "activity_breakdown": {"lines": {"code": 800, "test": 150, "documentation": 50, "design": 0, "config": 0}},
            }
        ],
        "commit_frequency": 0.5,
        "languages_detected": ["python"],
    }

    metrics = service.metrics_from_dict(payload)
    ranking = service.compute_contribution_score(metrics, user_email="solo@example.com")

    assert metrics.total_commits == 10
    assert ranking["score"] > 0
    assert ranking["user_commit_share"] == pytest.approx(1.0)
