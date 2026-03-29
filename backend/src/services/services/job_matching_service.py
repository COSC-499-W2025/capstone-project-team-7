"""Job matching service providing keyword-based and AI-powered matching.

Compares a user's skill profile against job requirements to produce a
compatibility score and a list of matched / missing skills.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Common skill aliases — maps informal / abbreviated names to their
# canonical forms so that e.g. "js" and "javascript" are treated as equal.
# ---------------------------------------------------------------------------
_SKILL_ALIASES: Dict[str, str] = {
    "js": "javascript",
    "ts": "typescript",
    "py": "python",
    "node": "node.js",
    "nodejs": "node.js",
    "postgres": "postgresql",
    "k8s": "kubernetes",
    "csharp": "c#",
    "c sharp": "c#",
    "cpp": "c++",
    "golang": "go",
    "tf": "terraform",
    "gke": "kubernetes",
    "eks": "kubernetes",
    "aks": "kubernetes",
    "dynamodb": "dynamodb",
    "mongo": "mongodb",
    "scikit": "scikit-learn",
    "sklearn": "scikit-learn",
    "numpy": "numpy",
    "react.js": "react",
    "reactjs": "react",
    "vue.js": "vue",
    "vuejs": "vue",
    "angular.js": "angular",
    "angularjs": "angular",
    "express.js": "express",
    "expressjs": "express",
    "next": "next.js",
    "nextjs": "next.js",
}


class JobMatchingService:
    """Provides keyword and AI-driven job-to-user matching."""

    # ------------------------------------------------------------------
    # Keyword matching
    # ------------------------------------------------------------------

    def compute_keyword_match(
        self,
        user_skills: list[str],
        job_skills: list[str],
    ) -> dict:
        """Compute a Jaccard-like keyword match score.

        Parameters
        ----------
        user_skills:
            Skills the user claims or that were extracted from their profile.
        job_skills:
            Skills extracted from the job posting.

        Returns
        -------
        dict
            ``{"score": float, "matched_skills": [...], "missing_skills": [...]}``

        The score is ``len(matched) / len(all_unique)`` where *all_unique* is
        the union of both skill sets (after normalization).  If both lists are
        empty the score is ``0.0``.
        """
        normalized_user = {self._normalize_skill(s) for s in user_skills}
        normalized_job = {self._normalize_skill(s) for s in job_skills}

        all_unique = normalized_user | normalized_job
        if not all_unique:
            return {"score": 0.0, "matched_skills": [], "missing_skills": []}

        matched = normalized_user & normalized_job
        missing = normalized_job - normalized_user

        score = len(matched) / len(all_unique)

        return {
            "score": round(score, 4),
            "matched_skills": sorted(matched),
            "missing_skills": sorted(missing),
        }

    # ------------------------------------------------------------------
    # AI matching
    # ------------------------------------------------------------------

    async def compute_ai_match(
        self,
        llm_client: Any,
        user_skills: list[str],
        job_description: str,
        job_title: str,
        job_company: str,
    ) -> dict:
        """Use an LLM to evaluate how well *user_skills* fit a job posting.

        Parameters
        ----------
        llm_client:
            Instance of ``analyzer.llm.client.LLMClient`` (or compatible)
            exposing a ``chat(messages, response_format=None) -> str`` method.
        user_skills:
            The user's skill list.
        job_description:
            Full text of the job description.
        job_title:
            Title of the job posting.
        job_company:
            Company name from the job posting.

        Returns
        -------
        dict
            ``{"score": float, "summary": str,
              "matched_skills": [...], "missing_skills": [...]}``
        """
        skills_text = ", ".join(user_skills) if user_skills else "(none provided)"

        prompt = (
            "You are a career-matching assistant. Evaluate how well the "
            "candidate's skills match the following job posting.\n\n"
            f"Job Title: {job_title}\n"
            f"Company: {job_company}\n"
            f"Job Description:\n{job_description}\n\n"
            f"Candidate Skills: {skills_text}\n\n"
            "Respond with ONLY a JSON object (no markdown fences) containing:\n"
            '{\n'
            '  "score": <float between 0.0 and 1.0>,\n'
            '  "summary": "<2-3 sentence explanation>",\n'
            '  "matched_skills": ["skill1", "skill2"],\n'
            '  "missing_skills": ["skill3", "skill4"]\n'
            '}\n'
        )

        messages = [
            {
                "role": "system",
                "content": (
                    "You are a helpful career advisor that evaluates job fit. "
                    "Always return valid JSON."
                ),
            },
            {"role": "user", "content": prompt},
        ]

        fallback: Dict[str, Any] = {
            "score": 0.0,
            "summary": "AI matching was unable to produce a result.",
            "matched_skills": [],
            "missing_skills": [],
        }

        try:
            raw_response = await self._call_llm(llm_client, messages)
        except Exception:
            logger.error("LLM call failed during AI match", exc_info=True)
            return fallback

        # Parse the JSON response.
        try:
            parsed = self._parse_json_response(raw_response)
        except (json.JSONDecodeError, ValueError):
            logger.warning(
                "Failed to parse LLM response as JSON: %s",
                raw_response[:300] if raw_response else "(empty)",
            )
            return fallback

        # Validate and clamp the score.
        try:
            score = float(parsed.get("score", 0.0))
            score = max(0.0, min(1.0, score))
        except (TypeError, ValueError):
            score = 0.0

        return {
            "score": round(score, 4),
            "summary": str(parsed.get("summary", "")),
            "matched_skills": list(parsed.get("matched_skills", [])),
            "missing_skills": list(parsed.get("missing_skills", [])),
        }

    # ------------------------------------------------------------------
    # Skill normalization
    # ------------------------------------------------------------------

    def _normalize_skill(self, skill: str) -> str:
        """Lowercase, strip, and resolve common aliases."""
        normalized = skill.strip().lower()
        return _SKILL_ALIASES.get(normalized, normalized)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    async def _call_llm(llm_client: Any, messages: List[dict]) -> str:
        """Call the LLM client, handling both sync and async interfaces.

        The ``LLMClient.chat`` method may be synchronous (returns ``str``
        directly) or asynchronous (returns a coroutine).  We handle both
        transparently so the caller does not need to care.
        """
        import asyncio

        result = llm_client.chat(messages=messages, response_format=None)

        # If the client returned a coroutine, await it.
        if asyncio.iscoroutine(result):
            result = await result

        return str(result)

    @staticmethod
    def _parse_json_response(text: str) -> dict:
        """Attempt to extract a JSON object from *text*.

        Handles common LLM quirks such as wrapping the JSON in markdown
        code fences (````json ... ````).
        """
        cleaned = text.strip()

        # Strip markdown code fences if present.
        if cleaned.startswith("```"):
            # Remove opening fence (optionally with language tag).
            first_newline = cleaned.index("\n") if "\n" in cleaned else len(cleaned)
            cleaned = cleaned[first_newline + 1:]
            # Remove closing fence.
            if cleaned.rstrip().endswith("```"):
                cleaned = cleaned.rstrip()[:-3].rstrip()

        return json.loads(cleaned)
