"""API skeleton routes aligned to docs/api-spec.yaml.

These routes provide stubbed responses and in-memory placeholders so the
Electron/Next clients can develop against stable contracts while the
backend implementations are completed. Replace stub logic with real
services incrementally.
"""

from __future__ import annotations

import logging
import os
import sys
import threading
from datetime import datetime
from enum import Enum
from pathlib import Path
import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, BackgroundTasks, Body, Depends, File, Header, HTTPException, UploadFile, status
from pydantic import BaseModel, Field

from api.dependencies import AuthContext, get_auth_context

# Add parent directory to path for absolute imports (needed for lazy imports in background tasks)
sys.path.insert(0, str(Path(__file__).parent.parent))

logger = logging.getLogger(__name__)

# Configuration constants
MAX_FILES_IN_RESPONSE = 100  # Maximum number of files to include in scan response


def _now_iso() -> str:
    return datetime.utcnow().isoformat() + "Z"


class JobState(str, Enum):
    queued = "queued"
    running = "running"
    succeeded = "succeeded"
    failed = "failed"
    canceled = "canceled"


class ErrorResponse(BaseModel):
    code: str
    message: str
    details: Optional[Dict[str, Any]] = None


class Pagination(BaseModel):
    limit: int = 20
    offset: int = 0
    total: int = 0


class ConsentStatus(BaseModel):
    user_id: str
    data_access: bool
    external_services: bool
    updated_at: str


class Upload(BaseModel):
    upload_id: str
    filename: Optional[str] = None
    size_bytes: Optional[int] = None
    status: str
    created_at: str
    error: Optional[ErrorResponse] = None


class ParseOptions(BaseModel):
    profile_id: Optional[str] = None
    relevance_only: bool = False


class Progress(BaseModel):
    percent: float = 0.0
    message: Optional[str] = None


class ScanRequest(BaseModel):
    source_path: Optional[str] = None
    upload_id: Optional[str] = None
    use_llm: bool = False
    llm_media: bool = False
    profile_id: Optional[str] = None
    relevance_only: bool = False
    persist_project: bool = True


class FileMetadata(BaseModel):
    path: str
    size_bytes: int
    mime_type: str
    created_at: Optional[str] = None
    modified_at: Optional[str] = None
    media_info: Optional[Dict[str, Any]] = None
    file_hash: Optional[str] = None


class ParseIssue(BaseModel):
    path: str
    code: str
    message: str


class ParseResult(BaseModel):
    files: List[FileMetadata] = Field(default_factory=list)
    issues: List[ParseIssue] = Field(default_factory=list)
    summary: Dict[str, Any] = Field(default_factory=dict)


class GitContributor(BaseModel):
    name: str
    commits: int
    percent: float


class GitTimelineItem(BaseModel):
    month: str
    commits: int


class GitRepoAnalysis(BaseModel):
    path: str
    commit_count: int
    date_range: Dict[str, str]
    branches: List[str] = Field(default_factory=list)
    contributors: List[GitContributor] = Field(default_factory=list)
    timeline: List[GitTimelineItem] = Field(default_factory=list)


class CodeRefactorFunction(BaseModel):
    name: str
    lines: int
    complexity: float
    params: int
    needs_refactor: bool


class CodeRefactorCandidate(BaseModel):
    path: str
    language: str
    lines: int
    code_lines: int
    complexity: float
    maintainability: float
    priority: str
    top_functions: List[CodeRefactorFunction] = Field(default_factory=list)


class CodeFileMetrics(BaseModel):
    lines: int
    code_lines: int
    comments: int
    functions: int
    classes: int
    complexity: float
    maintainability: float
    priority: str
    security_issues_count: int
    todos_count: int


class CodeFileDetail(BaseModel):
    path: str
    language: str
    success: bool
    size_mb: float
    analysis_time_ms: int
    metrics: CodeFileMetrics
    error: Optional[str] = None


class CodeAnalysisSummary(BaseModel):
    success: bool
    path: str
    total_files: int
    successful_files: int
    failed_files: int
    languages: Dict[str, int] = Field(default_factory=dict)
    metrics: Dict[str, Any] = Field(default_factory=dict)
    quality: Dict[str, Any] = Field(default_factory=dict)
    refactor_candidates: List[CodeRefactorCandidate] = Field(default_factory=list)
    file_details: List[CodeFileDetail] = Field(default_factory=list)


class ContributionContributor(BaseModel):
    name: str
    email: Optional[str] = None
    commits: int
    commit_percentage: float
    first_commit_date: Optional[str] = None
    last_commit_date: Optional[str] = None
    active_days: int
    contribution_frequency: float
    activity_breakdown: Dict[str, Any] = Field(default_factory=dict)
    languages_used: List[str] = Field(default_factory=list)


class ContributionTimelineItem(BaseModel):
    date: str
    commits: int


class ContributionMetrics(BaseModel):
    project_type: str
    total_contributors: int
    total_commits: int
    commit_frequency: float
    project_start_date: Optional[str] = None
    project_end_date: Optional[str] = None
    project_duration_days: Optional[int] = None
    user_commit_share: Optional[float] = None
    primary_contributor: Optional[str] = None
    activity_breakdown: Dict[str, Any] = Field(default_factory=dict)
    contributors: List[ContributionContributor] = Field(default_factory=list)
    timeline: List[ContributionTimelineItem] = Field(default_factory=list)


class SkillItem(BaseModel):
    name: str
    category: Optional[str] = None
    confidence: Optional[float] = None
    evidence: List[str] = Field(default_factory=list)


class SkillsAnalysis(BaseModel):
    top_skills: List[SkillItem] = Field(default_factory=list)
    categories: List[str] = Field(default_factory=list)
    skills: List[SkillItem] = Field(default_factory=list)


class SkillsProgressItem(BaseModel):
    period_label: str
    commits: int
    tests_changed: int
    top_skills: List[str] = Field(default_factory=list)


class SkillsProgress(BaseModel):
    timeline: List[SkillsProgressItem] = Field(default_factory=list)


class MediaAnalysisSummary(BaseModel):
    summary: Dict[str, Any] = Field(default_factory=dict)
    metrics: Dict[str, Any] = Field(default_factory=dict)
    insights: List[str] = Field(default_factory=list)
    issues: List[str] = Field(default_factory=list)


class PdfSummary(BaseModel):
    path: str
    num_pages: Optional[int] = None
    keywords: List[str] = Field(default_factory=list)
    summary_text: Optional[str] = None


class PdfAnalysisSummary(BaseModel):
    items: List[PdfSummary] = Field(default_factory=list)


class DocumentSummary(BaseModel):
    path: str
    word_count: Optional[int] = None
    summary_text: Optional[str] = None
    keywords: List[str] = Field(default_factory=list)
    headings: List[str] = Field(default_factory=list)


class DocumentAnalysisSummary(BaseModel):
    items: List[DocumentSummary] = Field(default_factory=list)


class DedupFile(BaseModel):
    path: str
    size_bytes: int
    mime_type: Optional[str] = None


class DedupGroup(BaseModel):
    hash: str
    file_count: int
    total_size_bytes: int
    wasted_bytes: int
    files: List[DedupFile] = Field(default_factory=list)


class DedupReport(BaseModel):
    summary: Dict[str, Any] = Field(default_factory=dict)
    duplicate_groups: List[DedupGroup] = Field(default_factory=list)


class AnalysisSummary(BaseModel):
    parse_result: Optional[ParseResult] = None
    git_analysis: Optional[List[GitRepoAnalysis]] = None
    code_analysis: Optional[CodeAnalysisSummary] = None
    contribution_metrics: Optional[ContributionMetrics] = None
    skills_analysis: Optional[SkillsAnalysis] = None
    skills_progress: Optional[SkillsProgress] = None
    media_analysis: Optional[MediaAnalysisSummary] = None
    pdf_analysis: Optional[PdfAnalysisSummary] = None
    document_analysis: Optional[DocumentAnalysisSummary] = None
    duplicate_report: Optional[DedupReport] = None
    ranking: Optional[Dict[str, Any]] = None
    summaries: Optional[Dict[str, Any]] = None
    search_index: Optional[Dict[str, Any]] = None


class ProjectSummary(BaseModel):
    project_id: str
    name: str
    project_type: str
    languages: List[str] = Field(default_factory=list)
    frameworks: List[str] = Field(default_factory=list)
    rank_score: Optional[float] = None
    created_at: str


class ProjectDetail(ProjectSummary):
    project_path: Optional[str] = None
    scan_timestamp: Optional[str] = None
    total_files: Optional[int] = None
    total_lines: Optional[int] = None
    has_media_analysis: bool = False
    has_pdf_analysis: bool = False
    has_code_analysis: bool = False
    has_git_analysis: bool = False
    has_contribution_metrics: bool = False
    contribution_score: Optional[float] = None
    user_commit_share: Optional[float] = None
    total_commits: Optional[int] = None
    primary_contributor: Optional[str] = None
    project_end_date: Optional[str] = None
    has_skills_progress: bool = False
    rank_score: Optional[float] = None
    summary: Dict[str, Any] = Field(default_factory=dict)
    analysis: Optional[AnalysisSummary] = None


class RankRequest(BaseModel):
    weights: Dict[str, float]


class RankResponse(BaseModel):
    score: float
    reasons: List[str] = Field(default_factory=list)


class ResumeItem(BaseModel):
    id: str
    project_id: str
    title: str
    role: Optional[str] = None
    summary: Optional[str] = None
    evidence: List[str] = Field(default_factory=list)
    thumbnail_url: Optional[str] = None
    created_at: str


class SelectionRequest(BaseModel):
    project_order: List[str] = Field(default_factory=list)
    skill_order: List[str] = Field(default_factory=list)
    selected_project_ids: List[str] = Field(default_factory=list)
    selected_skill_ids: List[str] = Field(default_factory=list)


class TimelineItem(BaseModel):
    project_id: str
    name: str
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    duration_days: Optional[int] = None


class ScanStatus(BaseModel):
    scan_id: str
    user_id: str  # Owner of the scan for user isolation
    project_id: Optional[str] = None
    upload_id: Optional[str] = None
    state: JobState
    progress: Optional[Progress] = None
    error: Optional[ErrorResponse] = None
    result: Optional[Dict[str, Any]] = None


# In-memory placeholders
_upload_store: Dict[str, Upload] = {}
_scan_store: Dict[str, ScanStatus] = {}
_project_store: Dict[str, ProjectDetail] = {}
_resume_store: Dict[str, ResumeItem] = {}
_config_store: Dict[str, Dict[str, Any]] = {}
_selection_store: Dict[str, SelectionRequest] = {}

# Thread lock for scan store access
_scan_store_lock = threading.Lock()

# Lazy-initialized scan service
_scan_service = None


def _get_scan_service():
    """Get or create the singleton scan service instance."""
    global _scan_service
    if _scan_service is None:
        from src.cli.services.scan_service import ScanService
        _scan_service = ScanService()
    return _scan_service


def _update_scan_status(
    scan_id: str,
    state: JobState,
    progress: Optional[Progress] = None,
    error: Optional[ErrorResponse] = None,
    result: Optional[Dict[str, Any]] = None,
    project_id: Optional[str] = None,
) -> None:
    """Thread-safe update of scan status using immutable pattern."""
    with _scan_store_lock:
        if scan_id in _scan_store:
            current = _scan_store[scan_id]
            updates: Dict[str, Any] = {"state": state}
            if progress is not None:
                updates["progress"] = progress
            if error is not None:
                updates["error"] = error
            if result is not None:
                updates["result"] = result
            if project_id is not None:
                updates["project_id"] = project_id
            # Use model_copy instead of direct mutation (Pydantic v2 best practice)
            _scan_store[scan_id] = current.model_copy(update=updates)


def _validate_scan_path(source_path: str) -> Path:
    """
    Validate and sanitize the scan path to prevent directory traversal attacks.

    Args:
        source_path: The path to validate

    Returns:
        Resolved Path object

    Raises:
        HTTPException: If path is invalid or not allowed
    """
    # Block access to sensitive system directories (check input BEFORE resolution)
    # This prevents bypassing via symlinks (e.g., /etc -> /private/etc on macOS)
    blocked_prefixes = [
        "/etc", "/var", "/usr", "/bin", "/sbin", "/lib", "/boot",
        "/root", "/proc", "/sys", "/dev",
        # macOS-specific paths (where symlinks resolve to)
        "/private/etc", "/private/var",
    ]

    # Check the original input path first (before symlink resolution)
    input_path = Path(source_path)
    try:
        # Make absolute without resolving symlinks
        if not input_path.is_absolute():
            input_path = Path.cwd() / input_path
        input_str = str(input_path)
    except (OSError, ValueError):
        input_str = source_path

    for blocked in blocked_prefixes:
        if input_str.startswith(blocked) or source_path.startswith(blocked):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"code": "path_not_allowed", "message": f"Access to {blocked} is not allowed"},
            )

    try:
        # Resolve to absolute path (handles ../ and symlinks)
        target = Path(source_path).resolve()
    except (OSError, ValueError) as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "invalid_path", "message": f"Invalid path: {e}"},
        )

    # Also check resolved path (catches symlink bypasses)
    resolved_str = str(target)
    for blocked in blocked_prefixes:
        if resolved_str.startswith(blocked):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"code": "path_not_allowed", "message": f"Access to {blocked} is not allowed"},
            )

    # Ensure path exists
    if not target.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "path_not_found", "message": f"Path does not exist: {source_path}"},
        )

    return target


def _run_scan_background(
    scan_id: str,
    source_path: str,
    relevance_only: bool,
    persist_project: bool,
    profile_id: Optional[str],
) -> None:
    """Background task that executes the scan pipeline."""
    try:
        # Update status to running
        _update_scan_status(
            scan_id,
            JobState.running,
            progress=Progress(percent=5.0, message="Starting scan..."),
        )

        target = Path(source_path)
        if not target.exists():
            _update_scan_status(
                scan_id,
                JobState.failed,
                error=ErrorResponse(
                    code="PATH_NOT_FOUND",
                    message=f"Source path does not exist: {source_path}",
                ),
            )
            return

        # Progress callback for scan service
        def progress_callback(payload):
            if isinstance(payload, str):
                _update_scan_status(
                    scan_id,
                    JobState.running,
                    progress=Progress(percent=30.0, message=payload),
                )
            elif isinstance(payload, dict) and payload.get("type") == "files":
                processed = payload.get("processed", 0)
                total = payload.get("total", 1)
                percent = min(90.0, 30.0 + (processed / max(total, 1)) * 60.0)
                _update_scan_status(
                    scan_id,
                    JobState.running,
                    progress=Progress(
                        percent=percent,
                        message=f"Processing files ({processed}/{total})...",
                    ),
                )

        # Run the scan
        from src.scanner.models import ScanPreferences
        preferences = ScanPreferences()
        scan_service = _get_scan_service()
        scan_result = scan_service.run_scan(
            target=target,
            relevant_only=relevance_only,
            preferences=preferences,
            progress_callback=progress_callback,
        )

        # Build result payload
        parse_summary = dict(scan_result.parse_result.summary) if scan_result.parse_result else {}
        files_data = []
        for meta in scan_result.parse_result.files[:MAX_FILES_IN_RESPONSE]:
            files_data.append({
                "path": meta.path,
                "size_bytes": meta.size_bytes,
                "mime_type": meta.mime_type,
            })

        result_payload = {
            "summary": {
                "total_files": parse_summary.get("files_processed", len(scan_result.parse_result.files)),
                "bytes_processed": parse_summary.get("bytes_processed", 0),
                "issues_count": parse_summary.get("issues_count", 0),
            },
            "languages": scan_result.languages,
            "has_media_files": scan_result.has_media_files,
            "pdf_count": len(scan_result.pdf_candidates),
            "document_count": len(scan_result.document_candidates),
            "git_repos_count": len(scan_result.git_repos),
            "files": files_data,
            "timings": scan_result.timings,
        }

        # Optionally persist to database
        project_id = None
        if persist_project and profile_id:
            try:
                from src.cli.services.projects_service import ProjectsService
                projects_service = ProjectsService()
                project_name = target.name or "scan"
                saved = projects_service.save_scan(
                    user_id=profile_id,
                    project_name=project_name,
                    project_path=str(target),
                    scan_data=result_payload,
                )
                project_id = saved.get("id")
                result_payload["project_id"] = project_id
            except Exception as persist_err:
                logger.warning(f"Failed to persist scan to database: {persist_err}")
                result_payload["persist_warning"] = str(persist_err)

        _update_scan_status(
            scan_id,
            JobState.succeeded,
            progress=Progress(percent=100.0, message="Scan completed"),
            result=result_payload,
            project_id=project_id,
        )

    except Exception as exc:
        logger.exception(f"Scan {scan_id} failed with error: {exc}")
        _update_scan_status(
            scan_id,
            JobState.failed,
            error=ErrorResponse(
                code="SCAN_ERROR",
                message=str(exc),
            ),
        )


router = APIRouter()


# Consent endpoints moved to consent_routes.py
# Upload endpoints moved to upload_routes.py


@router.post("/api/scans", response_model=ScanStatus, status_code=status.HTTP_202_ACCEPTED)
async def create_scan(
    request: ScanRequest,
    background_tasks: BackgroundTasks,
    auth: AuthContext = Depends(get_auth_context),
    idempotency_key: Optional[str] = Header(default=None, convert_underscores=True),
):
    """
    Start a new scan job for a source path.

    Requires authentication. Returns immediately with a scan_id that can be
    polled via GET /api/scans/{scan_id}. The scan runs in the background and
    updates its status as it progresses.
    """
    scan_id = idempotency_key or str(uuid.uuid4())

    # Return existing scan if idempotency key matches AND belongs to this user
    with _scan_store_lock:
        if scan_id in _scan_store:
            existing = _scan_store[scan_id]
            if existing.user_id != auth.user_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail={"code": "forbidden", "message": "Scan belongs to another user"},
                )
            return existing

    # Validate request - must have source_path or upload_id
    if not request.source_path and not request.upload_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "validation_error", "message": "Either source_path or upload_id must be provided"},
        )

    # For now, only source_path is supported
    if request.upload_id and not request.source_path:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail={"code": "not_implemented", "message": "Scanning from upload_id is not yet implemented. Please provide source_path."},
        )

    # Validate path before starting background task (security check)
    _validate_scan_path(request.source_path)

    # Validate profile_id if provided - must match authenticated user
    profile_id = request.profile_id
    if profile_id and profile_id != auth.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "forbidden", "message": "profile_id must match authenticated user"},
        )
    # Default profile_id to authenticated user if not provided
    if not profile_id:
        profile_id = auth.user_id

    # Create initial scan status with user_id for isolation
    scan_status = ScanStatus(
        scan_id=scan_id,
        user_id=auth.user_id,
        project_id=None,
        upload_id=request.upload_id,
        state=JobState.queued,
        progress=Progress(percent=0.0, message="Scan queued"),
        error=None,
        result=None,
    )

    with _scan_store_lock:
        _scan_store[scan_id] = scan_status

    # Schedule background scan
    background_tasks.add_task(
        _run_scan_background,
        scan_id=scan_id,
        source_path=request.source_path,
        relevance_only=request.relevance_only,
        persist_project=request.persist_project,
        profile_id=profile_id,
    )

    return scan_status


@router.get("/api/scans/{scan_id}", response_model=ScanStatus)
async def get_scan(
    scan_id: str,
    auth: AuthContext = Depends(get_auth_context),
):
    """
    Get the current status of a scan job.

    Requires authentication. Users can only access their own scans.
    Poll this endpoint to track scan progress. The scan is complete when
    state is 'succeeded' or 'failed'.
    """
    with _scan_store_lock:
        scan = _scan_store.get(scan_id)
    if not scan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "not_found", "message": "Scan not found"},
        )
    # User isolation - only return scans owned by the authenticated user
    if scan.user_id != auth.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "forbidden", "message": "Access denied"},
        )
    return scan


@router.post("/api/analysis/portfolio")
def start_analysis(payload: Dict[str, Any] = Body(...)):
    job_id = str(uuid.uuid4())
    return {
        "job_id": job_id,
        "state": JobState.succeeded,
        "progress": Progress(percent=100.0, message="Analysis stub"),
    }


# ============================================================================
# Project Management Endpoints (moved to project_routes.py)
# ============================================================================
# Project endpoints are now registered from project_routes.py
# See src/api/project_routes.py for POST/GET/DELETE implementations


# Legacy stub endpoints (kept for backward compatibility during migration)
@router.get("/api/projects-stub", response_model=Dict[str, Any])
def list_projects_stub(limit: int = 20, offset: int = 0, sort: Optional[str] = None):
    items = list(_project_store.values())[offset : offset + limit]
    return {
        "items": [p for p in items],
        "page": Pagination(limit=limit, offset=offset, total=len(_project_store)),
    }


class ProjectCreateRequest(BaseModel):
    name: str
    upload_id: Optional[str] = None
    scan_id: Optional[str] = None
    analysis_payload: Optional[Dict[str, Any]] = None


@router.post("/api/projects-stub", response_model=ProjectSummary)
def create_project_stub(payload: ProjectCreateRequest):
    project_id = str(uuid.uuid4())
    project = ProjectDetail(
        project_id=project_id,
        name=payload.name,
        project_type="unknown",
        languages=[],
        frameworks=[],
        created_at=_now_iso(),
        scan_timestamp=_now_iso(),
        analysis=AnalysisSummary(),
    )
    _project_store[project_id] = project
    return ProjectSummary(
        project_id=project_id,
        name=payload.name,
        project_type=project.project_type,
        languages=project.languages,
        frameworks=project.frameworks,
        rank_score=None,
        created_at=project.created_at,
    )


@router.get("/api/projects-stub/{project_id}", response_model=ProjectDetail)
def get_project_stub(project_id: str):
    project = _project_store.get(project_id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return project


@router.delete("/api/projects-stub/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project_stub(project_id: str):
    _project_store.pop(project_id, None)
    return


@router.delete("/api/projects-stub/{project_id}/insights", status_code=status.HTTP_204_NO_CONTENT)
def delete_insights(project_id: str):
    project = _project_store.get(project_id)
    if project:
        project.analysis = AnalysisSummary()
        _project_store[project_id] = project
    return


@router.post("/api/projects/{project_id}/append-upload/{upload_id}", status_code=status.HTTP_202_ACCEPTED)
def append_upload(project_id: str, upload_id: str):
    if project_id not in _project_store:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    if upload_id not in _upload_store:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Upload not found")
    return {"project_id": project_id, "upload_id": upload_id, "state": JobState.succeeded}


@router.post("/api/projects/{project_id}/rank", response_model=RankResponse)
def rank_project(project_id: str, payload: RankRequest):
    if project_id not in _project_store:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    score = sum(payload.weights.values())
    return RankResponse(score=score, reasons=["Stubbed ranking"])


@router.get("/api/projects/top", response_model=List[ProjectSummary])
def top_projects(limit: int = 3):
    items = list(_project_store.values())[:limit]
    return [
        ProjectSummary(
            project_id=p.project_id,
            name=p.name,
            project_type=p.project_type,
            languages=p.languages,
            frameworks=p.frameworks,
            rank_score=p.rank_score,
            created_at=p.created_at,
        )
        for p in items
    ]


@router.get("/api/projects/timeline", response_model=List[TimelineItem])
def project_timeline():
    items: List[TimelineItem] = []
    for p in _project_store.values():
        items.append(
            TimelineItem(
                project_id=p.project_id,
                name=p.name,
                start_date=p.scan_timestamp,
                end_date=p.project_end_date,
                duration_days=None,
            )
        )
    return items


@router.get("/api/resume/items", response_model=Dict[str, Any])
def list_resume_items(limit: int = 20, offset: int = 0):
    items = list(_resume_store.values())[offset : offset + limit]
    return {
        "items": items,
        "page": Pagination(limit=limit, offset=offset, total=len(_resume_store)),
    }


class ResumeCreateRequest(BaseModel):
    project_id: str
    title: str
    role: Optional[str] = None
    summary: Optional[str] = None
    evidence: List[str] = Field(default_factory=list)
    thumbnail_url: Optional[str] = None


@router.post("/api/resume/items", response_model=ResumeItem)
def create_resume_item(payload: ResumeCreateRequest):
    item_id = str(uuid.uuid4())
    item = ResumeItem(
        id=item_id,
        project_id=payload.project_id,
        title=payload.title,
        role=payload.role,
        summary=payload.summary,
        evidence=payload.evidence,
        thumbnail_url=payload.thumbnail_url,
        created_at=_now_iso(),
    )
    _resume_store[item_id] = item
    return item


@router.get("/api/resume/items/{item_id}", response_model=ResumeItem)
def get_resume_item(item_id: str):
    item = _resume_store.get(item_id)
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resume item not found")
    return item


@router.delete("/api/resume/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_resume_item(item_id: str):
    _resume_store.pop(item_id, None)
    return


@router.get("/api/config")
def get_config(user_id: Optional[str] = None):
    return _config_store.get(user_id or "default", {})


@router.put("/api/config")
def update_config(payload: Dict[str, Any] = Body(...)):
    user_id = payload.get("user_id", "default")
    _config_store[user_id] = payload
    return payload


@router.get("/api/config/profiles")
def list_profiles(user_id: Optional[str] = None):
    cfg = _config_store.get(user_id or "default", {})
    return cfg.get("profiles", [])


@router.post("/api/config/profiles")
def save_profile(payload: Dict[str, Any] = Body(...)):
    user_id = payload.get("user_id", "default")
    cfg = _config_store.setdefault(user_id, {})
    profiles = cfg.setdefault("profiles", [])
    profiles.append(payload)
    return payload


@router.get("/api/search")
def search(q: Optional[str] = None, scope: Optional[str] = None, project_id: Optional[str] = None, limit: int = 50):
    return {"items": [], "page": Pagination(limit=limit, offset=0, total=0)}


@router.get("/api/dedup", response_model=DedupReport)
def dedup(project_id: str):
    return DedupReport(
        summary={
            "total_files_analyzed": 0,
            "files_with_hash": 0,
            "duplicate_groups_count": 0,
            "total_duplicate_files": 0,
            "total_wasted_bytes": 0,
            "space_savings_percent": 0.0,
        },
        duplicate_groups=[],
    )


@router.post("/api/selection")
def save_selection(payload: SelectionRequest):
    key = "default"
    _selection_store[key] = payload
    return {"status": "saved"}
