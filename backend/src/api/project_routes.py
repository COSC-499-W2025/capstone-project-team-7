# Project API Routes Helper Module
# Provides models, services, and utilities for project scan CRUD operations
# Endpoints are registered in this module's router

from fastapi import APIRouter, HTTPException, status, Header, Depends, File, UploadFile, Query
from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Dict, Any, cast
from datetime import datetime
import asyncio
import logging
import sys
import os
from pathlib import Path
from dataclasses import asdict, is_dataclass
import uuid
import tempfile
import threading
import zipfile
from pathlib import PurePosixPath

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

try:
    from services.services.projects_service import ProjectsService, ProjectsServiceError
    from services.services.encryption import EncryptionService
    from services.services.project_overrides_service import ProjectOverridesService, ProjectOverridesServiceError
    from auth.consent_validator import ConsentValidator
    from api.llm_routes import get_user_client
except ModuleNotFoundError:  # pragma: no cover - test/import fallback
    from backend.src.services.services.projects_service import ProjectsService, ProjectsServiceError
    from backend.src.services.services.encryption import EncryptionService
    from backend.src.services.services.project_overrides_service import ProjectOverridesService, ProjectOverridesServiceError
    from backend.src.auth.consent_validator import ConsentValidator
    from backend.src.api.llm_routes import get_user_client

try:
    from scanner.parser import parse_zip
except ModuleNotFoundError:  # pragma: no cover - test/import fallback
    from backend.src.scanner.parser import parse_zip

try:
    from scanner.parser import parse_zip
except ModuleNotFoundError:  # pragma: no cover - test/import fallback
    from backend.src.scanner.parser import parse_zip

try:
    from scanner.models import ScanPreferences
except ModuleNotFoundError:  # pragma: no cover - test/import fallback
    from backend.src.scanner.models import ScanPreferences

try:
    from services.language_stats import summarize_languages
    from services.services.skills_analysis_service import SkillsAnalysisService
    from services.services.contribution_analysis_service import ContributionAnalysisService
    from local_analysis.git_repo import analyze_git_repo
    from api.upload_routes import uploads_store
except ModuleNotFoundError:  # pragma: no cover - test/import fallback
    from backend.src.services.language_stats import summarize_languages
    from backend.src.services.services.skills_analysis_service import SkillsAnalysisService
    from backend.src.services.services.contribution_analysis_service import ContributionAnalysisService
    from backend.src.local_analysis.git_repo import analyze_git_repo
    from backend.src.api.upload_routes import uploads_store

logger = logging.getLogger(__name__)

# Create router for project endpoints
router = APIRouter(prefix="/api/projects", tags=["Projects"])

# Import ALLOWED_ROLES from the service that manages roles
try:
    from services.services.project_overrides_service import ALLOWED_ROLES
except ImportError:
    from backend.src.services.services.project_overrides_service import ALLOWED_ROLES

# Initialize services
_projects_service: Optional[ProjectsService] = None
_projects_service_lock = threading.Lock()
_encryption_service: Optional[EncryptionService] = None
_overrides_service: Optional[ProjectOverridesService] = None
_encryption_service_lock = threading.Lock()
_overrides_service_lock = threading.Lock()


def get_projects_service() -> ProjectsService:
    """Get or create the ProjectsService singleton (thread-safe)."""
    global _projects_service
    if _projects_service is None:
        with _projects_service_lock:
            # Double-check pattern: verify again inside lock
            if _projects_service is None:
                try:
                    _encryption_service_instance = EncryptionService()
                except Exception:
                    _encryption_service_instance = None
                
                _projects_service = ProjectsService(
                    encryption_service=_encryption_service_instance,
                    encryption_required=False,  # Graceful degradation if encryption unavailable
                )
    return _projects_service


def get_encryption_service() -> Optional[EncryptionService]:
    """Get or create the EncryptionService singleton (thread-safe)."""
    global _encryption_service
    if _encryption_service is None:
        with _encryption_service_lock:
            # Double-check pattern: verify again inside lock
            if _encryption_service is None:
                try:
                    _encryption_service = EncryptionService()
                except Exception:
                    _encryption_service = None
    return _encryption_service


def get_overrides_service() -> ProjectOverridesService:
    """Get or create the ProjectOverridesService singleton (thread-safe).
    
    Note: This service stores user overrides with encryption when available.
    If encryption fails during initialization, overrides will be stored unencrypted
    with a warning logged. This is intentional for availability, but clients should
    be aware that sensitive fields (role, comparison_attributes) may not be encrypted.
    """
    global _overrides_service
    if _overrides_service is None:
        with _overrides_service_lock:
            # Double-check pattern: verify again inside lock
            if _overrides_service is None:
                try:
                    _encryption_service_instance = EncryptionService()
                    logger.info("Encryption service initialized successfully for overrides")
                except Exception as exc:
                    logger.warning(
                        f"Encryption service unavailable for overrides - "
                        f"sensitive fields will be stored unencrypted: {exc}"
                    )
                    _encryption_service_instance = None
                
                _overrides_service = ProjectOverridesService(
                    encryption_service=_encryption_service_instance,
                    encryption_required=False,  # Allow unencrypted storage if encryption unavailable
                )
    return _overrides_service


def normalize_project_data(project: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize project data from database to match model expectations.
    
    Handles None values for boolean and list fields by converting to defaults.
    Extracts total_files and total_lines from scan_data.summary if not present at root.
    """
    # Extract scan_data for potential fallback values
    scan_data = project.get('scan_data', {}) or {}
    summary = scan_data.get('summary', {}) or {} if isinstance(scan_data, dict) else {}
    
    # Convert None boolean fields to False
    boolean_fields = [
        'has_media_analysis', 'has_pdf_analysis', 'has_code_analysis',
        'has_git_analysis', 'has_contribution_metrics', 'has_skills_analysis',
        'has_document_analysis', 'has_skills_progress'
    ]
    for field in boolean_fields:
        if field in project and project[field] is None:
            project[field] = False
    
    # Extract total_files and total_lines from scan_data.summary if not at root
    if not project.get('total_files') and isinstance(summary, dict):
        project['total_files'] = summary.get('total_files', 0)
    
    if not project.get('total_lines') and isinstance(summary, dict):
        project['total_lines'] = summary.get('total_lines', 0)
    
    # Extract languages from scan_data if not at root
    if not project.get('languages') and isinstance(scan_data, dict):
        scan_languages = scan_data.get('languages')
        if isinstance(scan_languages, dict):
            # If languages is a dict with language stats, extract keys
            project['languages'] = list(scan_languages.keys())
        elif isinstance(scan_languages, list):
            # If languages is a list of objects with 'language' field, extract names
            if scan_languages and isinstance(scan_languages[0], dict):
                project['languages'] = [lang.get('language') for lang in scan_languages if lang.get('language')]
            else:
                project['languages'] = scan_languages
    
    # Normalize languages list to strings and drop null entries
    if 'languages' in project:
        languages = project.get('languages')
        if languages is None:
            project['languages'] = []
        elif isinstance(languages, list):
            project['languages'] = [str(lang) for lang in languages if lang]
    
    return project


def _coerce_skill_summary(summary: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not isinstance(summary, dict):
        return None
    overview = summary.get("overview") or summary.get("narrative")
    if not overview:
        return None
    return {
        "overview": overview,
        "timeline": summary.get("timeline") or summary.get("milestones") or [],
        "skills_focus": summary.get("skills_focus") or summary.get("strengths") or [],
        "suggested_next_steps": summary.get("suggested_next_steps") or summary.get("gaps") or [],
        "validation_warning": summary.get("validation_warning"),
    }


def _period_to_dict(period: Any) -> Dict[str, Any]:
    return {
        "period_label": period.period_label,
        "commits": period.commits,
        "tests_changed": period.tests_changed,
        "skill_count": period.skill_count,
        "evidence_count": period.evidence_count,
        "top_skills": period.top_skills,
        "languages": period.languages,
        "contributors": period.contributors,
        "commit_messages": period.commit_messages,
        "top_files": period.top_files,
        "activity_types": period.activity_types,
        "period_languages": period.period_languages,
    }


def _dict_to_metrics(data: Dict[str, Any]):
    from local_analysis.contribution_analyzer import (
        ProjectContributionMetrics,
        ContributorMetrics,
        ActivityBreakdown,
    )

    contributors = []
    for c in data.get("contributors", []):
        c_activity = c.get("activity_breakdown", {})
        contributor_activity = ActivityBreakdown(
            code_lines=c_activity.get("code_lines", 0),
            test_lines=c_activity.get("test_lines", 0),
            documentation_lines=c_activity.get("documentation_lines", 0),
            design_lines=c_activity.get("design_lines", 0),
            config_lines=c_activity.get("config_lines", 0),
        )

        contributor = ContributorMetrics(
            name=c.get("name", ""),
            email=c.get("email"),
            commits=c.get("commits", 0),
            commit_percentage=c.get("commit_percentage", 0.0),
            first_commit_date=c.get("first_commit_date"),
            last_commit_date=c.get("last_commit_date"),
            active_days=c.get("active_days", 0),
            activity_breakdown=contributor_activity,
            files_touched=set(c.get("files_touched", [])),
            languages_used=set(c.get("languages_used", [])),
        )
        contributors.append(contributor)

    activity = data.get("activity_breakdown", {})
    activity_breakdown = ActivityBreakdown(
        code_lines=activity.get("code_lines", 0),
        test_lines=activity.get("test_lines", 0),
        documentation_lines=activity.get("documentation_lines", 0),
        design_lines=activity.get("design_lines", 0),
        config_lines=activity.get("config_lines", 0),
    )

    return ProjectContributionMetrics(
        project_path=data.get("project_path", ""),
        project_type=data.get("project_type", "unknown"),
        total_commits=data.get("total_commits", 0),
        total_contributors=data.get("total_contributors", 0),
        project_duration_days=data.get("project_duration_days"),
        project_start_date=data.get("project_start_date"),
        project_end_date=data.get("project_end_date"),
        contributors=contributors,
        overall_activity_breakdown=activity_breakdown,
        commit_frequency=data.get("commit_frequency", 0.0),
        languages_detected=set(data.get("languages_detected", [])),
        timeline=data.get("timeline", []),
    )


def _build_skill_progression_from_scan(
    scan_data: Dict[str, Any],
    author_email: Optional[str] = None,
) -> tuple[List[Dict[str, Any]], Optional[Dict[str, Any]], Optional[str]]:
    skills_progress = scan_data.get("skills_progress")
    if isinstance(skills_progress, dict):
        existing_timeline = skills_progress.get("timeline") or []
        summary = _coerce_skill_summary(skills_progress.get("summary"))
        if existing_timeline:
            return existing_timeline, summary, None

    skills_analysis = scan_data.get("skills_analysis") or {}
    chronological = skills_analysis.get("chronological_overview") or []
    if not chronological:
        return [], None, "No skill progression timeline available."

    contribution_metrics = scan_data.get("contribution_metrics")
    metrics_obj = _dict_to_metrics(contribution_metrics) if isinstance(contribution_metrics, dict) else None

    from local_analysis.skill_progress_timeline import build_skill_progression

    author_emails = {author_email} if author_email else None
    progression = build_skill_progression(
        chronological,
        metrics_obj,
        author_emails=author_emails,
    )
    timeline = [_period_to_dict(p) for p in progression.timeline]
    if not timeline:
        return [], None, "No skill progression timeline available."
    return timeline, None, None


def _run_git_analysis_for_path(target_path: Path) -> List[Dict[str, Any]]:
    git_results: List[Dict[str, Any]] = []
    if (target_path / ".git").exists():
        result = analyze_git_repo(str(target_path))
        if "error" not in result:
            git_results.append(result)
    for git_dir in target_path.rglob(".git"):
        if git_dir.is_dir():
            repo_path = git_dir.parent
            if repo_path != target_path:
                result = analyze_git_repo(str(repo_path))
                if "error" not in result:
                    git_results.append(result)
    return git_results


def _score_to_proficiency(score: float) -> str:
    if score >= 0.8:
        return "Expert"
    if score >= 0.6:
        return "Advanced"
    if score >= 0.4:
        return "Intermediate"
    return "Beginner"


def _build_skills_analysis(service: SkillsAnalysisService) -> Dict[str, Any]:
    exported = service._extractor.export_to_dict()
    skills = exported.get("skills", [])
    skills_by_category: Dict[str, List[Dict[str, Any]]] = {}
    for skill in skills:
        category = skill.get("category", "other")
        skills_by_category.setdefault(category, []).append(
            {
                "name": skill.get("name"),
                "proficiency": _score_to_proficiency(float(skill.get("proficiency_score", 0.0))),
            }
        )
    return {
        "success": True,
        "total_skills": exported.get("summary", {}).get("total_skills", len(skills)),
        "skills_by_category": skills_by_category,
        "skills": skills,
        "chronological_overview": exported.get("chronological_overview", []),
        "skill_progression": exported.get("skill_progression", {}),
        "skill_adoption_timeline": exported.get("skill_adoption_timeline", []),
    }


def _serialize_parse_files(files: List[Any]) -> List[Dict[str, Any]]:
    serialized = []
    for meta in files:
        created_at = getattr(meta, "created_at", None)
        modified_at = getattr(meta, "modified_at", None)
        media_info = getattr(meta, "media_info", None)
        if media_info is not None and is_dataclass(media_info) and not isinstance(media_info, type):
            media_info = asdict(cast(Any, media_info))
        serialized.append(
            {
                "path": meta.path,
                "size_bytes": meta.size_bytes,
                "mime_type": meta.mime_type,
                "created_at": created_at.isoformat() if created_at else None,
                "modified_at": modified_at.isoformat() if modified_at else None,
                "file_hash": getattr(meta, "file_hash", None),
                "media_info": media_info,
            }
        )
    return serialized


def _serialize_parse_issues(issues: List[Any]) -> List[Dict[str, Any]]:
    return [{"path": issue.path, "code": issue.code, "message": issue.message} for issue in issues]


def _serialize_contribution_metrics(metrics: Any) -> Dict[str, Any]:
    payload = asdict(metrics)
    if "languages_detected" in payload and isinstance(payload["languages_detected"], set):
        payload["languages_detected"] = list(payload["languages_detected"])
    return payload


def _extract_archive_for_analysis(storage_path: Path, temp_path: Path) -> Path:
    with zipfile.ZipFile(storage_path, "r") as zf:
        for member in zf.namelist():
            member_path = PurePosixPath(member)
            if member_path.is_absolute():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Archive contains absolute paths",
                )
            if any(part == ".." for part in member_path.parts):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Archive contains invalid path traversal",
                )

            target_path_member = temp_path / member
            try:
                target_path_member.resolve().relative_to(temp_path.resolve())
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Archive contains invalid path traversal",
                )

            zf.extract(member, temp_path)

    content_dirs = list(temp_path.iterdir())
    if len(content_dirs) == 1 and content_dirs[0].is_dir():
        return content_dirs[0]
    return temp_path


def _run_code_analysis_for_path(
    target_path: Path,
    preferences: Optional[ScanPreferences],
) -> Optional[Dict[str, Any]]:
    try:
        from services.services.code_analysis_service import CodeAnalysisService, CodeAnalysisUnavailableError
    except ImportError:
        logger.info("Code analysis unavailable (services.services.code_analysis_service not installed)")
        return None

    try:
        service = CodeAnalysisService()
        result = service.run_analysis(target_path, preferences)

        summary = getattr(result, "summary", {}) or {}
        return {
            "total_files": summary.get("total_files", 0),
            "total_lines": summary.get("total_lines", 0),
            "code_lines": summary.get("total_code", 0),
            "comment_lines": summary.get("total_comments", 0),
            "functions": summary.get("total_functions", 0),
            "classes": summary.get("total_classes", 0),
            "avg_complexity": summary.get("avg_complexity"),
            "avg_maintainability": summary.get("avg_maintainability"),
        }
    except Exception as exc:
        if "CodeAnalysisUnavailableError" in type(exc).__name__ or "tree-sitter" in str(exc).lower():
            logger.info("Code analysis unavailable (tree-sitter not installed)")
        else:
            logger.warning(f"Code analysis failed: {exc}")
        return None


def verify_auth_token(authorization: Optional[str] = Header(None)) -> str:
    """
    Verify JWT token from Authorization header.
    
    Args:
        authorization: Bearer token from header
    
    Returns:
        User ID extracted from token
    
    Raises:
        HTTPException: If token is missing or invalid
    """
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authorization token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Extract token from "Bearer <token>" format
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header format. Use 'Bearer <token>'",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token = parts[1]
    
    # For now, we'll do basic JWT validation
    # In production, verify the signature against Supabase's public key
    try:
        import jwt
        # Decode without verification for now (development)
        # In production, use jwt.decode(token, key, algorithms=["HS256"])
        payload = jwt.decode(token, options={"verify_signature": False})
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: missing user ID",
            )
        return user_id
    except Exception as exc:
        logger.error(f"Token verification failed: {exc}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )


# ============================================================================
# Request/Response Models
# ============================================================================

class ProjectScanData(BaseModel):
    """Project scan data structure."""
    summary: Optional[Dict[str, Any]] = None
    code_analysis: Optional[Dict[str, Any]] = None
    skills_analysis: Optional[Dict[str, Any]] = None
    git_analysis: Optional[List[Dict[str, Any]]] = None
    contribution_metrics: Optional[Dict[str, Any]] = None
    contribution_ranking: Optional[Dict[str, Any]] = None
    media_analysis: Optional[Dict[str, Any]] = None
    pdf_analysis: Optional[List[Dict[str, Any]]] = None
    document_analysis: Optional[List[Dict[str, Any]]] = None
    skills_progress: Optional[Dict[str, Any]] = None
    languages: Optional[List[str]] = None
    files: Optional[List[Dict[str, Any]]] = None


class CreateProjectRequest(BaseModel):
    """Request model for creating a new project scan."""
    project_name: str = Field(..., description="Name/identifier for the project")
    project_path: str = Field(..., description="Filesystem path that was scanned")
    scan_data: ProjectScanData = Field(..., description="Complete scan results")
    role: Optional[str] = Field(None, description="User's role in the project (author, contributor, lead, maintainer, reviewer)")


class ProjectMetadata(BaseModel):
    """Lightweight project metadata (without full scan_data)."""
    id: str
    project_name: str
    project_path: str
    scan_timestamp: Optional[str] = None
    total_files: int = 0
    total_lines: int = 0
    languages: Optional[List[str]] = None
    has_media_analysis: Optional[bool] = False
    has_pdf_analysis: Optional[bool] = False
    has_code_analysis: Optional[bool] = False
    has_git_analysis: Optional[bool] = False
    has_contribution_metrics: Optional[bool] = False
    has_skills_analysis: Optional[bool] = False
    has_document_analysis: Optional[bool] = False
    has_skills_progress: Optional[bool] = False
    contribution_score: Optional[float] = None
    user_commit_share: Optional[float] = None
    total_commits: Optional[int] = None
    primary_contributor: Optional[str] = None
    project_end_date: Optional[str] = None
    thumbnail_url: Optional[str] = None
    created_at: Optional[str] = None
    role: Optional[str] = Field(None, description="User's role in the project (author, contributor, lead, maintainer, reviewer)")


class ProjectOverrides(BaseModel):
    """User-defined overrides for project display and metadata.
    
    Note on encryption:
    - role and comparison_attributes are encrypted at rest when encryption is available
    - Other fields (evidence, highlighted_skills, dates) are stored unencrypted
    - If encryption service is unavailable, all fields are stored unencrypted with a warning logged
    """
    role: Optional[str] = Field(None, description="User's role/title for this project")
    evidence: Optional[List[str]] = Field(None, description="List of accomplishment bullet points")
    thumbnail_url: Optional[str] = Field(None, description="Custom thumbnail URL")
    custom_rank: Optional[float] = Field(None, description="Manual ranking override (0-100)")
    start_date_override: Optional[str] = Field(None, description="Override for project start date (ISO date)")
    end_date_override: Optional[str] = Field(None, description="Override for project end date (ISO date)")
    comparison_attributes: Optional[Dict[str, str]] = Field(
        None, 
        description="Custom key-value pairs for comparisons (encrypted at rest)"
    )
    highlighted_skills: Optional[List[str]] = Field(None, description="Skills to highlight for this project")
    
    @field_validator('custom_rank')
    @classmethod
    def validate_custom_rank(cls, v: Optional[float]) -> Optional[float]:
        """Validate custom_rank is between 0 and 100."""
        if v is not None and not (0 <= v <= 100):
            raise ValueError('custom_rank must be between 0 and 100')
        return v


class ProjectDetail(ProjectMetadata):
    """Full project details including scan data."""
    scan_data: Optional[Dict[str, Any]] = None
    user_overrides: Optional[ProjectOverrides] = None


class CreateProjectResponse(BaseModel):
    """Response model for project creation."""
    id: str
    project_name: str
    scan_timestamp: str
    message: str = "Project scan saved successfully"


class ProjectListResponse(BaseModel):
    """Response model for project list."""
    count: int
    projects: List[ProjectMetadata]


class ErrorResponse(BaseModel):
    """Standard error response."""
    detail: str
    error_code: Optional[str] = None


class DeleteInsightsResponse(BaseModel):
    """Response model for insights deletion."""
    message: str = "Insights cleared successfully"
    insights_deleted_at: str


class ThumbnailUploadResponse(BaseModel):
    """Response model for thumbnail upload."""
    thumbnail_url: str
    message: str = "Thumbnail uploaded successfully"


class ThumbnailUpdateRequest(BaseModel):
    """Request model for updating thumbnail URL."""
    thumbnail_url: str = Field(..., description="Public URL of the thumbnail image")


class ThumbnailUpdateResponse(BaseModel):
    """Response model for thumbnail URL update."""
    message: str = "Thumbnail URL updated successfully"


class RoleUpdateRequest(BaseModel):
    """Request model for updating user role in a project."""
    role: str = Field(..., description="User's role in the project (author, contributor, lead, maintainer, reviewer)")


class RoleUpdateResponse(BaseModel):
    """Response model for role update."""
    project_id: str
    role: str
    message: str = "Role updated successfully"


class RankProjectRequest(BaseModel):
    """Request to compute ranking for a specific project."""
    user_email: Optional[str] = Field(None, description="User's email for contribution matching")
    user_name: Optional[str] = Field(None, description="User's name for contribution matching")


class RankingComponents(BaseModel):
    """Detailed breakdown of ranking score components."""
    volume: float = Field(..., description="Commit volume score (0-1)")
    user_share: float = Field(..., description="User's share of commits (0-1)")
    recency: float = Field(..., description="Project recency score (0-1)")
    frequency: float = Field(..., description="Commit frequency score (0-1)")
    activity_mix: float = Field(..., description="Activity diversity score (0-1)")


class RankProjectResponse(BaseModel):
    """Response with project ranking details."""
    project_id: str
    project_name: str
    score: float = Field(..., description="Overall ranking score (0-100)")
    user_commit_share: float = Field(..., description="User's percentage of commits (0-1)")
    total_commits: int = Field(..., description="Total commits in the project")
    components: RankingComponents = Field(..., description="Score component breakdown")
    reasons: List[str] = Field(..., description="Human-readable ranking reasons")


class TopProjectsResponse(BaseModel):
    """Response with top-ranked projects."""
    count: int
    projects: List[ProjectMetadata]


class ProjectTimelineEntry(BaseModel):
    """Single entry in project timeline."""
    project: Dict[str, Any] = Field(..., description="Full project object with all metadata")
    display_date: str = Field(..., description="Date to use for timeline display (end_date or scan_timestamp)")


class ProjectTimelineWarning(BaseModel):
    """Warning about a project that couldn't be included in timeline."""
    project_id: str
    project_name: str
    issue: str
    details: str


class ProjectTimelineResponse(BaseModel):
    """Response with chronologically ordered projects."""
    count: int
    timeline: List[ProjectTimelineEntry]
    warnings: Optional[List[ProjectTimelineWarning]] = Field(
        default=None,
        description="Projects with date parsing issues that were excluded from timeline"
    )


class SkillProgressPeriodModel(BaseModel):
    """Single period entry in a skills progression timeline."""
    period_label: str
    commits: int = 0
    tests_changed: int = 0
    skill_count: int = 0
    evidence_count: int = 0
    top_skills: List[str] = Field(default_factory=list)
    languages: Dict[str, int] = Field(default_factory=dict)
    contributors: int = 0
    commit_messages: List[str] = Field(default_factory=list)
    top_files: List[str] = Field(default_factory=list)
    activity_types: List[str] = Field(default_factory=list)
    period_languages: Dict[str, int] = Field(default_factory=dict)


class SkillProgressSummaryModel(BaseModel):
    """Summary of skill progression generated by an LLM."""
    overview: str
    timeline: List[str] = Field(default_factory=list)
    skills_focus: List[str] = Field(default_factory=list)
    suggested_next_steps: List[str] = Field(default_factory=list)
    validation_warning: Optional[str] = None


class SkillProgressTimelineResponse(BaseModel):
    """Timeline response for skill progression."""
    project_id: str
    timeline: List[SkillProgressPeriodModel]
    note: Optional[str] = None
    summary: Optional[SkillProgressSummaryModel] = None


class SkillProgressSummaryResponse(BaseModel):
    """Summary response for skill progression."""
    project_id: str
    summary: Optional[SkillProgressSummaryModel] = None
    note: Optional[str] = None
    llm_status: Optional[str] = None


class ProjectFromUploadRequest(BaseModel):
    """Request to create a project from an uploaded archive."""
    upload_id: str = Field(..., description="Upload ID from /api/uploads")
    project_name: Optional[str] = Field(None, description="Override project name")
    project_path: Optional[str] = Field(None, description="Optional display path for the project")
    relevant_only: bool = Field(False, description="Only include relevant files")
    preferences: Optional[Dict[str, Any]] = Field(
        None,
        description="Optional scan preferences (allowed_extensions, excluded_dirs, max_file_size_bytes, follow_symlinks)",
    )


# ============================================================================
# Project Overrides Models
# ============================================================================

class ProjectOverridesRequest(BaseModel):
    """Request model for updating project overrides (partial update supported)."""
    role: Optional[str] = Field(None, description="User's role/title for this project")
    evidence: Optional[List[str]] = Field(None, description="List of accomplishment bullet points")
    thumbnail_url: Optional[str] = Field(None, description="Custom thumbnail URL")
    custom_rank: Optional[float] = Field(None, description="Manual ranking override (0-100)")
    start_date_override: Optional[str] = Field(None, description="Override for project start date (ISO date)")
    end_date_override: Optional[str] = Field(None, description="Override for project end date (ISO date)")
    comparison_attributes: Optional[Dict[str, str]] = Field(
        None, 
        description="Custom key-value pairs for comparisons (encrypted at rest)"
    )
    highlighted_skills: Optional[List[str]] = Field(None, description="Skills to highlight for this project")
    
    @field_validator('custom_rank')
    @classmethod
    def validate_custom_rank(cls, v: Optional[float]) -> Optional[float]:
        """Validate custom_rank is between 0 and 100."""
        if v is not None and not (0 <= v <= 100):
            raise ValueError('custom_rank must be between 0 and 100')
        return v


class ProjectOverridesResponse(BaseModel):
    """Response model for project overrides."""
    project_id: str
    overrides: ProjectOverrides
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class DeleteOverridesResponse(BaseModel):
    """Response model for overrides deletion."""
    message: str = "Overrides cleared successfully"


# ============================================================================
# API Endpoints
# ============================================================================

@router.post(
    "",
    response_model=CreateProjectResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid request"},
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        500: {"model": ErrorResponse, "description": "Server error"},
    },
)
async def create_project(
    request: CreateProjectRequest,
    user_id: str = Depends(verify_auth_token),
) -> CreateProjectResponse:
    """
    Create a new project scan or update existing one.
    
    - **project_name**: Unique identifier for the project within user's account
    - **project_path**: Original filesystem path that was scanned
    - **scan_data**: Complete scan results (code analysis, skills, git, etc.)
    
    Acceptance Criteria:
    - Saved scans persist in encrypted storage
    - Scans are retrievable per user
    """
    try:
        # Validate input
        if not request.project_name.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="project_name cannot be empty",
            )
        
        if not request.project_path.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="project_path cannot be empty",
            )
        
        # Convert request to dictionary for service
        scan_data_dict = request.scan_data.dict(exclude_none=True)
        
        # Validate role if provided
        if request.role is not None and request.role not in ALLOWED_ROLES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid role '{request.role}'. Allowed roles: {', '.join(ALLOWED_ROLES)}",
            )
        
        # Get service and save scan
        service = get_projects_service()
        result = service.save_scan(
            user_id=user_id,
            project_name=request.project_name,
            project_path=request.project_path,
            scan_data=scan_data_dict,
            role=request.role,
        )
        
        return CreateProjectResponse(
            id=result.get("id", ""),
            project_name=result.get("project_name", ""),
            scan_timestamp=result.get("scan_timestamp", datetime.now().isoformat()),
            message="Project scan saved successfully",
        )
    
    except HTTPException:
        raise
    except ProjectsServiceError as exc:
        logger.error(f"Projects service error: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save project: {str(exc)}",
        )
    except Exception as exc:
        logger.exception("Unexpected error creating project")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred",
        )


@router.post(
    "/from-upload",
    response_model=CreateProjectResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid request"},
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        403: {"model": ErrorResponse, "description": "Forbidden"},
        404: {"model": ErrorResponse, "description": "Not found"},
        500: {"model": ErrorResponse, "description": "Server error"},
    },
)
async def create_project_from_upload(
    request: ProjectFromUploadRequest,
    user_id: str = Depends(verify_auth_token),
) -> CreateProjectResponse:
    """Create a project from an uploaded zip using the existing analysis pipeline."""
    try:
        upload_id = request.upload_id.strip()
        if not upload_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="upload_id cannot be empty",
            )

        if upload_id not in uploads_store:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Upload with ID '{upload_id}' not found",
            )

        upload_data = uploads_store[upload_id]
        if upload_data.get("user_id") != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this upload",
            )

        storage_path = Path(upload_data["storage_path"])
        if not storage_path.exists():
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Upload file not found on disk",
            )

        preferences = None
        if request.preferences:
            preferences = ScanPreferences(
                allowed_extensions=request.preferences.get("allowed_extensions"),
                excluded_dirs=request.preferences.get("excluded_dirs"),
                max_file_size_bytes=request.preferences.get("max_file_size_bytes"),
                follow_symlinks=request.preferences.get("follow_symlinks"),
            )

        parse_result = parse_zip(
            storage_path,
            relevant_only=request.relevant_only,
            preferences=preferences,
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            analysis_target = _extract_archive_for_analysis(storage_path, Path(temp_dir))
            languages = summarize_languages(parse_result.files)
            summary: Dict[str, Any] = dict(parse_result.summary)
            summary["languages"] = languages

            git_analysis = _run_git_analysis_for_path(analysis_target)
            git_data = git_analysis[0] if git_analysis else None

            code_analysis = _run_code_analysis_for_path(analysis_target, preferences)

            skills_service = SkillsAnalysisService()
            skills_service.extract_skills(
                target_path=analysis_target,
                code_analysis_result=code_analysis,
                git_analysis_result=git_data,
            )
            skills_analysis = _build_skills_analysis(skills_service)

            contribution_metrics_payload = None
            metrics_obj = None
            if git_data:
                try:
                    metrics_obj = ContributionAnalysisService().analyze_contributions(
                        git_analysis=git_data,
                        code_analysis=code_analysis,
                        parse_result=parse_result,
                    )
                    contribution_metrics_payload = _serialize_contribution_metrics(metrics_obj)
                except Exception:
                    contribution_metrics_payload = None

            skills_progress = None
            chronological = skills_analysis.get("chronological_overview") or []
            if chronological:
                from local_analysis.skill_progress_timeline import build_skill_progression

                progression = build_skill_progression(chronological, metrics_obj)
                skills_progress = {
                    "timeline": [_period_to_dict(period) for period in progression.timeline],
                }

            scan_data: Dict[str, Any] = {
                "archive": str(storage_path),
                "summary": summary,
                "files": _serialize_parse_files(parse_result.files),
                "issues": _serialize_parse_issues(parse_result.issues),
                "languages": languages,
                "git_analysis": git_analysis,
                "contribution_metrics": contribution_metrics_payload,
                "skills_analysis": skills_analysis,
                "skills_progress": skills_progress,
            }

            if code_analysis:
                scan_data["code_analysis"] = {"metrics": code_analysis}

        project_path = request.project_path or upload_data.get("metadata", {}).get("original_filename") or storage_path.name
        project_name = request.project_name or Path(project_path).stem

        service = get_projects_service()
        result = service.save_scan(
            user_id=user_id,
            project_name=project_name,
            project_path=project_path,
            scan_data=scan_data,
        )

        return CreateProjectResponse(
            id=result.get("id", ""),
            project_name=result.get("project_name", project_name),
            scan_timestamp=result.get("scan_timestamp", datetime.now().isoformat()),
            message="Project scan saved successfully",
        )

    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Project creation from upload failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create project: {str(exc)}",
        )


@router.get(
    "",
    response_model=ProjectListResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        500: {"model": ErrorResponse, "description": "Server error"},
    },
)
async def list_projects(
    user_id: str = Depends(verify_auth_token),
) -> ProjectListResponse:
    """
    Get all projects for the authenticated user.
    
    Returns metadata for all saved scans (ordered by most recent first).
    Does NOT include full scan_data to keep response lightweight.
    
    Acceptance Criteria:
    - Projects are retrievable per user
    - Only user's own projects are returned
    - Results ordered by scan_timestamp (newest first)
    """
    try:
        service = get_projects_service()
        # Use get_user_projects_with_roles to include role field from project_overrides
        projects = service.get_user_projects_with_roles(user_id)
        
        # Normalize and convert to ProjectMetadata objects for response
        metadata_projects = [
            ProjectMetadata(**normalize_project_data(project)) for project in projects
        ]
        
        return ProjectListResponse(
            count=len(metadata_projects),
            projects=metadata_projects,
        )
    
    except ProjectsServiceError as exc:
        logger.error(f"Projects service error: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve projects: {str(exc)}",
        )
    except Exception as exc:
        logger.exception("Unexpected error listing projects")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred",
        )


@router.get("/search")
async def search_projects(
    q: Optional[str] = None,
    scope: Optional[str] = None,
    project_id: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    user_id: str = Depends(verify_auth_token),
) -> Dict[str, Any]:
    """Search across projects' scan data (files/skills) for the authenticated user.

    Endpoint available at: `/api/projects/search`.
    """
    if not q or not q.strip():
        return {"items": [], "page": {"limit": limit, "offset": offset, "total": 0}}

    query_lower = q.lower()
    scope = scope or "all"

    try:
        service = get_projects_service()

        # If project_id is specified, search within that project only
        if project_id:
            try:
                uuid.UUID(project_id)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={"code": "validation_error", "message": "project_id must be a valid UUID"},
                )

            project = await asyncio.to_thread(service.get_project_scan, user_id, project_id)
            if not project:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail={"code": "not_found", "message": f"Project {project_id} not found"},
                )

            projects = [project]
        else:
            # Search across all user's projects (with scan_data)
            projects = await asyncio.to_thread(service.get_user_projects_with_scan_data, user_id)

        results: List[Dict[str, Any]] = []

        for project in projects:
            pid = project.get("id")
            pname = project.get("project_name", "Unknown")
            scan_data = project.get("scan_data", {}) or {}

            # Search in files
            if scope in ["all", "files"]:
                files = scan_data.get("files", []) or []
                for file_entry in files:
                    file_path = file_entry.get("path", "") or ""
                    file_name = Path(file_path).name if file_path else ""
                    mime_type = file_entry.get("mime_type", "") or file_entry.get("type", "")

                    if (query_lower in file_path.lower() or
                        query_lower in file_name.lower() or
                        query_lower in mime_type.lower()):
                        results.append({
                            "type": "file",
                            "project_id": pid,
                            "project_name": pname,
                            "path": file_path,
                            "name": file_name,
                            "size_bytes": file_entry.get("size_bytes") or file_entry.get("size") or 0,
                            "mime_type": mime_type,
                        })

            # Search in skills
            if scope in ["all", "skills"]:
                skills_data = scan_data.get("skills_analysis", {}) or {}
                if skills_data and skills_data.get("success"):
                    skills = skills_data.get("skills", {}) or {}
                    for category, skill_list in skills.items():
                        if isinstance(skill_list, list):
                            for skill in skill_list:
                                if isinstance(skill, str) and query_lower in skill.lower():
                                    results.append({
                                        "type": "skill",
                                        "project_id": pid,
                                        "project_name": pname,
                                        "category": category,
                                        "skill": skill,
                                    })
                                elif isinstance(skill, dict):
                                    skill_name = skill.get("name", "") or ""
                                    if query_lower in skill_name.lower():
                                        results.append({
                                            "type": "skill",
                                            "project_id": pid,
                                            "project_name": pname,
                                            "category": category,
                                            "skill": skill_name,
                                            "proficiency": skill.get("proficiency"),
                                        })

        # Pagination
        total = len(results)
        paginated = results[offset: offset + limit]

        return {"items": paginated, "page": {"limit": limit, "offset": offset, "total": total}}

    except ProjectsServiceError as exc:
        logger.error(f"Failed to search projects: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "search_error", "message": str(exc)},
        )
    except Exception as exc:
        logger.exception("Unexpected error during search")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "search_error", "message": "An unexpected error occurred"},
        ) from exc


@router.get("/top", response_model=TopProjectsResponse, status_code=200)
async def get_top_projects(
    limit: int = 10,
    user_id: str = Depends(verify_auth_token),
) -> TopProjectsResponse:
    """
    Get top-ranked projects sorted by contribution score.
    
    - **limit**: Maximum number of projects to return (default: 10)
    
    Returns projects sorted by contribution_score in descending order.
    Only includes projects that have been ranked (have contribution_score).
    """
    try:
        service = get_projects_service()
        
        # Get all user projects (run in thread pool to avoid blocking event loop)
        projects = await asyncio.to_thread(service.get_user_projects, user_id)
        
        # Filter to only projects with contribution scores and sort
        ranked_projects = [
            p for p in projects
            if p.get("contribution_score") is not None
        ]
        
        ranked_projects.sort(
            key=lambda p: p.get("contribution_score", 0),
            reverse=True
        )
        
        # Apply limit
        top_projects = ranked_projects[:limit]
        
        return TopProjectsResponse(
            count=len(top_projects),
            projects=top_projects,
        )
    
    except Exception as exc:
        logger.exception(f"Error fetching top projects: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch top projects: {str(exc)}",
        )


@router.get("/timeline", response_model=ProjectTimelineResponse, status_code=200)
async def get_project_timeline(
    user_id: str = Depends(verify_auth_token),
) -> ProjectTimelineResponse:
    """
    Get projects ordered chronologically by end date (newest first).
    
    Uses the following priority for determining the display date:
    1. end_date_override from user overrides (if set)
    2. project_end_date from scan data (if set)
    3. scan_timestamp as fallback
    
    This allows users to correct chronology via overrides.
    """
    try:
        service = get_projects_service()
        overrides_service = get_overrides_service()
        
        # Get all user projects (run in thread pool to avoid blocking event loop)
        projects = await asyncio.to_thread(service.get_user_projects, user_id)
        
        # Get project IDs for batch override fetch (filter out any None values)
        project_ids: List[str] = []
        for p in projects:
            pid = p.get("id")
            if pid:
                project_ids.append(pid)
        
        # Batch fetch overrides for all projects
        overrides_map: Dict[str, Dict[str, Any]] = {}
        if project_ids:
            overrides_map = await asyncio.to_thread(
                overrides_service.get_overrides_for_projects, user_id, project_ids
            )
        
        # Build timeline entries with full project objects
        timeline_entries = []
        warnings = []
        
        for project in projects:
            project_id = project.get("id")
            project_name = project.get("project_name", "Unknown")
            project_overrides = overrides_map.get(project_id, {})
            
            # Priority: end_date_override > project_end_date > scan_timestamp > created_at
            display_date = None
            
            # 1. Check for end_date_override
            end_date_override = project_overrides.get("end_date_override")
            if end_date_override:
                display_date = end_date_override
            
            # 2. Check for project_end_date from scan data
            if not display_date:
                project_end_date = project.get("project_end_date")
                if project_end_date:
                    display_date = project_end_date
            
            # 3. Fall back to scan_timestamp or created_at
            if not display_date:
                display_date = project.get("scan_timestamp") or project.get("created_at")
            
            if not display_date:
                # Warn about projects without any date information
                warnings.append({
                    "project_id": project_id or "unknown",
                    "project_name": project_name,
                    "issue": "missing_date",
                    "details": "Project has no date information (no end_date_override, project_end_date, scan_timestamp, or created_at)"
                })
                logger.warning(f"Project {project_name} ({project_id}) excluded from timeline: no date information")
                continue
            
            # Parse to datetime for proper sorting
            try:
                # Handle various timestamp formats
                ts_str = display_date.replace("Z", "+00:00")
                # Handle date-only format (YYYY-MM-DD)
                if len(ts_str) == 10:
                    ts_str = ts_str + "T00:00:00+00:00"
                dt = datetime.fromisoformat(ts_str)
            except Exception as e:
                # Warn about date parsing failures
                warnings.append({
                    "project_id": project_id or "unknown",
                    "project_name": project_name,
                    "issue": "invalid_date_format",
                    "details": f"Failed to parse date '{display_date}': {str(e)}"
                })
                logger.error(f"Failed to parse timestamp for {project_name}: {display_date}, error: {e}")
                continue
            
            timeline_entries.append({
                "project": project,
                "display_date": display_date,
                "_sort_key": dt,  # Use datetime object for sorting
            })
        
        # Sort by datetime object (newest first) - explicit comparison
        timeline_entries.sort(
            key=lambda e: e["_sort_key"],
            reverse=True
        )
        
        # Debug: Print order to console
        print("\n=== Timeline Order ===")
        for i, entry in enumerate(timeline_entries, 1):
            print(f"{i}. {entry['project'].get('project_name')} - {entry['display_date']} (dt: {entry['_sort_key']})")
        print("=====================\n")
        
        # Remove sort key before returning
        for entry in timeline_entries:
            entry.pop("_sort_key", None)
        
        return ProjectTimelineResponse(
            count=len(timeline_entries),
            timeline=timeline_entries,
            warnings=warnings if warnings else None,
        )
    
    except Exception as exc:
        logger.exception(f"Error fetching project timeline: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch project timeline: {str(exc)}",
        )


@router.get(
    "/{project_id}/skills/timeline",
    response_model=SkillProgressTimelineResponse,
    status_code=status.HTTP_200_OK,
)
async def get_project_skill_timeline(
    project_id: str,
    author_email: Optional[str] = Query(None, description="Filter timeline to a specific contributor email"),
    user_id: str = Depends(verify_auth_token),
) -> SkillProgressTimelineResponse:
    """Get skill progression timeline for a project."""
    try:
        service = get_projects_service()
        project = await asyncio.to_thread(service.get_project_scan, user_id, project_id)

        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project {project_id} not found",
            )

        scan_data = project.get("scan_data") or {}
        timeline, summary, note = _build_skill_progression_from_scan(scan_data, author_email)

        return SkillProgressTimelineResponse(
            project_id=project_id,
            timeline=[SkillProgressPeriodModel(**entry) for entry in timeline],
            note=note,
            summary=SkillProgressSummaryModel(**summary) if summary else None,
        )

    except HTTPException:
        raise
    except ProjectsServiceError as exc:
        logger.error(f"Projects service error: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve skill progression: {str(exc)}",
        )
    except Exception as exc:
        logger.exception("Unexpected error fetching skill progression timeline")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred",
        )


@router.post(
    "/{project_id}/skills/summary",
    response_model=SkillProgressSummaryResponse,
    status_code=status.HTTP_200_OK,
)
async def generate_project_skill_summary(
    project_id: str,
    user_id: str = Depends(verify_auth_token),
) -> SkillProgressSummaryResponse:
    """Generate an LLM summary for the skill progression timeline."""
    try:
        service = get_projects_service()
        project = await asyncio.to_thread(service.get_project_scan, user_id, project_id)

        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project {project_id} not found",
            )

        scan_data = project.get("scan_data") or {}
        timeline, summary, note = _build_skill_progression_from_scan(scan_data)
        if not timeline:
            return SkillProgressSummaryResponse(
                project_id=project_id,
                summary=SkillProgressSummaryModel(**summary) if summary else None,
                note=note or "No skill progression timeline available.",
                llm_status="skipped:no_timeline",
            )

        if summary:
            return SkillProgressSummaryResponse(
                project_id=project_id,
                summary=SkillProgressSummaryModel(**summary),
                llm_status="used:cached",
            )

        consent_validator = ConsentValidator()
        try:
            has_consent = consent_validator.validate_external_services_consent(user_id)
        except Exception:
            return SkillProgressSummaryResponse(
                project_id=project_id,
                note="Consent check failed. Please retry.",
                llm_status="skipped:consent_check_failed",
            )

        if not has_consent:
            return SkillProgressSummaryResponse(
                project_id=project_id,
                note="External services consent not granted.",
                llm_status="skipped:consent_not_granted",
            )

        client = get_user_client(user_id)
        if client is None:
            return SkillProgressSummaryResponse(
                project_id=project_id,
                note="No API key verified. Please verify your key in Settings.",
                llm_status="skipped:no_api_key",
            )

        from analyzer.llm.skill_progress_summary import summarize_skill_progress

        def call_model(prompt: str) -> str:
            return client._make_llm_call(
                [{"role": "user", "content": prompt}],
                max_tokens=1200,
                temperature=0.6,
                response_format={"type": "json_object"},
            )

        summary_result = summarize_skill_progress(timeline, call_model)

        return SkillProgressSummaryResponse(
            project_id=project_id,
            summary=SkillProgressSummaryModel(
                overview=summary_result.overview,
                timeline=summary_result.timeline,
                skills_focus=summary_result.skills_focus,
                suggested_next_steps=summary_result.suggested_next_steps,
                validation_warning=summary_result.validation_warning,
            ),
            llm_status="used",
        )

    except HTTPException:
        raise
    except ProjectsServiceError as exc:
        logger.error(f"Projects service error: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate skill summary: {str(exc)}",
        )
    except Exception as exc:
        logger.exception("Unexpected error generating skill progression summary")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred",
        )


@router.get(
    "/{project_id}",
    response_model=ProjectDetail,
    responses={
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        404: {"model": ErrorResponse, "description": "Project not found"},
        500: {"model": ErrorResponse, "description": "Server error"},
    },
)
async def get_project(
    project_id: str,
    user_id: str = Depends(verify_auth_token),
) -> ProjectDetail:
    """
    Get full details for a specific project including scan data.
    
    - **project_id**: UUID of the project to retrieve
    
    Returns encrypted scan data decrypted for display.
    Also includes any user-defined overrides (role, highlighted skills, date overrides, etc.)
    
    Acceptance Criteria:
    - Full scan data is retrievable by project ID
    - Only project owner can access their projects
    - User overrides are included in the response
    """
    try:
        service = get_projects_service()
        project = await asyncio.to_thread(service.get_project_scan, user_id, project_id)
        
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project {project_id} not found",
            )
        
        # Normalize project data before converting to model
        project = normalize_project_data(project)
        
        # Fetch user overrides for this project
        overrides_service = get_overrides_service()
        overrides = await asyncio.to_thread(overrides_service.get_overrides, user_id, project_id)
        
        # Build user_overrides object (or None if no overrides exist)
        user_overrides = None
        if overrides:
            user_overrides = ProjectOverrides(
                role=overrides.get("role"),
                evidence=overrides.get("evidence", []),
                thumbnail_url=overrides.get("thumbnail_url"),
                custom_rank=overrides.get("custom_rank"),
                start_date_override=overrides.get("start_date_override"),
                end_date_override=overrides.get("end_date_override"),
                comparison_attributes=overrides.get("comparison_attributes", {}),
                highlighted_skills=overrides.get("highlighted_skills", []),
            )
        
        # Convert to ProjectDetail object for response
        return ProjectDetail(**project, user_overrides=user_overrides)
    
    except HTTPException:
        raise
    except ProjectsServiceError as exc:
        logger.error(f"Projects service error: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve project: {str(exc)}",
        )
    except Exception as exc:
        logger.exception("Unexpected error retrieving project")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred",
        )


@router.delete(
    "/{project_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        404: {"model": ErrorResponse, "description": "Project not found"},
        500: {"model": ErrorResponse, "description": "Server error"},
    },
)
async def delete_project(
    project_id: str,
    user_id: str = Depends(verify_auth_token),
) -> None:
    """
    Delete a project scan.
    
    - **project_id**: UUID of the project to delete
    
    This removes the scan results and all associated data.
    Only the project owner can delete their projects.
    
    Returns 204 No Content on success.
    """
    try:
        service = get_projects_service()
        success = service.delete_project(user_id, project_id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project {project_id} not found or already deleted",
            )
    
    except HTTPException:
        raise
    except ProjectsServiceError as exc:
        logger.error(f"Projects service error: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete project: {str(exc)}",
        )
    except Exception as exc:
        logger.exception("Unexpected error deleting project")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred",
        )


# ============================================================================
# Project Ranking Endpoints
# ============================================================================

@router.post("/{project_id}/rank", response_model=RankProjectResponse, status_code=200)
async def rank_project(
    project_id: str,
    request: RankProjectRequest,
    user_id: str = Depends(verify_auth_token),
) -> RankProjectResponse:
    """
    Compute contribution-based ranking for a specific project.
    
    - **project_id**: UUID of the project to rank
    - **user_email**: Optional email to match against contributors
    - **user_name**: Optional name to match against contributors
    
    Returns a score (0-100) with detailed component breakdown and human-readable reasons.
    
    The ranking algorithm considers:
    - 50% commit volume (log-scaled)
    - 20% user's share of commits
    - 15% project recency
    - 10% commit frequency
    - 5% activity diversity (tests/docs/design)
    """
    try:
        # Note: sys.path is already configured in main.py at startup
        # No need for runtime path manipulation
        from local_analysis.contribution_analyzer import (
            ProjectContributionMetrics,
            ContributorMetrics,
            ActivityBreakdown,
        )
        from services.services.contribution_analysis_service import ContributionAnalysisService
        from datetime import datetime, timezone
        
        service = get_projects_service()
        
        # Get full project with scan data (run in thread pool to avoid blocking event loop)
        project = await asyncio.to_thread(service.get_project_scan, user_id, project_id)
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project {project_id} not found",
            )
        
        # Extract contribution metrics from scan_data
        scan_data = project.get("scan_data", {})
        contribution_metrics_dict = scan_data.get("contribution_metrics")
        
        if not contribution_metrics_dict:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Project does not have contribution metrics. Run a scan with git analysis first.",
            )
        
        # Reconstruct metrics object from dict
        def dict_to_metrics(data: Dict[str, Any]) -> ProjectContributionMetrics:
            """Convert dictionary to ProjectContributionMetrics object."""
            contributors = []
            for c in data.get("contributors", []):
                # Reconstruct activity breakdown for contributor
                c_activity = c.get("activity_breakdown", {})
                contributor_activity = ActivityBreakdown(
                    code_lines=c_activity.get("code_lines", 0),
                    test_lines=c_activity.get("test_lines", 0),
                    documentation_lines=c_activity.get("documentation_lines", 0),
                    design_lines=c_activity.get("design_lines", 0),
                    config_lines=c_activity.get("config_lines", 0),
                )
                
                contributor = ContributorMetrics(
                    name=c.get("name", ""),
                    email=c.get("email"),
                    commits=c.get("commits", 0),
                    commit_percentage=c.get("commit_percentage", 0.0),
                    first_commit_date=c.get("first_commit_date"),
                    last_commit_date=c.get("last_commit_date"),
                    active_days=c.get("active_days", 0),
                    activity_breakdown=contributor_activity,
                    files_touched=set(c.get("files_touched", [])),
                    languages_used=set(c.get("languages_used", [])),
                )
                contributors.append(contributor)
            
            # Reconstruct project activity breakdown
            activity = data.get("activity_breakdown", {})
            activity_breakdown = ActivityBreakdown(
                code_lines=activity.get("code_lines", 0),
                test_lines=activity.get("test_lines", 0),
                documentation_lines=activity.get("documentation_lines", 0),
                design_lines=activity.get("design_lines", 0),
                config_lines=activity.get("config_lines", 0),
            )
            
            return ProjectContributionMetrics(
                project_path=data.get("project_path", ""),
                project_type=data.get("project_type", "unknown"),
                total_commits=data.get("total_commits", 0),
                total_contributors=data.get("total_contributors", 0),
                project_duration_days=data.get("project_duration_days"),
                project_start_date=data.get("project_start_date"),
                project_end_date=data.get("project_end_date"),
                contributors=contributors,
                overall_activity_breakdown=activity_breakdown,
                commit_frequency=data.get("commit_frequency", 0.0),
                languages_detected=set(data.get("languages_detected", [])),
                timeline=data.get("timeline", []),
            )
        
        metrics = dict_to_metrics(contribution_metrics_dict)
        
        # Use the CLI service to compute the score (single source of truth)
        # Run in thread pool since this is CPU-intensive computation
        analysis_service = ContributionAnalysisService()
        ranking = await asyncio.to_thread(
            analysis_service.compute_contribution_score,
            metrics,
            user_email=request.user_email,
            user_name=request.user_name,
        )
        
        # Log the computed score
        logger.info(f"Computed contribution score for project {project_id}: {ranking['score']:.2f}")
        
        # Update the database with the contribution score (run in thread pool)
        try:
            service = get_projects_service()
            await asyncio.to_thread(
                service.update_project_score,
                user_id=user_id,
                project_id=project_id,
                contribution_score=ranking["score"],
                user_commit_share=ranking["user_commit_share"],
            )
            logger.info(f"Successfully saved contribution score {ranking['score']:.2f} to database for project {project_id}")
        except Exception as db_exc:
            logger.error(f"Failed to save contribution score to database: {db_exc}")
            # Continue anyway - return the score even if DB update fails
        
        # Generate human-readable reasons
        reasons = []
        score = ranking["score"]
        components = ranking["components"]
        
        if score >= 70:
            reasons.append("🌟 High-impact project")
        elif score >= 40:
            reasons.append("✨ Moderate-impact project")
        else:
            reasons.append("📝 Lower-impact project")
        
        if components["volume"] > 0.7:
            reasons.append(f"Large codebase with {ranking['total_commits']} commits")
        elif components["volume"] > 0.4:
            reasons.append(f"Medium-sized project with {ranking['total_commits']} commits")
        
        user_share = ranking["user_commit_share"]
        if user_share >= 0.8:
            reasons.append(f"Primary author ({user_share*100:.0f}% of commits)")
        elif user_share >= 0.5:
            reasons.append(f"Major contributor ({user_share*100:.0f}% of commits)")
        elif user_share >= 0.2:
            reasons.append(f"Contributing member ({user_share*100:.0f}% of commits)")
        elif user_share > 0:
            reasons.append(f"Minor contributor ({user_share*100:.0f}% of commits)")
        
        if components["recency"] > 0.8:
            reasons.append("Recent activity (within 6 months)")
        elif components["recency"] > 0.5:
            reasons.append("Moderate recency (6-12 months)")
        elif components["recency"] > 0.2:
            reasons.append("Older project (1-2 years)")
        
        if components["frequency"] > 0.6:
            reasons.append("High commit frequency")
        
        if components["activity_mix"] > 0.4:
            reasons.append("Good test/documentation coverage")
        
        return RankProjectResponse(
            project_id=project_id,
            project_name=project.get("project_name", "Unknown"),
            score=ranking["score"],
            user_commit_share=ranking["user_commit_share"],
            total_commits=ranking["total_commits"],
            components=RankingComponents(**components),
            reasons=reasons,
        )
    
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception(f"Error computing project rank: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to compute ranking: {str(exc)}",
        )





@router.delete(
    "/{project_id}/insights",
    response_model=DeleteInsightsResponse,
    status_code=status.HTTP_200_OK,
    responses={
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        404: {"model": ErrorResponse, "description": "Project not found"},
        500: {"model": ErrorResponse, "description": "Server error"},
    },
)
async def delete_project_insights(
    project_id: str,
    user_id: str = Depends(verify_auth_token),
) -> DeleteInsightsResponse:
    """
    Clear analysis data (insights) for a project while keeping the project record intact.

    - **project_id**: UUID of the project

    This operation:
    - Clears the scan_data JSONB column
    - Resets all analysis flags to false
    - Sets insights_deleted_at timestamp
    - Preserves the project record and file records

    Only the project owner can clear their project's insights.
    """
    try:
        service = get_projects_service()
        success = service.delete_project_insights(user_id, project_id)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project {project_id} not found or has no insights to clear",
            )

        return DeleteInsightsResponse(
            message="Insights cleared successfully",
            insights_deleted_at=datetime.now().isoformat(),
        )

    except HTTPException:
        raise
    except ProjectsServiceError as exc:
        logger.error(f"Projects service error: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to clear insights: {str(exc)}",
        )
    except Exception as exc:
        logger.exception("Unexpected error clearing project insights")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred",
        )


@router.post(
    "/{project_id}/thumbnail",
    response_model=ThumbnailUploadResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        404: {"model": ErrorResponse, "description": "Project not found"},
        400: {"model": ErrorResponse, "description": "Invalid file or upload error"},
        500: {"model": ErrorResponse, "description": "Server error"},
    },
)
async def upload_project_thumbnail(
    project_id: str,
    file: UploadFile = File(...),
    user_id: str = Depends(verify_auth_token),
) -> ThumbnailUploadResponse:
    """
    Upload a thumbnail image for a project.
    
    - **project_id**: UUID of the project
    - **file**: Image file to upload (JPEG, PNG, GIF, BMP, etc.)
    
    Accepts multipart/form-data with image file.
    Converts image to JPG format and uploads to Supabase storage.
    Updates project record with thumbnail URL.
    
    Returns the public URL of the uploaded thumbnail.
    """
    try:
        # Verify project exists and user owns it
        service = get_projects_service()
        project = service.get_project_scan(user_id, project_id)
        
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project {project_id} not found",
            )
        
        # Save uploaded file to temporary location
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.filename)[1]) as tmp_file:
            content = await file.read()
            tmp_file.write(content)
            tmp_file_path = tmp_file.name
        
        try:
            # Upload thumbnail using ProjectsService
            thumbnail_url, error_msg = service.upload_thumbnail(tmp_file_path, project_id)
            
            if error_msg:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Failed to upload thumbnail: {error_msg}",
                )
            
            # Update project with thumbnail URL
            success, update_error = service.update_project_thumbnail_url(project_id, thumbnail_url)
            
            if not success:
                logger.error(f"Failed to update project thumbnail URL: {update_error}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Thumbnail uploaded but database update failed: {update_error}",
                )
            
            return ThumbnailUploadResponse(thumbnail_url=thumbnail_url)
            
        finally:
            # Clean up temporary file
            try:
                os.unlink(tmp_file_path)
            except Exception as cleanup_exc:
                logger.warning(f"Failed to cleanup temp file: {cleanup_exc}")
    
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Unexpected error uploading thumbnail")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {str(exc)}",
        )


@router.patch(
    "/{project_id}/thumbnail",
    response_model=ThumbnailUpdateResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        404: {"model": ErrorResponse, "description": "Project not found"},
        400: {"model": ErrorResponse, "description": "Invalid request"},
        500: {"model": ErrorResponse, "description": "Server error"},
    },
)
async def update_project_thumbnail_url(
    project_id: str,
    request: ThumbnailUpdateRequest,
    user_id: str = Depends(verify_auth_token),
) -> ThumbnailUpdateResponse:
    """
    Update the thumbnail URL for a project.
    
    - **project_id**: UUID of the project
    - **thumbnail_url**: Public URL of the thumbnail image
    
    Updates the project's thumbnail_url field in the database.
    Use this endpoint if you've already uploaded the image to storage
    and just need to update the database reference.
    """
    try:
        # Verify project exists and user owns it
        service = get_projects_service()
        project = service.get_project_scan(user_id, project_id)
        
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project {project_id} not found",
            )
        
        # Update thumbnail URL
        success, error_msg = service.update_project_thumbnail_url(
            project_id, request.thumbnail_url
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to update thumbnail URL: {error_msg}",
            )
        
        return ThumbnailUpdateResponse()

    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Unexpected error updating thumbnail URL")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {str(exc)}",
        )


# ============================================================================
# Project Overrides Endpoints
# ============================================================================

@router.get(
    "/{project_id}/overrides",
    response_model=ProjectOverridesResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        404: {"model": ErrorResponse, "description": "Project not found"},
        500: {"model": ErrorResponse, "description": "Server error"},
    },
)
async def get_project_overrides(
    project_id: str,
    user_id: str = Depends(verify_auth_token),
) -> ProjectOverridesResponse:
    """
    Get user-defined overrides for a specific project.
    
    - **project_id**: UUID of the project
    
    Returns the current override settings. If no overrides have been set,
    returns default/empty values for all fields.
    
    Overrides include:
    - Chronology corrections (start_date_override, end_date_override)
    - Role and evidence bullet points
    - Highlighted skills
    - Comparison attributes
    - Custom ranking
    - Thumbnail URL override
    """
    try:
        # Verify project exists and user owns it
        projects_service = get_projects_service()
        project = await asyncio.to_thread(projects_service.get_project_scan, user_id, project_id)
        
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project {project_id} not found",
            )
        
        # Get overrides
        overrides_service = get_overrides_service()
        overrides = await asyncio.to_thread(overrides_service.get_overrides, user_id, project_id)
        
        # Build response with defaults if no overrides exist
        if overrides:
            return ProjectOverridesResponse(
                project_id=project_id,
                overrides=ProjectOverrides(
                    role=overrides.get("role"),
                    evidence=overrides.get("evidence", []),
                    thumbnail_url=overrides.get("thumbnail_url"),
                    custom_rank=overrides.get("custom_rank"),
                    start_date_override=overrides.get("start_date_override"),
                    end_date_override=overrides.get("end_date_override"),
                    comparison_attributes=overrides.get("comparison_attributes", {}),
                    highlighted_skills=overrides.get("highlighted_skills", []),
                ),
                created_at=overrides.get("created_at"),
                updated_at=overrides.get("updated_at"),
            )
        else:
            # Return empty overrides
            return ProjectOverridesResponse(
                project_id=project_id,
                overrides=ProjectOverrides(
                    role=None,
                    evidence=[],
                    thumbnail_url=None,
                    custom_rank=None,
                    start_date_override=None,
                    end_date_override=None,
                    comparison_attributes={},
                    highlighted_skills=[],
                ),
            )
    
    except HTTPException:
        raise
    except ProjectOverridesServiceError as exc:
        logger.error(f"Overrides service error: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve overrides: {str(exc)}",
        )
    except Exception as exc:
        logger.exception("Unexpected error retrieving project overrides")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred",
        )


@router.patch(
    "/{project_id}/overrides",
    response_model=ProjectOverridesResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        404: {"model": ErrorResponse, "description": "Project not found"},
        400: {"model": ErrorResponse, "description": "Invalid request"},
        500: {"model": ErrorResponse, "description": "Server error"},
    },
)
async def update_project_overrides(
    project_id: str,
    request: ProjectOverridesRequest,
    user_id: str = Depends(verify_auth_token),
) -> ProjectOverridesResponse:
    """
    Create or update user-defined overrides for a project.
    
    - **project_id**: UUID of the project
    
    Supports partial updates - only provided fields are updated.
    Pass empty string/list/dict to explicitly clear a field.
    
    Acceptance Criteria:
    - Overrides persist in encrypted storage
    - Overrides are reflected in timelines and comparisons
    """
    try:
        # Verify project exists and user owns it
        projects_service = get_projects_service()
        project = await asyncio.to_thread(projects_service.get_project_scan, user_id, project_id)
        
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project {project_id} not found",
            )
        
        # Update overrides
        overrides_service = get_overrides_service()
        updated = await asyncio.to_thread(
            overrides_service.upsert_overrides,
            user_id,
            project_id,
            role=request.role,
            evidence=request.evidence,
            thumbnail_url=request.thumbnail_url,
            custom_rank=request.custom_rank,
            start_date_override=request.start_date_override,
            end_date_override=request.end_date_override,
            comparison_attributes=request.comparison_attributes,
            highlighted_skills=request.highlighted_skills,
        )
        
        return ProjectOverridesResponse(
            project_id=project_id,
            overrides=ProjectOverrides(
                role=updated.get("role"),
                evidence=updated.get("evidence", []),
                thumbnail_url=updated.get("thumbnail_url"),
                custom_rank=updated.get("custom_rank"),
                start_date_override=updated.get("start_date_override"),
                end_date_override=updated.get("end_date_override"),
                comparison_attributes=updated.get("comparison_attributes", {}),
                highlighted_skills=updated.get("highlighted_skills", []),
            ),
            created_at=updated.get("created_at"),
            updated_at=updated.get("updated_at"),
        )
    
    except HTTPException:
        raise
    except ProjectOverridesServiceError as exc:
        logger.error(f"Overrides service error: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update overrides: {str(exc)}",
        )
    except Exception as exc:
        logger.exception("Unexpected error updating project overrides")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred",
        )


@router.delete(
    "/{project_id}/overrides",
    response_model=DeleteOverridesResponse,
    status_code=status.HTTP_200_OK,
    responses={
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        404: {"model": ErrorResponse, "description": "Project or overrides not found"},
        500: {"model": ErrorResponse, "description": "Server error"},
    },
)
async def delete_project_overrides(
    project_id: str,
    user_id: str = Depends(verify_auth_token),
) -> DeleteOverridesResponse:
    """
    Delete all user-defined overrides for a project.
    
    - **project_id**: UUID of the project
    
    This resets the project to use computed/scanned values instead of user overrides.
    The project itself is NOT deleted.
    
    Returns 404 if no overrides exist for the project.
    """
    try:
        # Verify project exists and user owns it
        projects_service = get_projects_service()
        project = await asyncio.to_thread(projects_service.get_project_scan, user_id, project_id)
        
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project {project_id} not found",
            )
        
        # Delete overrides
        overrides_service = get_overrides_service()
        deleted = await asyncio.to_thread(overrides_service.delete_overrides, user_id, project_id)
        
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No overrides found for project {project_id}",
            )
        
        return DeleteOverridesResponse(message="Overrides cleared successfully")
    
    except HTTPException:
        raise
    except ProjectOverridesServiceError as exc:
        logger.error(f"Overrides service error: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete overrides: {str(exc)}",
        )
    except Exception as exc:
        logger.exception("Unexpected error deleting project overrides")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred",
        )
async def update_project_role(
    project_id: str,
    request: RoleUpdateRequest,
    user_id: str = Depends(verify_auth_token),
) -> RoleUpdateResponse:
    """
    Update the user's role in a project.
    
    - **project_id**: UUID of the project
    - **role**: User's role (author, contributor, lead, maintainer, reviewer)
    
    Updates the project's role field in the project_overrides table.
    The role is used for display in portfolio and résumé views.
    """
    try:
        # Validate role
        if request.role not in ALLOWED_ROLES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid role '{request.role}'. Allowed roles: {', '.join(ALLOWED_ROLES)}",
            )
        
        # Verify project exists and user owns it
        service = get_projects_service()
        project = service.get_project_scan(user_id, project_id)
        
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project {project_id} not found",
            )
        
        # Update role in project_overrides
        overrides_service = get_overrides_service()
        overrides_service.upsert_overrides(
            user_id=user_id,
            project_id=project_id,
            role=request.role,
        )
        
        return RoleUpdateResponse(project_id=project_id, role=request.role)
    
    except HTTPException:
        raise
    except ProjectOverridesServiceError as exc:
        logger.exception("Failed to update project role")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update role: {str(exc)}",
        )
    except Exception as exc:
        logger.exception("Unexpected error updating project role")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {str(exc)}",
        )


@router.get(
    "/{project_id}/role",
    response_model=RoleUpdateResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        404: {"model": ErrorResponse, "description": "Project not found"},
        500: {"model": ErrorResponse, "description": "Server error"},
    },
)
async def get_project_role(
    project_id: str,
    user_id: str = Depends(verify_auth_token),
) -> RoleUpdateResponse:
    """
    Get the user's role in a project.
    
    - **project_id**: UUID of the project
    
    Returns the role from project_overrides, or null if not set.
    """
    try:
        # Verify project exists and user owns it
        service = get_projects_service()
        project = service.get_project_scan(user_id, project_id)
        
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project {project_id} not found",
            )
        
        # Get role from overrides
        overrides_service = get_overrides_service()
        overrides = overrides_service.get_overrides(user_id, project_id)
        
        role = overrides.get("role") if overrides else None
        
        return RoleUpdateResponse(
            project_id=project_id,
            role=role or "",
            message="Role retrieved successfully" if role else "No role set"
        )
    
    except HTTPException:
        raise
    except ProjectOverridesServiceError as exc:
        logger.exception("Failed to get project role")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get role: {str(exc)}",
        )
    except Exception as exc:
        logger.exception("Unexpected error getting project role")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {str(exc)}",
        )
# ============================================================================
# Append Upload to Project (with Deduplication)
# ============================================================================


class AppendUploadRequest(BaseModel):
    """Request body for appending an upload to a project."""
    skip_duplicates: bool = Field(True, description="Skip files with matching SHA-256 hash")


class AppendFileStatus(BaseModel):
    """Status of a single file in the append operation."""
    path: str
    status: str  # "added", "updated", "skipped_duplicate"
    sha256: Optional[str] = None


class AppendUploadResponse(BaseModel):
    """Response from append-upload endpoint."""
    project_id: str
    upload_id: str
    status: str = "completed"
    files_added: int
    files_updated: int
    files_skipped_duplicate: int
    total_files_in_upload: int
    files: List[AppendFileStatus]


@router.post(
    "/{project_id}/append-upload/{upload_id}",
    response_model=AppendUploadResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid request"},
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        403: {"model": ErrorResponse, "description": "Forbidden"},
        404: {"model": ErrorResponse, "description": "Project or upload not found"},
        500: {"model": ErrorResponse, "description": "Server error"},
    },
)
async def append_upload_to_project(
    project_id: str,
    upload_id: str,
    request: AppendUploadRequest = AppendUploadRequest(),
    user_id: str = Depends(verify_auth_token),
) -> AppendUploadResponse:
    """
    Merge files from a new upload into an existing project with deduplication.

    - Verifies upload exists and user owns it
    - Verifies project exists and user owns it
    - Compares each file by SHA-256 hash:
      - If hash matches existing file → skip (duplicate)
      - If path exists but different hash → update
      - If new path → add
    - Updates cached file metadata in the project

    Args:
        project_id: UUID of the target project
        upload_id: ID of the upload to merge
        request: Options for the append operation

    Returns:
        Detailed status for each file in the upload
    """
    # Import uploads_store lazily to avoid circular imports
    from api.upload_routes import uploads_store

    # Verify upload exists and user owns it
    if upload_id not in uploads_store:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Upload {upload_id} not found",
        )

    upload_data = uploads_store[upload_id]
    if upload_data.get("user_id") != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this upload",
        )

    # Verify project exists and user owns it
    service = get_projects_service()
    project = service.get_project_scan(user_id, project_id)

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project {project_id} not found",
        )

    # Get existing cached files for the project
    try:
        existing_files = service.get_cached_files(user_id, project_id)
    except ProjectsServiceError as exc:
        logger.warning(f"Failed to get cached files for project {project_id}: {exc}")
        existing_files = {}

    # Check if any cached files are missing sha256 (e.g., from TUI scans)
    # and trigger backfill from scan_data if needed
    files_missing_hash = any(
        not meta.get("sha256") for meta in existing_files.values()
    )
    if files_missing_hash:
        try:
            backfill_count = service.backfill_cached_file_hashes(user_id, project_id)
            if backfill_count > 0:
                logger.info(
                    f"Backfilled {backfill_count} sha256 hashes for project {project_id}"
                )
                # Reload cached files after backfill
                existing_files = service.get_cached_files(user_id, project_id)
        except ProjectsServiceError as exc:
            logger.warning(f"Failed to backfill hashes for project {project_id}: {exc}")

    # Build a lookup of existing hashes for deduplication
    existing_hashes: Dict[str, str] = {}  # sha256 -> path
    for path, meta in existing_files.items():
        sha = meta.get("sha256")
        if sha:
            existing_hashes[sha] = path

    # Parse the upload ZIP to get file metadata
    storage_path = Path(upload_data.get("storage_path", ""))
    if not storage_path.exists():
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Upload file not found on disk",
        )

    try:
        parse_result = parse_zip(storage_path, relevant_only=False)
    except Exception as exc:
        logger.exception(f"Failed to parse upload {upload_id}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to parse upload: {str(exc)}",
        )

    # Process each file and determine status
    files_added = 0
    files_updated = 0
    files_skipped_duplicate = 0
    file_statuses: List[AppendFileStatus] = []
    files_to_upsert: List[Dict[str, Any]] = []

    for file_meta in parse_result.files:
        rel_path = file_meta.path.replace("\\", "/")
        sha256 = file_meta.file_hash
        size_bytes = file_meta.size_bytes
        mime_type = file_meta.mime_type

        file_status: str

        # Check if this exact file (by hash) already exists
        if request.skip_duplicates and sha256 and sha256 in existing_hashes:
            file_status = "skipped_duplicate"
            files_skipped_duplicate += 1
        elif rel_path in existing_files:
            # Path exists - check if content changed
            existing_sha = existing_files[rel_path].get("sha256")
            if existing_sha == sha256:
                # Same content, skip
                file_status = "skipped_duplicate"
                files_skipped_duplicate += 1
            else:
                # Different content, update
                file_status = "updated"
                files_updated += 1
                files_to_upsert.append({
                    "relative_path": rel_path,
                    "size_bytes": size_bytes,
                    "mime_type": mime_type,
                    "sha256": sha256,
                    "metadata": {},
                    "last_seen_modified_at": file_meta.modified_at.isoformat() + "Z",
                    "last_scanned_at": datetime.now().isoformat() + "Z",
                })
        else:
            # New file
            file_status = "added"
            files_added += 1
            files_to_upsert.append({
                "relative_path": rel_path,
                "size_bytes": size_bytes,
                "mime_type": mime_type,
                "sha256": sha256,
                "metadata": {},
                "last_seen_modified_at": file_meta.modified_at.isoformat() + "Z",
                "last_scanned_at": datetime.now().isoformat() + "Z",
            })

        file_statuses.append(AppendFileStatus(
            path=rel_path,
            status=file_status,
            sha256=sha256,
        ))

    # Persist the new/updated files
    if files_to_upsert:
        try:
            service.upsert_cached_files(user_id, project_id, files_to_upsert)
        except ProjectsServiceError as exc:
            logger.error(f"Failed to upsert cached files: {exc}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to save file metadata: {str(exc)}",
            )

    return AppendUploadResponse(
        project_id=project_id,
        upload_id=upload_id,
        status="completed",
        files_added=files_added,
        files_updated=files_updated,
        files_skipped_duplicate=files_skipped_duplicate,
        total_files_in_upload=len(parse_result.files),
        files=file_statuses,
    )
