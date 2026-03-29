"""Job Board API routes -- scraping, listing, saving, matching."""

from __future__ import annotations

import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Optional
from urllib.parse import quote

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, status

from api.dependencies import AuthContext, get_auth_context
from api.models.job_models import (
    AiMatchResponse,
    JobListResponse,
    JobResponse,
    ScrapeRequest,
    ScrapeResponse,
    UpdateJobStatusRequest,
    UserJobResponse,
)
from api.settings_routes import get_or_hydrate_llm_client
from services.services.apify_service import ApifyService
# EncryptionService no longer needed — Apify token comes from env var
from services.services.job_matching_service import JobMatchingService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/jobs", tags=["Jobs"])

_apify_service = ApifyService()
_matching_service = JobMatchingService()


# ---------------------------------------------------------------------------
# Supabase helpers
# ---------------------------------------------------------------------------


def _supabase_headers(access_token: str) -> dict[str, str]:
    key = (
        os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        or os.getenv("SUPABASE_KEY")
        or os.getenv("SUPABASE_ANON_KEY", "")
    )
    return {
        "Authorization": f"Bearer {access_token}",
        "apikey": key,
        "Content-Type": "application/json",
    }


def _supabase_rest_url() -> str:
    base = os.getenv("SUPABASE_URL", "")
    if not base:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "configuration_error", "message": "SUPABASE_URL not set"},
        )
    return f"{base}/rest/v1"


# ---------------------------------------------------------------------------
# Token / skills helpers
# ---------------------------------------------------------------------------


def _get_apify_token() -> str:
    """Read the Apify API token from the APIFY_API_TOKEN environment variable."""
    token = os.getenv("APIFY_API_TOKEN", "")
    if not token:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": "no_apify_token",
                "message": "APIFY_API_TOKEN environment variable is not set.",
            },
        )
    return token


async def _get_user_skills(user_id: str, access_token: str) -> list[str]:
    """Aggregate skills from a user's projects (languages + scan_data)."""
    rest = _supabase_rest_url()
    url = f"{rest}/projects?user_id=eq.{user_id}&select=languages,scan_data"
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(url, headers=_supabase_headers(access_token))

    if resp.status_code >= 400:
        return []

    skills: set[str] = set()
    for proj in resp.json():
        for lang in proj.get("languages") or []:
            skills.add(lang.lower())
        scan = proj.get("scan_data") or {}
        if isinstance(scan, dict):
            sa = scan.get("skills_analysis") or {}
            for cat_skills in (sa.get("skills_by_category") or {}).values():
                for s in cat_skills:
                    if isinstance(s, dict) and "name" in s:
                        skills.add(s["name"].lower())
    return list(skills)


# ---------------------------------------------------------------------------
# POST /api/jobs/scrape
# ---------------------------------------------------------------------------


@router.post("/scrape", response_model=ScrapeResponse)
async def scrape_jobs(
    body: ScrapeRequest,
    auth: AuthContext = Depends(get_auth_context),
):
    """Trigger an Apify scrape, upsert results, and compute keyword matches."""
    # 1. Get Apify token from environment
    apify_token = _get_apify_token()

    # 2. Run scrape
    try:
        scrape_result = await _apify_service.scrape_jobs(
            apify_token=apify_token,
            source=body.source,
            search_query=body.search_query,
            location=body.location,
            limit=body.limit,
        )
        scraped_jobs = scrape_result.get("jobs", [])
    except Exception as exc:
        logger.error(f"Apify scrape failed for user {auth.user_id}: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"code": "scrape_error", "message": f"Scrape failed: {exc}"},
        )

    rest = _supabase_rest_url()
    headers = _supabase_headers(auth.access_token)

    # 3. Upsert jobs into the jobs table
    jobs_new = 0
    for job in scraped_jobs:
        upsert_headers = {**headers, "Prefer": "return=representation,resolution=merge-duplicates"}
        upsert_url = f"{rest}/jobs?on_conflict=external_id,source"
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(upsert_url, json=job, headers=upsert_headers)
        if resp.status_code < 300:
            rows = resp.json()
            if rows:
                # Track whether the row was freshly created (heuristic: created_at ~ now)
                jobs_new += 1

    # 4. Record the scrape run
    run_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    actor_id = {"linkedin": "curious_coder~linkedin-jobs-scraper", "indeed": "misceres~indeed-scraper"}.get(body.source, "unknown")
    scrape_run = {
        "id": run_id,
        "user_id": auth.user_id,
        "source": body.source,
        "actor_id": actor_id,
        "search_query": body.search_query,
        "location": body.location,
        "status": "completed",
        "jobs_found": len(scraped_jobs),
        "jobs_new": jobs_new,
        "started_at": now,
        "completed_at": now,
    }
    run_headers = {**headers, "Prefer": "return=representation"}
    async with httpx.AsyncClient(timeout=10) as client:
        await client.post(f"{rest}/job_scrape_runs", json=scrape_run, headers=run_headers)

    # 5. Fetch user skills for keyword matching
    user_skills = await _get_user_skills(auth.user_id, auth.access_token)

    # 6. Compute keyword match for each scraped job and auto-save as user_jobs
    if user_skills:
        for job in scraped_jobs:
            job_skills = [s.lower() for s in (job.get("skills") or [])]
            match_result = _matching_service.compute_keyword_match(user_skills, job_skills)
            score = match_result["score"]
            matched = match_result["matched_skills"]
            missing = match_result["missing_skills"]

            # Fetch the job id from DB by external_id + source
            lookup_url = (
                f"{rest}/jobs?external_id=eq.{job.get('external_id')}"
                f"&source=eq.{job.get('source')}&select=id"
            )
            async with httpx.AsyncClient(timeout=10) as client:
                lookup_resp = await client.get(lookup_url, headers=headers)
            if lookup_resp.status_code >= 400 or not lookup_resp.json():
                continue
            db_job_id = lookup_resp.json()[0]["id"]

            # Upsert user_jobs row with keyword score
            uj_payload = {
                "id": str(uuid.uuid4()),
                "user_id": auth.user_id,
                "job_id": db_job_id,
                "status": "saved",
                "keyword_match_score": score,
                "matched_skills": matched,
                "missing_skills": missing,
                "created_at": now,
                "updated_at": now,
            }
            uj_headers = {**headers, "Prefer": "return=representation,resolution=merge-duplicates"}
            uj_url = f"{rest}/user_jobs?on_conflict=user_id,job_id"
            async with httpx.AsyncClient(timeout=10) as client:
                await client.post(uj_url, json=uj_payload, headers=uj_headers)

    return ScrapeResponse(
        run_id=run_id,
        source=body.source,
        status="completed",
        jobs_found=len(scraped_jobs),
        jobs_new=jobs_new,
    )


# ---------------------------------------------------------------------------
# GET /api/jobs/saved
# ---------------------------------------------------------------------------


@router.get("/saved", response_model=JobListResponse)
async def list_saved_jobs(
    auth: AuthContext = Depends(get_auth_context),
    status_filter: Optional[str] = Query(None, alias="status"),
):
    """List the current user's saved/applied jobs with optional status filter."""
    rest = _supabase_rest_url()
    url = f"{rest}/user_jobs?user_id=eq.{auth.user_id}&select=*,jobs(*)&order=created_at.desc"
    if status_filter:
        url += f"&status=eq.{quote(status_filter, safe='')}"

    headers = {**_supabase_headers(auth.access_token), "Prefer": "count=exact"}
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(url, headers=headers)

    if resp.status_code >= 400:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"code": "upstream_error", "message": "Failed to fetch saved jobs"},
        )

    rows = resp.json()
    total = _parse_content_range_total(resp) or len(rows)
    jobs = [_map_user_job_row(r) for r in rows]
    return JobListResponse(count=total, jobs=jobs)


# ---------------------------------------------------------------------------
# GET /api/jobs/scrape-history
# ---------------------------------------------------------------------------


@router.get("/scrape-history")
async def scrape_history(auth: AuthContext = Depends(get_auth_context)):
    """Return recent scrape runs for the authenticated user."""
    rest = _supabase_rest_url()
    url = f"{rest}/job_scrape_runs?user_id=eq.{auth.user_id}&order=started_at.desc&limit=50"
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(url, headers=_supabase_headers(auth.access_token))

    if resp.status_code >= 400:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"code": "upstream_error", "message": "Failed to fetch scrape history"},
        )
    return resp.json()


# ---------------------------------------------------------------------------
# GET /api/jobs/
# ---------------------------------------------------------------------------


@router.get("/", response_model=JobListResponse)
async def list_jobs(
    auth: AuthContext = Depends(get_auth_context),
    source: Optional[str] = None,
    location: Optional[str] = None,
    is_remote: Optional[bool] = None,
    job_type: Optional[str] = None,
    experience_level: Optional[str] = None,
    salary_min: Optional[int] = None,
    salary_max: Optional[int] = None,
    skills: Optional[str] = None,
    posted_after: Optional[str] = None,
    search: Optional[str] = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
):
    """List jobs with filtering and pagination. Joins with user_jobs for this user."""
    rest = _supabase_rest_url()

    # Build query against the jobs table; left-join user_jobs for this user
    url = f"{rest}/jobs?select=*,user_jobs!left(*)&order=posted_at.desc.nullslast"

    # Apply filters (URL-encode user inputs to prevent PostgREST injection)
    if source:
        url += f"&source=eq.{quote(source, safe='')}"
    if location:
        url += f"&location=ilike.*{quote(location, safe='')}*"
    if is_remote is not None:
        url += f"&is_remote=is.{str(is_remote).lower()}"
    if job_type:
        url += f"&job_type=eq.{quote(job_type, safe='')}"
    if experience_level:
        url += f"&experience_level=eq.{quote(experience_level, safe='')}"
    if salary_min is not None:
        url += f"&salary_max=gte.{salary_min}"
    if salary_max is not None:
        url += f"&salary_min=lte.{salary_max}"
    if posted_after:
        url += f"&posted_at=gte.{quote(posted_after, safe='')}"
    if search:
        q = quote(search, safe='')
        url += f"&or=(title.ilike.*{q}*,company.ilike.*{q}*)"
    if skills:
        # Filter jobs whose skills array overlaps with requested skills
        skill_list = [s.strip() for s in skills.split(",") if s.strip()]
        if skill_list:
            skill_val = "{" + ",".join(quote(s, safe='') for s in skill_list) + "}"
            url += f"&skills=ov.{skill_val}"

    # Filter user_jobs join to this user only
    url += f"&user_jobs.user_id=eq.{auth.user_id}"

    # Pagination via Range header
    offset = (page - 1) * page_size
    range_end = offset + page_size - 1
    headers = {
        **_supabase_headers(auth.access_token),
        "Prefer": "count=exact",
        "Range": f"{offset}-{range_end}",
    }

    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(url, headers=headers)

    if resp.status_code >= 400:
        logger.warning(f"Jobs list query failed: {resp.status_code} {resp.text}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"code": "upstream_error", "message": "Failed to fetch jobs"},
        )

    rows = resp.json()
    total = _parse_content_range_total(resp) or len(rows)

    # Map rows: the join comes from the jobs perspective, so we pivot
    jobs: list[UserJobResponse] = []
    for row in rows:
        user_jobs_list = row.pop("user_jobs", []) or []
        uj = user_jobs_list[0] if user_jobs_list else None

        job_data = JobResponse(**{k: v for k, v in row.items() if k in JobResponse.model_fields})

        if uj:
            jobs.append(
                UserJobResponse(
                    id=uj.get("id", ""),
                    user_id=uj.get("user_id", auth.user_id),
                    job_id=row["id"],
                    status=uj.get("status", "saved"),
                    keyword_match_score=uj.get("keyword_match_score"),
                    ai_match_score=uj.get("ai_match_score"),
                    ai_match_summary=uj.get("ai_match_summary"),
                    matched_skills=uj.get("matched_skills") or [],
                    missing_skills=uj.get("missing_skills") or [],
                    notes=uj.get("notes"),
                    applied_at=uj.get("applied_at"),
                    created_at=uj.get("created_at"),
                    updated_at=uj.get("updated_at"),
                    job=job_data,
                )
            )
        else:
            # No user_jobs row yet -- present as unsaved
            jobs.append(
                UserJobResponse(
                    id="",
                    user_id=auth.user_id,
                    job_id=row["id"],
                    status="unsaved",
                    job=job_data,
                )
            )

    return JobListResponse(count=total, jobs=jobs)


# ---------------------------------------------------------------------------
# GET /api/jobs/{job_id}
# ---------------------------------------------------------------------------


@router.get("/{job_id}", response_model=UserJobResponse)
async def get_job(
    job_id: str,
    auth: AuthContext = Depends(get_auth_context),
):
    """Get a single job with the user's saved state (if any)."""
    rest = _supabase_rest_url()
    headers = _supabase_headers(auth.access_token)

    # Fetch the job
    url = f"{rest}/jobs?id=eq.{job_id}&select=*"
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(url, headers=headers)

    if resp.status_code >= 400 or not resp.json():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "not_found", "message": "Job not found"},
        )

    job_row = resp.json()[0]
    job_data = JobResponse(**{k: v for k, v in job_row.items() if k in JobResponse.model_fields})

    # Fetch user_jobs for this user + job
    uj_url = f"{rest}/user_jobs?user_id=eq.{auth.user_id}&job_id=eq.{job_id}&select=*"
    async with httpx.AsyncClient(timeout=10) as client:
        uj_resp = await client.get(uj_url, headers=headers)

    uj = uj_resp.json()[0] if (uj_resp.status_code < 400 and uj_resp.json()) else None

    if uj:
        return UserJobResponse(
            id=uj["id"],
            user_id=uj["user_id"],
            job_id=job_id,
            status=uj.get("status", "saved"),
            keyword_match_score=uj.get("keyword_match_score"),
            ai_match_score=uj.get("ai_match_score"),
            ai_match_summary=uj.get("ai_match_summary"),
            matched_skills=uj.get("matched_skills") or [],
            missing_skills=uj.get("missing_skills") or [],
            notes=uj.get("notes"),
            applied_at=uj.get("applied_at"),
            created_at=uj.get("created_at"),
            updated_at=uj.get("updated_at"),
            job=job_data,
        )

    return UserJobResponse(
        id="",
        user_id=auth.user_id,
        job_id=job_id,
        status="unsaved",
        job=job_data,
    )


# ---------------------------------------------------------------------------
# POST /api/jobs/{job_id}/save
# ---------------------------------------------------------------------------


@router.post("/{job_id}/save", response_model=UserJobResponse)
async def save_job(
    job_id: str,
    auth: AuthContext = Depends(get_auth_context),
):
    """Save a job for the user. Computes keyword match score on save."""
    rest = _supabase_rest_url()
    headers = _supabase_headers(auth.access_token)

    # Verify the job exists and get its skills
    job_url = f"{rest}/jobs?id=eq.{job_id}&select=*"
    async with httpx.AsyncClient(timeout=10) as client:
        job_resp = await client.get(job_url, headers=headers)

    if job_resp.status_code >= 400 or not job_resp.json():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "not_found", "message": "Job not found"},
        )

    job_row = job_resp.json()[0]

    # Compute keyword match
    user_skills = await _get_user_skills(auth.user_id, auth.access_token)
    job_skills = [s.lower() for s in (job_row.get("skills") or [])]
    keyword_score = None
    matched_skills: list[str] = []
    missing_skills: list[str] = []
    if user_skills:
        match_result = _matching_service.compute_keyword_match(user_skills, job_skills)
        keyword_score = match_result["score"]
        matched_skills = match_result["matched_skills"]
        missing_skills = match_result["missing_skills"]

    now = datetime.now(timezone.utc).isoformat()
    payload = {
        "id": str(uuid.uuid4()),
        "user_id": auth.user_id,
        "job_id": job_id,
        "status": "saved",
        "keyword_match_score": keyword_score,
        "matched_skills": matched_skills,
        "missing_skills": missing_skills,
        "created_at": now,
        "updated_at": now,
    }

    upsert_headers = {**headers, "Prefer": "return=representation,resolution=merge-duplicates"}
    upsert_url = f"{rest}/user_jobs?on_conflict=user_id,job_id"
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.post(upsert_url, json=payload, headers=upsert_headers)

    if resp.status_code >= 400:
        logger.warning(f"Failed to save job: {resp.status_code} {resp.text}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"code": "upstream_error", "message": "Failed to save job"},
        )

    row = resp.json()[0] if resp.json() else payload
    job_data = JobResponse(**{k: v for k, v in job_row.items() if k in JobResponse.model_fields})

    return UserJobResponse(
        id=row.get("id", payload["id"]),
        user_id=auth.user_id,
        job_id=job_id,
        status=row.get("status", "saved"),
        keyword_match_score=row.get("keyword_match_score"),
        matched_skills=row.get("matched_skills") or [],
        missing_skills=row.get("missing_skills") or [],
        created_at=row.get("created_at"),
        updated_at=row.get("updated_at"),
        job=job_data,
    )


# ---------------------------------------------------------------------------
# DELETE /api/jobs/{job_id}/save
# ---------------------------------------------------------------------------


@router.delete("/{job_id}/save")
async def unsave_job(
    job_id: str,
    auth: AuthContext = Depends(get_auth_context),
):
    """Remove the user's saved record for a job."""
    rest = _supabase_rest_url()
    url = f"{rest}/user_jobs?user_id=eq.{auth.user_id}&job_id=eq.{job_id}"
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.delete(url, headers=_supabase_headers(auth.access_token))

    if resp.status_code >= 400:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"code": "upstream_error", "message": "Failed to unsave job"},
        )
    return {"ok": True, "message": "Job unsaved"}


# ---------------------------------------------------------------------------
# PATCH /api/jobs/{job_id}/status
# ---------------------------------------------------------------------------


@router.patch("/{job_id}/status", response_model=UserJobResponse)
async def update_job_status(
    job_id: str,
    body: UpdateJobStatusRequest,
    auth: AuthContext = Depends(get_auth_context),
):
    """Update the status of a saved job (e.g. saved -> applied -> interviewing)."""
    rest = _supabase_rest_url()
    headers = _supabase_headers(auth.access_token)

    now = datetime.now(timezone.utc).isoformat()
    patch_payload: dict = {
        "status": body.status,
        "updated_at": now,
    }
    if body.notes is not None:
        patch_payload["notes"] = body.notes
    if body.applied_at is not None:
        patch_payload["applied_at"] = body.applied_at
    elif body.status == "applied":
        # Auto-set applied_at if transitioning to applied
        patch_payload["applied_at"] = now

    url = f"{rest}/user_jobs?user_id=eq.{auth.user_id}&job_id=eq.{job_id}"
    patch_headers = {**headers, "Prefer": "return=representation"}
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.patch(url, json=patch_payload, headers=patch_headers)

    if resp.status_code >= 400:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"code": "upstream_error", "message": "Failed to update job status"},
        )

    rows = resp.json()
    if not rows:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "not_found", "message": "No saved job found to update"},
        )

    row = rows[0]

    # Fetch the job data for the response
    job_data = await _fetch_job_response(job_id, headers, rest)

    return UserJobResponse(
        id=row["id"],
        user_id=row["user_id"],
        job_id=job_id,
        status=row["status"],
        keyword_match_score=row.get("keyword_match_score"),
        ai_match_score=row.get("ai_match_score"),
        ai_match_summary=row.get("ai_match_summary"),
        matched_skills=row.get("matched_skills") or [],
        missing_skills=row.get("missing_skills") or [],
        notes=row.get("notes"),
        applied_at=row.get("applied_at"),
        created_at=row.get("created_at"),
        updated_at=row.get("updated_at"),
        job=job_data,
    )


# ---------------------------------------------------------------------------
# POST /api/jobs/{job_id}/ai-match
# ---------------------------------------------------------------------------


@router.post("/{job_id}/ai-match", response_model=AiMatchResponse)
async def ai_match_job(
    job_id: str,
    auth: AuthContext = Depends(get_auth_context),
):
    """Compute an AI-powered match score between the user's profile and a job."""
    rest = _supabase_rest_url()
    headers = _supabase_headers(auth.access_token)

    # 1. Get LLM client
    llm_client = await get_or_hydrate_llm_client(auth.user_id, auth.access_token)
    if llm_client is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "no_llm_key",
                "message": "No OpenAI API key configured. Add one in Settings.",
            },
        )

    # 2. Fetch job description
    job_url = f"{rest}/jobs?id=eq.{job_id}&select=*"
    async with httpx.AsyncClient(timeout=10) as client:
        job_resp = await client.get(job_url, headers=headers)

    if job_resp.status_code >= 400 or not job_resp.json():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "not_found", "message": "Job not found"},
        )

    job_row = job_resp.json()[0]

    # 3. Fetch user skills for context
    user_skills = await _get_user_skills(auth.user_id, auth.access_token)

    # 4. Compute AI match
    try:
        result = await _matching_service.compute_ai_match(
            llm_client=llm_client,
            user_skills=user_skills,
            job_description=job_row.get("description", ""),
            job_title=job_row.get("title", ""),
            job_company=job_row.get("company", ""),
        )
    except Exception as exc:
        logger.error(f"AI match failed for user {auth.user_id}, job {job_id}: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"code": "ai_match_error", "message": f"AI matching failed: {exc}"},
        )

    # 5. Persist results to user_jobs
    now = datetime.now(timezone.utc).isoformat()
    patch_payload = {
        "ai_match_score": result.get("score", 0.0),
        "ai_match_summary": result.get("summary", ""),
        "matched_skills": result.get("matched_skills", []),
        "missing_skills": result.get("missing_skills", []),
        "updated_at": now,
    }
    uj_url = f"{rest}/user_jobs?user_id=eq.{auth.user_id}&job_id=eq.{job_id}"
    patch_headers = {**headers, "Prefer": "return=representation"}
    async with httpx.AsyncClient(timeout=10) as client:
        await client.patch(uj_url, json=patch_payload, headers=patch_headers)

    return AiMatchResponse(
        job_id=job_id,
        ai_match_score=result.get("score", 0.0),
        ai_match_summary=result.get("summary", ""),
        matched_skills=result.get("matched_skills", []),
        missing_skills=result.get("missing_skills", []),
    )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


async def _fetch_job_response(
    job_id: str, headers: dict[str, str], rest: str
) -> Optional[JobResponse]:
    """Fetch a single job row and return it as a JobResponse (or None)."""
    url = f"{rest}/jobs?id=eq.{job_id}&select=*"
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(url, headers=headers)

    if resp.status_code >= 400 or not resp.json():
        return None

    row = resp.json()[0]
    return JobResponse(**{k: v for k, v in row.items() if k in JobResponse.model_fields})


def _map_user_job_row(row: dict) -> UserJobResponse:
    """Map a user_jobs row (with nested jobs join) to UserJobResponse."""
    job_data_raw = row.get("jobs") or row.get("job")
    job_data = None
    if job_data_raw and isinstance(job_data_raw, dict):
        job_data = JobResponse(
            **{k: v for k, v in job_data_raw.items() if k in JobResponse.model_fields}
        )

    return UserJobResponse(
        id=row.get("id", ""),
        user_id=row.get("user_id", ""),
        job_id=row.get("job_id", ""),
        status=row.get("status", "saved"),
        keyword_match_score=row.get("keyword_match_score"),
        ai_match_score=row.get("ai_match_score"),
        ai_match_summary=row.get("ai_match_summary"),
        matched_skills=row.get("matched_skills") or [],
        missing_skills=row.get("missing_skills") or [],
        notes=row.get("notes"),
        applied_at=row.get("applied_at"),
        created_at=row.get("created_at"),
        updated_at=row.get("updated_at"),
        job=job_data,
    )


def _parse_content_range_total(resp: httpx.Response) -> Optional[int]:
    """Extract the total count from a PostgREST Content-Range header (e.g. '0-19/142')."""
    cr = resp.headers.get("content-range", "")
    if "/" in cr:
        try:
            return int(cr.split("/")[1])
        except (ValueError, IndexError):
            return None
    return None
