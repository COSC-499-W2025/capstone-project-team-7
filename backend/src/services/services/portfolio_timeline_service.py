"""Service for building skills and portfolio chronology timelines."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from .projects_service import ProjectsService, ProjectsServiceError


class PortfolioTimelineServiceError(Exception):
    """Raised when timeline retrieval fails."""


class PortfolioTimelineService:
    """Aggregate project and skill timelines from stored scan data."""

    def __init__(self, projects_service: Optional[ProjectsService] = None) -> None:
        self._projects_service = projects_service or ProjectsService()

    def get_projects_timeline(self, user_id: str) -> List[Dict[str, Any]]:
        try:
            projects = self._projects_service.get_user_projects_with_roles(user_id)
        except ProjectsServiceError as exc:
            raise PortfolioTimelineServiceError(str(exc)) from exc

        items: List[Dict[str, Any]] = []
        for project in projects:
            start_date = project.get("scan_timestamp") or project.get("created_at")
            end_date = project.get("project_end_date")
            items.append(
                {
                    "project_id": project.get("id"),
                    "name": project.get("project_name"),
                    "start_date": start_date,
                    "end_date": end_date,
                    "duration_days": _duration_days(start_date, end_date),
                    "role": project.get("role"),
                    "evidence": project.get("evidence", []),
                }
            )

        items.sort(key=_project_sort_key)
        return items

    def get_skills_timeline(self, user_id: str) -> List[Dict[str, Any]]:
        try:
            projects = self._projects_service.get_user_projects_with_scan_data(user_id)
        except ProjectsServiceError as exc:
            raise PortfolioTimelineServiceError(str(exc)) from exc

        timeline: Dict[str, Dict[str, Any]] = {}
        for project in projects:
            project_name = project.get("project_name") or project.get("id") or "unknown"
            scan_data = project.get("scan_data") or {}
            for entry in _extract_skill_timeline_entries(scan_data):
                period = entry.get("period_label")
                if not period:
                    continue
                slot = timeline.setdefault(
                    period,
                    {"skills": set(), "commits": 0, "projects": set()},
                )
                slot["skills"].update(entry.get("skills") or [])
                slot["projects"].add(project_name)
                slot["commits"] += int(entry.get("commits") or 0)

        items: List[Dict[str, Any]] = []
        for period, data in timeline.items():
            items.append(
                {
                    "period_label": period,
                    "skills": sorted(data["skills"]),
                    "commits": data["commits"],
                    "projects": sorted(data["projects"]),
                }
            )

        items.sort(key=_skills_sort_key)
        return items

    def get_portfolio_chronology(self, user_id: str) -> Dict[str, List[Dict[str, Any]]]:
        return {
            "projects": self.get_projects_timeline(user_id),
            "skills": self.get_skills_timeline(user_id),
        }

    def get_project_evolution(self, user_id: str, project_ids: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Return per-project monthly evolution data for the given projects.

        Each entry contains the project id/name and a list of monthly periods
        with commits, skill count, languages, and cumulative lines.
        """
        try:
            projects = self._projects_service.get_user_projects_with_scan_data(user_id)
        except ProjectsServiceError as exc:
            raise PortfolioTimelineServiceError(str(exc)) from exc

        results: List[Dict[str, Any]] = []
        for project in projects:
            pid = project.get("id")
            if project_ids and pid not in project_ids:
                continue

            scan_data = project.get("scan_data") or {}
            periods = _extract_project_evolution_periods(scan_data)
            if not periods:
                continue

            results.append({
                "project_id": pid,
                "project_name": project.get("project_name") or pid or "unknown",
                "total_commits": project.get("total_commits") or 0,
                "total_lines": project.get("total_lines") or 0,
                "periods": periods,
            })

        return results


def _duration_days(start_date: Optional[str], end_date: Optional[str]) -> Optional[int]:
    start_dt = _parse_datetime(start_date)
    end_dt = _parse_datetime(end_date)
    if not start_dt or not end_dt:
        return None
    delta = (end_dt - start_dt).days
    return delta if delta >= 0 else None


def _project_sort_key(item: Dict[str, Any]) -> Tuple[Any, ...]:
    start_date = item.get("start_date") or ""
    parsed = _parse_datetime(start_date)
    date_key = parsed or datetime.max
    name = item.get("name") or ""
    project_id = item.get("project_id") or ""
    return (date_key, str(start_date), str(name), str(project_id))


def _skills_sort_key(item: Dict[str, Any]) -> Tuple[Any, ...]:
    period = item.get("period_label") or ""
    return (_parse_period_label(period), str(period))


def _parse_period_label(label: str) -> Tuple[int, int, int, str]:
    if not label:
        return (9999, 12, 31, "")
    for fmt in ("%Y-%m-%d", "%Y-%m", "%Y/%m/%d", "%Y/%m"):
        try:
            dt = datetime.strptime(label, fmt)
            return (dt.year, dt.month, dt.day, label)
        except ValueError:
            continue
    return (9999, 12, 31, label)


def _parse_datetime(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    cleaned = str(value).strip()
    if cleaned.endswith("Z"):
        cleaned = cleaned[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(cleaned)
    except ValueError:
        try:
            parsed = datetime.fromisoformat(cleaned[:10])
        except ValueError:
            return None
    if parsed.tzinfo is not None:
        parsed = parsed.astimezone(timezone.utc).replace(tzinfo=None)
    return parsed


def _extract_project_evolution_periods(scan_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Extract monthly evolution periods from a single project's scan data.

    Uses skills_progress.timeline (preferred) or skills_analysis.chronological_overview.
    Returns sorted list of {period_label, commits, skill_count, languages, activity_types}.
    """
    periods: List[Dict[str, Any]] = []

    skills_progress = scan_data.get("skills_progress")
    if isinstance(skills_progress, dict):
        timeline = skills_progress.get("timeline")
        if isinstance(timeline, list):
            for entry in timeline:
                if not isinstance(entry, dict):
                    continue
                period = entry.get("period_label")
                if not period:
                    continue
                languages = entry.get("period_languages") or entry.get("languages") or {}
                periods.append({
                    "period_label": period,
                    "commits": int(entry.get("commits") or 0),
                    "skill_count": int(entry.get("skill_count") or 0),
                    "languages": languages if isinstance(languages, dict) else {},
                    "activity_types": entry.get("activity_types") or [],
                })

    if not periods:
        skills_analysis = scan_data.get("skills_analysis")
        if isinstance(skills_analysis, dict):
            overview = skills_analysis.get("chronological_overview")
            if isinstance(overview, list):
                for entry in overview:
                    if not isinstance(entry, dict):
                        continue
                    period = entry.get("period")
                    if not period:
                        continue
                    skills_list = entry.get("skills_exercised") or []
                    periods.append({
                        "period_label": period,
                        "commits": 0,
                        "skill_count": len(skills_list),
                        "languages": {},
                        "activity_types": [],
                    })

    periods.sort(key=lambda p: _parse_period_label(p.get("period_label", "")))
    return periods


def _extract_skill_timeline_entries(scan_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Extract skill timeline from scan data.

    Preference order:
    1) skills_progress.timeline (month-level progression with commits)
    2) skills_analysis.chronological_overview (derived from evidence timestamps)
    """
    skills_progress = scan_data.get("skills_progress")
    if isinstance(skills_progress, dict):
        timeline = skills_progress.get("timeline")
        if isinstance(timeline, list):
            return [
                {
                    "period_label": entry.get("period_label"),
                    "skills": entry.get("top_skills") or entry.get("skills") or [],
                    "commits": entry.get("commits") or 0,
                }
                for entry in timeline
                if isinstance(entry, dict)
            ]

    skills_analysis = scan_data.get("skills_analysis")
    if isinstance(skills_analysis, dict):
        overview = skills_analysis.get("chronological_overview")
        if isinstance(overview, list):
            return [
                {
                    "period_label": entry.get("period"),
                    "skills": entry.get("skills_exercised") or [],
                    "commits": 0,
                }
                for entry in overview
                if isinstance(entry, dict)
            ]

    return []
