"""Job search client — thin wrapper around the JSearch API (RapidAPI).

JSearch aggregates listings from Indeed, LinkedIn, Glassdoor and others and
returns direct URLs to the original postings.

Docs: https://rapidapi.com/letscrape-6bRBa3QguO5/api/jsearch
Free tier: 200 requests / month.

Set RAPIDAPI_KEY in .env to enable live search.
When the key is missing the client returns mock results so the UI
is still fully functional during development.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field, asdict
from typing import List, Optional

import httpx

logger = logging.getLogger(__name__)

JSEARCH_BASE = "https://jsearch.p.rapidapi.com"


@dataclass
class JobListing:
    """Normalised representation of a single job posting."""

    id: str
    title: str
    company: str
    location: str
    description: str
    salary_min: Optional[float] = None
    salary_max: Optional[float] = None
    url: str = ""
    created: str = ""
    contract_type: str = ""
    category: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class JobSearchParams:
    """Parameters accepted by the search endpoint."""

    keywords: str = ""
    location: str = ""
    remote_only: bool = False
    salary_min: Optional[int] = None
    category: str = ""
    results_per_page: int = 10
    page: int = 1
    country: str = "ca"


# ── Mock data for offline development ────────────────────────────────

_MOCK_JOBS: List[JobListing] = [
    JobListing(
        id="mock-1",
        title="Full-Stack Developer",
        company="TechCorp Inc.",
        location="Vancouver, BC",
        description="Build and maintain web applications using React, Node.js, and PostgreSQL. Collaborate with designers and product managers in an agile team.",
        salary_min=75000,
        salary_max=95000,
        url="https://www.indeed.com/q-full-stack-developer-l-vancouver-jobs.html",
        created="2026-03-25",
        contract_type="permanent",
        category="IT Jobs",
    ),
    JobListing(
        id="mock-2",
        title="Backend Engineer — Python",
        company="DataFlow Systems",
        location="Toronto, ON (Remote)",
        description="Design scalable microservices with FastAPI, PostgreSQL, and Redis. Strong testing culture; CI/CD with GitHub Actions.",
        salary_min=85000,
        salary_max=110000,
        url="https://www.indeed.com/q-backend-python-engineer-l-toronto-jobs.html",
        created="2026-03-24",
        contract_type="permanent",
        category="IT Jobs",
    ),
    JobListing(
        id="mock-3",
        title="Junior Software Developer",
        company="GreenLeaf Software",
        location="Kelowna, BC",
        description="Entry-level role working on internal tools. Python, JavaScript, and SQL experience preferred. Great mentorship programme.",
        salary_min=55000,
        salary_max=70000,
        url="https://www.indeed.com/q-junior-software-developer-l-kelowna-jobs.html",
        created="2026-03-23",
        contract_type="permanent",
        category="IT Jobs",
    ),
    JobListing(
        id="mock-4",
        title="DevOps / Cloud Engineer",
        company="CloudNine Hosting",
        location="Remote — Canada",
        description="Manage AWS infrastructure using Terraform and Kubernetes. On-call rotation, incident response, and automation scripting.",
        salary_min=90000,
        salary_max=120000,
        url="https://www.indeed.com/q-devops-cloud-engineer-l-canada-jobs.html",
        created="2026-03-22",
        contract_type="contract",
        category="IT Jobs",
    ),
    JobListing(
        id="mock-5",
        title="Front-End React Developer",
        company="PixelPerfect Design",
        location="Montreal, QC (Hybrid)",
        description="Implement pixel-perfect UIs from Figma mocks. React, TypeScript, Tailwind CSS, and accessibility best practices.",
        salary_min=70000,
        salary_max=90000,
        url="https://www.indeed.com/q-react-developer-l-montreal-jobs.html",
        created="2026-03-21",
        contract_type="permanent",
        category="IT Jobs",
    ),
]


def _filter_mock_jobs(params: JobSearchParams) -> List[JobListing]:
    """Basic keyword filter over mock data."""
    kw = params.keywords.lower()
    if not kw:
        return _MOCK_JOBS[: params.results_per_page]
    results = []
    for job in _MOCK_JOBS:
        text = f"{job.title} {job.description} {job.company} {job.category}".lower()
        if any(word in text for word in kw.split()):
            results.append(job)
    return results[: params.results_per_page]


# ── Live JSearch client ──────────────────────────────────────────────


def _jsearch_available() -> bool:
    return bool(os.getenv("RAPIDAPI_KEY"))


def _parse_jsearch_result(raw: dict) -> JobListing:
    """Convert a JSearch result dict into our normalised dataclass."""
    city = raw.get("job_city", "") or ""
    state = raw.get("job_state", "") or ""
    country = raw.get("job_country", "") or ""
    parts = [p for p in (city, state, country) if p]
    location = ", ".join(parts) or "Unknown"

    return JobListing(
        id=str(raw.get("job_id", "")),
        title=raw.get("job_title", ""),
        company=raw.get("employer_name", "Unknown"),
        location=location,
        description=raw.get("job_description", ""),
        salary_min=raw.get("job_min_salary"),
        salary_max=raw.get("job_max_salary"),
        url=raw.get("job_apply_link", ""),
        created=raw.get("job_posted_at_datetime_utc", ""),
        contract_type=raw.get("job_employment_type", ""),
        category=raw.get("job_job_title", ""),
    )


async def search_jobs(params: JobSearchParams) -> List[JobListing]:
    """Search JSearch for jobs, falling back to mock data when key is absent."""

    if not _jsearch_available():
        logger.info("RAPIDAPI_KEY not set — returning mock jobs")
        return _filter_mock_jobs(params)

    api_key = os.environ["RAPIDAPI_KEY"]

    query = params.keywords
    if params.location:
        query += f" in {params.location}"

    if not query.strip():
        logger.info("Empty search query — returning empty results")
        return []

    query_params: dict = {
        "query": query,
        "page": str(params.page),
        "num_pages": "1",
        "country": params.country or "ca",
        "date_posted": "all",
    }
    if params.remote_only:
        query_params["remote_jobs_only"] = "true"

    headers = {
        "x-rapidapi-host": "jsearch.p.rapidapi.com",
        "x-rapidapi-key": api_key,
    }

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                f"{JSEARCH_BASE}/search",
                params=query_params,
                headers=headers,
            )
            resp.raise_for_status()
            data = resp.json()
            results = data.get("data", [])
            return [_parse_jsearch_result(r) for r in results[:params.results_per_page]]
    except httpx.HTTPError as exc:
        logger.error("JSearch request failed: %s", exc)
        raise RuntimeError(f"Job search request failed: {exc}") from exc
