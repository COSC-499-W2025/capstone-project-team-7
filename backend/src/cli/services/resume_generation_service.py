"""
Resume Generation Service

Creates concise, resume-ready bullet points from existing project analysis data.
Designed to work offline using scan results, code analysis metrics, and git
signals already collected by the Textual CLI flow.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import re
import sys
from typing import Any, Dict, List, Optional, Sequence

from ...scanner.models import ParseResult

try:  # Optional import – contribution analysis is not always available
    from ...local_analysis.contribution_analyzer import ProjectContributionMetrics
except Exception:  # pragma: no cover - optional dependency missing
    ProjectContributionMetrics = None  # type: ignore[assignment]

_DATACLASS_KWARGS = {"slots": True} if sys.version_info >= (3, 10) else {}


class ResumeGenerationError(Exception):
    """Raised when resume generation cannot complete."""


@dataclass(**_DATACLASS_KWARGS)
class ResumeItem:
    """Final resume artifact and convenience renderer."""

    project_name: str
    start_date: str
    end_date: str
    bullets: List[str]
    output_path: Path

    def to_markdown(self) -> str:
        date_span = f"{self.start_date} – {self.end_date}" if self.end_date else self.start_date
        lines = [f"{self.project_name} — {date_span}"]
        for bullet in self.bullets:
            lines.append(f"- {bullet}")
        return "\n".join(lines)


class ResumeGenerationService:
    """Generate resume-ready markdown content from scan artifacts."""

    def generate_resume_item(
        self,
        *,
        target_path: Path,
        parse_result: Optional[ParseResult],
        languages: Optional[List[Dict[str, object]]] = None,
        code_analysis_result: Optional[Any] = None,
        contribution_metrics: Optional[ProjectContributionMetrics] = None,
        git_analysis: Optional[Sequence[Dict[str, Any]]] = None,
        output_path: Optional[Path] = None,
        ai_client: Optional[Any] = None,
    ) -> ResumeItem:
        if parse_result is None:
            raise ResumeGenerationError("⚠ No project analysis found — run a scan first.")

        project_name = self._project_name(target_path)
        start_date, end_date = self._derive_dates(git_analysis, contribution_metrics)
        date_label = start_date or "Unknown Dates"

        code_summary = getattr(code_analysis_result, "summary", None) or {}
        code_files = self._code_file_count(code_analysis_result, parse_result)
        git_signals = self._git_signals(git_analysis, contribution_metrics)

        ai_errors: list[str] = []
        if ai_client:
            try:
                return self._generate_with_ai(
                    ai_client=ai_client,
                    project_name=project_name,
                    start_date=date_label,
                    end_date=end_date,
                    languages=languages or [],
                    code_summary=code_summary,
                    code_files=code_files,
                    parse_result=parse_result,
                    contribution_metrics=contribution_metrics,
                    git_signals=git_signals,
                    output_path=output_path,
                    target_path=target_path,
                )
            except Exception as exc:  # pragma: no cover - AI fallback
                ai_errors.append(str(exc))

        bullets = self._build_bullets(
            project_name=project_name,
            languages=languages or [],
            code_summary=code_summary,
            code_files=code_files,
            parse_result=parse_result,
            contribution_metrics=contribution_metrics,
            git_signals=git_signals,
        )

        if len(bullets) < 2:
            raise ResumeGenerationError(
                "⚠ Insufficient project data to generate resume content\n"
                "Suggestion: Ensure the project has a recent scan, git history, or run deeper analysis."
                + (f"\nAI fallback errors: {ai_errors}" if ai_errors else "")
            )

        destination = self._resolve_destination(target_path, output_path)
        content = ResumeItem(
            project_name=project_name,
            start_date=date_label,
            end_date=end_date,
            bullets=bullets[:4],  # Cap at four bullets
            output_path=destination,
        )

        try:
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(content.to_markdown(), encoding="utf-8")
        except OSError as exc:  # pragma: no cover - filesystem specific
            raise ResumeGenerationError(
                "✗ Failed to write resume item\n"
                f"  Attempted path: {destination}\n"
                f"  Error: {exc}"
            ) from exc

        return content

    # ------------------------------------------------------------------ #
    # Bullet construction helpers
    # ------------------------------------------------------------------ #

    def _generate_with_ai(
        self,
        *,
        ai_client: Any,
        project_name: str,
        start_date: str,
        end_date: str,
        languages: List[Dict[str, object]],
        code_summary: Dict[str, Any],
        code_files: int,
        parse_result: ParseResult,
        contribution_metrics: Optional[ProjectContributionMetrics],
        git_signals: Dict[str, Any],
        output_path: Optional[Path],
        target_path: Path,
    ) -> ResumeItem:
        prompt = self._build_ai_prompt(
            project_name=project_name,
            start_date=start_date,
            end_date=end_date,
            languages=languages,
            code_summary=code_summary,
            code_files=code_files,
            parse_result=parse_result,
            contribution_metrics=contribution_metrics,
            git_signals=git_signals,
        )

        invoke = getattr(ai_client, "_make_llm_call", None)
        if not callable(invoke):
            raise ResumeGenerationError("AI client unavailable for resume generation.")
        try:
            ai_response = invoke(
                [{"role": "user", "content": prompt}],
                max_tokens=600,
                temperature=0.6,
            )
        except Exception as exc:
            raise ResumeGenerationError(f"AI resume generation failed: {exc}") from exc

        bullets = [line.strip()[2:].strip() for line in ai_response.splitlines() if line.strip().startswith("- ")]
        if len(bullets) < 2:
            # Fallback to paragraph split if model did not use bullets
            bullets = [line.strip() for line in ai_response.splitlines() if line.strip()][0:4]
        if len(bullets) < 2:
            raise ResumeGenerationError("AI response did not contain enough bullet points.")

        bullets = self._sanitize_ai_bullets(bullets)
        overview = self._project_overview_bullet(project_name, [])
        if overview and not any(overview.split(":")[0] in b for b in bullets[:1]):
            bullets.insert(0, overview)
        if len(bullets) < 2:
            raise ResumeGenerationError("AI resume generation produced too few bullets after sanitization.")

        destination = self._resolve_destination(target_path, output_path)
        content = ResumeItem(
            project_name=project_name,
            start_date=start_date,
            end_date=end_date,
            bullets=bullets[:4],
            output_path=destination,
        )
        try:
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(content.to_markdown(), encoding="utf-8")
        except OSError as exc:  # pragma: no cover
            raise ResumeGenerationError(
                "✗ Failed to write resume item\n"
                f"  Attempted path: {destination}\n"
                f"  Error: {exc}"
            ) from exc
        return content

    def _build_ai_prompt(
        self,
        *,
        project_name: str,
        start_date: str,
        end_date: str,
        languages: List[Dict[str, object]],
        code_summary: Dict[str, Any],
        code_files: int,
        parse_result: ParseResult,
        contribution_metrics: Optional[ProjectContributionMetrics],
        git_signals: Dict[str, Any],
    ) -> str:
        lang_block = ", ".join([lang.get("language", "") for lang in languages[:5] if lang.get("language")]) or "Unknown"
        files_processed = parse_result.summary.get("files_processed", len(parse_result.files))
        filtered = parse_result.summary.get("filtered_out")
        filter_txt = f", filtered {filtered}" if isinstance(filtered, int) and filtered > 0 else ""
        code_quality = {
            "maintainability": code_summary.get("avg_maintainability"),
            "complexity": code_summary.get("avg_complexity"),
            "security_issues": code_summary.get("security_issues"),
            "todos": code_summary.get("todos"),
        }
        contrib = None
        if contribution_metrics:
            contrib = {
                "project_type": contribution_metrics.project_type,
                "total_commits": contribution_metrics.total_commits,
                "total_contributors": contribution_metrics.total_contributors,
                "duration_days": contribution_metrics.project_duration_days,
                "activity_percentages": getattr(
                    getattr(contribution_metrics, "overall_activity_breakdown", None), "percentages", {}
                ),
            }
        prompt = f"""
You are building a concise resume snippet in Jake-resume style for a single project.
Return Markdown exactly as:

{project_name} — {start_date} – {end_date}
Overview: <1-2 sentence plain-language summary of what the project/program does>
- Bullet 1
- Bullet 2
- Bullet 3 (optional)
- Bullet 4 (optional)

Rules:
- 2–4 bullets, one line each (~90 chars), past-tense action verbs, results-focused.
- Prioritize stack/architecture, performance or UX gains, reliability, testing/operations.
- Keep it high-level and recruiter-friendly; avoid raw metric dumps or jargon overload.
- Do NOT invent metrics or percentages; only use numbers present in the facts below. If none exist, stay qualitative.
- You may humanize numbers when useful, but avoid making file counts the focal point.
- Keep a professional tone; include outcomes (speed, stability, UX, clarity) where possible.

Project facts (context only, do not echo verbatim):
- Stack/Languages: {lang_block}
- Files processed: {files_processed}{filter_txt}; code files: {code_files}
- Code quality: {code_quality}
- Git signals: {git_signals}
- Contribution metrics: {contrib}

Include:
- A short 1-2 sentence project overview describing what the project is and what the program actually does.
- Bullets that emphasize YOUR contributions and impact.

Write the Markdown block only, no extra text.

"""
        return "\n".join(line.rstrip() for line in prompt.strip().splitlines())

    def _build_bullets(
        self,
        *,
        project_name: str,
        languages: List[Dict[str, object]],
        code_summary: Dict[str, Any],
        code_files: int,
        parse_result: ParseResult,
        contribution_metrics: Optional[ProjectContributionMetrics],
        git_signals: Dict[str, Any],
    ) -> List[str]:
        bullets: List[str] = []
        meaningful_signals = bool(languages or code_summary or git_signals or contribution_metrics)

        overview = self._project_overview_bullet(project_name, languages)
        if overview:
            bullets.append(overview)

        commit_count = git_signals.get("commit_count")
        contributor_count = git_signals.get("contributor_count")
        project_type = git_signals.get("project_type")
        if commit_count:
            contrib_label = ""
            if contributor_count:
                collaborator = "solo effort" if int(contributor_count) == 1 else f"{contributor_count}-person team"
                contrib_label = f" as a {collaborator}"
            type_label = f" ({project_type})" if project_type else ""
            bullets.append(
                self._trim(
                    f"Delivered {self._humanize_count(commit_count)} commits{contrib_label}, maintaining steady release cadence{type_label}."
                )
            )

        stack = self._format_stack(languages)
        if stack or code_files:
            scope = (
                f"spanning {self._humanize_count(code_files)} source files"
                if code_files
                else "covering key components"
            )
            prefix = f"Built a {stack} solution" if stack else "Built the project foundation"
            bullets.append(self._trim(f"{prefix} {scope} with a structured analysis pipeline."))

        maintainability = code_summary.get("avg_maintainability")
        complexity = code_summary.get("avg_complexity")
        if maintainability or complexity:
            bullets.append(
                self._trim(
                    "Improved code quality and stability through structured analysis and refactor-ready insights."
                )
            )

        security_issues = code_summary.get("security_issues")
        todos = code_summary.get("todos")

        if security_issues or todos:
            findings = []
            if security_issues is not None:
                findings.append("security review")
            if todos is not None:
                findings.append("actionable follow-ups")
            joined = " and ".join(findings) if findings else "issues"
            bullets.append(
                self._trim(f"Hardened reliability by surfacing {joined} and directing remediation work.")
            )

        files_processed = parse_result.summary.get("files_processed", len(parse_result.files))
        filtered = parse_result.summary.get("filtered_out")
        if files_processed:
            filter_fragment = ""
            if isinstance(filtered, int) and filtered > 0:
                filter_fragment = f" with selective filters excluding {self._humanize_count(filtered)} artifacts"
            bullets.append(
                self._trim(
                    f"Streamlined archive-based scanning{filter_fragment} to keep re-scans fast and predictable."
                )
            )

        activity_bullet = self._activity_bullet(contribution_metrics)
        if activity_bullet:
            bullets.append(activity_bullet)

        if not bullets:
            files_processed = parse_result.summary.get("files_processed", len(parse_result.files))
            bullets.append(
                self._trim(
                    f"Documented project scope across {files_processed} files to map architecture and deliverables."
                )
            )
        else:
            contribution_note = self._contribution_bullet(git_signals, contribution_metrics)
            if contribution_note:
                bullets.append(contribution_note)

        if not meaningful_signals:
            raise ResumeGenerationError(
                "⚠ Insufficient project data to generate resume content\n"
                "Suggestion: Ensure the project has commits, language signals, or code analysis."
            )

        return bullets

    def _activity_bullet(
        self, contribution_metrics: Optional[ProjectContributionMetrics]
    ) -> Optional[str]:
        if contribution_metrics is None:
            return None
        breakdown = getattr(contribution_metrics, "overall_activity_breakdown", None)
        if not breakdown or not getattr(breakdown, "total_lines", 0):
            return None
        percentages = breakdown.percentages
        highlights: List[str] = []
        for label in ("test", "documentation", "design"):
            share = percentages.get(label, 0)
            if share >= 10:
                descriptor = "tests" if label == "test" else label
                highlights.append(f"{descriptor} {share:.0f}%")
        if not highlights:
            return None
        mix = ", ".join(highlights)
        return self._trim(f"Documented best practices by balancing workload across {mix}.")

    # ------------------------------------------------------------------ #
    # Metadata helpers
    # ------------------------------------------------------------------ #

    def _project_name(self, target: Path) -> str:
        if target.name:
            return target.stem if target.is_file() else target.name
        return "Project"

    def _resolve_destination(self, target: Path, output_path: Optional[Path]) -> Path:
        if output_path:
            return output_path
        base = target if target.is_dir() else target.parent
        if not base.exists():
            base = Path.cwd()
        return base / "resume_item.md"

    def _derive_dates(
        self,
        git_analysis: Optional[Sequence[Dict[str, Any]]],
        contribution_metrics: Optional[ProjectContributionMetrics],
    ) -> tuple[str, str]:
        start: Optional[str] = None
        end: Optional[str] = None

        if git_analysis:
            starts: List[str] = []
            ends: List[str] = []
            for entry in git_analysis:
                date_range = entry.get("date_range") if isinstance(entry, dict) else None
                if isinstance(date_range, dict):
                    if date_range.get("start"):
                        starts.append(date_range["start"])
                    if date_range.get("end"):
                        ends.append(date_range["end"])
            if starts:
                start = self._format_month_year(min(starts, default=None))
            if ends:
                end = self._format_month_year(max(ends, default=None))

        if contribution_metrics:
            start = start or self._format_month_year(contribution_metrics.project_start_date)
            end = end or self._format_month_year(contribution_metrics.project_end_date)

        if start is None and end is None:
            return "Unknown Dates", ""
        if start and not end:
            return start, "Present"
        return start or "Unknown Start", end or ""

    def _git_signals(
        self,
        git_analysis: Optional[Sequence[Dict[str, Any]]],
        contribution_metrics: Optional[ProjectContributionMetrics],
    ) -> Dict[str, Any]:
        signals: Dict[str, Any] = {}
        if git_analysis:
            commit_total = 0
            contributor_ids: set[tuple[str, str]] = set()
            project_type = None
            for entry in git_analysis:
                if not isinstance(entry, dict) or entry.get("error"):
                    continue
                commit_total += int(entry.get("commit_count") or 0)
                contributors = entry.get("contributors") or []
                for person in contributors:
                    name = (person.get("name") or "").strip()
                    email = (person.get("email") or "").strip()
                    contributor_ids.add((name, email))
                project_type = project_type or entry.get("project_type")
            if commit_total:
                signals["commit_count"] = commit_total
            if contributor_ids:
                # Deduplicate contributors across repositories by name/email tuple
                signals["contributor_count"] = len(contributor_ids)
            if project_type:
                signals["project_type"] = project_type

        if contribution_metrics:
            signals.setdefault("commit_count", contribution_metrics.total_commits)
            signals.setdefault("contributor_count", contribution_metrics.total_contributors)
            signals.setdefault("project_type", contribution_metrics.project_type)

        return signals

    def _code_file_count(self, code_analysis_result: Optional[Any], parse_result: ParseResult) -> int:
        summary = getattr(code_analysis_result, "summary", None) or {}
        total_files = summary.get("total_files")
        if total_files is None and getattr(code_analysis_result, "files", None):
            total_files = len(getattr(code_analysis_result, "files", []))
        if total_files is None:
            total_files = parse_result.summary.get("files_processed", len(parse_result.files))
        return int(total_files or 0)

    def _format_stack(self, languages: List[Dict[str, object]], *, limit: int = 3) -> str:
        names = [lang.get("language") for lang in languages if isinstance(lang, dict) and lang.get("language")]
        unique = []
        for name in names:
            if name not in unique:
                unique.append(name)
        if not unique:
            return ""
        return ", ".join(unique[:limit])

    def _trim(self, text: str, *, width: int = 400) -> str:
        text = " ".join(text.split())
        if len(text) <= width:
            return text
        return text  # avoid truncating resume bullets; keep full context

    def _project_overview_bullet(self, project_name: str, languages: List[Dict[str, object]]) -> Optional[str]:
        stack = self._format_stack(languages)
        descriptor = f"{stack} " if stack else ""
        return self._trim(f"{project_name}: {descriptor}project that scans and summarizes codebases for portfolio-ready insights.")

    def _sanitize_ai_bullets(self, bullets: List[str]) -> List[str]:
        cleaned: List[str] = []
        for bullet in bullets:
            # Strip hallucinated percentages entirely
            bullet = re.sub(r"\d+%+", "", bullet)
            bullet = " ".join(bullet.split())
            if bullet:
                cleaned.append(bullet)
        return cleaned

    def _contribution_bullet(
        self, git_signals: Dict[str, Any], contribution_metrics: Optional[ProjectContributionMetrics]
    ) -> Optional[str]:
        contributor_count = git_signals.get("contributor_count") or (
            getattr(contribution_metrics, "total_contributors", None) if contribution_metrics else None
        )
        commit_count = git_signals.get("commit_count") or (
            getattr(contribution_metrics, "total_commits", None) if contribution_metrics else None
        )
        project_type = git_signals.get("project_type") or (
            getattr(contribution_metrics, "project_type", None) if contribution_metrics else None
        )
        if contributor_count is None and project_type == "collaborative":
            contributor_count = 2  # fallback when team count is missing

        commit_phrase = (
            f" and delivered {self._humanize_count(commit_count)} commits"
            if commit_count is not None
            else ""
        )
        if contributor_count and contributor_count > 1:
            return self._trim(
                f"Collaborated with a {contributor_count}-person team{commit_phrase} to design scanning workflows and polish outputs."
            )
        return self._trim(f"Led end-to-end scanning workflow{commit_phrase} to showcase project impact.")

    def _humanize_count(self, value: Any) -> str:
        try:
            num = float(value)
        except Exception:
            return str(value)
        if num >= 1_000_000:
            return f"{num/1_000_000:.1f}M".rstrip("0").rstrip(".")
        if num >= 1_000:
            return f"{num/1_000:.1f}k".rstrip("0").rstrip(".")
        return str(int(num))

    def _format_month_year(self, raw: Optional[str]) -> Optional[str]:
        if not raw:
            return None
        value = raw.replace("Z", "+00:00")
        for parser in (self._from_iso, self._from_git_fmt, self._from_month_year):
            parsed = parser(value)
            if parsed:
                return parsed.strftime("%b %Y")
        return None

    @staticmethod
    def _from_iso(value: str) -> Optional[datetime]:
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            return None

    @staticmethod
    def _from_git_fmt(value: str) -> Optional[datetime]:
        for fmt in ("%a %b %d %H:%M:%S %Y %z", "%Y-%m-%d %H:%M:%S %z", "%b %d %Y"):
            try:
                return datetime.strptime(value, fmt)
            except ValueError:
                continue
        return None

    @staticmethod
    def _from_month_year(value: str) -> Optional[datetime]:
        try:
            return datetime.strptime(value, "%b %Y")
        except ValueError:
            return None
