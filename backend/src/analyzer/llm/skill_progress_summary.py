"""
LLM-powered summarization for skills progress timelines.

Uses a single model call to turn a timeline of period stats into a concise
narrative with milestones, strengths, and gaps. The caller provides a
`call_model` callable that returns the raw model text; this keeps the module
testable without hitting the network.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Protocol
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
    validation_warning: Optional[str] = None


def build_prompt(timeline: List[Dict[str, Any]]) -> str:
    """Create a deterministic prompt for summarizing skill progression."""
    overall_languages = sorted(
        {
            lang
            for entry in timeline or []
            for lang in (entry.get("period_languages") or entry.get("languages") or {}).keys()
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

    # Collect all commit messages and files for reference
    all_commit_messages = []
    all_top_files = []
    all_activity_types = set()
    for entry in timeline or []:
        all_commit_messages.extend(entry.get("commit_messages") or [])
        all_top_files.extend(entry.get("top_files") or [])
        all_activity_types.update(entry.get("activity_types") or [])

    total_commits = sum((entry.get("commits") or 0) for entry in timeline or [])
    total_tests = sum((entry.get("tests_changed") or 0) for entry in timeline or [])
    total_evidence = sum((entry.get("evidence_count") or 0) for entry in timeline or [])
    top_period = None
    try:
        top_period = max(timeline or [], key=lambda e: e.get("commits") or 0).get("period_label")
    except Exception:
        top_period = None

    return (
        "You are a precise software engineering coach who ONLY reports facts from the input data.\n\n"
        "INPUT DATA FIELDS:\n"
        "  - overall_languages: languages that appeared in changed files\n"
        "  - overall_top_skills: skills detected across all periods\n"
        "  - totals: commits, tests_changed, evidence_count, top_period_by_commits\n"
        "  - timeline: JSON array where EACH period contains:\n"
        "      * period_label: the month (e.g., '2025-10')\n"
        "      * commits: number of commits in that period\n"
        "      * tests_changed: number of test files modified\n"
        "      * skill_count, evidence_count: skill metrics\n"
        "      * top_skills: specific skills detected\n"
        "      * commit_messages: ACTUAL commit messages from that period\n"
        "      * top_files: ACTUAL files modified in that period\n"
        "      * activity_types: inferred activities (e.g., 'tests', 'ai', 'refactor')\n"
        "      * period_languages: languages of files CHANGED in that period with counts\n\n"
        "TASK: Produce STRICT JSON with keys:\n"
        "  - narrative (3-5 sentences): factual summary of what happened\n"
        "  - milestones (3-5 bullets): specific achievements with evidence\n"
        "  - strengths (2-3 bullets): demonstrated capabilities\n"
        "  - gaps (1-2 bullets): areas for improvement\n\n"
        "GROUNDING RULES (VIOLATIONS WILL BE REJECTED):\n"
        "  1. ONLY reference data that appears in the input. No fabrication.\n"
        "  2. If commits > 0, you MUST NOT say 'no commits' or 'zero activity'.\n"
        "  3. NEVER invent numbers. Only use: commits, tests_changed, skill_count, evidence_count.\n"
        "  4. NEVER invent language instance counts (e.g., '435 Python instances' is FORBIDDEN).\n"
        "  5. ONLY mention languages from period_languages. Do not guess or add others.\n"
        "  6. ONLY mention files from top_files. Do not invent file names or paths.\n"
        "  7. ONLY mention activities from activity_types or commit_messages. No fabrication.\n"
        "  8. Do NOT claim 'updated README' or 'documentation changes' unless 'docs' is in activity_types.\n"
        "  9. FORBIDDEN phrases unless backed by specific data:\n"
        "     - 'significant growth', 'strong emphasis', 'substantial activity'\n"
        "     - 'dominant language', 'primary focus' (unless data proves it)\n"
        "     - Any made-up counts or percentages\n"
        "  10. For milestones: MUST cite the specific period AND specific evidence (file, message, or skill).\n"
        "  11. If period_languages is empty, do NOT mention languages for that period.\n"
        "  12. Respond with JSON only. No markdown fences, no explanations.\n\n"
        f"Overall languages (from changed files): {overall_languages or '[]'}\n"
        f"Overall top skills: {overall_skills or '[]'}\n"
        f"All activity types: {sorted(all_activity_types) or '[]'}\n"
        f"Total commits: {total_commits}, total tests changed: {total_tests}, total evidence: {total_evidence}, "
        f"top period by commits: {top_period}\n\n"
        f"Timeline:\n{json.dumps(timeline, ensure_ascii=False, indent=2)}\n\n"
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
    
    # Dump the exact LLM input for debugging
    _dump_llm_input(timeline, prompt)
    
    try:
        raw = call_model(prompt)
    except Exception as exc:
        raise ValueError(f"Model call failed: {exc}") from exc

    def _truncate(value: str, limit: int = 320) -> str:
        text = (value or "")[: limit + 1]
        return text if len(text) <= limit else text[:limit] + "…"

    dump_paths = _dump_raw_response(raw)

    validation_warning: Optional[str] = None
    
    try:
        parsed = _coerce_json_response(raw)
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
        raise ValueError(f"Parse failed: {exc} | raw_snippet={snippet}{locations}") from exc

    # Validate grounding but don't block - capture as warning
    try:
        _validate_grounding(timeline, parsed)
    except ValueError as exc:
        validation_warning = str(exc)

    for key in ("narrative", "milestones", "strengths", "gaps"):
        if key not in parsed:
            raise ValueError(f"Missing key in model response: {key}")

    return SkillProgressSummary(
        narrative=str(parsed.get("narrative", "")).strip(),
        milestones=[str(x).strip() for x in parsed.get("milestones", []) if str(x).strip()],
        strengths=[str(x).strip() for x in parsed.get("strengths", []) if str(x).strip()],
        gaps=[str(x).strip() for x in parsed.get("gaps", []) if str(x).strip()],
        validation_warning=validation_warning,
    )


def _coerce_json_response(raw: str) -> Dict[str, Any]:
    """Best-effort JSON parsing with light cleanup for code fences."""
    if raw is None:
        raise ValueError("Model returned no content")

    # Strip markdown code fences like ```json ... ```
    fence_match = re.search(r"```(?:json)?\s*(.*?)```", str(raw), flags=re.DOTALL | re.IGNORECASE)
    if fence_match:
        candidate = fence_match.group(1)
    else:
        candidate = str(raw).strip()

    # Remove control characters that can break JSON parsing
    candidate = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", candidate)

    # Direct JSON parse
    try:
        return json.loads(candidate)
    except Exception:
        pass

    def _try_snippet_from_brackets(text: str) -> Dict[str, Any]:
        parse_errors: list[str] = []
        # Attempt to extract either object {} or array [] payloads.
        for opener, closer in (("{", "}"), ("[", "]")):
            start = text.find(opener)
            end = text.rfind(closer)
            if start != -1 and end != -1 and end > start:
                snippet = text[start : end + 1]
                try:
                    return json.loads(snippet)
                except Exception as exc:
                    parse_errors.append(str(exc))
                    try:
                        literal_obj = ast.literal_eval(snippet)
                        if isinstance(literal_obj, (dict, list)):
                            return literal_obj  # type: ignore[return-value]
                    except Exception as exc2:
                        parse_errors.append(str(exc2))
                        continue
        detail = f" Details: {' | '.join(parse_errors)}" if parse_errors else ""
        raise ValueError(f"Model did not return valid JSON.{detail}")

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


def _dump_llm_input(timeline: List[Dict[str, Any]], prompt: str) -> List[str]:
    """Dump the exact LLM input (timeline + prompt) for debugging."""
    written: List[str] = []
    
    # Analyze timeline for missing fields
    missing_report = []
    for entry in timeline or []:
        period = entry.get("period_label") or entry.get("period") or "unknown"
        missing = []
        if not entry.get("commit_messages"):
            missing.append("commit_messages")
        if not entry.get("top_files"):
            missing.append("top_files")
        if not entry.get("activity_types"):
            missing.append("activity_types")
        if not entry.get("period_languages"):
            missing.append("period_languages")
        if missing:
            missing_report.append(f"  {period}: MISSING {', '.join(missing)}")
    
    input_dump = {
        "timeline": timeline,
        "missing_fields_report": missing_report or ["All evidence fields present"],
        "prompt_preview": prompt[:2000] + "..." if len(prompt) > 2000 else prompt,
    }
    
    # Write to env path or default
    env_paths = os.environ.get("SKILL_SUMMARY_DEBUG_PATH", "")
    targets: List[str] = []
    for part in env_paths.split(","):
        target = part.strip()
        if target:
            # Create input dump path alongside the raw output
            base = Path(target)
            targets.append(str(base.parent / "skill_summary_input.json"))
    targets.append(str(Path(tempfile.gettempdir()) / "skill_summary_input.json"))
    
    for target in targets:
        try:
            path_obj = Path(target)
            path_obj.parent.mkdir(parents=True, exist_ok=True)
            path_obj.write_text(json.dumps(input_dump, indent=2, ensure_ascii=False), encoding="utf-8")
            written.append(str(path_obj))
        except Exception:
            continue
    
    return written
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
    # Track languages per period for dominance checks
    per_period_lang_sets: List[set[str]] = []
    for entry in timeline or []:
        langs = set()
        for lang_dict_key in ("languages", "period_languages"):
            lang_dict = entry.get(lang_dict_key)
            if isinstance(lang_dict, dict):
                langs.update({k.lower() for k in lang_dict.keys()})
        if langs:
            per_period_lang_sets.append(langs)
    lang_intersection = set.intersection(*per_period_lang_sets) if per_period_lang_sets else set()

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
            if total_commits > 0 and re.search(r"\bno commits\b", text, flags=re.IGNORECASE):
                raise ValueError("Model claimed no commits despite commit data")
            for lang in langs:
                if lang_intersection and lang not in lang_intersection and re.search(
                    r"(dominant|primary|main)\s+language.*(all|across)\s+periods",
                    text,
                    flags=re.IGNORECASE,
                ):
                    raise ValueError(f"Model overstated {lang} dominance across all periods")

    _validate_field(parsed.get("narrative", ""), "narrative")
    _validate_field(parsed.get("milestones", []), "milestones")
    _validate_field(parsed.get("strengths", []), "strengths")
    _validate_field(parsed.get("gaps", []), "gaps")
