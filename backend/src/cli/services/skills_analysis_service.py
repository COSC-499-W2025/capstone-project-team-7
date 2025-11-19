"""
Skills Analysis Service

Provides lightweight skill extraction and formatting helpers for the Textual CLI.
Currently summarizes languages and basic metadata from the scan results so the
dashboard can render a useful summary without requiring additional processors.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional


class SkillsAnalysisError(Exception):
    """Raised when skills analysis fails."""


@dataclass(slots=True)
class SkillsAnalysisResult:
    """Container for extracted skills/technology signals."""

    target: str
    languages: List[str]
    primary_language: Optional[str]
    total_code_files: int
    summary: Dict[str, Any]


class SkillsAnalysisService:
    """Minimal skills analysis helper to keep the Textual app running."""

    def extract_skills(
        self,
        target_path: Path,
        code_analysis_result: Optional[Any] = None,
        git_analysis_result: Optional[Dict[str, Any]] = None,
        file_contents: Optional[Dict[str, str]] = None,
    ) -> SkillsAnalysisResult:
        """
        Extract a simple skills report from code and git analysis results.
        Falls back gracefully if data is missing.
        """
        try:
            summary = getattr(code_analysis_result, "summary", None) or {}
            languages = summary.get("languages") or {}
            ordered = sorted(languages.items(), key=lambda item: item[1], reverse=True)
            language_list = [lang for lang, _ in ordered]
            primary_language = language_list[0] if language_list else None

            total_files = summary.get("total_files")
            if total_files is None and code_analysis_result is not None:
                total_files = len(getattr(code_analysis_result, "files", []) or [])

            git_info = {}
            if git_analysis_result:
                git_info = {
                    "commit_count": git_analysis_result.get("commit_count"),
                    "contributor_count": git_analysis_result.get("contributor_count"),
                    "project_type": git_analysis_result.get("project_type"),
                }
            summary = {**summary, **{"git": git_info}}

            return SkillsAnalysisResult(
                target=str(target_path),
                languages=language_list,
                primary_language=primary_language,
                total_code_files=total_files or 0,
                summary=summary,
            )
        except Exception as exc:  # pragma: no cover - defensive catch
            raise SkillsAnalysisError(f"Failed to extract skills: {exc}") from exc

    # --- Formatting helpers -------------------------------------------------

    def format_skills_paragraph(self, result: SkillsAnalysisResult) -> str:
        """Return a short paragraph suitable for a quick highlight."""
        if not result.languages:
            return "No code skills detected. Try scanning a repository with source files."

        langs = ", ".join(result.languages[:5])
        lead = f"Primary language: {result.primary_language}" if result.primary_language else "Mixed language project"
        return f"{lead}. Languages observed: {langs}. Total code files analyzed: {result.total_code_files}."

    def format_skills_summary(self, result: SkillsAnalysisResult) -> str:
        """Return a concise bullet-style summary."""
        lines = []
        lines.append("[b]Skills Snapshot[/b]")
        lines.append(f"Target: {result.target}")
        lines.append(f"Code files analyzed: {result.total_code_files}")
        if result.languages:
            lines.append(f"Primary language: {result.primary_language}")
            lines.append("Languages: " + ", ".join(result.languages[:8]))
        if result.summary.get("git"):
            git = result.summary["git"]
            commit_count = git.get("commit_count")
            contributor_count = git.get("contributor_count")
            project_type = git.get("project_type")
            if any([commit_count, contributor_count, project_type]):
                lines.append("")
                lines.append("[b]Git signals[/b]")
                if project_type:
                    lines.append(f"Project type: {project_type}")
                if commit_count is not None:
                    lines.append(f"Commits: {commit_count}")
                if contributor_count is not None:
                    lines.append(f"Contributors: {contributor_count}")
        return "\n".join(lines)

    def format_summary(self, result: SkillsAnalysisResult) -> str:
        """Full multi-section summary."""
        lines = []
        lines.append("[b]Skills Analysis[/b]")
        lines.append(f"Target: {result.target}")
        lines.append(f"Total code files: {result.total_code_files}")

        if result.languages:
            lines.append("")
            lines.append("[b]Languages[/b]")
            for lang in result.languages[:10]:
                lines.append(f"• {lang}")
        else:
            lines.append("")
            lines.append("No languages detected.")

        metrics = result.summary or {}
        quality = metrics.get("avg_maintainability")
        complexity = metrics.get("avg_complexity")
        if quality is not None or complexity is not None:
            lines.append("")
            lines.append("[b]Quality signals[/b]")
            if quality is not None:
                lines.append(f"• Avg maintainability: {quality:.1f}/100")
            if complexity is not None:
                lines.append(f"• Avg complexity: {complexity:.1f}")

        return "\n".join(lines)
