from __future__ import annotations

from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

import pytest

from services.resume_generation_service import (
    ResumeGenerationError,
    ResumeGenerationService,
)
from backend.src.local_analysis.contribution_analyzer import ActivityBreakdown, ProjectContributionMetrics
from backend.src.scanner.models import FileMetadata, ParseResult


def _file(path: str, size: int = 100, mime: str = "text/plain") -> FileMetadata:
    now = datetime.utcnow()
    return FileMetadata(
        path=path,
        size_bytes=size,
        mime_type=mime,
        created_at=now,
        modified_at=now,
    )


class _DummyCodeResult:
    def __init__(self, summary: dict, file_count: int = 3) -> None:
        self.summary = summary
        self.files = [object()] * file_count


def test_generate_resume_item_with_git_and_code_data(tmp_path: Path) -> None:
    service = ResumeGenerationService()
    parse_result = ParseResult(files=[_file("src/main.py")], summary={"files_processed": 1})

    code_result = _DummyCodeResult(
        {
            "avg_maintainability": 82.5,
            "avg_complexity": 3.1,
            "total_files": 4,
            "security_issues": 1,
            "todos": 2,
        }
    )

    activity = ActivityBreakdown(code_lines=200, test_lines=80, documentation_lines=40, design_lines=0, config_lines=20)
    contribution_metrics = ProjectContributionMetrics(
        project_path=str(tmp_path),
        project_type="collaborative",
        total_commits=24,
        total_contributors=3,
        project_duration_days=34,
        project_start_date="2025-10-15T00:00:00Z",
        project_end_date="2025-11-18T00:00:00Z",
        contributors=[],
        overall_activity_breakdown=activity,
        commit_frequency=0.0,
        languages_detected=set(),
    )

    git_analysis = [
        {
            "commit_count": 24,
            "contributors": [{"name": "A"}, {"name": "B"}],
            "project_type": "collaborative",
            "date_range": {"start": "2025-10-15T00:00:00Z", "end": "2025-11-18T00:00:00Z"},
        }
    ]

    output_path = tmp_path / "resume_item.md"
    item = service.generate_resume_item(
        target_path=tmp_path,
        parse_result=parse_result,
        languages=[{"language": "Python", "file_percent": 100.0, "files": 1}],
        code_analysis_result=code_result,
        contribution_metrics=contribution_metrics,
        git_analysis=git_analysis,
        output_path=output_path,
    )

    content = output_path.read_text()
    assert item.output_path == output_path
    assert content.startswith(f"{tmp_path.name} — Oct 2025 – Nov 2025")
    lines = content.splitlines()
    assert lines[1].startswith("Overview:")
    assert "Python" in lines[1]
    assert len(item.bullets) >= 2
    assert "Python" in content
    assert "collaborative" in content
    assert "maintainability" in content


def test_generate_resume_item_handles_unknown_dates(tmp_path: Path) -> None:
    service = ResumeGenerationService()
    parse_result = ParseResult(files=[_file("index.js")], summary={"files_processed": 1})
    code_result = _DummyCodeResult({"avg_maintainability": 75.0, "total_files": 2})

    item = service.generate_resume_item(
        target_path=tmp_path,
        parse_result=parse_result,
        languages=[{"language": "JavaScript", "file_percent": 100.0, "files": 1}],
        code_analysis_result=code_result,
        contribution_metrics=None,
        git_analysis=[],
        output_path=tmp_path / "resume_item.md",
    )

    header = item.to_markdown().splitlines()[0]
    assert "Unknown Dates" in header or header.endswith("Unknown Dates")
    assert item.to_markdown().splitlines()[1].startswith("Overview:")
    assert len(item.bullets) >= 2


def test_generate_resume_item_requires_meaningful_data(tmp_path: Path) -> None:
    service = ResumeGenerationService()
    parse_result = ParseResult(files=[_file("README.md", mime="text/markdown")], summary={"files_processed": 1})

    with pytest.raises(ResumeGenerationError) as excinfo:
        service.generate_resume_item(
            target_path=tmp_path,
            parse_result=parse_result,
            languages=[],
            code_analysis_result=None,
            contribution_metrics=None,
            git_analysis=[],
            output_path=tmp_path / "resume_item.md",
        )

    assert "Insufficient project data" in str(excinfo.value)


class _FakeAIClient:
    def __init__(self, response: str) -> None:
        self._response = response

    def _make_llm_call(self, messages, max_tokens=None, temperature=None):
        return self._response


def test_generate_resume_item_with_ai_client(tmp_path: Path) -> None:
    service = ResumeGenerationService()
    parse_result = ParseResult(files=[_file("src/main.py")], summary={"files_processed": 3})
    code_result = _DummyCodeResult({"avg_maintainability": 70, "avg_complexity": 2.3, "total_files": 3})
    ai_markdown = """project-x — Jan 2024 – Feb 2024
- Built a Textual UI with fast archive scans and cached rescans.
- Improved reliability and stability with structured code analysis.
- Coordinated with a 3-person team with clear ownership."""

    item = service.generate_resume_item(
        target_path=tmp_path,
        parse_result=parse_result,
        languages=[{"language": "Python"}],
        code_analysis_result=code_result,
        contribution_metrics=None,
        git_analysis=[{"commit_count": 15, "contributors": [{"name": "A"}, {"name": "B"}, {"name": "C"}]}],
        output_path=tmp_path / "resume_item.md",
        ai_client=_FakeAIClient(ai_markdown),
    )

    markdown = item.to_markdown()
    assert "Overview:" in markdown
    assert "Textual UI" in markdown
    assert "3-person team" in item.to_markdown()
    assert item.ai_generated is True


def test_generate_resume_item_uses_document_summary(tmp_path: Path) -> None:
    service = ResumeGenerationService()
    parse_result = ParseResult(files=[_file("src/app.py")], summary={"files_processed": 1})
    code_result = _DummyCodeResult({"avg_maintainability": 80, "total_files": 3})
    doc_result = SimpleNamespace(
        file_name="ProductVision.md",
        summary="Market research tool to surface possible sample groups for B2B studies.",
        success=True,
    )

    item = service.generate_resume_item(
        target_path=tmp_path,
        parse_result=parse_result,
        languages=[{"language": "Python"}],
        code_analysis_result=code_result,
        contribution_metrics=None,
        git_analysis=[],
        document_results=[doc_result],
        output_path=tmp_path / "resume_item.md",
    )

    markdown = item.to_markdown()
    overview_line = markdown.splitlines()[1]
    assert "Market research tool" in overview_line


def test_generate_resume_item_uses_pdf_summary_when_no_docs(tmp_path: Path) -> None:
    service = ResumeGenerationService()
    parse_result = ParseResult(files=[_file("src/app.py")], summary={"files_processed": 1})
    code_result = _DummyCodeResult({"avg_maintainability": 75, "total_files": 2})
    pdf_summary = SimpleNamespace(
        file_name="Strategy.pdf",
        success=True,
        summary_text="Customer insights dashboard that aggregates survey responses and highlights recruiting targets.",
        key_points=["Highlights recruiting targets"],
    )

    item = service.generate_resume_item(
        target_path=tmp_path,
        parse_result=parse_result,
        languages=[{"language": "TypeScript"}],
        code_analysis_result=code_result,
        contribution_metrics=None,
        git_analysis=[],
        pdf_summaries=[pdf_summary],
        output_path=tmp_path / "resume_item.md",
    )

    markdown = item.to_markdown()
    overview_line = markdown.splitlines()[1]
    assert "Customer insights dashboard" in overview_line


def test_document_summary_prefers_non_template_docs(tmp_path: Path) -> None:
    service = ResumeGenerationService()
    parse_result = ParseResult(files=[_file("src/app.py")], summary={"files_processed": 1})
    readme = SimpleNamespace(
        file_name="README.md",
        summary="React Vite template that provides a starter configuration for rapid prototyping.",
        success=True,
    )
    proposal = SimpleNamespace(
        file_name="ProjectProposal.md",
        summary="Course planning assistant that uses AI suggestions to balance credit loads and prerequisite chains.",
        success=True,
    )

    item = service.generate_resume_item(
        target_path=tmp_path,
        parse_result=parse_result,
        languages=[{"language": "Python"}],
        code_analysis_result=_DummyCodeResult({"avg_maintainability": 80, "total_files": 2}),
        contribution_metrics=None,
        git_analysis=[],
        document_results=[readme, proposal],
        output_path=tmp_path / "resume_item.md",
    )

    markdown = item.to_markdown()
    overview_line = markdown.splitlines()[1]
    assert "Course planning assistant" in overview_line
