"""Portfolio chronology API routes."""

from __future__ import annotations

import logging
from typing import List, Optional, Dict
from collections import defaultdict
from uuid import UUID
from typing import List, Optional, Dict, Any
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

_timeline_service: Optional[PortfolioTimelineService] = None
_portfolio_item_service: Optional[PortfolioItemService] = None
_projects_service: Optional[ProjectsService] = None


def get_portfolio_timeline_service() -> PortfolioTimelineService:
    global _timeline_service
    if _timeline_service is None:
        _timeline_service = PortfolioTimelineService()
    return _timeline_service


def get_portfolio_item_service() -> PortfolioItemService:
    global _portfolio_item_service
    if _portfolio_item_service is None:
        _portfolio_item_service = PortfolioItemService()
    return _portfolio_item_service


def get_projects_service() -> ProjectsService:
    """Get or create the ProjectsService singleton."""
    global _projects_service
    if _projects_service is None:
        try:
            from services.services.encryption import EncryptionService
            encryption_service = EncryptionService()
        except Exception:
            encryption_service = None
        _projects_service = ProjectsService(
            encryption_service=encryption_service,
            encryption_required=False,
        )
    return _projects_service


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
# Portfolio Refresh with Deduplication
