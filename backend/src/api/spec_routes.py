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
import tempfile
from datetime import datetime
from enum import Enum
from pathlib import Path
import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, BackgroundTasks, Body, Depends, Header, HTTPException, status
from pydantic import BaseModel, Field

from api.dependencies import AuthContext, get_auth_context
from services.services.projects_service import ProjectsService, ProjectsServiceError
from api.project_routes import (
    _run_git_analysis_for_path,
    _run_code_analysis_for_path,
    _build_skills_analysis,
    _serialize_contribution_metrics,
    _run_media_analysis,
    _run_pdf_analysis,
    _run_document_analysis,
    _run_duplicate_detection,
    _extract_archive_for_analysis,
)

# Add parent directory to path for absolute imports (needed for lazy imports in background tasks)
sys.path.insert(0, str(Path(__file__).parent.parent))

logger = logging.getLogger(__name__)

# Configuration constants
MAX_FILES_IN_RESPONSE = 100  # Maximum number of files to include in scan response
_use_api_mode = os.getenv("USE_API_MODE", "false").lower() in ("true", "1", "yes")


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


class ConsentUpdateRequest(BaseModel):
    user_id: Optional[str] = None
    data_access: bool = False
    external_services: bool = False


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


class ConfigResponse(BaseModel):
    scan_profiles: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    current_profile: Optional[str] = None
    max_file_size_mb: Optional[int] = None
    follow_symlinks: Optional[bool] = None

    class Config:
        extra = "allow"


# In-memory placeholders
_upload_store: Dict[str, Upload] = {}
_scan_store: Dict[str, ScanStatus] = {}
_project_store: Dict[str, ProjectDetail] = {}
_resume_store: Dict[str, ResumeItem] = {}
_consent_store: Dict[str, ConsentStatus] = {}

# Thread lock for scan store access
_scan_store_lock = threading.Lock()

# Lazy-initialized scan service
_scan_service = None
_scan_service_lock = threading.Lock()

# Lazy-initialized projects service for dedup reports
_projects_service: Optional[ProjectsService] = None
_projects_service_lock = threading.Lock()


def _get_scan_service():
    """Get or create the singleton scan service instance (thread-safe)."""
    global _scan_service
    if _scan_service is None:
        with _scan_service_lock:
            if _scan_service is None:
                from services.services.scan_service import ScanService
                _scan_service = ScanService(use_api=_use_api_mode)
    return _scan_service


def _get_projects_service() -> ProjectsService:
    """Get or create the singleton projects service instance (thread-safe)."""
    global _projects_service
    if _projects_service is None:
        with _projects_service_lock:
            if _projects_service is None:
                _projects_service = ProjectsService()
    return _projects_service


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
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY") or os.getenv("SUPABASE_ANON_KEY")
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


def _default_config() -> Dict[str, Any]:
    return {
        "scan_profiles": {
            "sample": {
                "description": "Scan common code and doc file types.",
                "extensions": [".py", ".md", ".json", ".txt", ".pdf", ".doc", ".docx"],
                "exclude_dirs": ["__pycache__", "node_modules", ".git"],
            }
        },
        "current_profile": "sample",
        "max_file_size_mb": 10,
        "follow_symlinks": False,
    }


def _run_scan_background(
    scan_id: str,
    source_path: str,
    relevance_only: bool,
    persist_project: bool,
    profile_id: Optional[str],
    access_token: Optional[str] = None,
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
        if _use_api_mode and access_token:
            from services.services.scan_service import ScanService
            scan_service = ScanService(use_api=True)
            scan_service.set_auth_token(access_token)
        else:
            scan_service = _get_scan_service()
        scan_result = scan_service.run_scan(
            target=target,
            relevant_only=relevance_only,
            preferences=preferences,
            progress_callback=progress_callback,
        )

        analysis_target = target
        temp_analysis_dir: Optional[tempfile.TemporaryDirectory[str]] = None

        if target.is_file() and target.suffix.lower() == ".zip":
            temp_analysis_dir = tempfile.TemporaryDirectory(prefix="scan-analysis-")
            _extract_archive_for_analysis(target, Path(temp_analysis_dir.name))
            analysis_target = Path(temp_analysis_dir.name)

        # ========================================
        # RUN ALL ANALYSES (optimized with parallel execution)
        # ========================================
        logger.info("=" * 50)
        logger.info("🚀 Starting all analysis pipelines (parallel mode)...")
        logger.info("=" * 50)
        
        _update_scan_status(
            scan_id,
            JobState.running,
            progress=Progress(percent=40.0, message="Running parallel analyses..."),
        )
        
        # PHASE 1: Run independent analyses in parallel
        # Git, Media, PDF, Document can all run simultaneously
        import concurrent.futures
        import threading
        
        git_analysis = None
        media_analysis = None
        pdf_analysis = None
        document_analysis = None
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            logger.info("🔄 Phase 1: Running independent analyses in parallel...")
            
            # Submit all independent analyses
            future_git = executor.submit(_run_git_analysis_for_path, analysis_target)
            future_media = executor.submit(_run_media_analysis, scan_result.parse_result)
            future_pdf = executor.submit(_run_pdf_analysis, analysis_target, scan_result.parse_result)
            future_document = executor.submit(_run_document_analysis, analysis_target, scan_result.parse_result)
            
            # Collect results as they complete
            try:
                git_analysis = future_git.result(timeout=120)
                logger.info("✅ Git analysis completed")
            except Exception as e:
                logger.warning(f"⚠️  Git analysis failed: {e}")
            
            try:
                media_analysis = future_media.result(timeout=60)
                logger.info("✅ Media analysis completed")
            except Exception as e:
                logger.warning(f"⚠️  Media analysis failed: {e}")
            
            try:
                pdf_analysis = future_pdf.result(timeout=90)
                logger.info("✅ PDF analysis completed")
            except Exception as e:
                logger.warning(f"⚠️  PDF analysis failed: {e}")
            
            try:
                document_analysis = future_document.result(timeout=60)
                logger.info("✅ Document analysis completed")
            except Exception as e:
                logger.warning(f"⚠️  Document analysis failed: {e}")
        
        logger.info("✨ Phase 1 complete")
        
        git_data = git_analysis[0] if git_analysis else None
        
        # PHASE 2: Code Analysis (with timeout to prevent hanging)
        _update_scan_status(
            scan_id,
            JobState.running,
            progress=Progress(percent=50.0, message="Running code analysis..."),
        )
        
        code_analysis = None
        try:
            # Calculate timeout based on file count (minimum 60s, +10s per 100 files)
            total_files = len(scan_result.parse_result.files) if scan_result and scan_result.parse_result else 0
            base_timeout = 60
            file_based_timeout = max(base_timeout, base_timeout + (total_files // 100) * 10)
            timeout_seconds = min(file_based_timeout, 300)  # Cap at 5 minutes
            
            logger.info(f"🔄 Phase 2: Code analysis starting...")
            logger.info(f"   Target: {analysis_target}")
            logger.info(f"   Timeout: {timeout_seconds}s for {total_files} files")
            
            # Run code analysis with dynamic timeout
            result_container = [None]
            exception_container = [None]
            
            def run_with_exception_handling():
                try:
                    logger.info(f"   Starting code analysis thread...")
                    result_container[0] = _run_code_analysis_for_path(analysis_target, preferences)
                    logger.info(f"   Code analysis thread completed")
                except Exception as e:
                    logger.error(f"   Code analysis thread error: {e}")
                    exception_container[0] = e
            
            thread = threading.Thread(target=run_with_exception_handling, daemon=True)
            thread.start()
            logger.info(f"   Waiting for code analysis (max {timeout_seconds}s)...")
            thread.join(timeout=timeout_seconds)
            
            if thread.is_alive():
                logger.warning(f"⚠️  Code analysis timed out after {timeout_seconds} seconds - skipping")
                code_analysis = None
            elif exception_container[0]:
                logger.warning(f"⚠️  Code analysis error: {exception_container[0]} - skipping")
                code_analysis = None
            else:
                code_analysis = result_container[0]
                if code_analysis:
                    logger.info(f"✅ Code analysis completed: {list(code_analysis.keys())}")
                else:
                    logger.info("⚠️  Code analysis returned None")
        except Exception as e:
            logger.warning(f"⚠️  Code analysis setup error: {e} - skipping")
            code_analysis = None
        
        logger.info("✨ Phase 2 complete")
        
        # PHASE 3: Run dependent analyses in parallel
        # Skills, Contribution Metrics, and Duplicate Detection can run together
        _update_scan_status(
            scan_id,
            JobState.running,
            progress=Progress(percent=65.0, message="Running dependent analyses..."),
        )
        
        skills_analysis = None
        contribution_metrics_payload = None
        metrics_obj = None
        duplicate_report = None
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            logger.info("🔄 Phase 3: Running dependent analyses in parallel...")
            
            # Skills Analysis
            def run_skills_analysis():
                try:
                    from services.services.skills_analysis_service import SkillsAnalysisService
                    skills_service = SkillsAnalysisService()
                    skills_service.extract_skills(
                        target_path=analysis_target,
                        code_analysis_result=code_analysis,
                        git_analysis_result=git_data,
                    )
                    return _build_skills_analysis(skills_service)
                except Exception as e:
                    logger.error(f"❌ Skills analysis failed: {e}", exc_info=True)
                    return None
            
            # Contribution Metrics
            def run_contribution_metrics():
                if not git_data:
                    return None, None
                try:
                    from services.services.contribution_analysis_service import ContributionAnalysisService
                    metrics = ContributionAnalysisService().analyze_contributions(
                        git_analysis=git_data,
                        code_analysis=code_analysis,
                        parse_result=scan_result.parse_result,
                    )
                    payload = _serialize_contribution_metrics(metrics)
                    return payload, metrics
                except Exception as e:
                    logger.error(f"❌ Contribution analysis failed: {e}", exc_info=True)
                    return None, None
            
            # Duplicate Detection
            def run_duplicate_detection():
                try:
                    return _run_duplicate_detection(scan_result.parse_result)
                except Exception as e:
                    logger.warning(f"⚠️  Duplicate detection failed: {e}")
                    return None
            
            # Submit parallel tasks
            future_skills = executor.submit(run_skills_analysis)
            future_contrib = executor.submit(run_contribution_metrics)
            future_dupes = executor.submit(run_duplicate_detection)
            
            # Collect results
            try:
                skills_analysis = future_skills.result(timeout=120)
                if skills_analysis:
                    logger.info("✅ Skills analysis completed")
            except Exception as e:
                logger.warning(f"⚠️  Skills analysis timeout/error: {e}")
            
            try:
                contribution_metrics_payload, metrics_obj = future_contrib.result(timeout=90)
                if contribution_metrics_payload:
                    logger.info("✅ Contribution metrics completed")
            except Exception as e:
                logger.warning(f"⚠️  Contribution metrics timeout/error: {e}")
            
            try:
                duplicate_report = future_dupes.result(timeout=60)
                if duplicate_report:
                    logger.info("✅ Duplicate detection completed")
            except Exception as e:
                logger.warning(f"⚠️  Duplicate detection timeout/error: {e}")
        
        logger.info("✨ Phase 3 complete")
        
        # PHASE 4: Skills Progress Timeline (depends on skills analysis)
        skills_progress = None
        if skills_analysis:
            chronological = skills_analysis.get("chronological_overview") or []
            if chronological:
                try:
                    logger.info("🔄 Phase 4: Building skills progress timeline...")
                    from local_analysis.skill_progress_timeline import build_skill_progression
                    progression = build_skill_progression(chronological, metrics_obj)
                    from api.project_routes import _period_to_dict
                    skills_progress = {
                        "timeline": [_period_to_dict(period) for period in progression.timeline],
                    }
                    logger.info("✅ Skills progress timeline completed")
                except Exception as e:
                    logger.error(f"❌ Skills progress failed: {e}", exc_info=True)
        
        logger.info("=" * 50)
        logger.info("✨ All analysis pipelines completed")
        logger.info("=" * 50)

        # Build result payload with all analyses
        parse_summary = dict(scan_result.parse_result.summary) if scan_result.parse_result else {}
        files_data = []
        for meta in scan_result.parse_result.files[:MAX_FILES_IN_RESPONSE]:
            files_data.append({
                "path": meta.path,
                "size_bytes": meta.size_bytes,
                "mime_type": meta.mime_type,
                "file_hash": meta.file_hash,
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
        
        # Add all analyses to the result payload
        if git_analysis:
            logger.info(f"💾 Saving git analysis to scan_data ({len(git_analysis)} repos)")
            result_payload["git_analysis"] = git_analysis
        
        if code_analysis:
            logger.info(f"💾 Saving code analysis to scan_data")
            result_payload["code_analysis"] = code_analysis
        else:
            logger.warning("⚠️  No code analysis data to save")
        
        if skills_analysis:
            logger.info(f"💾 Saving skills analysis to scan_data")
            result_payload["skills_analysis"] = skills_analysis
        
        if contribution_metrics_payload:
            logger.info(f"💾 Saving contribution metrics to scan_data")
            result_payload["contribution_metrics"] = contribution_metrics_payload
        
        if skills_progress:
            logger.info(f"💾 Saving skills progress to scan_data")
            result_payload["skills_progress"] = skills_progress
        
        if media_analysis:
            logger.info(f"💾 Saving media analysis to scan_data")
            result_payload["media_analysis"] = media_analysis
        
        if pdf_analysis:
            logger.info(f"💾 Saving PDF analysis to scan_data ({len(pdf_analysis)} PDFs)")
            result_payload["pdf_analysis"] = pdf_analysis
        
        if document_analysis:
            logger.info(f"💾 Saving document analysis to scan_data ({len(document_analysis)} documents)")
            result_payload["document_analysis"] = document_analysis
        
        if duplicate_report:
            logger.info(f"💾 Saving duplicate report to scan_data")
            result_payload["duplicate_report"] = duplicate_report

        if temp_analysis_dir is not None:
            temp_analysis_dir.cleanup()

        # Convert all sets to lists for JSON serialization
        def convert_sets_to_lists(obj):
            """Recursively convert all sets to lists in a data structure."""
            if isinstance(obj, set):
                return list(obj)
            elif isinstance(obj, dict):
                return {k: convert_sets_to_lists(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert_sets_to_lists(item) for item in obj]
            else:
                return obj
        
        result_payload = convert_sets_to_lists(result_payload)
        logger.info("✅ Converted all sets to lists for JSON serialization")

        # Optionally persist to database
        project_id = None
        if persist_project and profile_id:
            logger.info(f"📝 Attempting to save project to database (user_id={profile_id}, project_name={target.name})")
            try:
                projects_service = ProjectsService()
                if access_token and hasattr(projects_service, "apply_access_token"):
                    projects_service.apply_access_token(access_token)
                project_name = target.name or "scan"
                saved = projects_service.save_scan(
                    user_id=profile_id,
                    project_name=project_name,
                    project_path=str(target),
                    scan_data=result_payload,
                )
                project_id = saved.get("id")
                result_payload["project_id"] = project_id
                logger.info(f"✅ Project saved successfully! project_id={project_id}")
                
                # Auto-generate portfolio item using the shared helper function
                try:
                    logger.info(f"📋 Auto-generating portfolio item for project {project_id}...")
                    from services.services.portfolio_item_service import PortfolioItemService
                    from api.portfolio_routes import generate_portfolio_content_from_project
                    
                    portfolio_service = PortfolioItemService()
                    
                    # Generate and persist portfolio item
                    portfolio_result = generate_portfolio_content_from_project(
                        project=saved,
                        persist=True,
                        user_id=profile_id,
                        portfolio_service=portfolio_service
                    )
                    
                    if portfolio_result.get('id'):
                        logger.info(f"✅ Portfolio item auto-generated! portfolio_item_id={portfolio_result['id']}")
                        result_payload["portfolio_item_id"] = portfolio_result['id']
                    else:
                        logger.warning("⚠️ Portfolio generation succeeded but no ID returned")
                    
                except Exception as portfolio_err:
                    logger.warning(f"⚠️ Failed to auto-generate portfolio item: {portfolio_err}", exc_info=True)
                    # Don't fail the scan if portfolio generation fails
                    result_payload["portfolio_generation_warning"] = str(portfolio_err)
                
                # Auto-generate resume item using the shared helper function
                try:
                    logger.info(f"📝 Auto-generating resume item for project {project_id}...")
                    from services.services.resume_storage_service import ResumeStorageService
                    from api.resume_routes import generate_resume_content_from_project
                    
                    resume_service = ResumeStorageService()
                    # Apply access token if available for RLS
                    if access_token:
                        resume_service.apply_access_token(access_token)
                    
                    # Generate and persist resume item
                    resume_result = generate_resume_content_from_project(
                        project=saved,
                        persist=True,
                        user_id=profile_id,
                        resume_service=resume_service
                    )
                    
                    if resume_result.get('id'):
                        logger.info(f"✅ Resume item auto-generated! resume_item_id={resume_result['id']}")
                        result_payload["resume_item_id"] = resume_result['id']
                    else:
                        logger.warning("⚠️ Resume generation succeeded but no ID returned")
                    
                except Exception as resume_err:
                    logger.warning(f"⚠️ Failed to auto-generate resume item: {resume_err}", exc_info=True)
                    # Don't fail the scan if resume generation fails
                    result_payload["resume_generation_warning"] = str(resume_err)
                
            except Exception as persist_err:
                logger.error(f"❌ Failed to persist scan to database: {persist_err}", exc_info=True)
                result_payload["persist_warning"] = str(persist_err)
        elif not persist_project:
            logger.warning(f"⚠️  Project NOT saved: persist_project=False")
        elif not profile_id:
            logger.warning(f"⚠️  Project NOT saved: profile_id is None")

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
def set_consent(payload: ConsentUpdateRequest = Body(...)):
    if payload.external_services and not payload.data_access:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "validation_error", "message": "External services consent requires data_access"},
        )
    user_id = payload.user_id or "unknown-user"
    status_obj = ConsentStatus(
        user_id=user_id,
        data_access=bool(payload.data_access),
        external_services=bool(payload.external_services),
        updated_at=_now_iso(),
    )
    _consent_store[user_id] = status_obj
    return status_obj


# POST /api/uploads removed — real implementation is in upload_routes.py


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
        access_token=auth.access_token,
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


# Commented out - Real implementations now in project_routes.py
# @router.post("/api/projects/{project_id}/rank", response_model=RankResponse)
# def rank_project(project_id: str, payload: RankRequest):
#     if project_id not in _project_store:
#         raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
#     score = sum(payload.weights.values())
#     return RankResponse(score=score, reasons=["Stubbed ranking"])


# Commented out - Real implementation now in project_routes.py
# @router.get("/api/projects/top", response_model=List[ProjectSummary])
# def top_projects(limit: int = 3):
#     items = list(_project_store.values())[:limit]
#     return [
#         ProjectSummary(
#             project_id=p.project_id,
#             name=p.name,
#             project_type=p.project_type,
#             languages=p.languages,
#             frameworks=p.frameworks,
#             rank_score=p.rank_score,
#             created_at=p.created_at,
#         )
#         for p in items
#     ]


# Commented out - Real implementation now in project_routes.py
# @router.get("/api/projects/timeline", response_model=List[TimelineItem])
# def project_timeline():
#     items: List[TimelineItem] = []
#     for p in _project_store.values():
#         items.append(
#             TimelineItem(
#                 project_id=p.project_id,
#                 name=p.name,
#                 start_date=p.scan_timestamp,
#                 end_date=p.project_end_date,
#                 duration_days=None,
#             )
#         )
#     return items


# Commented out - Real implementation now in resume_routes.py
# @router.get("/api/resume/items", response_model=Dict[str, Any])
# def list_resume_items(limit: int = 20, offset: int = 0):
#     items = list(_resume_store.values())[offset : offset + limit]
#     return {
#         "items": items,
#         "page": Pagination(limit=limit, offset=offset, total=len(_resume_store)),
#     }
#
#
# class ResumeCreateRequest(BaseModel):
#     project_id: str
#     title: str
#     role: Optional[str] = None
#     summary: Optional[str] = None
#     evidence: List[str] = Field(default_factory=list)
#     thumbnail_url: Optional[str] = None
#
#
# @router.post("/api/resume/items", response_model=ResumeItem)
# def create_resume_item(payload: ResumeCreateRequest):
#     item_id = str(uuid.uuid4())
#     item = ResumeItem(
#         id=item_id,
#         project_id=payload.project_id,
#         title=payload.title,
#         role=payload.role,
#         summary=payload.summary,
#         evidence=payload.evidence,
#         thumbnail_url=payload.thumbnail_url,
#         created_at=_now_iso(),
#     )
#     _resume_store[item_id] = item
#     return item
#
#
# @router.get("/api/resume/items/{item_id}", response_model=ResumeItem)
# def get_resume_item(item_id: str):
#     item = _resume_store.get(item_id)
#     if not item:
#         raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resume item not found")
#     return item
#
#
# @router.delete("/api/resume/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
# def delete_resume_item(item_id: str):
#     _resume_store.pop(item_id, None)
#     return


@router.get("/api/config", response_model=ConfigResponse)
def get_config(user_id: Optional[str] = None, authorization: Optional[str] = Header(default=None)):
    if not user_id and not authorization:
        return _default_config()
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


# NOTE: `/api/search` endpoint moved to `project_routes.py` (as `/api/projects/search`).
# The previous implementation lived here; it was removed to avoid duplicate routes.


def _build_dedup_report(files: List[Dict[str, Any]]) -> DedupReport:
    total_files_analyzed = len(files)
    files_with_hash = 0
    hash_groups: Dict[str, List[Dict[str, Any]]] = {}

    for entry in files:
        file_hash = entry.get("file_hash")
        if not file_hash:
            continue
        files_with_hash += 1
        hash_groups.setdefault(file_hash, []).append(entry)

    duplicate_groups: List[DedupGroup] = []
    total_duplicate_files = 0
    total_wasted_bytes = 0
    total_dup_size = 0

    for file_hash, group_files in hash_groups.items():
        if len(group_files) < 2:
            continue
        sizes: List[int] = []
        dedup_files: List[DedupFile] = []
        for entry in group_files:
            size_value = int(entry.get("size_bytes") or 0)
            sizes.append(size_value)
            dedup_files.append(
                DedupFile(
                    path=entry.get("path") or "unknown",
                    size_bytes=size_value,
                    mime_type=entry.get("mime_type"),
                )
            )
        total_size_bytes = sum(sizes)
        wasted_bytes = sum(sizes[1:])
        total_dup_size += total_size_bytes
        total_wasted_bytes += wasted_bytes
        total_duplicate_files += len(group_files)
        duplicate_groups.append(
            DedupGroup(
                hash=file_hash,
                file_count=len(group_files),
                total_size_bytes=total_size_bytes,
                wasted_bytes=wasted_bytes,
                files=dedup_files,
            )
        )

    duplicate_groups.sort(key=lambda group: group.wasted_bytes, reverse=True)
    space_savings_percent = (total_wasted_bytes / total_dup_size * 100.0) if total_dup_size else 0.0

    summary = {
        "total_files_analyzed": total_files_analyzed,
        "files_with_hash": files_with_hash,
        "duplicate_groups_count": len(duplicate_groups),
        "total_duplicate_files": total_duplicate_files,
        "total_wasted_bytes": total_wasted_bytes,
        "space_savings_percent": round(space_savings_percent, 2),
    }
    return DedupReport(summary=summary, duplicate_groups=duplicate_groups)


@router.get("/api/dedup", response_model=DedupReport)
def dedup(project_id: str, auth: AuthContext = Depends(get_auth_context)):
    if not project_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "validation_error", "message": "project_id is required"},
        )

    try:
        uuid.UUID(project_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "validation_error", "message": "project_id must be a valid UUID"},
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "validation_error", "message": "project_id is required"},
        )

    try:
        service = _get_projects_service()
        project = service.get_project_scan(auth.user_id, project_id)
    except ProjectsServiceError as exc:
        logger.error(f"Failed to load project for dedup: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "project_error", "message": str(exc)},
        )
    except Exception as exc:
        logger.exception("Failed to load project for dedup")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "project_error", "message": "Unable to load project"},
        ) from exc

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "not_found", "message": f"Project {project_id} not found"},
        )

    scan_data = project.get("scan_data") or {}
    files = scan_data.get("files") or []
    if not isinstance(files, list):
        files = []

    return _build_dedup_report(files)
