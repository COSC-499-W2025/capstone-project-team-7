from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import pytest

from backend.src.cli.services.code_analysis_service import (
    CODE_FILE_EXTENSIONS,
    CodeAnalysisService,
    CodeAnalysisUnavailableError,
)
from backend.src.scanner.models import FileMetadata, ParseResult, ScanPreferences


class DummyFunction:
    def __init__(self, name: str, lines: int, complexity: int, params: int, needs_refactor: bool = True) -> None:
        self.name = name
        self.lines = lines
        self.complexity = complexity
        self.params = params
        self.needs_refactor = needs_refactor


class DummyMetrics:
    def __init__(
        self,
        *,
        maintainability: float = 72.0,
        complexity: int = 15,
        top_functions: Optional[List[DummyFunction]] = None,
    ) -> None:
        self.lines = 200
        self.code_lines = 150
        self.comments = 20
        self.functions = 8
        self.classes = 2
        self.complexity = complexity
        self.top_functions = top_functions or []
        self.security_issues: List[str] = []
        self.todos: List[str] = []
        self.warnings: List[str] = []
        self._maintainability = maintainability

    @property
    def maintainability_score(self) -> float:
        return self._maintainability


class DummyFileResult:
    def __init__(self, path: str, language: str, metrics: DummyMetrics) -> None:
        self.path = path
        self.language = language
        self.metrics = metrics
        self.success = True


class DummyDirectoryResult:
    def __init__(self, path: str, files: List[DummyFileResult], summary: Dict[str, Any]) -> None:
        self.path = path
        self.files = files
        self.summary = summary

    @property
    def successful(self) -> int:
        return sum(1 for file in self.files if getattr(file, "success", False))

    def get_refactor_candidates(self, limit: int = 3) -> List[DummyFileResult]:
        return self.files[:limit]


def _file(path: str, mime: str = "text/plain") -> FileMetadata:
    now = datetime.utcnow()
    return FileMetadata(
        path=path,
        size_bytes=123,
        mime_type=mime,
        created_at=now,
        modified_at=now,
    )


def test_code_file_candidates_filters_supported_files() -> None:
    service = CodeAnalysisService()
    parse_result = ParseResult(
        files=[
            _file("src/app.py"),
            _file("src/styles.css"),
            _file("README.md"),
            _file("assets/logo.png", "image/png"),
        ]
    )

    matches = service.code_file_candidates(parse_result)

    assert [meta.path for meta in matches] == ["src/app.py", "src/styles.css"]
    assert all(Path(meta.path).suffix.lower() in CODE_FILE_EXTENSIONS for meta in matches)


def test_run_analysis_uses_preferences_and_builder(tmp_path: Path) -> None:
    captured_kwargs: Dict[str, Any] = {}

    class DummyAnalyzer:
        def __init__(self, **kwargs: Any) -> None:
            captured_kwargs.update(kwargs)

        def analyze_directory(self, target: Path) -> DummyDirectoryResult:
            return DummyDirectoryResult(path=str(target), files=[], summary={})

    service = CodeAnalysisService(analyzer_builder=DummyAnalyzer)
    prefs = ScanPreferences(
        max_file_size_bytes=3 * 1024 * 1024,
        excluded_dirs=["build", "custom"],
    )

    result = service.run_analysis(tmp_path, prefs)

    assert result.path == str(tmp_path)
    assert pytest.approx(captured_kwargs["max_file_mb"]) == pytest.approx(3.0)
    assert "custom" in captured_kwargs["excluded"]


def test_run_analysis_surfaces_dependency_error(tmp_path: Path) -> None:
    def broken_builder(**_: Any) -> Any:
        raise ImportError("tree-sitter missing")

    service = CodeAnalysisService(analyzer_builder=broken_builder)

    with pytest.raises(CodeAnalysisUnavailableError):
        service.run_analysis(tmp_path, None)


def test_format_summary_highlights_languages_and_refactors() -> None:
    metrics = DummyMetrics(
        maintainability=78.0,
        complexity=15,
        top_functions=[DummyFunction("process_data", 80, 14, 3)],
    )
    file_result = DummyFileResult(path="proj/app.py", language="python", metrics=metrics)

    directory_result = DummyDirectoryResult(
        path="proj",
        files=[file_result],
        summary={
            "total_files": 1,
            "successful": 1,
            "languages": {"Python": 1},
            "total_lines": 200,
            "total_code": 150,
            "total_comments": 20,
            "total_functions": 8,
            "total_classes": 2,
            "avg_complexity": 15.0,
            "avg_maintainability": metrics.maintainability_score,
            "security_issues": 0,
            "todos": 2,
            "high_priority_files": 1,
            "functions_needing_refactor": 1,
        },
    )

    service = CodeAnalysisService(analyzer_builder=lambda **_: None)  # builder unused for formatting
    summary_text = service.format_summary(directory_result)

    assert "Code analysis" in summary_text
    assert "Python" in summary_text
    assert "Avg maintainability" in summary_text
    assert "Refactor candidates" in summary_text
