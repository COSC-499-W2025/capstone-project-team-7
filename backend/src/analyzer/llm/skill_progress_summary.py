"""
LLM-powered summarization for skills progress timelines.

Uses a single model call to turn a timeline of period stats into a concise
narrative with milestones, strengths, and gaps. The caller provides a
`call_model` callable that returns the raw model text; this keeps the module
testable without hitting the network.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Protocol
import json


class _ModelCaller(Protocol):
    """Protocol for the LLM caller to keep this module testable."""

    def __call__(self, prompt: str) -> str: ...


@dataclass
class SkillProgressSummary:
    narrative: str
    milestones: List[str] = field(default_factory=list)
    strengths: List[str] = field(default_factory=list)
    gaps: List[str] = field(default_factory=list)


def build_prompt(timeline: List[Dict[str, Any]]) -> str:
    """Create a deterministic prompt for summarizing skill progression."""
    return (
        "You are a concise software engineering coach.\n"
        "Input: JSON array of periods with keys period_label, commits, tests_changed, "
        "skill_count, evidence_count, top_skills, languages.\n"
        "Task: Produce STRICT JSON with keys narrative (3-5 sentences), milestones (3-5 bullets), "
        "strengths (2-3 bullets), gaps (1-2 bullets). Only discuss trends that appear in the data; "
        "do NOT invent periods or skills.\n"
        f"Timeline:\n{json.dumps(timeline, ensure_ascii=False, indent=2)}\n"
        "Respond with JSON only."
    )


def summarize_skill_progress(
    timeline: List[Dict[str, Any]],
    call_model: _ModelCaller,
) -> SkillProgressSummary:
    """
    Summarize skill progression timeline via a single model call.

    Args:
        timeline: list of period dictionaries.
        call_model: callable that returns raw model text given a prompt.

    Returns:
        SkillProgressSummary object.

    Raises:
        ValueError: if timeline is empty or response is invalid.
    """
    if not timeline:
        raise ValueError("Timeline required for skill progression summary")

    prompt = build_prompt(timeline)
    raw = call_model(prompt)

    try:
        parsed = json.loads(raw)
    except Exception as exc:
        raise ValueError(f"Model did not return valid JSON: {exc}") from exc

    for key in ("narrative", "milestones", "strengths", "gaps"):
        if key not in parsed:
            raise ValueError(f"Missing key in model response: {key}")

    return SkillProgressSummary(
        narrative=str(parsed.get("narrative", "")).strip(),
        milestones=[str(x).strip() for x in parsed.get("milestones", []) if str(x).strip()],
        strengths=[str(x).strip() for x in parsed.get("strengths", []) if str(x).strip()],
        gaps=[str(x).strip() for x in parsed.get("gaps", []) if str(x).strip()],
    )
