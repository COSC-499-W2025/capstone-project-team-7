"""Portfolio deployment service — generates static HTML and deploys to Vercel.

The generated HTML uses Tailwind CSS (CDN) and the same custom CSS classes /
design tokens as the app's PortfolioOverview component so the deployed
portfolio looks identical to the in-app view.
"""

from __future__ import annotations

import base64
import html as html_mod
import logging
import os
import re
from typing import Any, Dict, List

import httpx

logger = logging.getLogger(__name__)

_VERCEL_API = "https://api.vercel.com/v13/deployments"

MONTHS = ["", "Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def _esc(text: Any) -> str:
    return html_mod.escape(str(text)) if text else ""


def _format_period(label: str) -> str:
    m = re.match(r"^(\d{4})-(\d{2})$", label or "")
    if not m:
        return label or ""
    mi = int(m.group(2))
    return f"{MONTHS[mi]} {m.group(1)}" if 1 <= mi <= 12 else label


def _period_value(label: str) -> int:
    m = re.match(r"^(\d{4})-(\d{2})$", label or "")
    return int(m.group(1)) * 100 + int(m.group(2)) if m else 0


# ---------------------------------------------------------------------------
# Section renderers — match the PortfolioOverview React component exactly
# ---------------------------------------------------------------------------


def _heatmap_section(heatmap_data: List[Dict[str, Any]]) -> str:
    """Renders the Activity Heatmap panel (matches activity-heatmap.tsx)."""
    if not heatmap_data:
        return ""
    commit_map: Dict[str, int] = {}
    max_c = 0
    years_set: set[int] = set()
    for e in heatmap_data:
        p = e.get("period", "")
        c = e.get("commits", 0)
        commit_map[p] = c
        if c > max_c:
            max_c = c
        y = int(p[:4]) if len(p) >= 4 and p[:4].isdigit() else None
        if y:
            years_set.add(y)
    years = sorted(years_set, reverse=True)
    if not years:
        return ""

    # Peak activity label
    peak_period = ""
    peak_commits = 0
    for e in heatmap_data:
        if e.get("commits", 0) > peak_commits:
            peak_commits = e["commits"]
            peak_period = e.get("period", "")
    peak_label = _format_period(peak_period)

    def _cls(commits: int) -> str:
        if commits == 0 or max_c == 0:
            return "bg-slate-100 text-slate-300"
        r = commits / max_c
        if r >= 0.85:
            return "bg-sky-700 text-sky-50"
        if r >= 0.65:
            return "bg-sky-600 text-sky-50"
        if r >= 0.4:
            return "bg-sky-300 text-sky-950"
        return "bg-sky-100 text-sky-700"

    month_hdr = "".join(
        f'<div class="text-center text-[10px] font-semibold uppercase tracking-[0.18em] text-slate-400">{m}</div>'
        for m in MONTHS[1:]
    )
    year_rows = ""
    for yr in years:
        total = 0
        cells = ""
        for mi in range(1, 13):
            key = f"{yr}-{mi:02d}"
            c = commit_map.get(key, 0)
            total += c
            cells += (
                f'<div class="flex h-6 items-center justify-center rounded-lg border border-white/70 '
                f'text-[9px] font-semibold transition-colors sm:h-7 sm:rounded-xl sm:text-[10px] md:h-8 {_cls(c)}" '
                f'title="{MONTHS[mi]} {yr}: {c} commits">{c if c else ""}</div>'
            )
        year_rows += (
            f'<div class="grid grid-cols-[42px_minmax(240px,1fr)] items-center gap-2.5 '
            f'md:grid-cols-[56px_minmax(360px,1fr)_72px] md:gap-3">'
            f'<div class="text-xs font-semibold text-slate-700 md:text-sm">{yr}</div>'
            f'<div class="grid grid-cols-12 gap-1.5">{cells}</div>'
            f'<div class="hidden text-right text-xs font-medium text-slate-500 md:block">{total:,}</div>'
            f'</div>'
        )

    legend = (
        '<div class="flex flex-col gap-3 border-t border-slate-200 pt-3 text-xs text-slate-500 sm:flex-row sm:items-center sm:justify-between">'
        '<div class="flex items-center gap-1.5">'
        '<span>Lower activity</span>'
        '<div class="h-3.5 w-3.5 rounded-md bg-slate-100"></div>'
        '<div class="h-3.5 w-3.5 rounded-md bg-sky-100"></div>'
        '<div class="h-3.5 w-3.5 rounded-md bg-sky-300"></div>'
        '<div class="h-3.5 w-3.5 rounded-md bg-sky-600"></div>'
        '<div class="h-3.5 w-3.5 rounded-md bg-sky-700"></div>'
        '<span>Higher activity</span></div>'
        f'<p>{len(years)} year{"" if len(years) == 1 else "s"} tracked</p></div>'
    )

    return (
        f'<article class="portfolio-panel p-5">'
        f'<div class="flex flex-wrap items-start justify-between gap-3">'
        f'<div>'
        f'<p class="text-[11px] font-semibold uppercase tracking-[0.22em] text-muted-foreground">Activity</p>'
        f'<h3 class="mt-1 text-lg font-semibold tracking-tight text-foreground">Activity Heatmap</h3>'
        f'<p class="mt-1 text-sm text-muted-foreground">Monthly contribution density, compressed into a year-by-year dashboard view.</p>'
        f'</div>'
        f'<div class="rounded-md border border-border bg-muted px-3 py-1.5 text-xs font-medium text-muted-foreground">Peak: {_esc(peak_label)}</div>'
        f'</div>'
        f'<div class="mt-5"><div class="space-y-4"><div class="overflow-x-auto">'
        f'<div class="min-w-[18rem] space-y-3 sm:min-w-[24rem] md:min-w-[38rem]">'
        f'<div class="grid grid-cols-[42px_minmax(240px,1fr)] items-center gap-2.5 md:grid-cols-[56px_minmax(360px,1fr)_72px] md:gap-3">'
        f'<div></div><div class="grid grid-cols-12 gap-1.5">{month_hdr}</div>'
        f'<div class="hidden text-right text-[10px] font-semibold uppercase tracking-[0.18em] text-slate-400 md:block">Total</div></div>'
        f'{year_rows}</div></div>{legend}</div></div></article>'
    )


def _timeline_section(skills_timeline: List[Dict[str, Any]]) -> str:
    """Renders the Skills Timeline panel (matches skills-timeline.tsx)."""
    if not skills_timeline:
        return ""

    items = sorted(skills_timeline, key=lambda x: _period_value(x.get("period_label", "")), reverse=True)
    max_c = max((i.get("commits", 0) for i in items), default=1) or 1
    num_periods = len(items)

    rows = ""
    for item in items:
        c = item.get("commits", 0)
        skills = item.get("skills", [])
        projects = item.get("projects", [])
        bar_w = max(6, int((c / max_c) * 100))
        tags = "".join(
            f'<span class="rounded-full border border-primary/15 bg-primary/10 px-2.5 py-1 text-[11px] font-medium text-accent-foreground">{_esc(s)}</span>'
            for s in skills[:6]
        )
        if len(skills) > 6:
            tags += f'<span class="rounded-full border border-border bg-background px-2.5 py-1 text-[11px] font-medium text-muted-foreground">+{len(skills) - 6} more</span>'
        skill_html = f'<div class="flex flex-wrap gap-1.5">{tags}</div>' if skills else '<p class="text-xs text-muted-foreground">No skill tags were attributed to this period.</p>'
        rows += (
            f'<article class="rounded-2xl border border-border bg-card p-3.5">'
            f'<div class="grid gap-3 sm:grid-cols-[112px_minmax(0,1fr)] sm:items-center">'
            f'<div class="rounded-xl border border-border bg-background px-3 py-2.5">'
            f'<p class="text-[11px] font-semibold uppercase tracking-[0.18em] text-muted-foreground">{_esc(_format_period(item.get("period_label", "")))}</p>'
            f'<p class="mt-1 text-xl font-semibold tracking-tight text-foreground">{c}</p>'
            f'<p class="text-xs text-muted-foreground">commit{"" if c == 1 else "s"}</p></div>'
            f'<div class="space-y-2.5">'
            f'<div class="flex items-center gap-2">'
            f'<div class="h-2 flex-1 overflow-hidden rounded-full bg-background">'
            f'<div class="h-full rounded-full bg-primary" style="width:{bar_w}%"></div></div>'
            f'<span class="text-[11px] font-medium text-muted-foreground">{len(projects)} project{"" if len(projects) == 1 else "s"}</span></div>'
            f'{skill_html}'
            f'</div></div></article>'
        )

    return (
        f'<article class="portfolio-panel p-5">'
        f'<div class="flex flex-wrap items-start justify-between gap-3">'
        f'<div>'
        f'<p class="text-[11px] font-semibold uppercase tracking-[0.22em] text-muted-foreground">Skills Insights</p>'
        f'<h3 class="mt-1 text-lg font-semibold tracking-tight text-foreground">Skills Timeline</h3>'
        f'<p class="mt-1 text-sm text-muted-foreground">Monthly skill adoption, arranged into compact cards that read cleanly on desktop and mobile.</p>'
        f'</div>'
        f'<div class="rounded-md border border-border bg-muted px-3 py-1.5 text-xs font-medium text-muted-foreground">{num_periods} periods</div>'
        f'</div>'
        f'<div class="mt-5"><div class="max-h-[30rem] space-y-3 overflow-y-auto pr-1">{rows}</div></div></article>'
    )


def _projects_section(top_projects: List[Dict[str, Any]]) -> str:
    """Renders the Top Projects panel (matches portfolio-overview.tsx)."""
    if not top_projects:
        return ""

    cards = ""
    for idx, p in enumerate(top_projects):
        score = p.get("contribution_score")
        commits = p.get("total_commits")
        share = p.get("user_commit_share")
        primary = p.get("primary_contributor")
        name = _esc(p.get("project_name", ""))

        score_html = ""
        if score is not None:
            score_html = (
                f'<div class="rounded-md border border-border bg-muted px-2.5 py-1.5 text-right text-xs font-semibold text-foreground">'
                f'{round(score)}'
                f'<div class="mt-0.5 text-[10px] font-medium uppercase tracking-[0.18em] text-muted-foreground">score</div>'
                f'</div>'
            )

        subtitle = ""
        if primary:
            subtitle = f'<p class="mt-1 break-all text-xs leading-5 text-muted-foreground">Primary contributor: {_esc(primary)}</p>'

        chips = ""
        if commits is not None:
            chips += f'<span class="rounded-md border border-border bg-white px-2.5 py-1 text-[11px] font-medium text-muted-foreground">{commits:,} commits</span>'
        if share is not None:
            chips += f'<span class="rounded-md border border-border bg-white px-2.5 py-1 text-[11px] font-medium text-muted-foreground">{round(share * 100)}% yours</span>'

        cards += (
            f'<article class="min-w-0 overflow-hidden rounded-md border border-border bg-muted/85 p-4 transition-colors hover:border-border hover:bg-white">'
            f'<div class="flex items-start justify-between gap-4">'
            f'<div class="flex min-w-0 items-start gap-3">'
            f'<div class="flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-md border border-border bg-white text-sm font-semibold text-foreground">#{idx + 1}</div>'
            f'<div class="min-w-0">'
            f'<h4 class="truncate text-sm font-semibold text-foreground">{name}</h4>'
            f'{subtitle}'
            f'</div></div>'
            f'{score_html}'
            f'</div>'
            f'{f"""<div class="mt-3 flex flex-wrap gap-2">{chips}</div>""" if chips else ""}'
            f'</article>'
        )

    return (
        f'<article id="portfolio-projects" class="portfolio-panel p-5">'
        f'<div class="flex flex-wrap items-start justify-between gap-3">'
        f'<div>'
        f'<p class="text-[11px] font-semibold uppercase tracking-[0.22em] text-muted-foreground">Showcase</p>'
        f'<h3 class="mt-1 text-lg font-semibold tracking-tight text-foreground">Top Projects</h3>'
        f'<p class="mt-1 text-sm text-muted-foreground">Ranked work surfaced with the clearest contribution and output signals.</p>'
        f'</div>'
        f'<div class="rounded-md border border-border bg-muted px-3 py-1.5 text-xs font-medium text-muted-foreground">{len(top_projects)} shown</div>'
        f'</div>'
        f'<div class="mt-5 grid gap-3 2xl:grid-cols-2">{cards}</div></article>'
    )


def _skills_section(all_skills: List[str]) -> str:
    """Renders the All Skills panel (matches portfolio-overview.tsx)."""
    if not all_skills:
        return ""
    tags = "".join(
        f'<div class="rounded-md border border-border bg-muted/85 px-3 py-2.5 text-sm font-medium text-foreground">{_esc(s)}</div>'
        for s in all_skills
    )
    return (
        f'<article id="portfolio-skills" class="portfolio-panel p-5">'
        f'<div class="flex flex-wrap items-start justify-between gap-3">'
        f'<div>'
        f'<p class="text-[11px] font-semibold uppercase tracking-[0.22em] text-muted-foreground">Skills Library</p>'
        f'<h3 class="mt-1 text-lg font-semibold tracking-tight text-foreground">All Skills</h3>'
        f'<p class="mt-1 text-sm text-muted-foreground">{len(all_skills)} skills across all projects</p>'
        f'</div>'
        f'<div class="rounded-md border border-border bg-muted px-3 py-1.5 text-xs font-medium text-muted-foreground">Scrollable list</div>'
        f'</div>'
        f'<div class="mt-5 max-h-[24rem] overflow-y-auto pr-1"><div class="grid gap-2 sm:grid-cols-2">{tags}</div></div></article>'
    )


# ---------------------------------------------------------------------------
# Custom CSS — exact copies from globals.css so the deployed page matches
# ---------------------------------------------------------------------------

_CUSTOM_CSS = r"""
:root {
  --background: 220 30% 97%;
  --foreground: 224 28% 14%;
  --muted: 220 25% 94%;
  --muted-foreground: 221 12% 43%;
  --card: 0 0% 100%;
  --card-foreground: 224 28% 14%;
  --primary: 214 86% 56%;
  --primary-foreground: 0 0% 100%;
  --secondary: 220 28% 95%;
  --secondary-foreground: 224 24% 18%;
  --accent: 214 100% 96%;
  --accent-foreground: 215 70% 27%;
  --border: 220 20% 88%;
  --ring: 214 86% 56%;
  --radius: 18px;
  --shadow-soft: 0 18px 42px rgba(15, 23, 42, 0.08);
  --shadow-inset: inset 0 1px 0 rgba(255, 255, 255, 0.8);
  --opacity-hover: 0.28;
}
*, *::before, *::after { box-sizing: border-box; }
body {
  margin: 0;
  background: hsl(var(--background));
  color: hsl(var(--foreground));
  font-family: "Avenir Next", "Segoe UI", "Helvetica Neue", sans-serif;
  -webkit-font-smoothing: antialiased;
}
h1,h2,h3,h4 {
  font-family: "Iowan Old Style", "Palatino Linotype", Georgia, serif;
  letter-spacing: -0.03em;
}

/* -- Component classes from globals.css -- */
.portfolio-panel {
  border-radius: 24px;
  background: linear-gradient(180deg, hsl(var(--card)), hsl(var(--background) / 0.72));
  box-shadow: var(--shadow-soft);
  transition: transform 180ms ease;
}
.portfolio-panel:hover {
  transform: translateY(-2px);
  border-color: hsl(var(--primary) / var(--opacity-hover));
}
.portfolio-panel-subtle {
  border-radius: 18px;
  background: linear-gradient(180deg, hsl(var(--card) / 0.88), hsl(var(--muted) / 0.72));
  box-shadow: var(--shadow-inset);
}
.portfolio-panel-subtle:hover {
  transform: translateY(-2px);
  border-color: hsl(var(--primary) / var(--opacity-hover));
}
.portfolio-chip {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 7px 12px;
  border-radius: 999px;
  background: hsl(var(--card) / 0.82);
  color: hsl(var(--foreground) / 0.84);
  font-size: 12px;
  line-height: 16px;
  font-weight: 600;
  transition: transform 160ms ease, background-color 160ms ease, color 160ms ease;
}
.portfolio-chip:hover {
  transform: translateY(-1px);
  background: hsl(var(--accent) / 0.72);
  color: hsl(var(--foreground));
}

/* -- Tailwind CSS variable bridges -- */
.bg-card { background: hsl(var(--card)); }
.bg-muted { background: hsl(var(--muted)); }
.bg-background { background: hsl(var(--background)); }
.bg-primary { background: hsl(var(--primary)); }
.bg-primary\/10 { background: hsl(var(--primary) / 0.1); }
.bg-primary\/5 { background: hsl(var(--primary) / 0.05); }
.bg-muted\/85 { background: hsl(var(--muted) / 0.85); }
.bg-muted\/70 { background: hsl(var(--muted) / 0.72); }
.text-foreground { color: hsl(var(--foreground)); }
.text-muted-foreground { color: hsl(var(--muted-foreground)); }
.text-primary { color: hsl(var(--primary)); }
.text-primary-foreground { color: hsl(var(--primary-foreground)); }
.text-accent-foreground { color: hsl(var(--accent-foreground)); }
.border-border { border-color: hsl(var(--border)); }
.border-primary\/15 { border-color: hsl(var(--primary) / 0.15); }
.border-primary\/25 { border-color: hsl(var(--primary) / 0.25); }
"""


# ---------------------------------------------------------------------------
# Main HTML generator
# ---------------------------------------------------------------------------


def _get_primary_skill(skills_timeline: List[Dict[str, Any]], all_skills: List[str]) -> str:
    counts: Dict[str, int] = {}
    for period in skills_timeline:
        for skill in period.get("skills", []):
            counts[skill] = counts.get(skill, 0) + 1
    if counts:
        return max(counts, key=lambda k: counts[k])
    return all_skills[0] if all_skills else "No skill data"


def _get_latest_activity(skills_timeline: List[Dict[str, Any]]) -> str:
    if not skills_timeline:
        return "No activity yet"
    latest = max(skills_timeline, key=lambda x: _period_value(x.get("period_label", "")))
    return _format_period(latest.get("period_label", ""))


def _get_peak_activity(skills_timeline: List[Dict[str, Any]]) -> tuple:
    if not skills_timeline:
        return ("No activity yet", 0)
    peak = max(skills_timeline, key=lambda x: x.get("commits", 0))
    return (_format_period(peak.get("period_label", "")), peak.get("commits", 0))


def generate_portfolio_html(
    profile: Dict[str, Any],
    settings: Dict[str, Any],
    skills_timeline: List[Dict[str, Any]],
    top_projects: List[Dict[str, Any]],
    heatmap_data: List[Dict[str, Any]],
    all_skills: List[str],
) -> str:
    """Generate a self-contained HTML portfolio page matching PortfolioOverview."""
    display_name = _esc(profile.get("display_name", "Portfolio"))
    avatar_url = profile.get("avatar_url")
    career_title = profile.get("career_title")
    education = profile.get("education")
    bio = profile.get("bio")

    total_commits = sum(e.get("commits", 0) for e in skills_timeline)
    active_months = len(skills_timeline)
    primary_skill = _get_primary_skill(skills_timeline, all_skills)
    latest_activity = _get_latest_activity(skills_timeline)
    peak_label, peak_commits = _get_peak_activity(skills_timeline)
    lead_project = top_projects[0] if top_projects else None

    # --- Avatar ---
    avatar_html = (
        f'<img src="{_esc(avatar_url)}" alt="avatar" class="h-full w-full object-cover">'
        if avatar_url
        else '<svg class="h-7 w-7 text-muted-foreground" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>'
    )

    # --- Career subtitle ---
    career_html = ""
    if career_title:
        career_html += f'<p class="text-base font-medium text-foreground">{_esc(career_title)}</p>'
    if education:
        career_html += f'<p class="text-sm text-muted-foreground">{_esc(education)}</p>'

    # --- Summary section (left column) ---
    summary_left = f"""
      <div class="flex gap-4">
        <div class="flex h-16 w-16 flex-shrink-0 items-center justify-center overflow-hidden rounded-md border-2 border-border bg-muted">
          {avatar_html}
        </div>
        <div class="min-w-0 space-y-3">
          <div class="space-y-1">
            <p class="text-[11px] font-semibold uppercase tracking-[0.24em] text-muted-foreground">Portfolio Dashboard</p>
            <div class="flex flex-wrap items-center gap-2">
              <h2 class="text-[2.2rem] font-semibold tracking-[-0.04em] text-foreground">{display_name}</h2>
              <span class="rounded-full border border-primary/15 bg-primary/10 px-2.5 py-1 text-[11px] font-semibold uppercase tracking-[0.14em] text-accent-foreground">Storyboard</span>
            </div>
            {career_html}
          </div>
          <p class="max-w-2xl text-sm leading-6 text-muted-foreground">
            {_esc(bio) if bio else "Project output, contribution activity, and extracted skills are grouped into a tighter dashboard so the strongest signals are visible quickly."}
          </p>
          <div class="flex flex-wrap gap-2">
            <span class="portfolio-chip">
              <svg class="h-3.5 w-3.5" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><rect x="2" y="7" width="20" height="14" rx="2"/><path d="M16 3h-8l-2 4h12z"/></svg>
              {len(top_projects)} project{"" if len(top_projects) == 1 else "s"}
            </span>
            <span class="portfolio-chip">
              <svg class="h-3.5 w-3.5" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><circle cx="12" cy="8" r="7"/><polyline points="8.21 13.89 7 23 12 20 17 23 15.79 13.88"/></svg>
              Focus skill: {_esc(primary_skill)}
            </span>
            <span class="portfolio-chip">
              <svg class="h-3.5 w-3.5" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><rect x="3" y="4" width="18" height="18" rx="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>
              Latest activity: {_esc(latest_activity)}
            </span>
          </div>
        </div>
      </div>"""

    # --- Summary section (right column — 3 info cards) ---
    lead_name = _esc(lead_project.get("project_name", "")) if lead_project else "No ranked project yet"
    lead_score = f"Score {round(lead_project['contribution_score'])}" if lead_project and lead_project.get("contribution_score") is not None else "Contribution ranking appears here once available."

    summary_right = f"""
      <div class="grid gap-3 sm:grid-cols-3 xl:grid-cols-1">
        <div class="portfolio-panel-subtle p-4">
          <div class="flex items-start justify-between gap-3">
            <div class="min-w-0">
              <p class="text-[11px] font-semibold uppercase tracking-[0.18em] text-muted-foreground">Top Project</p>
              <p class="mt-1 truncate text-sm font-semibold text-foreground">{lead_name}</p>
              <p class="mt-1 text-xs text-muted-foreground">{lead_score}</p>
            </div>
            <div class="rounded-2xl border border-border bg-white p-2.5 text-foreground shadow-[0_10px_20px_rgba(15,23,42,0.07)]">
              <svg class="h-4 w-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M6 9H4.5a2.5 2.5 0 0 1 0-5C7 4 9 8 12 8s5-4 7.5-4a2.5 2.5 0 0 1 0 5H18"/><path d="m18 15-6-6-6 6"/><path d="M12 21.8V9"/></svg>
            </div>
          </div>
        </div>
        <div class="portfolio-panel-subtle p-4">
          <div class="flex items-start justify-between gap-3">
            <div class="min-w-0">
              <p class="text-[11px] font-semibold uppercase tracking-[0.18em] text-muted-foreground">Peak Activity</p>
              <p class="mt-1 text-sm font-semibold text-foreground">{_esc(peak_label)}</p>
              <p class="mt-1 text-xs text-muted-foreground">{f"{peak_commits:,} commits in the busiest period" if peak_commits > 0 else "Scan git history to surface your busiest period."}</p>
            </div>
            <div class="rounded-2xl border border-border bg-white p-2.5 text-foreground shadow-[0_10px_20px_rgba(15,23,42,0.07)]">
              <svg class="h-4 w-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><circle cx="12" cy="12" r="4"/><line x1="1.05" y1="12" x2="7" y2="12"/><line x1="17.01" y1="12" x2="22.96" y2="12"/></svg>
            </div>
          </div>
        </div>
        <div class="portfolio-panel-subtle p-4">
          <div class="flex items-start justify-between gap-3">
            <div class="min-w-0">
              <p class="text-[11px] font-semibold uppercase tracking-[0.18em] text-muted-foreground">Skills Coverage</p>
              <p class="mt-1 text-sm font-semibold text-foreground">{f"{len(all_skills)} tracked skills" if all_skills else "Awaiting extraction"}</p>
              <p class="mt-1 text-xs text-muted-foreground">{"Skill signals stay grouped with timeline activity for faster review." if all_skills else "Run project scans to populate the skills library."}</p>
            </div>
            <div class="rounded-2xl border border-border bg-white p-2.5 text-foreground shadow-[0_10px_20px_rgba(15,23,42,0.07)]">
              <svg class="h-4 w-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="m12 3-1.912 5.813a2 2 0 0 1-1.275 1.275L3 12l5.813 1.912a2 2 0 0 1 1.275 1.275L12 21l1.912-5.813a2 2 0 0 1 1.275-1.275L21 12l-5.813-1.912a2 2 0 0 1-1.275-1.275z"/></svg>
            </div>
          </div>
        </div>
      </div>"""

    # --- 4 stat cards ---
    stats_data = [
        ("Briefcase", '<svg class="h-4 w-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><rect x="2" y="7" width="20" height="14" rx="2"/><path d="M16 3h-8l-2 4h12z"/></svg>', len(top_projects), "Projects", "Scanned repositories"),
        ("GitCommit", '<svg class="h-4 w-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><circle cx="12" cy="12" r="4"/><line x1="1.05" y1="12" x2="7" y2="12"/><line x1="17.01" y1="12" x2="22.96" y2="12"/></svg>', total_commits, "Total Commits", "Across tracked periods"),
        ("Award", '<svg class="h-4 w-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><circle cx="12" cy="8" r="7"/><polyline points="8.21 13.89 7 23 12 20 17 23 15.79 13.88"/></svg>', len(all_skills), "Skills", "Extracted capabilities"),
        ("Calendar", '<svg class="h-4 w-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><rect x="3" y="4" width="18" height="18" rx="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>', active_months, "Active Months", "Months with git activity"),
    ]
    stats_html = ""
    for _, icon_svg, value, label, detail in stats_data:
        stats_html += (
            f'<div class="portfolio-panel-subtle p-4">'
            f'<div class="flex items-start justify-between gap-3">'
            f'<div class="rounded-md border border-border bg-white p-2 text-foreground">{icon_svg}</div>'
            f'<span class="text-[11px] font-semibold uppercase tracking-[0.18em] text-muted-foreground">{label}</span>'
            f'</div>'
            f'<p class="mt-4 text-2xl font-semibold tracking-tight text-foreground">{value:,}</p>'
            f'<p class="mt-1 text-xs text-muted-foreground">{detail}</p>'
            f'</div>'
        )

    # --- Insight sections (heatmap + skills timeline side by side) ---
    show_heatmap = settings.get("show_heatmap", True)
    show_timeline = settings.get("show_skills_timeline", True)
    show_projects = settings.get("show_top_projects", True)
    show_skills = settings.get("show_all_skills", True)

    heatmap_html = _heatmap_section(heatmap_data) if show_heatmap else ""
    timeline_html = _timeline_section(skills_timeline) if show_timeline else ""
    projects_html = _projects_section(top_projects) if show_projects else ""
    skills_html = _skills_section(all_skills) if show_skills else ""

    insights_section = ""
    if heatmap_html or timeline_html:
        if heatmap_html and timeline_html:
            grid_class = "grid gap-4 xl:grid-cols-[minmax(0,1.18fr)_minmax(320px,0.92fr)]"
        else:
            grid_class = "grid gap-4 grid-cols-1"
        insights_section = f'<section class="{grid_class}">{heatmap_html}{timeline_html}</section>'

    library_section = ""
    if projects_html or skills_html:
        if projects_html and skills_html:
            grid_class = "grid gap-4 xl:grid-cols-[minmax(0,1.15fr)_minmax(320px,0.95fr)]"
        else:
            grid_class = "grid gap-4 grid-cols-1"
        library_section = f'<section class="{grid_class}">{projects_html}{skills_html}</section>'

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{display_name} &mdash; Portfolio</title>
<script src="https://cdn.tailwindcss.com"></script>
<style>{_CUSTOM_CSS}</style>
</head>
<body>
<div class="flex flex-col gap-6 px-6 py-7 sm:px-8" style="max-width:1520px;margin:0 auto">

  <!-- Summary Panel -->
  <section class="portfolio-panel p-5 sm:p-6">
    <div class="grid gap-5 xl:grid-cols-[minmax(0,1.2fr)_minmax(320px,0.82fr)]">
      {summary_left}
      {summary_right}
    </div>
  </section>

  <!-- Stat Cards -->
  <section class="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
    {stats_html}
  </section>

  <!-- Insights (Heatmap + Skills Timeline) -->
  {insights_section}

  <!-- Projects + Skills -->
  {library_section}

  <footer class="text-center text-xs text-muted-foreground py-4">Built with DevFolio</footer>
</div>
</body>
</html>"""


# ---------------------------------------------------------------------------
# Vercel deployment
# ---------------------------------------------------------------------------


async def deploy_to_vercel(html_content: str, share_token: str) -> Dict[str, Any]:
    """Deploy a static HTML file to Vercel. Returns {{url, status}}."""
    token = os.getenv("VERCEL_API_TOKEN")
    if not token:
        return {"url": None, "status": "error", "error": "VERCEL_API_TOKEN not configured"}

    safe_token = "".join(c if c.isalnum() else "-" for c in share_token[:12]).lower().strip("-")
    project_name = f"portfolio-{safe_token}"
    encoded = base64.b64encode(html_content.encode("utf-8")).decode("ascii")

    payload = {
        "name": project_name,
        "files": [{"file": "index.html", "data": encoded, "encoding": "base64"}],
        "projectSettings": {"framework": None},
        "target": "production",
    }
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(_VERCEL_API, json=payload, headers=headers)

    if resp.status_code >= 400:
        logger.error("Vercel deploy failed: %s %s", resp.status_code, resp.text)
        return {"url": None, "status": "error", "error": f"Vercel API error ({resp.status_code})"}

    data = resp.json()
    url = data.get("url")
    if url and not url.startswith("http"):
        url = f"https://{url}"
    return {"url": url, "status": "success"}


async def delete_vercel_deployment(share_token: str) -> None:
    """Delete a Vercel project (and all its deployments) by name."""
    token = os.getenv("VERCEL_API_TOKEN")
    if not token:
        return

    safe_token = "".join(c if c.isalnum() else "-" for c in share_token[:12]).lower().strip("-")
    project_name = f"portfolio-{safe_token}"

    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.delete(
            f"https://api.vercel.com/v9/projects/{project_name}",
            headers={"Authorization": f"Bearer {token}"},
        )
    if resp.status_code >= 400 and resp.status_code != 404:
        logger.error("Vercel project delete failed: %s %s", resp.status_code, resp.text)
