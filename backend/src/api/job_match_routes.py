"""Job Match API routes.

Endpoints:
    POST /api/jobs/search   — search for jobs based on keywords / preferences
    POST /api/jobs/match    — search + score + AI explanation against user profile
    POST /api/jobs/explain  — get AI explanation for a single job vs user profile
    GET  /api/jobs/saved    — list saved jobs for current user
    POST /api/jobs/saved    — save a job posting
    DELETE /api/jobs/saved/{job_id} — unsave a job posting
"""

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from api.dependencies import AuthContext, get_auth_context
from services.job_search_client import JobSearchParams, search_jobs, JobListing
from services.services import local_store

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/jobs", tags=["Job Match"])


# ── Request / Response models ────────────────────────────────────────


class JobSearchRequest(BaseModel):
    keywords: str = Field("", description="Search keywords (e.g. 'python developer')")
    location: str = Field("", description="City or region")
    remote_only: bool = False
    salary_min: Optional[int] = None
    category: str = ""
    results_per_page: int = Field(10, ge=1, le=50)
    country: str = Field("ca", description="2-letter country code (Adzuna)")


class UserProfile(BaseModel):
    """Lightweight profile blob sent from frontend for matching."""
    skills: List[str] = Field(default_factory=list)
    job_titles: List[str] = Field(default_factory=list)
    experience_summary: str = ""
    education: str = ""


class JobMatchRequest(BaseModel):
    search: JobSearchRequest = Field(default_factory=JobSearchRequest)
    profile: UserProfile = Field(default_factory=UserProfile)
    resume_id: Optional[str] = Field(None, description="User resume ID to score against")


class JobExplainRequest(BaseModel):
    job: dict = Field(..., description="Serialised JobListing dict")
    profile: UserProfile = Field(default_factory=UserProfile)


class ScoredJob(BaseModel):
    job: dict
    score: float = Field(description="0-100 keyword match score")
    ai_score: Optional[float] = Field(None, description="0-100 AI resume match score")
    match_reasons: List[str] = Field(default_factory=list)


class JobMatchResponse(BaseModel):
    jobs: List[ScoredJob]
    total: int


class JobExplainResponse(BaseModel):
    explanation: str


# ── Scoring helpers ──────────────────────────────────────────────────


def _keyword_score(job: JobListing, profile: UserProfile) -> tuple[float, list[str]]:
    """Simple keyword overlap scorer. Returns (score, reasons)."""
    if not profile.skills and not profile.job_titles:
        return 50.0, ["No profile data provided — showing unscored results"]

    job_text = f"{job.title} {job.description} {job.category} {job.company}".lower()
    matches: list[str] = []

    for skill in profile.skills:
        if skill.lower() in job_text:
            matches.append(f"Matches skill: {skill}")

    for title in profile.job_titles:
        if title.lower() in job_text:
            matches.append(f"Matches desired role: {title}")

    if profile.experience_summary:
        for word in profile.experience_summary.lower().split():
            if len(word) > 4 and word in job_text and len(matches) < 8:
                matches.append(f"Keyword overlap: {word}")

    total_criteria = max(len(profile.skills) + len(profile.job_titles), 1)
    raw = len(matches) / total_criteria
    score = min(round(raw * 100, 1), 100)
    return score, matches


def _build_match_prompt(job: dict, profile: UserProfile) -> str:
    skills_str = ", ".join(profile.skills) if profile.skills else "not specified"
    titles_str = ", ".join(profile.job_titles) if profile.job_titles else "not specified"
    return (
        "You are a career advisor. Given the candidate's profile and a job listing, "
        "explain in 2-3 concise sentences why this job is a good (or poor) match.\n\n"
        f"## Candidate\n"
        f"- Skills: {skills_str}\n"
        f"- Desired roles: {titles_str}\n"
        f"- Experience: {profile.experience_summary or 'not specified'}\n"
        f"- Education: {profile.education or 'not specified'}\n\n"
        f"## Job\n"
        f"- Title: {job.get('title', 'N/A')}\n"
        f"- Company: {job.get('company', 'N/A')}\n"
        f"- Description: {job.get('description', 'N/A')[:500]}\n\n"
        "Respond with ONLY the explanation — no bullet points, no heading."
    )


def _get_llm_client_for_user(user_id: str):
    """Try to retrieve the user's cached LLM client (if they've configured one)."""
    try:
        from api.llm_routes import get_user_client
        return get_user_client(user_id)
    except Exception:
        return None


async def _explain_match(job: dict, profile: UserProfile, user_id: str) -> str:
    """Generate an AI explanation for a job match. Returns empty string on failure."""
    client = _get_llm_client_for_user(user_id)
    if client is None:
        return ""
    try:
        prompt = _build_match_prompt(job, profile)
        response = client.client.chat.completions.create(
            model=client.DEFAULT_MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=200,
            temperature=0.5,
        )
        return response.choices[0].message.content.strip()
    except Exception as exc:
        logger.warning("LLM match explanation failed: %s", exc)
        return ""


def _extract_resume_text(structured_data: Dict[str, Any]) -> str:
    """Build a plain-text representation of resume structured_data for AI scoring."""
    parts: list[str] = []

    contact = structured_data.get("contact", {})
    if contact.get("full_name"):
        parts.append(f"Name: {contact['full_name']}")

    skills = structured_data.get("skills", {})
    for category in ["languages", "frameworks", "developer_tools", "libraries"]:
        items = skills.get(category, [])
        if items:
            parts.append(f"{category.replace('_', ' ').title()}: {', '.join(items)}")
    custom_skills = skills.get("custom", {})
    for cat_name, items in custom_skills.items():
        if items:
            parts.append(f"{cat_name}: {', '.join(items)}")

    for exp in structured_data.get("experience", []):
        line = f"{exp.get('position', '')} at {exp.get('company', '')}"
        if exp.get("start_date"):
            line += f" ({exp['start_date']} - {exp.get('end_date', 'Present')})"
        bullets = exp.get("bullets", [])
        if bullets:
            line += "\n  " + "\n  ".join(f"- {b}" for b in bullets)
        parts.append(line)

    for proj in structured_data.get("projects", []):
        line = proj.get("name", "")
        if proj.get("technologies"):
            line += f" [{proj['technologies']}]"
        bullets = proj.get("bullets", [])
        if bullets:
            line += "\n  " + "\n  ".join(f"- {b}" for b in bullets)
        parts.append(line)

    for edu in structured_data.get("education", []):
        line = f"{edu.get('degree', '')} {edu.get('field_of_study', '')} — {edu.get('institution', '')}"
        parts.append(line)

    return "\n".join(parts)


def _build_resume_score_prompt(job: dict, resume_text: str) -> str:
    """Build a prompt asking the AI to score a resume against a job description."""
    return (
        "You are an expert recruiter. Score how well this resume matches the job posting.\n"
        "Return ONLY a JSON object with two keys: \"score\" (integer 0-100) and \"reason\" (one sentence).\n\n"
        f"## Resume\n{resume_text[:2000]}\n\n"
        f"## Job Posting\n"
        f"Title: {job.get('title', 'N/A')}\n"
        f"Company: {job.get('company', 'N/A')}\n"
        f"Description: {job.get('description', 'N/A')[:1000]}\n"
        f"Category: {job.get('category', 'N/A')}\n\n"
        "Respond with ONLY valid JSON, nothing else."
    )


async def _ai_resume_score(job: dict, resume_text: str, user_id: str) -> tuple[Optional[float], str]:
    """Score a job against resume text using AI. Returns (score, reason) or (None, '')."""
    client = _get_llm_client_for_user(user_id)
    if client is None:
        return None, ""
    try:
        prompt = _build_resume_score_prompt(job, resume_text)
        response = client.client.chat.completions.create(
            model=client.DEFAULT_MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=150,
            temperature=0.3,
        )
        import json as _json
        raw = response.choices[0].message.content.strip()
        # Strip markdown code fences if present
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
        data = _json.loads(raw)
        score = float(data.get("score", 0))
        reason = str(data.get("reason", ""))
        return min(max(score, 0), 100), reason
    except Exception as exc:
        logger.warning("AI resume scoring failed: %s", exc)
        return None, ""


def _get_user_resume(user_id: str, resume_id: str, access_token: str) -> Optional[Dict[str, Any]]:
    """Fetch a user resume's structured_data. Returns None on failure."""
    try:
        from services.services.user_resume_service import UserResumeService
        svc = UserResumeService()
        svc.apply_access_token(access_token)
        return svc.get_resume(user_id, resume_id)
    except Exception as exc:
        logger.warning("Failed to fetch resume %s: %s", resume_id, exc)
        return None


# ── Endpoints ────────────────────────────────────────────────────────


@router.post("/search", response_model=List[dict])
async def search_job_listings(
    body: JobSearchRequest,
    auth: AuthContext = Depends(get_auth_context),
):
    """Plain job search — no scoring or AI."""
    params = JobSearchParams(
        keywords=body.keywords,
        location=body.location,
        remote_only=body.remote_only,
        salary_min=body.salary_min,
        category=body.category,
        results_per_page=body.results_per_page,
        country=body.country,
    )
    jobs = await search_jobs(params)
    return [j.to_dict() for j in jobs]


@router.post("/match", response_model=JobMatchResponse)
async def match_jobs(
    body: JobMatchRequest,
    auth: AuthContext = Depends(get_auth_context),
):
    """Search + score + optional AI explanation."""
    params = JobSearchParams(
        keywords=body.search.keywords or " ".join(body.profile.job_titles),
        location=body.search.location,
        remote_only=body.search.remote_only,
        salary_min=body.search.salary_min,
        category=body.search.category,
        results_per_page=body.search.results_per_page,
        country=body.search.country,
    )
    raw_jobs = await search_jobs(params)

    # If a resume_id is provided, fetch the resume for AI scoring
    resume_text = ""
    if body.resume_id:
        resume_record = _get_user_resume(auth.user_id, body.resume_id, auth.access_token)
        if resume_record:
            structured = resume_record.get("structured_data") or {}
            resume_text = _extract_resume_text(structured)

    scored: list[ScoredJob] = []
    for job in raw_jobs:
        score, reasons = _keyword_score(job, body.profile)
        jd = job.to_dict()

        ai_score: Optional[float] = None

        # AI resume scoring when resume is selected
        if resume_text:
            ai_score, ai_reason = await _ai_resume_score(jd, resume_text, auth.user_id)
            if ai_reason:
                reasons.insert(0, f"AI: {ai_reason}")
        elif score >= 40:
            # Fallback to profile-based explanation when no resume selected
            explanation = await _explain_match(jd, body.profile, auth.user_id)
            if explanation:
                reasons.insert(0, explanation)

        scored.append(ScoredJob(job=jd, score=score, ai_score=ai_score, match_reasons=reasons))

    # Sort by ai_score if available, otherwise by keyword score
    scored.sort(key=lambda s: s.ai_score if s.ai_score is not None else s.score, reverse=True)
    return JobMatchResponse(jobs=scored, total=len(scored))


@router.post("/explain", response_model=JobExplainResponse)
async def explain_job_match(
    body: JobExplainRequest,
    auth: AuthContext = Depends(get_auth_context),
):
    """Get AI explanation for a single job vs profile."""
    explanation = await _explain_match(body.job, body.profile, auth.user_id)
    if not explanation:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="LLM not configured — add your API key in Settings → AI Analysis first.",
        )
    return JobExplainResponse(explanation=explanation)


# ── Saved jobs endpoints ─────────────────────────────────────────────


class SaveJobRequest(BaseModel):
    job: dict = Field(..., description="Full job listing data to save")


@router.get("/saved")
async def list_saved(auth: AuthContext = Depends(get_auth_context)):
    """List all saved jobs for the current user."""
    return local_store.list_saved_jobs(auth.user_id)


@router.post("/saved")
async def save_job(
    body: SaveJobRequest,
    auth: AuthContext = Depends(get_auth_context),
):
    """Save a job posting."""
    return local_store.save_job(auth.user_id, body.job)


@router.delete("/saved/{job_id}")
async def unsave_job(
    job_id: str,
    auth: AuthContext = Depends(get_auth_context),
):
    """Remove a saved job."""
    deleted = local_store.delete_saved_job(auth.user_id, job_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Saved job not found")
    return {"ok": True}
