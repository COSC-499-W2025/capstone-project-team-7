"""
LLM-powered summarization for skills progress timelines.

Uses a single model call to turn a timeline of period stats into a concise,
developer-friendly summary with actionable insights. The caller provides a
`call_model` callable that returns the raw model text; this keeps the module
testable without hitting the network.

OUTPUT STRUCTURE (developer-focused):
- overview: 3-5 sentences describing project phases/chapters
- timeline: Per-period bullets with concrete examples from commits/files
- skills_focus: Which skills were exercised and how
- suggested_next_steps: Actionable coaching based on gaps
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
    """Developer-friendly skill progression summary."""
    overview: str  # 3-5 sentences describing project phases
    timeline: List[str] = field(default_factory=list)  # Per-period bullets with examples
    skills_focus: List[str] = field(default_factory=list)  # Which skills were exercised
    suggested_next_steps: List[str] = field(default_factory=list)  # Actionable coaching
    validation_warning: Optional[str] = None

    # Legacy property aliases for backward compatibility
    @property
    def narrative(self) -> str:
        return self.overview

    @property
    def milestones(self) -> List[str]:
        return self.timeline

    @property
    def strengths(self) -> List[str]:
        return self.skills_focus

    @property
    def gaps(self) -> List[str]:
        return self.suggested_next_steps


def _filter_noise_languages(lang_dict: Dict[str, int], threshold_pct: float = 0.05) -> Dict[str, int]:
    """Filter out noise languages that represent less than threshold of total."""
    if not lang_dict:
        return {}
    total = sum(lang_dict.values())
    if total == 0:
        return {}
    # Keep languages that are >= threshold OR have at least 3 files
    return {
        lang: count for lang, count in lang_dict.items()
        if count / total >= threshold_pct or count >= 3
    }


def _get_primary_languages(lang_dict: Dict[str, int], top_n: int = 3) -> List[str]:
    """Get the top N languages by file count."""
    if not lang_dict:
        return []
    sorted_langs = sorted(lang_dict.items(), key=lambda x: x[1], reverse=True)
    return [lang for lang, _ in sorted_langs[:top_n]]


def _describe_period_focus(entry: Dict[str, Any]) -> str:
    """Generate a human-readable focus description for a period."""
    activity_types = entry.get("activity_types") or []
    top_skills = entry.get("top_skills") or []
    commits = entry.get("commits") or 0
    tests = entry.get("tests_changed") or 0

    if commits == 0:
        return "light activity or setup"

    focus_parts = []
    if "tests" in activity_types or tests > 0:
        focus_parts.append("testing")
    if "ai" in activity_types:
        focus_parts.append("AI/LLM integration")
    if "api" in activity_types:
        focus_parts.append("API development")
    if "auth" in activity_types:
        focus_parts.append("authentication")
    if "refactor" in activity_types:
        focus_parts.append("refactoring")
    if "ui" in activity_types:
        focus_parts.append("UI work")
    if "async" in activity_types:
        focus_parts.append("async/concurrency")
    if "cli" in activity_types:
        focus_parts.append("CLI tooling")
    if "migrations" in activity_types:
        focus_parts.append("database migrations")
    if "config" in activity_types:
        focus_parts.append("configuration")
    if "docs" in activity_types:
        focus_parts.append("documentation")
    if "bugfix" in activity_types:
        focus_parts.append("bug fixes")
    if "feature" in activity_types:
        focus_parts.append("new features")

    if not focus_parts and top_skills:
        focus_parts = top_skills[:2]

    return ", ".join(focus_parts[:3]) if focus_parts else "general development"


def build_prompt(timeline: List[Dict[str, Any]]) -> str:
    """Create a developer-focused prompt for summarizing skill progression."""

    # Aggregate overall stats with noise filtering
    overall_languages: Dict[str, int] = {}
    for entry in timeline or []:
        for lang, count in (entry.get("period_languages") or entry.get("languages") or {}).items():
            if lang:
                overall_languages[lang] = overall_languages.get(lang, 0) + count

    # Filter noise languages (like stray C files)
    filtered_languages = _filter_noise_languages(overall_languages)
    primary_languages = _get_primary_languages(filtered_languages)

    # Collect skills preserving order of appearance
    overall_skills = []
    seen_skills = set()
    for entry in timeline or []:
        for skill in entry.get("top_skills") or []:
            if skill not in seen_skills:
                seen_skills.add(skill)
                overall_skills.append(skill)

    # Collect activity types across all periods
    all_activity_types = set()
    for entry in timeline or []:
        all_activity_types.update(entry.get("activity_types") or [])

    # Calculate totals
    total_commits = sum((entry.get("commits") or 0) for entry in timeline or [])
    total_tests = sum((entry.get("tests_changed") or 0) for entry in timeline or [])
    total_evidence = sum((entry.get("evidence_count") or 0) for entry in timeline or [])

    # Find busiest period
    top_period = None
    if timeline:
        try:
            top_period = max(timeline, key=lambda e: e.get("commits") or 0).get("period_label")
        except Exception:
            pass

    # Build per-period summaries for the prompt
    period_summaries = []
    for entry in timeline or []:
        period = entry.get("period_label", "unknown")
        commits = entry.get("commits") or 0
        tests = entry.get("tests_changed") or 0
        skills = entry.get("top_skills") or []
        messages = (entry.get("commit_messages") or [])[:5]  # Top 5 for prompt
        files = (entry.get("top_files") or [])[:5]
        activities = entry.get("activity_types") or []

        # Filter period languages too
        period_langs = _filter_noise_languages(entry.get("period_languages") or {})

        summary = {
            "period": period,
            "commits": commits,
            "tests_changed": tests,
            "focus": _describe_period_focus(entry),
            "skills": skills[:5],
            "activities": activities,
            "languages": list(period_langs.keys()),
            "sample_commits": messages,
            "sample_files": files,
        }
        period_summaries.append(summary)

    # Build the prompt
    prompt = f"""You are a friendly developer coach reviewing someone's project history. Your job is to help them understand what they accomplished and what they could focus on next.

INPUT DATA:
- Primary languages: {primary_languages}
- All skills detected: {overall_skills}
- Activity types seen: {sorted(all_activity_types)}
- Total commits: {total_commits}, tests changed: {total_tests}
- Busiest period: {top_period}

PERIOD-BY-PERIOD DATA:
{json.dumps(period_summaries, indent=2)}

FULL TIMELINE (for reference):
{json.dumps(timeline, indent=2)}

YOUR TASK: Create a JSON summary that helps this developer understand their work. Output these exact keys:

{{
  "overview": "3-5 sentences describing the project phases. Start with what the project seems to be about, then describe how the work evolved (e.g., 'setup phase' -> 'core features' -> 'testing/polish'). Be specific about WHAT was built, not just that 'work happened'.",

  "timeline": [
    "In <period>, you focused on <focus area>, with commits like '<actual commit message>' and changes to <actual file>.",
    "In <period>, testing ramped up with <N> test files changed, focusing on <skill or area>.",
    "...3-6 bullets, one per significant period"
  ],

  "skills_focus": [
    "<Skill>: <how it was used, e.g., 'grew throughout Oct-Nov with integration tests for LLM routes'>",
    "<Skill>: <concrete observation>",
    "...3-5 bullets for the most-used skills"
  ],

  "suggested_next_steps": [
    "Consider <actionable suggestion based on gaps>, e.g., 'adding performance benchmarks' or 'earlier testing in the cycle'",
    "...2-3 kind, actionable bullets"
  ]
}}

GROUNDING RULES (your response will be validated):
1. ONLY use numbers that appear in the input: commits, tests_changed, evidence_count, skill_count.
2. ONLY mention skills that appear in "top_skills" for that period. If a skill IS listed, do NOT say it's missing or absent.
3. ONLY mention languages from period_languages. Ignore tiny/noise languages.
4. Quote actual commit messages from sample_commits. Do not invent commit messages.
5. Reference actual files from sample_files. Do not invent file paths.
6. If a period has 0 commits, say "light activity" or "setup", don't invent details.
7. Do NOT use phrases like "N instances of Python" or made-up percentages.
8. Do NOT say "no evidence of X" or "missing X" if X appears in that period's skills.
9. suggested_next_steps should be KIND and ACTIONABLE, not critical. Focus on growth opportunities.
10. For skills_focus, describe HOW the skill was used, not just that it exists.
11. It's okay to say "more testing in November than September" if tests_changed supports it.

FORBIDDEN:
- Invented numbers, statistics, or percentages
- "significant growth" / "substantial" / "dominant" without clear data backing
- Claiming a skill is missing when it appears in top_skills
- Generic filler like "broadening of expertise" or "expanding horizons"
- Phrases like "440 instances" or any count not in the input

Respond with valid JSON only. No markdown fences."""

    return prompt


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

    # Accept both new and legacy field names
    overview = parsed.get("overview") or parsed.get("narrative", "")
    timeline_bullets = parsed.get("timeline") or parsed.get("milestones", [])
    skills_focus = parsed.get("skills_focus") or parsed.get("strengths", [])
    next_steps = parsed.get("suggested_next_steps") or parsed.get("gaps", [])

    # Require at least the overview/narrative
    if not overview:
        raise ValueError("Missing 'overview' or 'narrative' in model response")

    return SkillProgressSummary(
        overview=str(overview).strip(),
        timeline=[str(x).strip() for x in timeline_bullets if str(x).strip()],
        skills_focus=[str(x).strip() for x in skills_focus if str(x).strip()],
        suggested_next_steps=[str(x).strip() for x in next_steps if str(x).strip()],
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
    """Reject summaries that invent numbers, languages, or contradict input data."""
    allowed_numbers = set()
    allowed_languages = set()
    all_skills = set()  # Track all skills mentioned across periods
    
    # Aggregate language counts to filter noise
    total_lang_counts: Dict[str, int] = {}
    
    for entry in timeline or []:
        # Extract years from period_label (e.g., "2025-08" -> 2025)
        period_label = entry.get("period_label") or entry.get("period") or ""
        if isinstance(period_label, str):
            year_match = re.match(r"(\d{4})", period_label)
            if year_match:
                allowed_numbers.add(int(year_match.group(1)))

        for key in ("commits", "tests_changed", "skill_count", "evidence_count"):
            val = entry.get(key)
            if isinstance(val, int):
                allowed_numbers.add(val)
        
        # Capture counts inside languages/period_languages
        for lang_dict_key in ("languages", "period_languages"):
            lang_dict = entry.get(lang_dict_key)
            if isinstance(lang_dict, dict):
                for lang, count in lang_dict.items():
                    total_lang_counts[lang.lower()] = total_lang_counts.get(lang.lower(), 0) + count
                    if isinstance(count, int):
                        allowed_numbers.add(count)
        
        # Capture skills for contradiction checking
        for skill in entry.get("top_skills") or []:
            all_skills.add(skill.lower())
        
        # Counts of commit messages/files
        for list_key in ("commit_messages", "top_files"):
            lst = entry.get(list_key)
            if isinstance(lst, list):
                allowed_numbers.add(len(lst))
    
    # Filter noise languages (< 5% of total) from allowed set
    total_files = sum(total_lang_counts.values()) if total_lang_counts else 0
    for lang, count in total_lang_counts.items():
        if total_files == 0 or count / total_files >= 0.05 or count >= 3:
            allowed_languages.add(lang)
    
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
            
            # Check for contradictions: claiming skill is missing when it's in top_skills
            for skill in all_skills:
                # Look for patterns like "no evidence of X", "missing X", "lack of X", "no X"
                contradiction_patterns = [
                    rf"\bno\s+(?:evidence\s+of\s+)?{re.escape(skill)}\b",
                    rf"\bmissing\s+{re.escape(skill)}\b",
                    rf"\black\s+of\s+{re.escape(skill)}\b",
                    rf"\babsent\s+{re.escape(skill)}\b",
                    rf"\bno\s+{re.escape(skill)}\s+(?:skills?|evidence|work)\b",
                ]
                for pattern in contradiction_patterns:
                    if re.search(pattern, text, flags=re.IGNORECASE):
                        raise ValueError(f"Model claimed '{skill}' is missing but it appears in top_skills")
            
            for lang in langs:
                if lang_intersection and lang not in lang_intersection and re.search(
                    r"(dominant|primary|main)\s+language.*(all|across)\s+periods",
                    text,
                    flags=re.IGNORECASE,
                ):
                    raise ValueError(f"Model overstated {lang} dominance across all periods")

    # Validate both old and new field names
    _validate_field(parsed.get("overview", "") or parsed.get("narrative", ""), "overview")
    _validate_field(parsed.get("timeline", []) or parsed.get("milestones", []), "timeline")
    _validate_field(parsed.get("skills_focus", []) or parsed.get("strengths", []), "skills_focus")
    _validate_field(parsed.get("suggested_next_steps", []) or parsed.get("gaps", []), "suggested_next_steps")
