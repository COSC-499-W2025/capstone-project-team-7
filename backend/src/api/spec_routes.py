"""API skeleton routes aligned to docs/api-spec.yaml.

These routes provide stubbed responses and in-memory placeholders so the
Electron/Next clients can develop against stable contracts while the
backend implementations are completed. Replace stub logic with real
services incrementally.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
import os
import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Body, File, Header, HTTPException, UploadFile, status
from pydantic import BaseModel, Field


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
    project_id: Optional[str] = None
    upload_id: Optional[str] = None
    state: JobState
    progress: Optional[Progress] = None
    error: Optional[ErrorResponse] = None
    result: Optional[Dict[str, Any]] = None


class ConfigUpdateRequest(BaseModel):
    user_id: Optional[str] = None
    current_profile: Optional[str] = None
    max_file_size_mb: Optional[int] = None
    follow_symlinks: Optional[bool] = None


class ProfileUpsertRequest(BaseModel):
    user_id: Optional[str] = None
    name: str
    extensions: Optional[List[str]] = None
    exclude_dirs: Optional[List[str]] = None
    description: Optional[str] = None


class ProfilesResponse(BaseModel):
    current_profile: str
    profiles: Dict[str, Dict[str, Any]]


class ProfileSaveResponse(BaseModel):
    name: str
    profile: Dict[str, Any]
    current_profile: str


# In-memory placeholders
_upload_store: Dict[str, Upload] = {}
_scan_store: Dict[str, ScanStatus] = {}
_project_store: Dict[str, ProjectDetail] = {}
_resume_store: Dict[str, ResumeItem] = {}
_selection_store: Dict[str, SelectionRequest] = {}
_consent_store: Dict[str, ConsentStatus] = {}


router = APIRouter()


def _get_config_manager(user_id: Optional[str]):
    if not user_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="user_id is required")
    try:
        from config.config_manager import ConfigManager
    except Exception as exc:  # pragma: no cover - optional dependency
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Config service unavailable: {exc}",
        ) from exc
    try:
        return ConfigManager(user_id)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unable to load config: {exc}",
        ) from exc


def _parse_bearer_token(authorization: Optional[str]) -> Optional[str]:
    if not authorization:
        return None
    parts = authorization.split()
    if len(parts) == 2 and parts[0].lower() == "bearer":
        return parts[1]
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid authorization header")


def _get_supabase_user_id(token: str) -> str:
    try:
        from supabase import create_client
    except Exception as exc:  # pragma: no cover - optional dependency
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Supabase client unavailable: {exc}",
        ) from exc

    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_ANON_KEY") or os.getenv("SUPABASE_KEY")
    if not url or not key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Supabase credentials missing",
        )

    try:
        client = create_client(url, key)
        response = client.auth.get_user(token)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

    user = getattr(response, "user", None) or (response or {}).get("user")
    user_id = getattr(user, "id", None) or (user or {}).get("id")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )
    return user_id


def _resolve_user_id(user_id: Optional[str], authorization: Optional[str]) -> str:
    token = _parse_bearer_token(authorization)
    if token:
        authed_user_id = _get_supabase_user_id(token)
        if user_id and user_id != authed_user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User mismatch",
            )
        return authed_user_id
    if not user_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="user_id is required")
    return user_id


@router.get("/api/consent", response_model=ConsentStatus)
def get_consent(user_id: str):
    if user_id in _consent_store:
        return _consent_store[user_id]
    status_obj = ConsentStatus(
        user_id=user_id,
        data_access=False,
        external_services=False,
        updated_at=_now_iso(),
    )
    _consent_store[user_id] = status_obj
    return status_obj


@router.post("/api/consent", response_model=ConsentStatus)
def set_consent(payload: Dict[str, Any] = Body(...)):
    user_id = payload.get("user_id", "unknown-user")
    status_obj = ConsentStatus(
        user_id=user_id,
        data_access=bool(payload.get("data_access", False)),
        external_services=bool(payload.get("external_services", False)),
        updated_at=_now_iso(),
    )
    _consent_store[user_id] = status_obj
    return status_obj


@router.post("/api/uploads", response_model=Upload)
async def create_upload(
    file: UploadFile = File(...),
    idempotency_key: Optional[str] = Header(default=None, convert_underscores=True),
):
    if idempotency_key and idempotency_key in _upload_store:
        return _upload_store[idempotency_key]
    upload_id = idempotency_key or str(uuid.uuid4())
    upload = Upload(
        upload_id=upload_id,
        filename=file.filename,
        size_bytes=None,
        status="stored",
        created_at=_now_iso(),
    )
    _upload_store[upload_id] = upload
    return upload


@router.get("/api/uploads/{upload_id}", response_model=Upload)
def get_upload(upload_id: str):
    upload = _upload_store.get(upload_id)
    if not upload:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Upload not found")
    return upload


@router.post("/api/uploads/{upload_id}/parse")
def parse_upload(upload_id: str, options: ParseOptions = Body(default=None)):
    upload = _upload_store.get(upload_id)
    if not upload:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Upload not found")
    # Stub: mark parsed
    upload.status = "parsed"
    _upload_store[upload_id] = upload
    return {
        "upload_id": upload_id,
        "state": JobState.succeeded,
        "progress": Progress(percent=100.0, message="Parsed (stub)"),
    }


@router.post("/api/scans", response_model=ScanStatus, status_code=status.HTTP_202_ACCEPTED)
def create_scan(
    request: ScanRequest,
    idempotency_key: Optional[str] = Header(default=None, convert_underscores=True),
):
    scan_id = idempotency_key or str(uuid.uuid4())
    if scan_id in _scan_store:
        return _scan_store[scan_id]

    project_id = str(uuid.uuid4()) if request.persist_project else None
    upload_id = request.upload_id or (str(uuid.uuid4()) if request.source_path else None)
    project = ProjectDetail(
        project_id=project_id or str(uuid.uuid4()),
        name=request.source_path or "scan",
        project_type="unknown",
        languages=[],
        frameworks=[],
        created_at=_now_iso(),
        scan_timestamp=_now_iso(),
    )
    _project_store[project.project_id] = project
    scan_status = ScanStatus(
        scan_id=scan_id,
        project_id=project.project_id,
        upload_id=upload_id,
        state=JobState.succeeded,
        progress=Progress(percent=100.0, message="Completed (stub)"),
        result={"project": project.dict(), "analysis": AnalysisSummary().dict()},
    )
    _scan_store[scan_id] = scan_status
    return scan_status


@router.get("/api/scans/{scan_id}", response_model=ScanStatus)
def get_scan(scan_id: str):
    scan = _scan_store.get(scan_id)
    if not scan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scan not found")
    return scan


@router.post("/api/analysis/portfolio")
def start_analysis(payload: Dict[str, Any] = Body(...)):
    job_id = str(uuid.uuid4())
    return {
        "job_id": job_id,
        "state": JobState.succeeded,
        "progress": Progress(percent=100.0, message="Analysis stub"),
    }


@router.get("/api/projects", response_model=Dict[str, Any])
def list_projects(limit: int = 20, offset: int = 0, sort: Optional[str] = None):
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


@router.post("/api/projects", response_model=ProjectSummary)
def create_project(payload: ProjectCreateRequest):
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


@router.get("/api/projects/{project_id}", response_model=ProjectDetail)
def get_project(project_id: str):
    project = _project_store.get(project_id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return project


@router.delete("/api/projects/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(project_id: str):
    _project_store.pop(project_id, None)
    return


@router.delete("/api/projects/{project_id}/insights", status_code=status.HTTP_204_NO_CONTENT)
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
def get_config(user_id: Optional[str] = None, authorization: Optional[str] = Header(default=None)):
    resolved_user_id = _resolve_user_id(user_id, authorization)
    manager = _get_config_manager(resolved_user_id)
    return manager.config


@router.put("/api/config")
def update_config(payload: ConfigUpdateRequest, authorization: Optional[str] = Header(default=None)):
    resolved_user_id = _resolve_user_id(payload.user_id, authorization)
    manager = _get_config_manager(resolved_user_id)

    if payload.current_profile:
        if not manager.set_current_profile(payload.current_profile):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unknown profile '{payload.current_profile}'",
            )

    if payload.max_file_size_mb is not None or payload.follow_symlinks is not None:
        ok = manager.update_settings(
            max_file_size_mb=payload.max_file_size_mb,
            follow_symlinks=payload.follow_symlinks,
        )
        if not ok:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Unable to update settings",
            )

    return manager.config


@router.get("/api/config/profiles", response_model=ProfilesResponse)
def list_profiles(user_id: Optional[str] = None, authorization: Optional[str] = Header(default=None)):
    resolved_user_id = _resolve_user_id(user_id, authorization)
    manager = _get_config_manager(resolved_user_id)
    return {
        "current_profile": manager.get_current_profile(),
        "profiles": manager.config.get("scan_profiles", {}) or {},
    }


@router.post("/api/config/profiles", response_model=ProfileSaveResponse)
def save_profile(payload: ProfileUpsertRequest, authorization: Optional[str] = Header(default=None)):
    resolved_user_id = _resolve_user_id(payload.user_id, authorization)
    manager = _get_config_manager(resolved_user_id)
    scan_profiles = manager.config.get("scan_profiles", {}) or {}
    exists = payload.name in scan_profiles

    if exists:
        ok = manager.update_profile(
            payload.name,
            extensions=payload.extensions,
            exclude_dirs=payload.exclude_dirs,
            description=payload.description,
        )
    else:
        ok = manager.create_custom_profile(
            payload.name,
            payload.extensions or [],
            payload.exclude_dirs or [],
            payload.description or "Custom profile",
        )

    if not ok:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unable to {'update' if exists else 'create'} profile '{payload.name}'",
        )

    scan_profiles = manager.config.get("scan_profiles", {}) or {}
    return {
        "name": payload.name,
        "profile": scan_profiles.get(payload.name, {}),
        "current_profile": manager.get_current_profile(),
    }


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