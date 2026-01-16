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
            projects = self._projects_service.get_user_projects(user_id)
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
