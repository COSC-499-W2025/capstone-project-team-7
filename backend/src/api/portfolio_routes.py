"""Portfolio chronology API routes."""

from __future__ import annotations

import logging
from typing import List, Optional, Dict
from collections import defaultdict
from uuid import UUID
from typing import Any, Dict, List, Literal, Optional
from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from api.dependencies import AuthContext, get_auth_context
from api.models.portfolio_item_models import PortfolioItem, PortfolioItemCreate, PortfolioItemUpdate
from services.services.portfolio_item_service import (
    PortfolioItemService,
    PortfolioItemServiceError,
)
from services.services.portfolio_timeline_service import (
    PortfolioTimelineService,
    PortfolioTimelineServiceError,
)
from services.services.projects_service import ProjectsService, ProjectsServiceError

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Portfolio"])


def get_portfolio_timeline_service(
    auth: AuthContext = Depends(get_auth_context),
) -> PortfolioTimelineService:
    projects_service = get_projects_service(auth)
    return PortfolioTimelineService(projects_service=projects_service)


def get_portfolio_item_service(
    auth: AuthContext = Depends(get_auth_context),
) -> PortfolioItemService:
    service = PortfolioItemService()
    service.apply_access_token(auth.access_token)
    return service


def get_projects_service(
    auth: AuthContext = Depends(get_auth_context),
) -> ProjectsService:
    try:
        from services.services.encryption import EncryptionService
        encryption_service = EncryptionService()
    except Exception:
        encryption_service = None
    service = ProjectsService(
        encryption_service=encryption_service,
        encryption_required=False,
    )
    service.apply_access_token(auth.access_token)
    return service


class ErrorResponse(BaseModel):
    code: str
    message: str


class TimelineItem(BaseModel):
    project_id: str
    name: str
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    duration_days: Optional[int] = None
    role: Optional[str] = Field(None, description="User's role in the project")
    evidence: List[str] = Field(default_factory=list, description="Evidence of success bullet points")


class SkillsTimelineItem(BaseModel):
    period_label: str
    skills: List[str] = Field(default_factory=list)
    commits: int = 0
    projects: List[str] = Field(default_factory=list)


class SkillsTimelineResponse(BaseModel):
    items: List[SkillsTimelineItem] = Field(default_factory=list)


class PortfolioChronology(BaseModel):
    projects: List[TimelineItem] = Field(default_factory=list)
    skills: List[SkillsTimelineItem] = Field(default_factory=list)

class ProjectEvolutionPeriod(BaseModel):
    period_label: str
    commits: int = 0
    skill_count: int = 0
    languages: Dict[str, Any] = Field(default_factory=dict)
    activity_types: List[str] = Field(default_factory=list)


class ProjectEvolutionItem(BaseModel):
    project_id: str
    project_name: str
    total_commits: int = 0
    total_lines: int = 0
    periods: List[ProjectEvolutionPeriod] = Field(default_factory=list)


class ProjectEvolutionResponse(BaseModel):
    items: List[ProjectEvolutionItem] = Field(default_factory=list)


class SkillsListResponse(BaseModel):
    """Response for GET /api/skills endpoint."""
    skills: List[str] = Field(default_factory=list, description="Unique skills sorted alphabetically")


@router.get(
    "/api/skills",
    response_model=SkillsListResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        500: {"model": ErrorResponse, "description": "Skills retrieval failed"},
    },
)
def get_all_skills(
    category: Optional[str] = None,
    auth: AuthContext = Depends(get_auth_context),
    service: PortfolioTimelineService = Depends(get_portfolio_timeline_service),
) -> SkillsListResponse:
    """
    Get all unique skills across user's projects.

    Optionally filter by category: languages, frameworks, tools.
    Returns skills sorted alphabetically.
    """
    try:
        timeline_items = service.get_skills_timeline(auth.user_id)
        # Extract unique skills from all timeline periods
        unique_skills: set[str] = set()
        for item in timeline_items:
            unique_skills.update(item.get("skills", []))
        sorted_skills = sorted(unique_skills, key=str.lower)
    except PortfolioTimelineServiceError as exc:
        logger.exception("Failed to retrieve skills")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "skills_error", "message": str(exc)},
        ) from exc
    return SkillsListResponse(skills=sorted_skills)


@router.get(
    "/api/skills/timeline",
    response_model=SkillsTimelineResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        500: {"model": ErrorResponse, "description": "Timeline retrieval failed"},
    },
)
def get_skills_timeline(
    auth: AuthContext = Depends(get_auth_context),
    service: PortfolioTimelineService = Depends(get_portfolio_timeline_service),
) -> SkillsTimelineResponse:
    try:
        items = [SkillsTimelineItem(**item) for item in service.get_skills_timeline(auth.user_id)]
    except PortfolioTimelineServiceError as exc:
        logger.exception("Failed to build skills timeline")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "timeline_error", "message": str(exc)},
        ) from exc
    return SkillsTimelineResponse(items=items)


@router.get(
    "/api/portfolio/chronology",
    response_model=PortfolioChronology,
    responses={
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        500: {"model": ErrorResponse, "description": "Timeline retrieval failed"},
    },
)
def get_portfolio_chronology(
    auth: AuthContext = Depends(get_auth_context),
    service: PortfolioTimelineService = Depends(get_portfolio_timeline_service),
) -> PortfolioChronology:
    try:
        chronology = service.get_portfolio_chronology(auth.user_id)
    except PortfolioTimelineServiceError as exc:
        logger.exception("Failed to build portfolio chronology")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "timeline_error", "message": str(exc)},
        ) from exc
    return PortfolioChronology(
        projects=[TimelineItem(**item) for item in chronology.get("projects", [])],
        skills=[SkillsTimelineItem(**item) for item in chronology.get("skills", [])],
    )


@router.get(
    "/api/portfolio/project-evolution",
    response_model=ProjectEvolutionResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        500: {"model": ErrorResponse, "description": "Evolution retrieval failed"},
    },
)
def get_project_evolution(
    project_ids: Optional[str] = None,
    auth: AuthContext = Depends(get_auth_context),
    service: PortfolioTimelineService = Depends(get_portfolio_timeline_service),
) -> ProjectEvolutionResponse:
    """Return per-project monthly evolution data.

    Optionally filter by comma-separated project IDs.
    """
    ids_list = [pid.strip() for pid in project_ids.split(",") if pid.strip()] if project_ids else None
    try:
        items = service.get_project_evolution(auth.user_id, project_ids=ids_list)
    except PortfolioTimelineServiceError as exc:
        logger.exception("Failed to build project evolution")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "evolution_error", "message": str(exc)},
        ) from exc
    return ProjectEvolutionResponse(
        items=[ProjectEvolutionItem(**item) for item in items],
    )


@router.get(
    "/api/portfolio/items",
    response_model=List[PortfolioItem],
    responses={
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        500: {"model": ErrorResponse, "description": "Portfolio item retrieval failed"},
    },
)
async def get_all_portfolio_items(
    auth: AuthContext = Depends(get_auth_context),
    service: PortfolioItemService = Depends(get_portfolio_item_service),
) -> List[PortfolioItem]:
    try:
        items = service.get_all_portfolio_items(UUID(auth.user_id))
        return items
    except PortfolioItemServiceError as exc:
        logger.exception("Failed to retrieve portfolio items")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "portfolio_items_error", "message": str(exc)},
        ) from exc


@router.get(
    "/api/portfolio/items/{item_id}",
    response_model=PortfolioItem,
    responses={
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        404: {"model": ErrorResponse, "description": "Portfolio item not found"},
        500: {"model": ErrorResponse, "description": "Portfolio item retrieval failed"},
    },
)
async def get_portfolio_item(
    item_id: UUID,
    auth: AuthContext = Depends(get_auth_context),
    service: PortfolioItemService = Depends(get_portfolio_item_service),
) -> PortfolioItem:
    try:
        item = service.get_portfolio_item(UUID(auth.user_id), item_id)
        if not item:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"code": "not_found", "message": "Portfolio item not found"})
        return item
    except PortfolioItemServiceError as exc:
        logger.exception(f"Failed to retrieve portfolio item {item_id}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "portfolio_item_error", "message": str(exc)},
        ) from exc


@router.post(
    "/api/portfolio/items",
    response_model=PortfolioItem,
    status_code=status.HTTP_201_CREATED,
    responses={
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        500: {"model": ErrorResponse, "description": "Portfolio item creation failed"},
    },
)
async def create_portfolio_item(
    item: PortfolioItemCreate,
    auth: AuthContext = Depends(get_auth_context),
    service: PortfolioItemService = Depends(get_portfolio_item_service),
) -> PortfolioItem:
    try:
        new_item = service.create_portfolio_item(UUID(auth.user_id), item)
        return new_item
    except PortfolioItemServiceError as exc:
        logger.exception("Failed to create portfolio item")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "portfolio_item_creation_error", "message": str(exc)},
        ) from exc


@router.patch(
    "/api/portfolio/items/{item_id}",
    response_model=PortfolioItem,
    responses={
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        404: {"model": ErrorResponse, "description": "Portfolio item not found"},
        500: {"model": ErrorResponse, "description": "Portfolio item update failed"},
    },
)
async def update_portfolio_item(
    item_id: UUID,
    item_update: PortfolioItemUpdate,
    auth: AuthContext = Depends(get_auth_context),
    service: PortfolioItemService = Depends(get_portfolio_item_service),
) -> PortfolioItem:
    try:
        updated_item = service.update_portfolio_item(UUID(auth.user_id), item_id, item_update)
        if not updated_item:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"code": "not_found", "message": "Portfolio item not found"})
        return updated_item
    except PortfolioItemServiceError as exc:
        logger.exception(f"Failed to update portfolio item {item_id}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "portfolio_item_update_error", "message": str(exc)},
        ) from exc


@router.delete(
    "/api/portfolio/items/{item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        404: {"model": ErrorResponse, "description": "Portfolio item not found"},
        500: {"model": ErrorResponse, "description": "Portfolio item deletion failed"},
    },
    response_model=None,
)
async def delete_portfolio_item(
    item_id: UUID,
    auth: AuthContext = Depends(get_auth_context),
    service: PortfolioItemService = Depends(get_portfolio_item_service),
):
    try:
        success = service.delete_portfolio_item(UUID(auth.user_id), item_id)
        if not success:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"code": "not_found", "message": "Portfolio item not found"})
    except PortfolioItemServiceError as exc:
        logger.exception(f"Failed to delete portfolio item {item_id}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "portfolio_item_deletion_error", "message": str(exc)},
        )


# ============================================================================
# Portfolio Refresh with Deduplication
# ============================================================================


class PortfolioRefreshRequest(BaseModel):
    """Request body for portfolio refresh."""
    include_duplicates: bool = Field(True, description="Include cross-project duplicate detection")


class DuplicateFileInfo(BaseModel):
    """Information about a single duplicate file."""
    path: str
    project_id: str
    project_name: str


class DuplicateGroup(BaseModel):
    """A group of files that share the same SHA-256 hash."""
    sha256: str
    file_count: int
    wasted_bytes: int
    files: List[DuplicateFileInfo]


class DedupSummary(BaseModel):
    """Summary of deduplication analysis."""
    duplicate_groups_count: int
    total_wasted_bytes: int


class DedupReport(BaseModel):
    """Full deduplication report."""
    summary: DedupSummary
    duplicate_groups: List[DuplicateGroup]


class PortfolioRefreshResponse(BaseModel):
    """Response from portfolio refresh endpoint."""
    status: str = "completed"
    projects_scanned: int
    total_files: int
    total_size_bytes: int
    dedup_report: Optional[DedupReport] = None


@router.post(
    "/api/portfolio/refresh",
    response_model=PortfolioRefreshResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        500: {"model": ErrorResponse, "description": "Refresh failed"},
    },
)
def refresh_portfolio(
    request: PortfolioRefreshRequest = PortfolioRefreshRequest(),
    auth: AuthContext = Depends(get_auth_context),
    service: ProjectsService = Depends(get_projects_service),
) -> PortfolioRefreshResponse:
    """
    Refresh entire portfolio with cross-project duplicate detection.

    Scans all user projects and detects files duplicated across multiple projects.
    Returns a deduplication report identifying duplicate files by SHA-256 hash.
    """
    try:
        # Get all user projects
        projects = service.get_user_projects(auth.user_id)

        total_files = 0
        total_size_bytes = 0

        # Map: sha256 -> list of (file_info, size_bytes)
        hash_to_files: Dict[str, List[tuple]] = defaultdict(list)

        # Build a mapping of project_id -> project_name for quick lookup
        project_names: Dict[str, str] = {p["id"]: p.get("project_name", "Unknown") for p in projects}

        # Scan each project for cached files
        for project in projects:
            project_id = project["id"]
            project_name = project.get("project_name", "Unknown")

            try:
                cached_files = service.get_cached_files(auth.user_id, project_id)
            except Exception as exc:
                logger.warning(f"Failed to get cached files for project {project_id}: {exc}")
                continue

            for rel_path, file_meta in cached_files.items():
                sha256 = file_meta.get("sha256")
                size_bytes = file_meta.get("size_bytes", 0)

                total_files += 1
                total_size_bytes += size_bytes

                if sha256:
                    hash_to_files[sha256].append({
                        "path": rel_path,
                        "project_id": project_id,
                        "project_name": project_name,
                        "size_bytes": size_bytes,
                    })

        # Build dedup report if requested
        dedup_report = None
        if request.include_duplicates:
            duplicate_groups = []
            total_wasted_bytes = 0

            for sha256, files in hash_to_files.items():
                # Only consider duplicates across different projects
                unique_projects = set(f["project_id"] for f in files)
                if len(unique_projects) > 1:
                    # This is a cross-project duplicate
                    file_size = files[0]["size_bytes"]
                    # Wasted bytes = (count - 1) * size (keeping one copy is not wasted)
                    wasted = (len(files) - 1) * file_size
                    total_wasted_bytes += wasted

                    duplicate_groups.append(DuplicateGroup(
                        sha256=sha256,
                        file_count=len(files),
                        wasted_bytes=wasted,
                        files=[
                            DuplicateFileInfo(
                                path=f["path"],
                                project_id=f["project_id"],
                                project_name=f["project_name"],
                            )
                            for f in files
                        ],
                    ))

            # Sort by wasted bytes descending
            duplicate_groups.sort(key=lambda g: g.wasted_bytes, reverse=True)

            dedup_report = DedupReport(
                summary=DedupSummary(
                    duplicate_groups_count=len(duplicate_groups),
                    total_wasted_bytes=total_wasted_bytes,
                ),
                duplicate_groups=duplicate_groups,
            )

        return PortfolioRefreshResponse(
            status="completed",
            projects_scanned=len(projects),
            total_files=total_files,
            total_size_bytes=total_size_bytes,
            dedup_report=dedup_report,
        )

    except ProjectsServiceError as exc:
        logger.exception("Failed to refresh portfolio")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "refresh_error", "message": str(exc)},
        ) from exc
    except Exception as exc:
        logger.exception("Unexpected error refreshing portfolio")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "refresh_error", "message": str(exc)},
        ) from exc


# ============================================================================
# Portfolio Generation Endpoint
# ============================================================================

class PortfolioGenerateRequest(BaseModel):
    """Request body for portfolio generation."""
    project_id: Optional[str] = Field(None, description="Project ID to generate portfolio item from")
    upload_id: Optional[str] = Field(None, description="Upload ID to generate portfolio item from (not yet implemented)")
    persist: bool = Field(True, description="If true, persist the generated portfolio item; if false, return draft only")


class PortfolioGenerateResponse(BaseModel):
    """Response from portfolio generation."""
    id: Optional[str] = Field(None, description="Portfolio item ID (only if persisted)")
    title: str = Field(..., description="Generated portfolio item title")
    summary: Optional[str] = Field(None, description="Generated portfolio item summary")
    role: Optional[str] = Field(None, description="User's role in the project")
    evidence: Optional[str] = Field(None, description="Evidence/details supporting the portfolio item")
    persisted: bool = Field(..., description="Whether the item was persisted to storage")


@router.post(
    "/api/portfolio/generate",
    response_model=PortfolioGenerateResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid request - must provide project_id or upload_id"},
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        404: {"model": ErrorResponse, "description": "Project or upload not found"},
        501: {"model": ErrorResponse, "description": "upload_id generation not yet implemented"},
        500: {"model": ErrorResponse, "description": "Portfolio generation failed"},
    },
)
async def generate_portfolio_item(
    request: PortfolioGenerateRequest,
    auth: AuthContext = Depends(get_auth_context),
    projects_service: ProjectsService = Depends(get_projects_service),
    portfolio_service: PortfolioItemService = Depends(get_portfolio_item_service),
) -> PortfolioGenerateResponse:
    """
    Generate a portfolio item from a scanned project or upload.
    
    This endpoint bridges the gap between project scans and portfolio items:
    - Takes a project_id (from a completed scan) or upload_id
    - Extracts relevant information to create portfolio-ready content
    - Optionally persists to /api/portfolio/items
    
    The generated portfolio item includes:
    - title: Derived from project name
    - summary: Generated from languages, skills, and contribution metrics
    - role: User's role in the project (author/contributor/etc)
    - evidence: Key metrics and achievements from the scan
    
    Set persist=false to preview the generated content without saving.
    """
    # Validate request - must have project_id or upload_id
    if not request.project_id and not request.upload_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "validation_error", "message": "Either project_id or upload_id is required"},
        )
    
    # upload_id path not yet implemented
    if request.upload_id and not request.project_id:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail={"code": "not_implemented", "message": "Generation from upload_id is not yet implemented. Use project_id from a saved scan."},
        )
    
    try:
        # Fetch project data
        project = projects_service.get_project_scan(auth.user_id, request.project_id)
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"code": "not_found", "message": f"Project with ID '{request.project_id}' not found"},
            )
        
        # Extract scan_data — key may exist with None value, or decryption may return
        # a non-dict type; both cases would crash .get() calls below
        _raw = project.get("scan_data")
        scan_data = _raw if isinstance(_raw, dict) else {}
        
        # Generate title from project name
        title = project.get("project_name", "Untitled Project")
        
        # Generate summary from scan data
        summary_parts = []
        
        # Add language info
        languages = scan_data.get("languages") or project.get("languages", [])
        if languages:
            if isinstance(languages, list) and len(languages) > 0:
                if isinstance(languages[0], dict):
                    top_langs = [l.get("name", l.get("language", "Unknown")) for l in languages[:3]]
                else:
                    top_langs = languages[:3]
                summary_parts.append(f"Technologies: {', '.join(top_langs)}")
        
        # Add contribution info
        contribution = scan_data.get("contribution_metrics") or scan_data.get("contribution_analysis", {})
        if contribution:
            project_type = contribution.get("project_type", "")
            if project_type:
                summary_parts.append(f"Project type: {project_type}")
            total_commits = contribution.get("total_commits")
            if total_commits:
                summary_parts.append(f"Commits: {total_commits}")
        
        # Add skills info
        skills = scan_data.get("skills", [])
        if skills:
            skill_names = [s.get("name", s) if isinstance(s, dict) else s for s in skills[:5]]
            if skill_names:
                summary_parts.append(f"Skills: {', '.join(skill_names)}")
        
        summary = ". ".join(summary_parts) if summary_parts else None
        
        # Get role
        role = project.get("role")
        
        # Generate evidence from metrics
        evidence_parts = []
        
        # File/line counts
        total_files = project.get("total_files") or scan_data.get("total_files", 0)
        total_lines = project.get("total_lines") or scan_data.get("total_lines", 0)
        if total_files:
            evidence_parts.append(f"Files analyzed: {total_files}")
        if total_lines:
            evidence_parts.append(f"Lines of code: {total_lines}")
        
        # Code metrics
        code_metrics = scan_data.get("code_metrics") or scan_data.get("code_analysis", {})
        if code_metrics:
            functions = code_metrics.get("functions", 0)
            classes = code_metrics.get("classes", 0)
            if functions:
                evidence_parts.append(f"Functions: {functions}")
            if classes:
                evidence_parts.append(f"Classes: {classes}")
        
        # Git info
        git_analysis = scan_data.get("git_analysis", [])
        if git_analysis and len(git_analysis) > 0:
            repo = git_analysis[0] if isinstance(git_analysis, list) else git_analysis
            commit_count = repo.get("commit_count", 0)
            if commit_count:
                evidence_parts.append(f"Commit history: {commit_count} commits")
        
        evidence = "; ".join(evidence_parts) if evidence_parts else None
        
        # Persist if requested
        item_id = None
        if request.persist:
            portfolio_item = PortfolioItemCreate(
                title=title,
                summary=summary,
                role=role,
                evidence=evidence,
            )
            created_item = portfolio_service.create_portfolio_item(
                UUID(auth.user_id),
                portfolio_item,
            )
            item_id = str(created_item.id)
        
        return PortfolioGenerateResponse(
            id=item_id,
            title=title,
            summary=summary,
            role=role,
            evidence=evidence,
            persisted=request.persist,
        )
        
    except HTTPException:
        raise
    except PortfolioItemServiceError as exc:
        logger.exception("Failed to persist portfolio item")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "persistence_error", "message": str(exc)},
        ) from exc
    except ProjectsServiceError as exc:
        logger.exception("Failed to fetch project for portfolio generation")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "project_error", "message": str(exc)},
        ) from exc
    except Exception as exc:
        logger.exception("Unexpected error generating portfolio item")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "generation_error", "message": str(exc)},
        ) from exc


# ============================================================================
# Resource Suggestions
# ============================================================================


class ResourceEntryModel(BaseModel):
    title: str
    url: str
    type: Literal["article", "video", "course", "docs"]
    level: Literal["beginner", "intermediate", "advanced"]


class ResourceSuggestionModel(BaseModel):
    skill_name: str
    current_tier: str
    target_tier: str
    reason: str
    importance: Optional[str] = None
    resources: List[ResourceEntryModel]


class ResourceSuggestionsResponse(BaseModel):
    suggestions: List[ResourceSuggestionModel]
    role: Optional[str] = None
    role_label: Optional[str] = None


@router.get(
    "/api/portfolio/resource-suggestions",
    response_model=ResourceSuggestionsResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        500: {"model": ErrorResponse, "description": "Failed to generate suggestions"},
    },
)
def get_resource_suggestions(
    role: Optional[str] = None,
    auth: AuthContext = Depends(get_auth_context),
    projects_service: ProjectsService = Depends(get_projects_service),
):
    """Return personalised learning resource suggestions based on scanned skills."""
    try:
        projects = projects_service.get_user_projects(auth.user_id)
        if not isinstance(projects, list):
            projects = []
    except Exception as exc:
        logger.exception("Failed to load projects for resource suggestions")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "project_load_error", "message": str(exc)},
        ) from exc

    from services.services.resource_suggestions_service import get_suggestions

    result = get_suggestions(
        user_id=auth.user_id,
        projects=projects,
        role=role,
    )

    return ResourceSuggestionsResponse(
        suggestions=[ResourceSuggestionModel(**s) for s in result["suggestions"]],
        role=result.get("role"),
        role_label=result.get("role_label"),
    )


# ============================================================================
# LinkedIn Post Generation
# ============================================================================


class LinkedInPostRequest(BaseModel):
    scope: Literal["portfolio", "project"] = Field("portfolio")
    project_id: Optional[str] = Field(None, description="Required when scope is 'project'")


class LinkedInPostResponse(BaseModel):
    post_text: str
    share_url: Optional[str] = None


@router.post(
    "/api/portfolio/linkedin-post",
    response_model=LinkedInPostResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        404: {"model": ErrorResponse, "description": "Project not found"},
        500: {"model": ErrorResponse, "description": "Failed to generate post"},
    },
)
def generate_linkedin_post(
    body: LinkedInPostRequest,
    auth: AuthContext = Depends(get_auth_context),
    projects_service: ProjectsService = Depends(get_projects_service),
):
    """Generate a LinkedIn post from portfolio or project data."""
    from services.services.linkedin_post_builder import (
        build_portfolio_post,
        build_project_post,
    )

    try:
        projects = projects_service.get_user_projects(auth.user_id)
        if not isinstance(projects, list):
            projects = []
    except Exception as exc:
        logger.exception("Failed to load projects for LinkedIn post")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "project_load_error", "message": str(exc)},
        ) from exc

    # Resolve public share URL
    share_url: Optional[str] = None
    try:
        from services.services.portfolio_settings_service import PortfolioSettingsService
        settings_service = PortfolioSettingsService()
        settings_service.apply_access_token(auth.access_token)
        settings = settings_service.get_settings(auth.user_id)
        if settings and settings.get("is_public") and settings.get("share_token"):
            share_url = settings["share_token"]
    except Exception as exc:
        logger.warning("Failed to resolve public share URL for LinkedIn post: %s", exc)

    if body.scope == "project" and body.project_id:
        project = next((p for p in projects if p.get("id") == body.project_id), None)
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"code": "not_found", "message": "Project not found"},
            )
        post_text = build_project_post(project)
    else:
        from services.services.resource_suggestions_service import collect_skill_names

        all_skills = collect_skill_names(projects)
        post_text = build_portfolio_post(
            projects=projects,
            skills=all_skills,
            share_url=share_url,
        )

    return LinkedInPostResponse(post_text=post_text, share_url=share_url)


# ============================================================================
# Portfolio Refresh with Deduplication
