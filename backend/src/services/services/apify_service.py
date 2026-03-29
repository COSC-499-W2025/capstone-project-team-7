"""Apify integration service for scraping jobs from LinkedIn, Indeed, and Glassdoor.

Uses the Apify API to trigger actor runs for each platform and normalizes
the raw output into a flat dictionary matching the ``jobs`` DB table columns.
"""

from __future__ import annotations

import hashlib
import logging
import re
from typing import Any, Dict, List, Optional, Tuple

import httpx

logger = logging.getLogger(__name__)

APIFY_BASE_URL = "https://api.apify.com/v2"

ACTOR_IDS: Dict[str, str] = {
    "linkedin": "curious_coder~linkedin-jobs-scraper",
    "indeed": "misceres~indeed-scraper",
}

DEFAULT_SCRAPE_LIMIT = 25

# ---------------------------------------------------------------------------
# Known skills list used for keyword extraction from job descriptions.
# ---------------------------------------------------------------------------
KNOWN_SKILLS: List[str] = [
    "Python", "JavaScript", "TypeScript", "Java", "C++", "C#", "Go", "Rust",
    "Ruby", "PHP", "Swift", "Kotlin", "SQL", "HTML", "CSS",
    "React", "Angular", "Vue", "Next.js", "Node.js", "Express",
    "Django", "Flask", "FastAPI", "Spring", ".NET",
    "Docker", "Kubernetes", "AWS", "GCP", "Azure",
    "Git", "Linux", "PostgreSQL", "MongoDB", "Redis",
    "GraphQL", "REST", "TensorFlow", "PyTorch",
    "pandas", "NumPy", "Scikit-learn",
    "Agile", "Scrum", "CI/CD", "Terraform", "Jenkins",
]

# Pre-compile word-boundary patterns for each skill (case-insensitive).
_SKILL_PATTERNS: List[Tuple[re.Pattern, str]] = [
    (re.compile(rf"\b{re.escape(skill)}\b", re.IGNORECASE), skill)
    for skill in KNOWN_SKILLS
]


class ApifyServiceError(Exception):
    """Raised when an Apify API interaction fails."""


class ApifyService:
    """Stateless service that drives Apify actor runs and normalizes results."""

    def __init__(self) -> None:
        pass

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def scrape_jobs(
        self,
        apify_token: str,
        source: str,
        search_query: str,
        location: str | None = None,
        limit: int = DEFAULT_SCRAPE_LIMIT,
    ) -> dict:
        """Trigger an Apify actor run for *source* and return normalized jobs.

        The run is started **synchronously** (``waitForFinish=120``) so the
        caller does not need to poll for completion.

        Parameters
        ----------
        apify_token:
            Apify API token.
        source:
            One of ``"linkedin"``, ``"indeed"``, ``"glassdoor"``.
        search_query:
            Free-text job search query (e.g. ``"software engineer"``).
        location:
            Optional location filter (e.g. ``"Vancouver, BC"``).
        limit:
            Maximum number of results to request from the actor.

        Returns
        -------
        dict
            ``{"status": "completed", "jobs_found": N, "jobs": [...]}``.

        Raises
        ------
        ApifyServiceError
            On any HTTP or parsing error.
        """
        source_lower = source.lower()
        actor_id = ACTOR_IDS.get(source_lower)
        if actor_id is None:
            raise ApifyServiceError(
                f"Unsupported source '{source}'. "
                f"Must be one of: {', '.join(ACTOR_IDS)}"
            )

        run_input = self._build_actor_input(source_lower, search_query, location, limit)

        import asyncio

        async with httpx.AsyncClient(timeout=300.0) as client:
            # 1. Start the actor run (wait up to 180 s for it to finish).
            run_url = (
                f"{APIFY_BASE_URL}/acts/{actor_id}/runs"
                f"?token={apify_token}&waitForFinish=180"
            )
            logger.info(
                "Starting Apify actor run for %s (query=%r, location=%r, limit=%d)",
                source_lower, search_query, location, limit,
            )

            try:
                run_resp = await client.post(run_url, json=run_input)
                run_resp.raise_for_status()
            except httpx.HTTPStatusError as exc:
                raise ApifyServiceError(
                    f"Apify actor run request failed ({exc.response.status_code}): "
                    f"{exc.response.text}"
                ) from exc
            except httpx.RequestError as exc:
                raise ApifyServiceError(
                    f"Network error while contacting Apify: {exc}"
                ) from exc

            resp_json = run_resp.json()
            run_data = resp_json.get("data") or resp_json
            run_id = run_data.get("id", "")
            dataset_id = run_data.get("defaultDatasetId")
            run_status = run_data.get("status", "")
            logger.info(
                "Apify run started: id=%s status=%s dataset=%s",
                run_id, run_status, dataset_id,
            )

            # 2. If the run hasn't finished yet, poll until it does (up to 5 min).
            terminal_statuses = {"SUCCEEDED", "FAILED", "ABORTED", "TIMED-OUT"}
            if run_status not in terminal_statuses:
                if not run_id:
                    raise ApifyServiceError(
                        f"Apify run has no ID to poll (status={run_status})"
                    )
                logger.info("Run %s still %s, polling every 10s...", run_id, run_status)
                for attempt in range(30):  # 30 x 10s = 5 minutes max
                    await asyncio.sleep(10)
                    try:
                        poll_url = f"{APIFY_BASE_URL}/actor-runs/{run_id}?token={apify_token}"
                        poll_resp = await client.get(poll_url)
                        poll_resp.raise_for_status()
                        poll_json = poll_resp.json()
                        poll_data = poll_json.get("data") or poll_json
                        run_status = poll_data.get("status", "")
                        dataset_id = poll_data.get("defaultDatasetId") or dataset_id
                        logger.info("Run %s poll #%d: status=%s", run_id, attempt + 1, run_status)
                        if run_status in terminal_statuses:
                            break
                    except Exception:
                        logger.warning("Poll #%d failed for run %s", attempt + 1, run_id, exc_info=True)

            if run_status != "SUCCEEDED":
                raise ApifyServiceError(
                    f"Apify actor run did not succeed (status={run_status})"
                )

            if not dataset_id:
                raise ApifyServiceError(
                    "Apify response did not include a dataset ID"
                )

            # 3. Fetch the dataset items.
            dataset_url = (
                f"{APIFY_BASE_URL}/datasets/{dataset_id}/items"
                f"?token={apify_token}&format=json"
            )
            try:
                ds_resp = await client.get(dataset_url)
                ds_resp.raise_for_status()
            except httpx.HTTPStatusError as exc:
                raise ApifyServiceError(
                    f"Failed to fetch dataset ({exc.response.status_code}): "
                    f"{exc.response.text}"
                ) from exc
            except httpx.RequestError as exc:
                raise ApifyServiceError(
                    f"Network error fetching dataset: {exc}"
                ) from exc

            raw_items: List[dict] = ds_resp.json()

        # 3. Normalize each raw item.
        jobs: List[dict] = []
        for raw in raw_items:
            try:
                jobs.append(self.normalize_job(raw, source_lower))
            except Exception:
                logger.warning("Skipping un-normalizable item from %s", source_lower, exc_info=True)

        logger.info(
            "Apify scrape complete for %s: %d raw items -> %d normalized jobs",
            source_lower, len(raw_items), len(jobs),
        )

        return {
            "status": "completed",
            "jobs_found": len(jobs),
            "jobs": jobs,
        }

    # ------------------------------------------------------------------
    # Normalization
    # ------------------------------------------------------------------

    def normalize_job(self, raw: dict, source: str) -> dict:
        """Convert a raw Apify result dict into a flat dict matching the
        ``jobs`` DB table schema.

        Field mapping per source:

        * **LinkedIn**: title, companyName, location, salary, url,
          description, postedAt
        * **Indeed**: title, company, location, salary, url, description,
          positionName, jobType
        * **Glassdoor**: jobTitle, employerName, locationName, salary (or
          payPercentile90), url, description, postedDate
        """
        source = source.lower()

        if source == "linkedin":
            # Verified fields: title, companyName, location, link, descriptionText,
            # postedAt, employmentType, workRemoteAllowed, salary, seniorityLevel
            title = raw.get("title") or raw.get("standardizedTitle") or ""
            company = raw.get("companyName") or ""
            location = raw.get("location") or None
            url = raw.get("link") or raw.get("url") or None
            description = raw.get("descriptionText") or raw.get("description") or ""
            posted_at = raw.get("postedAt") or None
            job_type_raw = raw.get("employmentType") or ""
            is_remote = bool(raw.get("workRemoteAllowed")) or "remote" in (location or "").lower()
        elif source == "indeed":
            # Verified fields: positionName, company, location, url, description,
            # postedAt, jobType, salary, id, postingDateParsed
            title = raw.get("positionName") or raw.get("title") or ""
            company = raw.get("company") or ""
            location = raw.get("location") or None
            url = raw.get("url") or None
            description = raw.get("description") or ""
            posted_at = raw.get("postingDateParsed") or raw.get("postedAt") or None
            job_type_raw = ""
            # Indeed returns jobType as a list, e.g. ["Full-time"]
            jt = raw.get("jobType")
            if isinstance(jt, list) and jt:
                job_type_raw = jt[0]
            elif isinstance(jt, str):
                job_type_raw = jt
            is_remote = "remote" in (raw.get("location") or "").lower()
        else:
            raise ValueError(f"Unknown source: {source}")

        # Skip jobs with no meaningful title or company
        if not title.strip():
            title = "Untitled Position"
        if not company.strip():
            company = "Unknown Company"

        # Normalize job_type to match DB CHECK constraint
        job_type = self._normalize_job_type(job_type_raw)

        salary_min, salary_max, salary_currency = self._parse_salary(raw, source)
        skills = self.extract_skills_from_description(description)
        external_id = self._generate_external_id(raw, source)

        return {
            "external_id": external_id,
            "source": source,
            "title": title,
            "company": company,
            "location": location,
            "is_remote": is_remote,
            "description": description,
            "url": url,
            "salary_min": salary_min,
            "salary_max": salary_max,
            "salary_currency": salary_currency,
            "job_type": job_type,
            "posted_at": posted_at,
            "skills": skills,
        }

    @staticmethod
    def _normalize_job_type(raw_type: str) -> str | None:
        """Map raw job type strings to DB-allowed values or None."""
        _JOB_TYPE_MAP = {
            "full-time": "full-time", "full time": "full-time", "fulltime": "full-time",
            "ft": "full-time", "permanent": "full-time", "regular": "full-time",
            "part-time": "part-time", "part time": "part-time", "parttime": "part-time",
            "pt": "part-time",
            "internship": "internship", "intern": "internship",
            "contract": "contract", "contractor": "contract", "temporary": "contract",
            "temp": "contract", "freelance": "contract",
        }
        if not raw_type:
            return None
        return _JOB_TYPE_MAP.get(raw_type.lower().strip())

    # ------------------------------------------------------------------
    # Skills extraction
    # ------------------------------------------------------------------

    def extract_skills_from_description(self, description: str) -> list[str]:
        """Return a de-duplicated list of known skills found in *description*.

        Matching is **case-insensitive** and respects word boundaries so that,
        for example, ``"Express"`` does not match inside ``"expression"``.
        """
        if not description:
            return []

        found: list[str] = []
        seen: set[str] = set()
        for pattern, canonical in _SKILL_PATTERNS:
            if pattern.search(description):
                key = canonical.lower()
                if key not in seen:
                    seen.add(key)
                    found.append(canonical)
        return found

    # ------------------------------------------------------------------
    # Salary parsing
    # ------------------------------------------------------------------

    def _parse_salary(
        self, raw: dict, source: str
    ) -> tuple[int | None, int | None, str]:
        """Extract ``(salary_min, salary_max, salary_currency)`` from *raw*.

        Different platforms expose salary data in wildly different shapes so
        we try multiple keys and fall back to ``None`` gracefully.
        """
        salary_min: int | None = None
        salary_max: int | None = None
        currency: str = "USD"

        salary_raw = raw.get("salary") or ""

        # Glassdoor sometimes stores a numeric percentile value.
        if source == "glassdoor":
            pay90 = raw.get("payPercentile90")
            if pay90 is not None:
                try:
                    salary_max = int(float(pay90))
                except (ValueError, TypeError):
                    pass

            pay10 = raw.get("payPercentile10")
            if pay10 is not None:
                try:
                    salary_min = int(float(pay10))
                except (ValueError, TypeError):
                    pass

        # Attempt to parse a human-readable salary string like
        # "$80,000 - $120,000" or "CA$60K-CA$90K".
        if isinstance(salary_raw, str) and salary_raw.strip():
            cleaned = salary_raw.replace(",", "").replace("K", "000").replace("k", "000")

            # Try to detect currency symbol.
            if "CA$" in salary_raw or "CAD" in salary_raw.upper():
                currency = "CAD"
            elif "EUR" in salary_raw.upper() or "\u20ac" in salary_raw:
                currency = "EUR"
            elif "GBP" in salary_raw.upper() or "\u00a3" in salary_raw:
                currency = "GBP"

            numbers = re.findall(r"[\d]+(?:\.[\d]+)?", cleaned)
            numeric_values = []
            for n in numbers:
                try:
                    numeric_values.append(int(float(n)))
                except (ValueError, TypeError):
                    continue

            if len(numeric_values) >= 2:
                salary_min = min(numeric_values[0], numeric_values[1])
                salary_max = max(numeric_values[0], numeric_values[1])
            elif len(numeric_values) == 1:
                salary_min = numeric_values[0]
                salary_max = numeric_values[0]

        elif isinstance(salary_raw, (int, float)):
            salary_min = int(salary_raw)
            salary_max = int(salary_raw)

        return salary_min, salary_max, currency

    # ------------------------------------------------------------------
    # External-ID generation
    # ------------------------------------------------------------------

    def _generate_external_id(self, raw: dict, source: str) -> str:
        """Return a stable external ID for the job posting.

        We prefer the platform's own identifier when available and fall back
        to an MD5 hash of the URL.
        """
        # LinkedIn often includes an 'id' or 'jobId' field.
        platform_id = (
            raw.get("id")
            or raw.get("jobId")
            or raw.get("externalId")
            or raw.get("job_id")
        )
        if platform_id:
            return f"{source}_{platform_id}"

        url = raw.get("url") or ""
        if url:
            url_hash = hashlib.md5(url.encode()).hexdigest()
            return f"{source}_{url_hash}"

        # Last resort: hash the whole raw dict.
        blob = str(sorted(raw.items())).encode()
        return f"{source}_{hashlib.md5(blob).hexdigest()}"

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _build_actor_input(
        source: str,
        search_query: str,
        location: str | None,
        limit: int,
    ) -> dict:
        """Build the JSON input payload for the Apify actor.

        Input schemas verified against actual Apify actor APIs:
        - LinkedIn (curious_coder): requires ``urls`` (LinkedIn search URLs)
        - Indeed (misceres): accepts ``position``, ``location``, ``maxItems``
        """
        from urllib.parse import quote_plus

        if source == "linkedin":
            # Build a LinkedIn jobs search URL from query + location
            params = f"keywords={quote_plus(search_query)}"
            if location:
                params += f"&location={quote_plus(location)}"
            search_url = f"https://www.linkedin.com/jobs/search/?{params}"
            return {
                "urls": [search_url],
                "maxResults": limit,
            }

        if source == "indeed":
            actor_input: Dict[str, Any] = {
                "position": search_query,
                "maxItems": limit,
            }
            if location:
                actor_input["location"] = location
            return actor_input

        raise ApifyServiceError(f"Cannot build input for unknown source: {source}")
