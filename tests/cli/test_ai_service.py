from __future__ import annotations

from backend.src.cli.services.ai_service import AIService


def test_format_analysis_includes_sections() -> None:
    service = AIService()
    payload = {
        "portfolio_summary": {"summary": "Overall strong project mix."},
        "projects": [
            {
                "project_name": "App",
                "project_path": "src/app",
                "analysis": "Solid structure.",
                "file_summaries": [{"file_path": "src/app/main.py"}],
            }
        ],
        "file_summaries": [{"file_path": "README.md", "analysis": "Good docs."}],
        "files_analyzed_count": 5,
    }

    rendered = service.format_analysis(payload)

    assert "Portfolio Overview" in rendered
    assert "Project Insights" in rendered
    assert "Key Files" in rendered


def test_summarize_analysis_produces_preview() -> None:
    service = AIService()
    payload = {
        "files_analyzed_count": 10,
        "project_count": 2,
        "project_analysis": {"analysis": "Detailed insight line 1.\nMore detail."},
    }

    summary = service.summarize_analysis(payload)

    assert "Files analyzed: 10" in summary
    assert "Projects analyzed: 2" in summary
    assert "Preview" in summary
