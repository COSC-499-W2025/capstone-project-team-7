"""Service that generates personalised learning resource suggestions.

Aggregates skills across all of a user's scanned projects, identifies skills
at beginner or intermediate proficiency, and recommends curated resources at
the next tier.  Optionally weights suggestions by role importance when a target
role is specified.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def _tier_index(tier: str) -> int:
    from analyzer.resource_map import TIER_ORDER
    try:
        return TIER_ORDER.index(tier)
    except ValueError:
        return 0


def _aggregate_user_skills(projects: List[Dict[str, Any]]) -> Dict[str, str]:
    """Return {skill_name: highest_tier} across all user projects."""
    skills: Dict[str, int] = {}  # skill_name -> best tier index

    for project in projects:
        scan_data = project.get("scan_data")
        if not isinstance(scan_data, dict):
            continue

        skills_analysis = scan_data.get("skills_analysis")
        if not isinstance(skills_analysis, dict):
            continue

        by_category = skills_analysis.get("skills_by_category")
        if not isinstance(by_category, dict):
            continue

        for _category, entries in by_category.items():
            if not isinstance(entries, list):
                continue
            for entry in entries:
                if isinstance(entry, str):
                    name = entry
                    tier_idx = 0
                elif isinstance(entry, dict):
                    name = entry.get("name", "")
                    tier = entry.get("highest_tier") or entry.get("tier") or "beginner"
                    tier_idx = _tier_index(tier)
                else:
                    continue
                if not name:
                    continue
                skills[name] = max(skills.get(name, -1), tier_idx)

    from analyzer.resource_map import TIER_ORDER
    return {name: TIER_ORDER[idx] for name, idx in skills.items()}


def collect_skill_names(projects: List[Dict[str, Any]]) -> List[str]:
    """Return a flat deduplicated list of skill names across all projects."""
    seen: set = set()
    result: List[str] = []
    for project in projects:
        scan_data = project.get("scan_data")
        if not isinstance(scan_data, dict):
            continue
        sa = scan_data.get("skills_analysis")
        if not isinstance(sa, dict):
            continue
        for entries in (sa.get("skills_by_category") or {}).values():
            if not isinstance(entries, list):
                continue
            for entry in entries:
                name = entry.get("name") if isinstance(entry, dict) else (entry if isinstance(entry, str) else None)
                if name and name not in seen:
                    seen.add(name)
                    result.append(name)
    return result


def get_suggestions(
    user_id: str,
    projects: List[Dict[str, Any]],
    role: Optional[str] = None,
) -> Dict[str, Any]:
    """Build resource suggestions for a user.

    Args:
        user_id: The authenticated user's ID.
        projects: List of project dicts (each with ``scan_data``).
        role: Optional role key (e.g. ``"backend_developer"``) to weight
              suggestions by role importance.

    Returns:
        Dict with *suggestions* list, *role*, and *role_label*.
    """
    from analyzer.resource_map import get_next_tier, get_resources_for_skill

    aggregated = _aggregate_user_skills(projects)
    if not aggregated:
        return {"suggestions": [], "role": role, "role_label": None}

    # Load role profile for importance weighting (optional)
    importance_map: Dict[str, str] = {}
    role_label: Optional[str] = None
    if role:
        try:
            from analyzer.skill_gap_analyzer import ROLE_PROFILES
            profile = ROLE_PROFILES.get(role)
            if profile:
                role_label = profile.get("label", role)
                importance_map = profile.get("expected_skills", {})
        except ImportError:
            pass

    suggestions: List[Dict[str, Any]] = []

    for skill_name, current_tier in aggregated.items():
        target_tier = get_next_tier(current_tier)
        if target_tier is None:
            # Already advanced — no suggestion needed
            continue

        resources = get_resources_for_skill(skill_name, target_tier)
        if not resources:
            continue

        importance = importance_map.get(skill_name)
        if importance:
            reason = (
                f"You're at {current_tier} level — this is a {importance.replace('_', ' ')} "
                f"skill for {role_label or role}. Level up to {target_tier}."
            )
        else:
            reason = (
                f"You're at {current_tier} level. "
                f"These resources can help you reach {target_tier}."
            )

        suggestions.append({
            "skill_name": skill_name,
            "current_tier": current_tier,
            "target_tier": target_tier,
            "reason": reason,
            "importance": importance,
            "resources": resources,
        })

    # Sort: role-critical first, then recommended, then alphabetical
    _importance_order = {"critical": 0, "recommended": 1, "nice_to_have": 2}
    suggestions.sort(
        key=lambda s: (
            _importance_order.get(s.get("importance") or "", 3),
            s["skill_name"],
        )
    )

    return {
        "suggestions": suggestions,
        "role": role,
        "role_label": role_label,
    }
