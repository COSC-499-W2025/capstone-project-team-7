"""
Resume Generation Service

Creates concise, resume-ready bullet points from existing project analysis data.
Designed to work offline using scan results, code analysis metrics, and git
signals already collected by the backend API flow.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import re
import sys
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Sequence, Tuple

from scanner.models import ParseResult

try:  # Optional import – contribution analysis is not always available
    from local_analysis.contribution_analyzer import ProjectContributionMetrics
except Exception:  # pragma: no cover - optional dependency missing
    ProjectContributionMetrics = None  # type: ignore[assignment]

if TYPE_CHECKING:  # pragma: no cover - typing only
    from analyzer.project_detector import ProjectInfo
    from analyzer.skills_extractor import Skill
    from local_analysis.document_analyzer import DocumentAnalysisResult
    from local_analysis.pdf_summarizer import DocumentSummary

_DATACLASS_KWARGS = {"slots": True} if sys.version_info >= (3, 10) else {}


class ResumeGenerationError(Exception):
    """Raised when resume generation cannot complete."""


@dataclass(**_DATACLASS_KWARGS)
class ResumeItem:
    """Final resume artifact and convenience renderer."""

    project_name: str
    start_date: str
    end_date: str
    overview: str
    bullets: List[str]
    output_path: Path
    ai_generated: bool = False
    role: str = ""  # User's role in the project (author, contributor, lead, etc.)

    def to_markdown(self) -> str:
        date_span = f"{self.start_date} – {self.end_date}" if self.end_date else self.start_date
        lines = [f"{self.project_name} — {date_span}"]
        if self.role:
            lines.append(f"Role: {self.role.title()}")
        overview_line = self.overview.strip()
        if overview_line:
            lines.append(f"Overview: {overview_line}")
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
        detected_projects: Optional[Sequence["ProjectInfo"]] = None,
        skills: Optional[Sequence["Skill"]] = None,
        document_results: Optional[Sequence["DocumentAnalysisResult"]] = None,
        pdf_summaries: Optional[Sequence["DocumentSummary"]] = None,
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
        project_profile = self._project_profile(project_name, detected_projects)
        readme_summary = self._readme_summary(target_path)
        document_summary = self._document_summary_text(document_results)
        pdf_summary = self._pdf_summary_text(pdf_summaries)
        project_summary_text = readme_summary or document_summary or pdf_summary
        integration_signals = self._detect_integrations(parse_result)
        skill_highlights = self._skill_highlights(skills)
        overview_text = self._build_overview_text(
            project_name=project_name,
            project_profile=project_profile,
            project_summary=project_summary_text,
            languages=languages or [],
            integration_signals=integration_signals,
        )

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
                    project_profile=project_profile,
                    project_summary=project_summary_text,
                    integration_signals=integration_signals,
                    skill_highlights=skill_highlights,
                    fallback_overview=overview_text,
                )
            except Exception as exc:  # pragma: no cover - AI fallback
                ai_errors.append(str(exc))

        bullets = self._build_bullets(
            project_name=project_name,
            languages=languages or [],
            code_summary=code_summary,
            contribution_metrics=contribution_metrics,
            git_signals=git_signals,
            project_profile=project_profile,
            integration_signals=integration_signals,
            skill_highlights=skill_highlights,
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
            overview=overview_text,
            bullets=bullets[:4],  # Cap at four bullets
            ai_generated=False,
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
        project_profile: Dict[str, Any],
        project_summary: Optional[str],
        integration_signals: List[str],
        skill_highlights: List[str],
        fallback_overview: str,
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
            project_profile=project_profile,
            project_summary=project_summary,
            integration_signals=integration_signals,
            skill_highlights=skill_highlights,
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

        overview_line, bullet_lines = self._extract_ai_sections(ai_response)
        overview_line = overview_line or fallback_overview
        bullets = [line.strip() for line in bullet_lines if line.strip()]
        if len(bullets) < 2:
            raise ResumeGenerationError("AI response did not contain enough bullet points.")

        bullets = self._sanitize_ai_bullets(bullets)
        if len(bullets) < 2:
            raise ResumeGenerationError("AI resume generation produced too few bullets after sanitization.")

        destination = self._resolve_destination(target_path, output_path)
        content = ResumeItem(
            project_name=project_name,
            start_date=start_date,
            end_date=end_date,
            overview=overview_line,
            bullets=bullets[:4],
            ai_generated=True,
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
        project_profile: Dict[str, Any],
        project_summary: Optional[str],
        integration_signals: List[str],
        skill_highlights: List[str],
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
        project_desc = project_summary or project_profile.get("description") or "project"
        structure = project_profile.get("structure")
        if structure:
            project_desc = f"{project_desc} ({structure})"
        integrations_text = ", ".join(integration_signals) if integration_signals else "None noted"
        skills_text = ", ".join(skill_highlights[:5]) if skill_highlights else "Not detected"
        summary_fact = project_summary or "Not provided"
        prompt = f"""
You are a senior software engineer writing resume bullets. Convert project scan data into polished, professional accomplishments.

OUTPUT FORMAT:
{project_name} — {start_date} – {end_date}
Overview: One sentence describing what the project does and its key technical approach.
- Bullet 1
- Bullet 2
- Bullet 3 (optional)
- Bullet 4 (optional)

REQUIREMENTS:
1. QUANTIFY WHEN POSSIBLE: Include metrics where the data supports them. Good metrics include:
   - Latency/performance: "0.78s median latency", "40% faster", "sub-200ms response"
   - Scale: "30+ users", "1000+ requests/day", "15 API endpoints"
   - Coverage/quality: "85% test coverage", "13-check validation gate", "3-retry queue"
   - Codebase: "12 modules", "50+ components", "8 integrated services"
   If data doesn't support specific metrics, focus on technical accomplishments instead.

2. STRUCTURE: Action verb + What you built + How/with what + Impact or result
   - Good: "Architected a modular Manifest V3 system with background/content scripts, secure API communication, and local storage, achieving Chrome Web Store approval."
   - Good: "Built a real-time data pipeline using Redis streams and async workers for reliable message processing."
   - Bad: "Built a Chrome extension that shows grades." (no technical detail)

3. TECHNICAL DENSITY: Pack specific technologies, patterns, and architectural decisions into each bullet.

4. NO FILLER: Eliminate phrases like "making skills tangible", "emphasizing production readiness", "connecting architecture to user value".

5. BULLET LENGTH: 120-180 characters ideal. Dense with information, not padding.

EXAMPLE BULLETS (emulate this style):
- "Built a WhatsApp-based receipt processing system integrating OpenAI Vision, Google Drive, and queued job workflows, delivering structured confirmations with 0.78s median end-to-end latency."
- "Engineered a modular CLI tool in Go with Git pre-commit hook integration, supporting Conventional Commits and YAML configuration for flexible developer workflows."
- "Automated quality assurance with unit tests, linting, GitHub Actions CI/CD pipelines, and semantic-release for reliable versioned releases."
- "Strengthened production reliability through retry queues, dead-letter storage, health checks, and pre-deploy validation gates."

PROJECT DATA (use to generate technical details and metrics where available):
- Summary: {summary_fact}
- Profile: {project_desc}
- Stack: {lang_block}
- Files: {files_processed}{filter_txt}; code files: ~{code_files}
- Integrations: {integrations_text}
- Skills: {skills_text}
- Quality metrics: {code_quality}
- Git signals: {git_signals}
- Contribution data: {contrib}

INFERENCE GUIDANCE:
- If files_processed > 50: can mention "50+ files" or "large-scale codebase"
- If multiple integrations: can count them ("integrated 5 external services")
- If contribution_metrics shows commits: can use for activity ("200+ commits")
- If no metrics available: focus on technical approach and architecture instead

Output ONLY the formatted entry. No commentary, no explanations.

"""
        return "\n".join(line.rstrip() for line in prompt.strip().splitlines())

    def _build_bullets(
        self,
        *,
        project_name: str,
        languages: List[Dict[str, object]],
        code_summary: Dict[str, Any],
        contribution_metrics: Optional[ProjectContributionMetrics],
        git_signals: Dict[str, Any],
        project_profile: Dict[str, Any],
        integration_signals: List[str],
        skill_highlights: List[str],
    ) -> List[str]:
        bullets: List[str] = []
        meaningful_signals = bool(
            languages or code_summary or contribution_metrics or git_signals or integration_signals or skill_highlights
        )

        stack_bullet = self._stack_bullet(languages, integration_signals, project_profile)
        if stack_bullet:
            bullets.append(stack_bullet)

        skills_bullet = self._skills_bullet(skill_highlights)
        if skills_bullet:
            bullets.append(skills_bullet)

        quality_bullet = self._quality_bullet(code_summary)
        if quality_bullet:
            bullets.append(quality_bullet)

        teamwork_bullet = self._team_bullet(contribution_metrics, git_signals)
        if teamwork_bullet:
            bullets.append(teamwork_bullet)

        if not bullets:
            bullets.append(
                self._trim("Designed and implemented core application features with modular architecture and clean code practices.")
            )

        if len(bullets) == 1:
            bullets.append(
                self._trim("Delivered production-ready functionality with comprehensive error handling and user-focused design.")
            )

        if not meaningful_signals:
            raise ResumeGenerationError(
                "⚠ Insufficient project data to generate resume content\n"
                "Suggestion: Ensure the project has languages, integrations, or code analysis signals."
            )

        return bullets

    def _build_overview_text(
        self,
        *,
        project_name: str,
        project_profile: Dict[str, Any],
        project_summary: Optional[str],
        languages: List[Dict[str, object]],
        integration_signals: List[str],
    ) -> str:
        summary = (project_summary or "").strip()
        sentences: List[str] = []
        if summary:
            sentences.append(self._ensure_sentence(self._first_sentence(summary)))
        else:
            descriptor = project_profile.get("description") or project_profile.get("primary_type") or "project"
            descriptor = descriptor.replace("_", " ").replace("-", " ").strip()
            stack = self._format_stack(languages)
            subject = " ".join(part for part in (stack, descriptor) if part).strip()
            if not subject:
                subject = "project"
            article = self._article_for(subject)
            overview = f"{article} {subject}"
            integration_text = self._format_integrations(integration_signals)
            if integration_text:
                overview += f" leveraging {integration_text}"
            sentences.append(self._ensure_sentence(overview))
        structure = project_profile.get("structure")
        if structure:
            sentences.append(self._ensure_sentence(f"Includes {structure}"))
        overview_text = " ".join(sentences).strip()
        if not overview_text:
            overview_text = f"{project_name} project."
        return overview_text

    def _stack_bullet(
        self,
        languages: List[Dict[str, object]],
        integration_signals: List[str],
        project_profile: Dict[str, Any],
    ) -> Optional[str]:
        stack = self._format_stack(languages)
        integration_text = self._format_integrations(integration_signals)
        if not stack and not integration_text:
            return None
        integration_count = len(integration_signals) if integration_signals else 0
        if stack and integration_text:
            return self._trim(
                f"Architected a {stack} application integrating {integration_count} external services ({integration_text}), implementing end-to-end feature workflows."
            )
        if stack:
            primary = project_profile.get("primary_type")
            descriptor = f"{stack} {primary}" if primary and primary not in stack else stack
            return self._trim(f"Engineered a full-stack {descriptor} system with modular architecture and production-ready patterns.")
        return self._trim(f"Integrated {integration_count} services ({integration_text}) with secure API communication and error handling.")

    def _skills_bullet(self, skill_highlights: List[str]) -> Optional[str]:
        if not skill_highlights:
            return None
        listed = ", ".join(skill_highlights[:3])
        skill_count = len(skill_highlights)
        return self._trim(f"Demonstrated proficiency in {listed} across {skill_count}+ technical domains through hands-on implementation.")

    def _quality_bullet(self, code_summary: Dict[str, Any]) -> Optional[str]:
        focus: List[str] = []
        metrics: List[str] = []
        if code_summary.get("avg_maintainability") is not None:
            score = code_summary.get("avg_maintainability")
            metrics.append(f"{score:.0f}% maintainability score" if isinstance(score, (int, float)) else "maintainability analysis")
            focus.append("code quality standards")
        if code_summary.get("avg_complexity") is not None:
            focus.append("complexity optimization")
        if code_summary.get("security_issues"):
            count = code_summary.get("security_issues")
            metrics.append(f"{count} security issue{'s' if count != 1 else ''} addressed")
            focus.append("security hardening")
        if code_summary.get("todos"):
            count = code_summary.get("todos")
            metrics.append(f"{count}-item backlog")
        if not focus:
            return None
        metric_text = f" ({', '.join(metrics)})" if metrics else ""
        phrase = self._join_with_and(self._dedupe_preserve_order(focus))
        return self._trim(f"Enforced {phrase}{metric_text}, ensuring production-grade reliability and maintainability.")

    def _team_bullet(
        self,
        contribution_metrics: Optional[ProjectContributionMetrics],
        git_signals: Dict[str, Any],
    ) -> Optional[str]:
        contributors = None
        project_type = git_signals.get("project_type")
        commits = git_signals.get("commit_count", 0)
        if contribution_metrics:
            contributors = getattr(contribution_metrics, "total_contributors", None)
            project_type = project_type or getattr(contribution_metrics, "project_type", None)
            commits = getattr(contribution_metrics, "total_commits", commits)
        contributors = contributors or git_signals.get("contributor_count")
        commit_text = f" across {commits}+ commits" if commits and commits > 10 else ""
        if contributors and contributors > 1:
            return self._trim(
                f"Collaborated with a {contributors}-person team{commit_text}, coordinating code reviews, feature planning, and deployment workflows."
            )
        if (contributors == 1) or (project_type and str(project_type).lower() == "solo"):
            return self._trim(f"Owned full development lifecycle end-to-end{commit_text}, from architecture design through deployment and documentation.")
        if project_type:
            return self._trim(f"Led the {project_type} initiative{commit_text}, driving technical decisions and milestone delivery.")
        return None

    def _project_profile(
        self,
        project_name: str,
        detected_projects: Optional[Sequence["ProjectInfo"]],
    ) -> Dict[str, Any]:
        profile: Dict[str, Any] = {
            "project_name": project_name,
            "project_names": [],
            "primary_type": None,
            "description": None,
            "structure": None,
        }
        if not detected_projects:
            return profile

        names: List[str] = []
        descriptions: List[str] = []
        types: List[str] = []
        for entry in detected_projects:
            name = self._safe_attr(entry, "name")
            if name:
                names.append(str(name))
            desc = self._safe_attr(entry, "description")
            if desc:
                descriptions.append(str(desc))
            proj_type = self._safe_attr(entry, "project_type")
            if proj_type:
                types.append(str(proj_type))
        if names:
            profile["project_names"] = names
        if descriptions:
            profile["description"] = descriptions[0]
        if types:
            profile["primary_type"] = types[0]
        if len(names) > 1:
            listed = ", ".join(names[:3])
            extra = f" (+{len(names) - 3})" if len(names) > 3 else ""
            profile["structure"] = f"{len(names)} projects ({listed}{extra})"
        return profile

    def _safe_attr(self, entry: Any, attr: str) -> Optional[Any]:
        if entry is None:
            return None
        if hasattr(entry, attr):
            return getattr(entry, attr, None)
        if isinstance(entry, dict):
            return entry.get(attr)
        return None

    def _readme_summary(self, target_path: Path, *, max_chars: int = 800) -> Optional[str]:
        try:
            base = target_path if target_path.is_dir() else target_path.parent
        except Exception:
            return None
        if not base or not base.exists():
            return None
        for name in ("README.md", "readme.md", "README.MD", "ReadMe.md"):
            candidate = base / name
            if not candidate.is_file():
                continue
            try:
                text = candidate.read_text(encoding="utf-8", errors="ignore")[:max_chars]
            except OSError:
                continue
            cleaned_lines: List[str] = []
            for line in text.splitlines():
                stripped = line.strip()
                if not stripped:
                    if cleaned_lines:
                        break
                    continue
                stripped = stripped.lstrip("#*- ").strip()
                if stripped:
                    cleaned_lines.append(stripped)
                if len(" ".join(cleaned_lines)) >= max_chars:
                    break
            paragraph = " ".join(cleaned_lines).strip()
            if not paragraph:
                continue
            paragraph = re.sub(r"\[[^\]]+\]\([^)]+\)", "", paragraph)
            paragraph = paragraph.replace("`", "")
            sentences = re.split(r"(?<=[.!?])\s+", paragraph)
            for sentence in sentences:
                cleaned = sentence.strip()
                if len(cleaned) >= 40:
                    return cleaned
        return None

    def _detect_integrations(self, parse_result: ParseResult) -> List[str]:
        if not parse_result or not parse_result.files:
            return []
        features: List[str] = []
        seen: set[str] = set()
        mappings = [
            ("dockerized tooling", {"dockerfile", "docker-compose.yml", "docker-compose.yaml"}),
            ("Supabase workflows", {"supabase"}),
            ("API dashboards", {"textual"}),
            ("command-line UX", {"/cli/", "\\cli\\"}),
            ("Next.js/Node tooling", {"next.config", "package.json"}),
            ("Tailwind styling", {"tailwind.config"}),
            ("GitHub Actions CI", {".github/workflows"}),
            ("automated testing", {"pytest.ini", "pyproject.toml", "tests/"}),
        ]
        for meta in parse_result.files:
            path = str(meta.path)
            normalized = path.replace("\\", "/").lower()
            name = Path(path).name.lower()
            for label, markers in mappings:
                if label in seen:
                    continue
                for marker in markers:
                    if marker in normalized or marker == name:
                        seen.add(label)
                        features.append(label)
                        break
        return features

    def _skill_highlights(self, skills: Optional[Sequence["Skill"]]) -> List[str]:
        highlights: List[str] = []
        if not skills:
            return highlights
        for entry in skills:
            name = getattr(entry, "name", None)
            if name is None and isinstance(entry, dict):
                name = entry.get("name")
            if not name:
                continue
            category = getattr(entry, "category", None)
            if category is None and isinstance(entry, dict):
                category = entry.get("category")
            label = str(name)
            if category:
                label = f"{label} ({category})"
            if label not in highlights:
                highlights.append(label)
                if len(highlights) >= 5:
                    break
        return highlights

    def _document_summary_text(
        self, document_results: Optional[Sequence["DocumentAnalysisResult"]]
    ) -> Optional[str]:
        if not document_results:
            return None
        best_text: Optional[str] = None
        best_score = float("-inf")
        for idx, entry in enumerate(document_results):
            if isinstance(entry, dict):
                summary = entry.get("summary")
                key_points = entry.get("key_points") or entry.get("key_topics") or []
                if not summary and key_points:
                    summary = key_points[0]
                file_name = entry.get("file_name", "")
            else:
                summary = getattr(entry, "summary", None)
                if not summary:
                    topics = getattr(entry, "key_topics", None) or getattr(entry, "key_points", None)
                    if topics:
                        summary = topics[0]
                file_name = getattr(entry, "file_name", "")
            if not summary:
                continue
            normalized = summary.strip()
            if not normalized:
                continue
            cleaned = self._first_sentence(normalized, max_chars=400)
            name = (file_name or "").lower()
            score = min(len(cleaned), 600) / 600.0
            score += self._document_name_weight(name)
            score += self._summary_keyword_weight(cleaned)
            score -= idx * 0.01
            if score > best_score:
                best_text = cleaned
                best_score = score
        return best_text

    def _pdf_summary_text(
        self, pdf_summaries: Optional[Sequence["DocumentSummary"]]
    ) -> Optional[str]:
        if not pdf_summaries:
            return None
        best_text: Optional[str] = None
        best_score = float("-inf")
        for idx, summary in enumerate(pdf_summaries):
            if isinstance(summary, dict):
                if not summary.get("success"):
                    continue
                text = summary.get("summary_text")
                key_points = summary.get("key_points") or []
                file_name = summary.get("file_name", "")
            else:
                if not getattr(summary, "success", False):
                    continue
                text = getattr(summary, "summary_text", None)
                key_points = getattr(summary, "key_points", None) or []
                file_name = getattr(summary, "file_name", "")
            snippet = (text or "").strip()
            if not snippet and key_points:
                snippet = key_points[0].strip()
            if not snippet:
                continue
            cleaned = self._first_sentence(snippet, max_chars=400)
            score = min(len(cleaned), 600) / 600.0
            score += self._document_name_weight((file_name or "").lower())
            score += self._summary_keyword_weight(cleaned)
            score -= idx * 0.01
            if score > best_score:
                best_score = score
                best_text = cleaned
        return best_text

    def _format_integrations(self, integrations: List[str], *, limit: int = 3) -> str:
        if not integrations:
            return ""
        unique = self._dedupe_preserve_order(integrations)
        if len(unique) <= limit:
            return ", ".join(unique)
        extra = len(unique) - limit
        return ", ".join(unique[:limit]) + f", +{extra} more"

    def _join_with_and(self, items: List[str]) -> str:
        if not items:
            return ""
        if len(items) == 1:
            return items[0]
        if len(items) == 2:
            return " and ".join(items)
        return ", ".join(items[:-1]) + f", and {items[-1]}"

    def _dedupe_preserve_order(self, values: List[str]) -> List[str]:
        seen: set[str] = set()
        ordered: List[str] = []
        for value in values:
            if value not in seen:
                ordered.append(value)
                seen.add(value)
        return ordered

    def _first_sentence(self, text: str, *, max_chars: int = 240) -> str:
        cleaned = " ".join((text or "").split())
        if not cleaned:
            return ""
        parts = re.split(r"(?<=[.!?])\s+", cleaned)
        first = parts[0] if parts else cleaned
        if len(first) > max_chars:
            truncated = first[:max_chars].rsplit(" ", 1)[0].strip()
            if truncated:
                first = truncated + "…"
        return first

    def _ensure_sentence(self, text: str) -> str:
        cleaned = text.strip()
        if not cleaned:
            return ""
        if cleaned[-1] in ".!?":
            return cleaned
        return f"{cleaned}."

    def _article_for(self, phrase: str) -> str:
        stripped = phrase.strip().lower()
        if not stripped:
            return "A"
        return "An" if stripped[0] in "aeiou" else "A"

    def _document_name_weight(self, lowered_name: str) -> float:
        if not lowered_name:
            return 0.0
        weight = 0.0
        high_priority = (
            "proposal",
            "requirements",
            "architecture",
            "systemarchitecture",
            "design",
            "vision",
            "strategy",
            "analysis",
        )
        medium_priority = ("overview", "guide", "plan", "spec", "roadmap")
        for token in high_priority:
            if token in lowered_name:
                weight += 4.0
                break
        for token in medium_priority:
            if token in lowered_name:
                weight += 2.0
                break
        if "readme" in lowered_name:
            weight += 1.5
        return weight

    def _summary_keyword_weight(self, summary: str) -> float:
        lowered = summary.lower()
        weight = 0.0
        positive_terms = {
            "course": 1.0,
            "planner": 1.0,
            "student": 0.8,
            "schedule": 0.8,
            "curriculum": 0.8,
            "research": 1.0,
            "market": 1.0,
            "insight": 0.8,
            "ai": 1.5,
            "llm": 1.5,
            "analysis": 0.7,
            "recommendation": 0.7,
            "prediction": 0.7,
        }
        for term, value in positive_terms.items():
            if term in lowered:
                weight += value
        negative_terms = ("template", "boilerplate", "starter", "example project", "minimal setup")
        for term in negative_terms:
            if term in lowered:
                weight -= 3.0
        return weight

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

    def _sanitize_ai_bullets(self, bullets: List[str]) -> List[str]:
        cleaned: List[str] = []
        for bullet in bullets:
            # Strip hallucinated percentages entirely
            bullet = re.sub(r"\d+%+", "", bullet)
            bullet = " ".join(bullet.split())
            if bullet:
                cleaned.append(bullet)
        return cleaned

    def _extract_ai_sections(self, response: str) -> Tuple[Optional[str], List[str]]:
        overview: Optional[str] = None
        bullets: List[str] = []
        extra_lines: List[str] = []
        for raw in response.splitlines():
            line = raw.strip()
            if not line:
                continue
            lower = line.lower()
            if lower.startswith("overview:"):
                overview = line.split(":", 1)[1].strip()
                continue
            if line.startswith("- "):
                bullets.append(line[2:].strip())
            else:
                extra_lines.append(line)
        if not bullets:
            bullets = extra_lines[:4]
        return overview, bullets

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
