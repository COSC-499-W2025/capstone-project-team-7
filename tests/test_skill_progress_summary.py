"""
Tests for LLM skill progression summarizer.
"""

from pathlib import Path
import sys
import json
import pytest

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
    assert "contributors" in prompt
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


def test_summarize_skill_progress_coerces_json_fences():
    timeline = [{"period_label": "2024-01", "commits": 1, "tests_changed": 2, "skill_count": 3, "evidence_count": 4}]

    def fake_model(prompt: str) -> str:
        return """```json
        {
            "narrative": "ok",
            "milestones": ["a"],
            "strengths": ["b"],
            "gaps": ["c"]
        }
        ```"""

    summary = summarize_skill_progress(timeline, fake_model)
    assert summary.narrative
    assert summary.milestones == ["a"]


def test_summarize_skill_progress_handles_embedded_json():
    timeline = [{"period_label": "2024-01", "commits": 1, "tests_changed": 2, "skill_count": 3, "evidence_count": 4}]

    def fake_model(prompt: str) -> str:
        return 'Here you go: {"narrative": "n", "milestones": [], "strengths": [], "gaps": []}'

    summary = summarize_skill_progress(timeline, fake_model)
    assert summary.narrative == "n"


def test_build_prompt_includes_evidence_fields():
    timeline = [
        {
            "period_label": "2024-02",
            "commits": 5,
            "tests_changed": 1,
            "skill_count": 2,
            "evidence_count": 3,
            "top_skills": ["Async IO", "Testing"],
            "languages": {"Python": 2},
            "contributors": 1,
            "commit_messages": ["Add async worker", "Refactor test harness"],
            "top_files": ["src/app.py", "tests/test_app.py"],
            "activity_types": ["code", "tests"],
            "period_languages": {"Python": 2},
        }
    ]
    prompt = build_prompt(timeline)
    assert "Add async worker" in prompt
    assert "src/app.py" in prompt
    assert "activity_types" in prompt
    assert "period_languages" in prompt


def test_prompt_forbids_invented_content():
    timeline = [
        {
            "period_label": "2024-03",
            "commits": 2,
            "tests_changed": 0,
            "skill_count": 1,
            "evidence_count": 1,
            "top_skills": ["LLM"],
            "languages": {"Python": 1},
            "contributors": 1,
            "commit_messages": ["Wire LLM client"],
            "top_files": ["backend/src/analyzer.py"],
            "activity_types": ["ai"],
            "period_languages": {"Python": 1},
        }
    ]
    prompt = build_prompt(timeline)
    assert "Do NOT invent periods" in prompt
    assert "Milestones must cite concrete evidence" in prompt


def test_summarize_skill_progress_rejects_hallucinated_numbers():
    timeline = [
        {
            "period_label": "2024-05",
            "commits": 3,
            "tests_changed": 1,
            "skill_count": 1,
            "evidence_count": 2,
            "languages": {"Python": 1},
            "period_languages": {"Python": 1},
            "top_skills": ["APIs"],
            "commit_messages": ["Add API endpoint"],
            "top_files": ["src/api.py"],
        }
    ]

    def fake_model(prompt: str) -> str:
        # Invents a number not present in the input
        return json.dumps(
            {
                "narrative": "Handled 406 commits.",
                "milestones": [],
                "strengths": [],
                "gaps": [],
            }
        )

    with pytest.raises(ValueError):
        summarize_skill_progress(timeline, fake_model)


def test_summarize_skill_progress_rejects_hallucinated_languages():
    timeline = [
        {
            "period_label": "2024-06",
            "commits": 2,
            "tests_changed": 0,
            "skill_count": 1,
            "evidence_count": 1,
            "languages": {"Python": 1},
            "period_languages": {"Python": 1},
            "top_skills": ["Testing"],
            "commit_messages": ["Add tests"],
            "top_files": ["tests/test_app.py"],
        }
    ]

    def fake_model(prompt: str) -> str:
        return json.dumps(
            {
                "narrative": "Work was done in C.",
                "milestones": [],
                "strengths": [],
                "gaps": [],
            }
        )

    with pytest.raises(ValueError):
        summarize_skill_progress(timeline, fake_model)


def test_summarize_skill_progress_accepts_python_literal_json():
    timeline = [{"period_label": "2024-01", "commits": 1, "tests_changed": 0, "skill_count": 1, "evidence_count": 1}]

    def fake_model(prompt: str) -> str:
        # Returns single-quoted Python literal; should be coerced.
        return "{'narrative': 'ok', 'milestones': ['a'], 'strengths': [], 'gaps': []}"

    summary = summarize_skill_progress(timeline, fake_model)
    assert summary.narrative == "ok"


def test_summarize_skill_progress_accepts_leading_prose_with_json():
    timeline = [{"period_label": "2024-02", "commits": 1, "tests_changed": 0, "skill_count": 1, "evidence_count": 1}]

    def fake_model(prompt: str) -> str:
        return "Sure, here it is:\n{\"narrative\": \"n\", \"milestones\": [], \"strengths\": [], \"gaps\": []}"

    summary = summarize_skill_progress(timeline, fake_model)
    assert summary.narrative == "n"


def test_summarize_skill_progress_rejects_absent_json():
    timeline = [{"period_label": "2024-03", "commits": 1, "tests_changed": 0, "skill_count": 1, "evidence_count": 1}]

    def fake_model(prompt: str) -> str:
        return "No JSON here"

    with pytest.raises(ValueError) as err:
        summarize_skill_progress(timeline, fake_model)
    assert "raw_snippet" in str(err.value)


def test_summarize_skill_progress_wraps_call_model_error():
    timeline = [{"period_label": "2024-04", "commits": 1, "tests_changed": 0, "skill_count": 1, "evidence_count": 1}]

    def fake_model(prompt: str) -> str:
        raise RuntimeError("AI response was not json")

    with pytest.raises(ValueError) as err:
        summarize_skill_progress(timeline, fake_model)
    assert "Model call failed" in str(err.value)
