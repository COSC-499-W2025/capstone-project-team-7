"""Helpers for constructing a skills progress timeline from existing analyses.

This module is intentionally heuristic-only: it stitches together the
SkillsExtractor chronological overview and contribution metrics to produce a
month-level timeline without new git calls.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import re

from .contribution_analyzer import ProjectContributionMetrics


# Reuse the contribution analyzer's notion of test files.
_TEST_REGEX = re.compile(
    r'(?:test[_-]|_test\.|\.test\.|\.spec\.|/tests?/|/specs?/|/__tests__/|_spec\.)',
    re.IGNORECASE,
)


@dataclass
class SkillProgressPeriod:
    """Aggregated snapshot for a single month/period."""

    period_label: str
    commits: int = 0
    tests_changed: int = 0
    skill_count: int = 0
    evidence_count: int = 0
    top_skills: List[str] = field(default_factory=list)
    languages: Dict[str, int] = field(default_factory=dict)


@dataclass
class SkillProgression:
    """Container for skill progression timeline."""

    timeline: List[SkillProgressPeriod] = field(default_factory=list)


def _is_test_path(path: str) -> bool:
    """Lightweight check for test-like paths."""
    return bool(_TEST_REGEX.search(path))


def build_skill_progression(
    chronological_overview: List[Dict[str, Any]],
    contribution_metrics: Optional[ProjectContributionMetrics] = None,
) -> SkillProgression:
    """
    Build a month-level skill progression timeline.

    Args:
        chronological_overview: Output from SkillsExtractor.get_chronological_overview().
        contribution_metrics: ProjectContributionMetrics (optional) for commit counts and languages.

    Returns:
        SkillProgression with one period per month label found in the inputs.
    """
    periods: Dict[str, SkillProgressPeriod] = {}

    # Seed with skills/timestamps.
    for entry in chronological_overview or []:
        period = entry.get("period")
        if not period:
            continue
        period_ref = periods.setdefault(period, SkillProgressPeriod(period_label=period))
        period_ref.skill_count = entry.get("skill_count", period_ref.skill_count)
        period_ref.evidence_count = entry.get("evidence_count", period_ref.evidence_count)

        skills = entry.get("skills_exercised") or []
        if skills:
            # Keep stable ordering; de-duplicate while preserving order.
            seen = set()
            ordered = []
            for skill in skills:
                if skill in seen:
                    continue
                seen.add(skill)
                ordered.append(skill)
            period_ref.top_skills = ordered[:5]

        details = entry.get("details") or []
        test_hits = sum(1 for d in details if _is_test_path(str(d.get("file_path", ""))))
        period_ref.tests_changed += test_hits

    # Merge commit timeline/languages from contribution metrics, if available.
    if contribution_metrics:
        for month_entry in contribution_metrics.timeline or []:
            month = month_entry.get("month")
            if not month:
                continue
            period_ref = periods.setdefault(month, SkillProgressPeriod(period_label=month))
            period_ref.commits = month_entry.get("commits", period_ref.commits)

        if contribution_metrics.languages_detected:
            lang_counts = {lang: 1 for lang in sorted(contribution_metrics.languages_detected)}
            for period_ref in periods.values():
                # Languages are applied uniformly; we don't have per-period language usage.
                period_ref.languages = dict(lang_counts)

    timeline = [periods[key] for key in sorted(periods.keys())]
    return SkillProgression(timeline=timeline)
