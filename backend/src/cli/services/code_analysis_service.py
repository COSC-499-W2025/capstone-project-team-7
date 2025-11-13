from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from ...scanner.models import FileMetadata, ParseResult, ScanPreferences

try:  # tree-sitter / parser extras are optional
    from ...local_analysis.code_parser import (
        CodeAnalyzer,
        DirectoryResult,
        EXCLUDED_DIRS,
    )
except Exception:  # pragma: no cover - optional dependency tree
    CodeAnalyzer = None  # type: ignore[assignment]
    DirectoryResult = Any  # type: ignore[assignment]
    EXCLUDED_DIRS = {"node_modules", ".git", "__pycache__", "venv", ".venv", "build", "dist"}


CODE_FILE_EXTENSIONS: Tuple[str, ...] = (
    ".py",
    ".js",
    ".ts",
    ".tsx",
    ".java",
    ".c",
    ".cpp",
    ".cc",
    ".h",
    ".hpp",
    ".go",
    ".rs",
    ".rb",
    ".php",
    ".cs",
    ".html",
    ".css",
    ".scss",
    ".sass",
    ".jsx",
)


class CodeAnalysisError(RuntimeError):
    """Base error for the code analysis helpers."""


class CodeAnalysisUnavailableError(CodeAnalysisError):
    """Raised when the local code analysis dependencies are missing."""


AnalyzerBuilder = Callable[..., Any]


class CodeAnalysisService:
    """Bridge between the Textual UI and the tree-sitter powered analyzer."""

    def __init__(self, analyzer_builder: Optional[AnalyzerBuilder] = None) -> None:
        self._analyzer_builder = analyzer_builder

    # --- Detection helpers -------------------------------------------------

    def code_file_candidates(self, parse_result: Optional[ParseResult]) -> List[FileMetadata]:
        """Return files from the scan that look like source code."""
        if not parse_result:
            return []
        candidates: List[FileMetadata] = []
        for meta in parse_result.files:
            suffix = Path(meta.path).suffix.lower()
            if suffix in CODE_FILE_EXTENSIONS:
                candidates.append(meta)
        return candidates

    # --- Execution helpers -------------------------------------------------

    def run_analysis(
        self,
        target: Path,
        preferences: Optional[ScanPreferences] = None,
    ) -> DirectoryResult:
        """Analyze the provided directory and return the raw DirectoryResult."""
        analyzer = self._create_analyzer(preferences)
        try:
            return analyzer.analyze_directory(target)
        except CodeAnalysisError:
            raise
        except Exception as exc:  # pragma: no cover - analyzer specific failures
            raise CodeAnalysisError(f"Code analysis failed: {exc}") from exc

    def _create_analyzer(self, preferences: Optional[ScanPreferences]):
        analyzer_kwargs = self._build_analyzer_kwargs(preferences)
        builder = self._analyzer_builder
        if builder is None:
            if CodeAnalyzer is None:
                raise CodeAnalysisUnavailableError(
                    "Code analysis requires tree-sitter language bindings. "
                    "Install the optional dependencies listed in README.md."
                )
            builder = CodeAnalyzer
        try:
            return builder(**analyzer_kwargs)
        except ImportError as exc:  # pragma: no cover - missing deps bubble up
            raise CodeAnalysisUnavailableError(str(exc)) from exc
        except CodeAnalysisUnavailableError:
            raise
        except Exception as exc:  # pragma: no cover - builder specific failure
            raise CodeAnalysisError(f"Unable to initialize code analyzer: {exc}") from exc

    def _build_analyzer_kwargs(self, preferences: Optional[ScanPreferences]) -> Dict[str, Any]:
        max_file_mb = 5.0
        if preferences and preferences.max_file_size_bytes:
            max_file_mb = max(0.5, preferences.max_file_size_bytes / (1024 * 1024))

        excluded = set(EXCLUDED_DIRS)
        if preferences and preferences.excluded_dirs:
            excluded.update({entry for entry in preferences.excluded_dirs if entry})

        return {
            "max_file_mb": max_file_mb,
            "max_depth": 10,
            "excluded": excluded,
        }

    # --- Formatting helpers ------------------------------------------------

    def format_summary(self, result: DirectoryResult) -> str:
        """Return a multi-line string summarizing analyzer output."""
        summary = getattr(result, "summary", None) or {}
        lines: List[str] = []
        lines.append("[b]Code analysis[/b]")
        lines.append(f"Target: {getattr(result, 'path', 'unknown')}")
        lines.append("")

        total_files = summary.get("total_files", len(getattr(result, "files", [])))
        successful = summary.get("successful")
        if successful is None:
            successful = getattr(result, "successful", 0)
            if callable(successful):
                successful = successful()
        failed = max(total_files - successful, 0)
        lines.append(f"Files analyzed: {successful}/{total_files} (failed: {failed})")

        lines.append("")
        lines.append("[b]Code metrics[/b]")
        lines.append(f"• Total lines: {summary.get('total_lines', 0):,}")
        lines.append(f"• Code lines: {summary.get('total_code', 0):,}")
        lines.append(f"• Comment lines: {summary.get('total_comments', 0):,}")
        lines.append(f"• Functions: {summary.get('total_functions', 0)}")
        lines.append(f"• Classes: {summary.get('total_classes', 0)}")

        maintainability = summary.get("avg_maintainability")
        complexity = summary.get("avg_complexity")
        if maintainability is not None or complexity is not None:
            lines.append("")
            lines.append("[b]Quality snapshot[/b]")
            if maintainability is not None:
                lines.append(f"• Avg maintainability: {maintainability:.1f}/100")
                lines.append(f"• Overall status: {self._quality_label(maintainability)}")
            if complexity is not None:
                lines.append(f"• Avg complexity: {complexity:.1f}")

        lines.append("")
        lines.append("[b]Issues detected[/b]")
        lines.append(f"• Potential security issues: {summary.get('security_issues', 0)}")
        lines.append(f"• TODO/FIXME comments: {summary.get('todos', 0)}")
        lines.append(f"• High-priority files: {summary.get('high_priority_files', 0)}")
        lines.append(f"• Functions needing refactor: {summary.get('functions_needing_refactor', 0)}")

        language_block = self._format_languages(summary.get("languages") or {})
        if language_block:
            lines.append("")
            lines.append("[b]Languages[/b]")
            lines.extend(language_block)

        refactor_block = self._format_refactor_targets(result)
        if refactor_block:
            lines.append("")
            lines.append("[b]Refactor candidates[/b]")
            lines.extend(refactor_block)

        return "\n".join(lines).strip()

    def _format_languages(self, languages: Dict[str, int]) -> List[str]:
        if not languages:
            return []
        ordered = sorted(languages.items(), key=lambda item: item[1], reverse=True)
        return [f"• {lang}: {count} file{'s' if count != 1 else ''}" for lang, count in ordered[:5]]

    def _format_refactor_targets(self, result: DirectoryResult, limit: int = 3) -> List[str]:
        formatter = getattr(result, "get_refactor_candidates", None)
        if not callable(formatter):
            return []
        candidates: List[str] = []
        for file_result in formatter(limit=limit):
            metrics = getattr(file_result, "metrics", None)
            if not metrics:
                continue
            name = Path(getattr(file_result, "path", "unknown")).name
            candidates.append(
                f"• {name}: maintainability {metrics.maintainability_score:.0f}/100, complexity {metrics.complexity}"
            )
            highlights = [
                func for func in getattr(metrics, "top_functions", []) if getattr(func, "needs_refactor", False)
            ]
            for func in highlights[:2]:
                candidates.append(
                    f"   - {func.name}: {func.lines} lines, complexity {func.complexity}, params {func.params}"
                )
        return candidates

    @staticmethod
    def _quality_label(score: float) -> str:
        if score >= 80:
            return "[green]excellent[/green]"
        if score >= 70:
            return "[green]good[/green]"
        if score >= 60:
            return "[yellow]fair[/yellow]"
        if score >= 50:
            return "[#f97316]needs work[/#f97316]"
        return "[red]critical[/red]"
