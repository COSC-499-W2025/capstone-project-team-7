"""
Tests for LLM skill progression summarizer.
"""

from pathlib import Path
import sys
import json

# Add backend/src to path
backend_src_path = Path(__file__).parent.parent / "backend" / "src"
sys.path.insert(0, str(backend_src_path))

from backend.src.analyzer.llm.skill_progress_summary import (
    build_prompt,
    summarize_skill_progress,
)


def test_build_prompt_contains_timeline_json():
    timeline = [{"period_label": "2024-01", "commits": 3, "top_skills": ["Testing"], "languages": {"Python": 1}}]
    prompt = build_prompt(timeline)
    assert "period_label" in prompt
    assert "Testing" in prompt
    assert "JSON" in prompt


def test_summarize_skill_progress_parses_valid_json():
    timeline = [{"period_label": "2024-01", "commits": 3, "top_skills": ["Testing"], "languages": {"Python": 1}}]

    def fake_model(prompt: str) -> str:
        return json.dumps(
            {
                "narrative": "Steady testing work in January.",
                "milestones": ["Added tests"],
                "strengths": ["Testing discipline"],
                "gaps": ["Limited language diversity"],
            }
        )

    summary = summarize_skill_progress(timeline, fake_model)
    assert summary.narrative.startswith("Steady")
    assert summary.milestones == ["Added tests"]
    assert summary.strengths == ["Testing discipline"]
    assert summary.gaps == ["Limited language diversity"]


def test_summarize_skill_progress_rejects_missing_keys():
    timeline = [{"period_label": "2024-01"}]

    def fake_model(prompt: str) -> str:
        return json.dumps({"narrative": "x"})

    try:
        summarize_skill_progress(timeline, fake_model)
        assert False, "Expected ValueError for missing keys"
    except ValueError as exc:
        assert "Missing key" in str(exc)
