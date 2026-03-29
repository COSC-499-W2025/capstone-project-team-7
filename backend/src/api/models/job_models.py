"""Pydantic models for the Job Board API request/response contracts."""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Core resource representations
# ---------------------------------------------------------------------------


class JobResponse(BaseModel):
    id: str
    external_id: str
    source: str  # linkedin | indeed | glassdoor
    title: str
    company: str
    location: Optional[str] = None
    is_remote: bool = False
    job_type: Optional[str] = None
    experience_level: Optional[str] = None
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    salary_currency: str = "USD"
    description: Optional[str] = None
    url: Optional[str] = None
    company_logo_url: Optional[str] = None
    skills: List[str] = []
    posted_at: Optional[str] = None
    scraped_at: Optional[str] = None


class UserJobResponse(BaseModel):
    id: str
    user_id: str
    job_id: str
    status: str
    keyword_match_score: Optional[float] = None
    ai_match_score: Optional[float] = None
    ai_match_summary: Optional[str] = None
    matched_skills: List[str] = []
    missing_skills: List[str] = []
    notes: Optional[str] = None
    applied_at: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    job: Optional[JobResponse] = None


class JobListResponse(BaseModel):
    count: int
    jobs: List[UserJobResponse]


# ---------------------------------------------------------------------------
# Scrape
# ---------------------------------------------------------------------------


class ScrapeRequest(BaseModel):
    source: str = Field(..., pattern="^(linkedin|indeed)$")
    search_query: str = Field(..., min_length=1, max_length=200)
    location: Optional[str] = None
    limit: int = Field(default=25, ge=1, le=100)


class ScrapeResponse(BaseModel):
    run_id: str
    source: str
    status: str
    jobs_found: int
    jobs_new: int


# ---------------------------------------------------------------------------
# Job status management
# ---------------------------------------------------------------------------


class UpdateJobStatusRequest(BaseModel):
    status: str = Field(..., pattern="^(saved|applied|interviewing|offer|rejected)$")
    notes: Optional[str] = None
    applied_at: Optional[str] = None


# ---------------------------------------------------------------------------
# AI matching
# ---------------------------------------------------------------------------


class AiMatchRequest(BaseModel):
    job_id: str


class AiMatchResponse(BaseModel):
    job_id: str
    ai_match_score: float
    ai_match_summary: str
    matched_skills: List[str]
    missing_skills: List[str]
