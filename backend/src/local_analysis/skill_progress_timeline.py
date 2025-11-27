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
    contributors: int = 0
    commit_messages: List[str] = field(default_factory=list)
    top_files: List[str] = field(default_factory=list)
    activity_types: List[str] = field(default_factory=list)
    period_languages: Dict[str, int] = field(default_factory=dict)


@dataclass
class SkillProgression:
    """Container for skill progression timeline."""

    timeline: List[SkillProgressPeriod] = field(default_factory=list)


def _is_test_path(path: str) -> bool:
    """Lightweight check for test-like paths."""
    return bool(_TEST_REGEX.search(path))


def _infer_activity_types(messages: List[str], files: List[str]) -> List[str]:
    """Derive simple activity labels from commit messages and file paths."""
    labels: set[str] = set()
    for path in files:
        lowered = path.lower()
        if _is_test_path(path):
            labels.add("tests")
        if "migrate" in lowered or "migration" in lowered or "schema" in lowered:
            labels.add("migrations")
        if "ui" in lowered or "frontend" in lowered or lowered.endswith(".tcss"):
            labels.add("ui")
        if "async" in lowered or "concurrency" in lowered:
            labels.add("async")
        if "refactor" in lowered:
            labels.add("refactor")
        if "ai" in lowered or "llm" in lowered:
            labels.add("ai")
        if "docs" in lowered or "readme" in lowered or lowered.endswith(".md"):
            labels.add("docs")
        if "auth" in lowered or "login" in lowered or "session" in lowered:
            labels.add("auth")
        if "api" in lowered or "route" in lowered or "endpoint" in lowered:
            labels.add("api")
        if "cli" in lowered or "command" in lowered:
            labels.add("cli")
        if "config" in lowered or "settings" in lowered or lowered.endswith(".yaml") or lowered.endswith(".yml") or lowered.endswith(".json"):
            labels.add("config")
    for msg in messages:
        lowered = msg.lower()
        if "test" in lowered:
            labels.add("tests")
        if "refactor" in lowered:
            labels.add("refactor")
        if "async" in lowered or "concurrency" in lowered:
            labels.add("async")
        if "migrate" in lowered or "migration" in lowered or "schema" in lowered:
            labels.add("migrations")
        if "ui" in lowered or "frontend" in lowered:
            labels.add("ui")
        if "ai" in lowered or "llm" in lowered:
            labels.add("ai")
        if "docs" in lowered or "readme" in lowered or "documentation" in lowered:
            labels.add("docs")
        if "auth" in lowered or "login" in lowered or "session" in lowered:
            labels.add("auth")
        if "api" in lowered or "route" in lowered or "endpoint" in lowered:
            labels.add("api")
        if "cli" in lowered or "command" in lowered:
            labels.add("cli")
        if "fix" in lowered or "bug" in lowered:
            labels.add("bugfix")
        if "feat" in lowered or "feature" in lowered or "add" in lowered:
            labels.add("feature")
    return sorted(labels)


def build_skill_progression(
    chronological_overview: List[Dict[str, Any]],
    contribution_metrics: Optional[ProjectContributionMetrics] = None,
    *,
    author_emails: Optional[set[str]] = None,
) -> SkillProgression:
    """
    Build a month-level skill progression timeline.

    Args:
        chronological_overview: Output from SkillsExtractor.get_chronological_overview().
        contribution_metrics: ProjectContributionMetrics (optional) for commit counts and languages.
        author_emails: Optional set of author emails to filter git activity to a single contributor.

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
        # Build per-month language hints if present in the timeline entries
        per_month_languages: Dict[str, Dict[str, int]] = {}
        for month_entry in contribution_metrics.timeline or []:
            month = month_entry.get("month")
            if not month:
                continue
            langs = month_entry.get("languages") or month_entry.get("period_languages") or {}
            if isinstance(langs, dict):
                per_month_languages[month] = {k: v for k, v in langs.items() if k}

        for month_entry in contribution_metrics.timeline or []:
            month = month_entry.get("month")
            if not month:
                continue
            period_ref = periods.setdefault(month, SkillProgressPeriod(period_label=month))
            # Note: git_repo.py provides commits at month level, not per-contributor
            # When author_emails filter is set, we still use the month-level commits
            # because the timeline is already filtered by author in contribution_analyzer
            month_commits = month_entry.get("commits", 0)
            if author_emails:
                # Timeline from contribution_analyzer is already author-filtered,
                # so we can use the month-level commit count directly
                period_ref.commits = month_commits
                period_ref.contributors = 1 if month_commits > 0 else 0
            else:
                period_ref.commits = month_commits if month_commits > 0 else period_ref.commits
                period_ref.contributors = max(
                    period_ref.contributors, getattr(contribution_metrics, "total_contributors", 0)
                )
            # Carry over evidence-rich fields if present
            commit_messages = month_entry.get("messages") or month_entry.get("commit_messages") or []
            if commit_messages:
                period_ref.commit_messages = list(commit_messages)[:15]  # Increased from 10
            top_files = month_entry.get("top_files") or []
            if top_files:
                period_ref.top_files = list(top_files)[:10]  # Increased from 5
            period_ref.activity_types = _infer_activity_types(period_ref.commit_messages, period_ref.top_files)
            period_langs = month_entry.get("languages") or month_entry.get("period_languages")
            if isinstance(period_langs, dict):
                period_ref.period_languages = dict(period_langs)

        # Attach per-period languages only; do not fall back to repo-wide stats.
        for period_ref in periods.values():
            period_langs = per_month_languages.get(period_ref.period_label)
            period_ref.languages = dict(period_langs) if period_langs else {}
            period_ref.period_languages = dict(period_langs) if period_langs else {}

    timeline = [periods[key] for key in sorted(periods.keys())]
    return SkillProgression(timeline=timeline)
