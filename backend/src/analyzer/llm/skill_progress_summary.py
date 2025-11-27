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
import re
import ast
import tempfile
from pathlib import Path
import os


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
    overall_languages = sorted(
        {
            lang
            for entry in timeline or []
            for lang in (entry.get("languages") or {}).keys()
            if lang
        }
    )
    overall_skills = []
    seen_skills = set()
    for entry in timeline or []:
        for skill in entry.get("top_skills") or []:
            if skill in seen_skills:
                continue
            seen_skills.add(skill)
            overall_skills.append(skill)

    total_commits = sum((entry.get("commits") or 0) for entry in timeline or [])
    total_tests = sum((entry.get("tests_changed") or 0) for entry in timeline or [])
    total_evidence = sum((entry.get("evidence_count") or 0) for entry in timeline or [])
    top_period = None
    try:
        top_period = max(timeline or [], key=lambda e: e.get("commits") or 0).get("period_label")
    except Exception:
        top_period = None

    return (
        "You are a concise software engineering coach.\n"
        "Input:\n"
        "  - overall_languages: list of all languages observed\n"
        "  - overall_top_skills: list of notable skills across periods\n"
        "  - totals: commits, tests_changed, evidence_count, top_period_by_commits\n"
        "  - timeline: JSON array of periods with keys: period_label, commits, tests_changed, "
        "skill_count, evidence_count, top_skills, languages, contributors, commit_messages, top_files, activity_types, period_languages.\n"
        "Task: Produce STRICT JSON with keys narrative (3-5 sentences), milestones (3-5 bullets), "
        "strengths (2-3 bullets), gaps (1-2 bullets).\n"
        "Grounding rules (hard constraints):\n"
        "  - Use only the provided data. Do NOT invent periods, numbers, skills, files, or languages.\n"
        "  - Milestones must cite concrete evidence from the same period (commit_messages, top_files, top_skills, period_languages, tests_changed).\n"
        "  - Mention dominant languages explicitly when period_languages are present; do not fabricate other languages.\n"
        "  - Avoid vague phrases like \"significant growth\" or \"skill enhancement\" unless explicitly supported by provided evidence.\n"
        "  - If contributors > 1, note collaboration; otherwise treat as individual.\n"
        "  - Respond with JSON only.\n"
        f"Overall languages: {overall_languages or '[]'}\n"
        f"Overall top skills: {overall_skills or '[]'}\n"
        f"Total commits: {total_commits}, total tests changed: {total_tests}, total evidence: {total_evidence}, "
        f"top period by commits: {top_period}\n"
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
    try:
        raw = call_model(prompt)
    except Exception as exc:
        raise ValueError(f"Model call failed: {exc}") from exc

    def _truncate(value: str, limit: int = 320) -> str:
        text = (value or "")[: limit + 1]
        return text if len(text) <= limit else text[:limit] + "…"

    dump_paths = _dump_raw_response(raw)

    try:
        parsed = _coerce_json_response(raw)
        _validate_grounding(timeline, parsed)
    except ValueError as exc:
        snippet = _truncate(str(raw))
        try:
            debug_path = Path(tempfile.gettempdir()) / "skill_summary_raw.txt"
            debug_path.write_text(str(raw), encoding="utf-8")
            if str(debug_path) not in dump_paths:
                dump_paths.append(str(debug_path))
        except Exception:
            pass
        locations = f" | raw_dumped={','.join(dump_paths)}" if dump_paths else ""
        raise ValueError(f"{exc} | raw_snippet={snippet}{locations}") from exc

    for key in ("narrative", "milestones", "strengths", "gaps"):
        if key not in parsed:
            raise ValueError(f"Missing key in model response: {key}")

    return SkillProgressSummary(
        narrative=str(parsed.get("narrative", "")).strip(),
        milestones=[str(x).strip() for x in parsed.get("milestones", []) if str(x).strip()],
        strengths=[str(x).strip() for x in parsed.get("strengths", []) if str(x).strip()],
        gaps=[str(x).strip() for x in parsed.get("gaps", []) if str(x).strip()],
    )


def _coerce_json_response(raw: str) -> Dict[str, Any]:
    """Best-effort JSON parsing with light cleanup for code fences."""
    if raw is None:
        raise ValueError("Model returned no content")

    # Strip markdown code fences like ```json ... ```
    fence_match = re.search(r"```(?:json)?\\s*(.*?)```", str(raw), flags=re.DOTALL | re.IGNORECASE)
    if fence_match:
        candidate = fence_match.group(1)
    else:
        candidate = str(raw).strip()

    # Direct JSON parse
    try:
        return json.loads(candidate)
    except Exception:
        pass

    def _try_snippet_from_brackets(text: str) -> Dict[str, Any]:
        # Attempt to extract either object {} or array [] payloads.
        for opener, closer in (("{", "}"), ("[", "]")):
            start = text.find(opener)
            end = text.rfind(closer)
            if start != -1 and end != -1 and end > start:
                snippet = text[start : end + 1]
                try:
                    return json.loads(snippet)
                except Exception:
                    try:
                        literal_obj = ast.literal_eval(snippet)
                        if isinstance(literal_obj, (dict, list)):
                            return literal_obj  # type: ignore[return-value]
                    except Exception:
                        continue
        raise ValueError("Model did not return valid JSON")

    return _try_snippet_from_brackets(candidate)


def _dump_raw_response(raw: Any) -> List[str]:
    """Persist raw model response to configured debug paths for troubleshooting."""
    targets: List[str] = []
    env_paths = os.environ.get("SKILL_SUMMARY_DEBUG_PATH", "")
    for part in env_paths.split(","):
        target = part.strip()
        if target:
            targets.append(target)
    # Always attempt a default temp file for convenience
    targets.append(str(Path(tempfile.gettempdir()) / "skill_summary_raw.txt"))

    written: List[str] = []
    for target in targets:
        try:
            path_obj = Path(target)
            path_obj.parent.mkdir(parents=True, exist_ok=True)
            path_obj.write_text(str(raw), encoding="utf-8")
            written.append(str(path_obj))
        except Exception:
            continue
    return written


_KNOWN_LANGUAGES = {
    "python",
    "javascript",
    "typescript",
    "shell",
    "bash",
    "go",
    "java",
    "ruby",
    "rust",
    "c#",
    "c++",
    "c",
    "php",
    "swift",
    "kotlin",
    "objective-c",
    "objective-c++",
}


def _validate_grounding(timeline: List[Dict[str, Any]], parsed: Dict[str, Any]) -> None:
    """Reject summaries that invent numbers or languages not present in input."""
    allowed_numbers = set()
    allowed_languages = set()
    for entry in timeline or []:
        for key in ("commits", "tests_changed", "skill_count", "evidence_count"):
            val = entry.get(key)
            if isinstance(val, int):
                allowed_numbers.add(val)
        # capture counts inside languages/period_languages
        for lang_dict_key in ("languages", "period_languages"):
            lang_dict = entry.get(lang_dict_key)
            if isinstance(lang_dict, dict):
                allowed_languages.update({k.lower() for k in lang_dict.keys()})
                for count in lang_dict.values():
                    if isinstance(count, int):
                        allowed_numbers.add(count)
        # counts of commit messages/files
        for list_key in ("commit_messages", "top_files"):
            lst = entry.get(list_key)
            if isinstance(lst, list):
                allowed_numbers.add(len(lst))
    # Aggregate totals from timeline
    total_commits = sum((entry.get("commits") or 0) for entry in timeline or [])
    total_tests = sum((entry.get("tests_changed") or 0) for entry in timeline or [])
    total_evidence = sum((entry.get("evidence_count") or 0) for entry in timeline or [])
    allowed_numbers.update({total_commits, total_tests, total_evidence})

    def _extract_numbers(text: str) -> List[int]:
        return [int(x) for x in re.findall(r"-?\d+", text)]

    def _extract_languages(text: str) -> List[str]:
        found = []
        for lang in _KNOWN_LANGUAGES:
            if lang == "c":
                if re.search(r"\bC\b", text):
                    found.append("c")
                continue
            if re.search(rf"\b{re.escape(lang)}\b", text, flags=re.IGNORECASE):
                found.append(lang.lower())
        return found

    def _validate_field(value: Any, field_name: str) -> None:
        texts: List[str] = []
        if isinstance(value, str):
            texts.append(value)
        elif isinstance(value, list):
            texts.extend([str(x) for x in value if isinstance(x, (str, int, float))])
        for text in texts:
            numbers = _extract_numbers(text)
            for num in numbers:
                if num <= 5:  # allow small list ordinals
                    continue
                if num not in allowed_numbers:
                    raise ValueError(f"Model hallucinated number {num} in {field_name}")
            langs = _extract_languages(text)
            for lang in langs:
                if lang not in allowed_languages:
                    raise ValueError(f"Model hallucinated language {lang} in {field_name}")

    _validate_field(parsed.get("narrative", ""), "narrative")
    _validate_field(parsed.get("milestones", []), "milestones")
    _validate_field(parsed.get("strengths", []), "strengths")
    _validate_field(parsed.get("gaps", []), "gaps")
