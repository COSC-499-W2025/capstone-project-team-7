"""
Service-level tests for skill progress summarization.
"""

from pathlib import Path
import sys
import json
import types

# Add backend/src to path
backend_src_path = Path(__file__).parent.parent / "backend" / "src"
sys.path.insert(0, str(backend_src_path))

# Stub pypdf to avoid optional dependency during import chain
if "pypdf" not in sys.modules:  # pragma: no cover - test harness shim
    errors_module = types.SimpleNamespace(PdfReadError=Exception)
    sys.modules["pypdf"] = types.SimpleNamespace(PdfReader=lambda *args, **kwargs: None, errors=errors_module)
    sys.modules["pypdf.errors"] = errors_module

from backend.src.cli.services.skills_analysis_service import SkillsAnalysisService


def test_service_summarizes_progression():
    service = SkillsAnalysisService()
    timeline = [{"period_label": "2024-01", "commits": 3, "top_skills": ["Testing"], "languages": {"Python": 1}}]

    def fake_model(prompt: str) -> str:
        return json.dumps(
            {
                "narrative": "January focused on testing.",
                "milestones": ["Added tests"],
                "strengths": ["Testing discipline"],
                "gaps": ["Coverage breadth"],
            }
        )

    summary = service.summarize_skill_progression(timeline, fake_model)
    assert summary.narrative.startswith("January")
    assert "Added tests" in summary.milestones


def test_service_rejects_empty_timeline():
    service = SkillsAnalysisService()

    def fake_model(prompt: str) -> str:
        return "{}"

    try:
        service.summarize_skill_progression([], fake_model)
        assert False, "Expected failure on empty timeline"
    except ValueError:
        pass
