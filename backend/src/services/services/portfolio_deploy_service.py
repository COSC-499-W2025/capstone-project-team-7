"""Portfolio deployment service — generates static HTML and deploys to Vercel.

The generated HTML uses a pre-built static CSS bundle (inlined) containing
only the Tailwind utility classes actually used by the template, plus the
same custom CSS classes / design tokens as the app's PortfolioOverview
component so the deployed portfolio looks identical to the in-app view.

Note: We intentionally avoid the Tailwind Play CDN (cdn.tailwindcss.com)
because it ships ~300 KB of JS that generates CSS client-side, is marked
"not for production" by the Tailwind team, and causes a flash of unstyled
content on every page load.  Inlining only the rules we need keeps the
deployed page fast and free of external CDN dependencies.
"""

from __future__ import annotations

import base64
import hashlib
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
/* ── Design tokens (from globals.css) ─────────────────────────────── */
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

/* ── Reset / base ─────────────────────────────────────────────────── */
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
body {
  margin: 0;
  background: hsl(var(--background));
  color: hsl(var(--foreground));
  font-family: "Avenir Next", "Segoe UI", "Helvetica Neue", sans-serif;
  -webkit-font-smoothing: antialiased;
  line-height: 1.5;
}
h1,h2,h3,h4 {
  font-family: "Iowan Old Style", "Palatino Linotype", Georgia, serif;
  letter-spacing: -0.03em;
}
img, svg { display: block; }
article, section, footer { display: block; }

/* ── Component classes from globals.css ───────────────────────────── */
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

/* ── CSS-variable-based colour bridges ────────────────────────────── */
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
.border-white\/70 { border-color: rgba(255,255,255,0.7); }

/* ── Tailwind utility classes (static, only those used in template) ── */

/* Display */
.block { display: block; }
.inline-flex { display: inline-flex; }
.flex { display: flex; }
.grid { display: grid; }
.hidden { display: none; }

/* Flex */
.flex-col { flex-direction: column; }
.flex-wrap { flex-wrap: wrap; }
.flex-shrink-0 { flex-shrink: 0; }
.flex-1 { flex: 1 1 0%; }
.items-center { align-items: center; }
.items-start { align-items: start; }
.justify-center { justify-content: center; }
.justify-between { justify-content: space-between; }

/* Grid */
.grid-cols-1 { grid-template-columns: repeat(1, minmax(0, 1fr)); }
.grid-cols-12 { grid-template-columns: repeat(12, minmax(0, 1fr)); }
.grid-cols-\[42px_minmax\(240px\,1fr\)\] { grid-template-columns: 42px minmax(240px,1fr); }

/* Gap */
.gap-1\.5 { gap: 0.375rem; }
.gap-2 { gap: 0.5rem; }
.gap-2\.5 { gap: 0.625rem; }
.gap-3 { gap: 0.75rem; }
.gap-4 { gap: 1rem; }
.gap-5 { gap: 1.25rem; }
.gap-6 { gap: 1.5rem; }

/* Spacing */
.space-y-1 > * + * { margin-top: 0.25rem; }
.space-y-2\.5 > * + * { margin-top: 0.625rem; }
.space-y-3 > * + * { margin-top: 0.75rem; }
.space-y-4 > * + * { margin-top: 1rem; }

/* Padding */
.p-2 { padding: 0.5rem; }
.p-2\.5 { padding: 0.625rem; }
.p-3\.5 { padding: 0.875rem; }
.p-4 { padding: 1rem; }
.p-5 { padding: 1.25rem; }
.px-2\.5 { padding-left: 0.625rem; padding-right: 0.625rem; }
.px-3 { padding-left: 0.75rem; padding-right: 0.75rem; }
.px-6 { padding-left: 1.5rem; padding-right: 1.5rem; }
.py-1 { padding-top: 0.25rem; padding-bottom: 0.25rem; }
.py-1\.5 { padding-top: 0.375rem; padding-bottom: 0.375rem; }
.py-2\.5 { padding-top: 0.625rem; padding-bottom: 0.625rem; }
.py-4 { padding-top: 1rem; padding-bottom: 1rem; }
.py-7 { padding-top: 1.75rem; padding-bottom: 1.75rem; }
.pt-3 { padding-top: 0.75rem; }
.pr-1 { padding-right: 0.25rem; }

/* Margin */
.mt-0\.5 { margin-top: 0.125rem; }
.mt-1 { margin-top: 0.25rem; }
.mt-3 { margin-top: 0.75rem; }
.mt-4 { margin-top: 1rem; }
.mt-5 { margin-top: 1.25rem; }

/* Sizing */
.h-2 { height: 0.5rem; }
.h-3\.5 { height: 0.875rem; }
.h-4 { height: 1rem; }
.h-6 { height: 1.5rem; }
.h-7 { height: 1.75rem; }
.h-9 { height: 2.25rem; }
.h-16 { height: 4rem; }
.h-full { height: 100%; }
.w-3\.5 { width: 0.875rem; }
.w-4 { width: 1rem; }
.w-7 { width: 1.75rem; }
.w-9 { width: 2.25rem; }
.w-16 { width: 4rem; }
.w-full { width: 100%; }
.min-w-0 { min-width: 0px; }
.min-w-\[18rem\] { min-width: 18rem; }
.max-w-2xl { max-width: 42rem; }
.max-h-\[24rem\] { max-height: 24rem; }
.max-h-\[30rem\] { max-height: 30rem; }

/* Overflow */
.overflow-hidden { overflow: hidden; }
.overflow-x-auto { overflow-x: auto; }
.overflow-y-auto { overflow-y: auto; }

/* Typography */
.text-center { text-align: center; }
.text-right { text-align: right; }
.text-\[9px\] { font-size: 9px; }
.text-\[10px\] { font-size: 10px; }
.text-\[11px\] { font-size: 11px; }
.text-xs { font-size: 0.75rem; line-height: 1rem; }
.text-sm { font-size: 0.875rem; line-height: 1.25rem; }
.text-base { font-size: 1rem; line-height: 1.5rem; }
.text-lg { font-size: 1.125rem; line-height: 1.75rem; }
.text-xl { font-size: 1.25rem; line-height: 1.75rem; }
.text-2xl { font-size: 1.5rem; line-height: 2rem; }
.text-\[2\.2rem\] { font-size: 2.2rem; }
.font-medium { font-weight: 500; }
.font-semibold { font-weight: 600; }
.uppercase { text-transform: uppercase; }
.truncate { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.break-all { word-break: break-all; }
.leading-5 { line-height: 1.25rem; }
.leading-6 { line-height: 1.5rem; }
.tracking-\[-0\.04em\] { letter-spacing: -0.04em; }
.tracking-tight { letter-spacing: -0.025em; }
.tracking-\[0\.12em\] { letter-spacing: 0.12em; }
.tracking-\[0\.14em\] { letter-spacing: 0.14em; }
.tracking-\[0\.18em\] { letter-spacing: 0.18em; }
.tracking-\[0\.22em\] { letter-spacing: 0.22em; }
.tracking-\[0\.24em\] { letter-spacing: 0.24em; }

/* Borders */
.border { border-width: 1px; border-style: solid; }
.border-2 { border-width: 2px; border-style: solid; }
.border-t { border-top-width: 1px; border-top-style: solid; }
.rounded-md { border-radius: 0.375rem; }
.rounded-lg { border-radius: 0.5rem; }
.rounded-xl { border-radius: 0.75rem; }
.rounded-2xl { border-radius: 1rem; }
.rounded-full { border-radius: 9999px; }
.border-slate-200 { border-color: #e2e8f0; }

/* Background colours (standard palette) */
.bg-white { background-color: #fff; }
.bg-slate-100 { background-color: #f1f5f9; }
.bg-sky-100 { background-color: #e0f2fe; }
.bg-sky-300 { background-color: #7dd3fc; }
.bg-sky-600 { background-color: #0284c7; }
.bg-sky-700 { background-color: #0369a1; }

/* Text colours (standard palette) */
.text-white { color: #fff; }
.text-slate-300 { color: #cbd5e1; }
.text-slate-400 { color: #94a3b8; }
.text-slate-500 { color: #64748b; }
.text-slate-700 { color: #334155; }
.text-sky-50 { color: #f0f9ff; }
.text-sky-700 { color: #0369a1; }
.text-sky-950 { color: #082f49; }

/* Shadows */
.shadow-\[0_10px_20px_rgba\(15\,23\,42\,0\.07\)\] { box-shadow: 0 10px 20px rgba(15,23,42,0.07); }

/* Transitions */
.transition-colors { transition-property: color, background-color, border-color; transition-duration: 150ms; transition-timing-function: cubic-bezier(0.4,0,0.2,1); }

/* Object fit */
.object-cover { object-fit: cover; }

/* ── Responsive: sm (>=640px) ─────────────────────────────────────── */
@media (min-width: 640px) {
  .sm\:px-8 { padding-left: 2rem; padding-right: 2rem; }
  .sm\:p-6 { padding: 1.5rem; }
  .sm\:h-7 { height: 1.75rem; }
  .sm\:rounded-xl { border-radius: 0.75rem; }
  .sm\:text-\[10px\] { font-size: 10px; }
  .sm\:grid-cols-2 { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .sm\:grid-cols-3 { grid-template-columns: repeat(3, minmax(0, 1fr)); }
  .sm\:grid-cols-\[112px_minmax\(0\,1fr\)\] { grid-template-columns: 112px minmax(0,1fr); }
  .sm\:items-center { align-items: center; }
  .sm\:flex-row { flex-direction: row; }
  .sm\:justify-between { justify-content: space-between; }
  .sm\:min-w-\[24rem\] { min-width: 24rem; }
}

/* ── Responsive: md (>=768px) ─────────────────────────────────────── */
@media (min-width: 768px) {
  .md\:block { display: block; }
  .md\:h-8 { height: 2rem; }
  .md\:text-sm { font-size: 0.875rem; line-height: 1.25rem; }
  .md\:grid-cols-\[56px_minmax\(360px\,1fr\)_72px\] { grid-template-columns: 56px minmax(360px,1fr) 72px; }
  .md\:gap-3 { gap: 0.75rem; }
  .md\:min-w-\[38rem\] { min-width: 38rem; }
}

/* ── Responsive: xl (>=1280px) ────────────────────────────────────── */
@media (min-width: 1280px) {
  .xl\:grid-cols-1 { grid-template-columns: repeat(1, minmax(0, 1fr)); }
  .xl\:grid-cols-4 { grid-template-columns: repeat(4, minmax(0, 1fr)); }
  .xl\:grid-cols-\[minmax\(0\,1\.2fr\)_minmax\(320px\,0\.82fr\)\] { grid-template-columns: minmax(0,1.2fr) minmax(320px,0.82fr); }
  .xl\:grid-cols-\[minmax\(0\,1\.18fr\)_minmax\(320px\,0\.92fr\)\] { grid-template-columns: minmax(0,1.18fr) minmax(320px,0.92fr); }
  .xl\:grid-cols-\[minmax\(0\,1\.15fr\)_minmax\(320px\,0\.95fr\)\] { grid-template-columns: minmax(0,1.15fr) minmax(320px,0.95fr); }
}

/* ── Responsive: 2xl (>=1536px) ───────────────────────────────────── */
@media (min-width: 1536px) {
  .\32xl\:grid-cols-2 { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}

/* ── Hover states ─────────────────────────────────────────────────── */
.hover\:border-border:hover { border-color: hsl(var(--border)); }
.hover\:bg-white:hover { background-color: #fff; }
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

    # --- Avatar (only allow http/https URLs) ---
    safe_avatar = None
    if avatar_url and isinstance(avatar_url, str):
        if avatar_url.startswith("https://") or avatar_url.startswith("http://"):
            safe_avatar = avatar_url
    avatar_html = (
        f'<img src="{_esc(safe_avatar)}" alt="avatar" class="h-full w-full object-cover">'
        if safe_avatar
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


def _safe_project_name(share_token: str) -> str:
    """Derive a Vercel project name from a share token, with validation."""
    safe = "".join(c if c.isalnum() else "-" for c in share_token[:12]).lower().strip("-")
    if len(safe) < 4:
        safe = hashlib.sha256(share_token.encode()).hexdigest()[:12]
    return f"portfolio-{safe}"


async def deploy_to_vercel(html_content: str, share_token: str) -> Dict[str, Any]:
    """Deploy a static HTML file to Vercel. Returns {{url, status}}."""
    token = os.getenv("VERCEL_API_TOKEN")
    if not token:
        return {"url": None, "status": "error", "error": "VERCEL_API_TOKEN not configured"}

    project_name = _safe_project_name(share_token)
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

    try:
        data = resp.json()
    except Exception:
        return {"url": None, "status": "error", "error": "Invalid response from Vercel"}

    url = data.get("url")
    if url and not url.startswith("http"):
        url = f"https://{url}"
    return {"url": url, "status": "success"}


async def delete_vercel_deployment(share_token: str) -> str | None:
    """Delete a Vercel project by name. Returns an error string or None on success."""
    token = os.getenv("VERCEL_API_TOKEN")
    if not token:
        return None

    project_name = _safe_project_name(share_token)

    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.delete(
            f"https://api.vercel.com/v9/projects/{project_name}",
            headers={"Authorization": f"Bearer {token}"},
        )
    if resp.status_code >= 400 and resp.status_code != 404:
        logger.error("Vercel project delete failed: %s %s", resp.status_code, resp.text)
        return f"Vercel API error ({resp.status_code})"
    return None
