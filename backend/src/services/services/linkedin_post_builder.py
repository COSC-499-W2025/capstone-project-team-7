"""Template-based LinkedIn post text generator.

Produces short, shareable posts from portfolio or single-project data.
No external API dependencies — just string interpolation.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional


def _extract_languages(scan_data: Dict[str, Any]) -> List[str]:
    """Pull language names from scan_data."""
    languages = scan_data.get("languages") or scan_data.get("summary", {}).get("languages") or []
    if isinstance(languages, list):
        return [
            (l.get("name") or l.get("language") or str(l)) if isinstance(l, dict) else str(l)
            for l in languages[:6]
        ]
    return []


def _extract_commit_count(scan_data: Dict[str, Any]) -> int:
    git_analysis = scan_data.get("git_analysis")
    if isinstance(git_analysis, list) and git_analysis:
        return git_analysis[0].get("commit_count", 0)
    return 0


def build_portfolio_post(
    projects: List[Dict[str, Any]],
    skills: List[str],
    share_url: Optional[str] = None,
) -> str:
    """Generate a LinkedIn post summarising the user's portfolio."""
    lines: List[str] = []
    lines.append("I just updated my developer portfolio!\n")

    if projects:
        lines.append(f"Across {len(projects)} project{'s' if len(projects) != 1 else ''}, here are some highlights:\n")
        # Pick top 3 projects (prefer those with contribution_score)
        ranked = sorted(
            projects,
            key=lambda p: p.get("contribution_score") or 0,
            reverse=True,
        )[:3]
        for p in ranked:
            name = p.get("project_name") or "Unnamed"
            sd = p.get("scan_data") or {}
            langs = _extract_languages(sd)
            commits = _extract_commit_count(sd)
            detail_parts = []
            if langs:
                detail_parts.append(", ".join(langs[:3]))
            if commits:
                detail_parts.append(f"{commits} commits")
            detail = f" ({' | '.join(detail_parts)})" if detail_parts else ""
            lines.append(f"  - {name}{detail}")
        lines.append("")

    if skills:
        display_skills = skills[:8]
        lines.append("Key skills demonstrated: " + ", ".join(display_skills))
        if len(skills) > 8:
            lines.append(f"  ...and {len(skills) - 8} more")
        lines.append("")

    if share_url:
        lines.append(f"Check out my portfolio: {share_url}")
        lines.append("")

    # Hashtags
    tags = ["#SoftwareDevelopment", "#Portfolio", "#OpenToWork"]
    # Add language hashtags
    all_langs: List[str] = []
    for p in projects[:5]:
        sd = p.get("scan_data") or {}
        all_langs.extend(_extract_languages(sd))
    seen: set = set()
    for lang in all_langs:
        tag = f"#{lang.replace(' ', '').replace('.', '')}"
        if tag not in seen and len(tags) < 8:
            tags.append(tag)
            seen.add(tag)
    lines.append(" ".join(tags))

    return "\n".join(lines)


def build_project_post(project: Dict[str, Any]) -> str:
    """Generate a LinkedIn post for a single project."""
    name = project.get("project_name") or "Unnamed Project"
    sd = project.get("scan_data") or {}
    langs = _extract_languages(sd)
    commits = _extract_commit_count(sd)
    summary = sd.get("summary") or {}
    total_files = summary.get("total_files", 0)

    lines: List[str] = []
    lines.append(f"Excited to share a project I've been working on: {name}!\n")

    detail_parts = []
    if langs:
        detail_parts.append(f"Built with {', '.join(langs[:4])}")
    if total_files:
        detail_parts.append(f"{total_files} files")
    if commits:
        detail_parts.append(f"{commits} commits")
    if detail_parts:
        lines.append(" | ".join(detail_parts) + "\n")

    # Extract skills from this project
    sa = sd.get("skills_analysis")
    if isinstance(sa, dict):
        skill_names: List[str] = []
        for entries in (sa.get("skills_by_category") or {}).values():
            if not isinstance(entries, list):
                continue
            for e in entries:
                n = e.get("name") if isinstance(e, dict) else (e if isinstance(e, str) else None)
                if n and n not in skill_names:
                    skill_names.append(n)
        if skill_names:
            lines.append("Skills demonstrated: " + ", ".join(skill_names[:6]) + "\n")

    role = project.get("role")
    if role:
        lines.append(f"My role: {role}\n")

    tags = ["#SoftwareDevelopment", "#Project"]
    for lang in langs[:3]:
        tags.append(f"#{lang.replace(' ', '').replace('.', '')}")
    lines.append(" ".join(tags))

    return "\n".join(lines)
