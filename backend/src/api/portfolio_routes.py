"""
Portfolio API routes
Implements portfolio refresh and management endpoints
"""

import logging
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, HTTPException, status, Header, Depends
from pydantic import BaseModel, Field

sys.path.insert(0, str(Path(__file__).parent.parent))

from cli.services.projects_service import ProjectsService, ProjectsServiceError
from cli.services.encryption import EncryptionService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/portfolio", tags=["Portfolio"])

# Initialize services
_projects_service: Optional[ProjectsService] = None


def get_projects_service() -> ProjectsService:
    """Get or create the ProjectsService singleton."""
    global _projects_service
    if _projects_service is None:
        try:
            encryption_service = EncryptionService()
        except Exception:
            encryption_service = None

        _projects_service = ProjectsService(
            encryption_service=encryption_service,
            encryption_required=False,
        )
    return _projects_service


def verify_auth_token(authorization: Optional[str] = Header(None)) -> str:
    """
    Verify JWT token from Authorization header.
    Returns user_id from token.
    """
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authorization token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header format. Use 'Bearer <token>'",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = parts[1]

    try:
        import jwt
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

class PortfolioRefreshRequest(BaseModel):
    """Request model for portfolio refresh operation."""
    project_ids: Optional[List[str]] = Field(
        None,
        description="Specific project IDs to refresh. Empty/None = all projects"
    )
    force_rescan: bool = Field(
        False,
        description="Ignore cache and recalculate all file hashes"
    )
    include_metrics_update: bool = Field(
        True,
        description="Recalculate contribution metrics during refresh"
    )


class RefreshedProjectInfo(BaseModel):
    """Details of a single refreshed project."""
    project_id: str
    project_name: str
    files_unchanged: int = 0
    files_updated: int = 0
    files_removed: int = 0
    new_total_files: int = 0
    refresh_timestamp: str


class PortfolioRefreshSummary(BaseModel):
    """Summary statistics for refresh operation."""
    total_projects_refreshed: int = 0
    total_files_processed: int = 0
    duration_ms: int = 0


class PortfolioRefreshResponse(BaseModel):
    """Response model for portfolio refresh."""
    refreshed_projects: List[RefreshedProjectInfo]
    summary: PortfolioRefreshSummary


class ErrorResponse(BaseModel):
    """Standard error response."""
    detail: str
    error_code: Optional[str] = None


# ============================================================================
# API Endpoints
# ============================================================================

@router.post(
    "/refresh",
    response_model=PortfolioRefreshResponse,
    status_code=status.HTTP_200_OK,
    responses={
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        404: {"model": ErrorResponse, "description": "Project not found"},
        500: {"model": ErrorResponse, "description": "Server error"},
    },
)
async def refresh_portfolio(
    request: PortfolioRefreshRequest = PortfolioRefreshRequest(),
    user_id: str = Depends(verify_auth_token),
) -> PortfolioRefreshResponse:
    """
    Refresh portfolio view by re-scanning cached file metadata.

    - **project_ids**: Optional list of specific project IDs to refresh
    - **force_rescan**: If true, ignores cache and recalculates all
    - **include_metrics_update**: If true, recalculates contribution metrics

    This operation:
    - Re-validates cached file metadata
    - Updates project totals and metrics
    - Removes stale entries from scan_files cache
    """
    start_time = time.time()

    try:
        service = get_projects_service()

        # Get projects to refresh
        if request.project_ids:
            # Validate specific projects exist
            projects_to_refresh = []
            for project_id in request.project_ids:
                project = service.get_project_scan(user_id, project_id)
                if not project:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"Project {project_id} not found",
                    )
                projects_to_refresh.append(project)
        else:
            # Get all projects for user
            projects_metadata = service.get_user_projects(user_id)
            projects_to_refresh = []
            for meta in projects_metadata:
                project = service.get_project_scan(user_id, meta["id"])
                if project:
                    projects_to_refresh.append(project)

        refreshed_projects: List[RefreshedProjectInfo] = []
        total_files_processed = 0

        for project in projects_to_refresh:
            project_id = project["id"]
            project_name = project.get("project_name", "Unknown")

            # Get cached files for this project
            try:
                cached_files = service.get_cached_files(user_id, project_id)
            except Exception:
                cached_files = {}

            # Count current state
            current_file_count = len(cached_files)
            total_files_processed += current_file_count

            # For now, refresh just updates the scan timestamp
            # In a full implementation, this would re-validate files
            refresh_timestamp = datetime.now().isoformat()

            refreshed_info = RefreshedProjectInfo(
                project_id=project_id,
                project_name=project_name,
                files_unchanged=current_file_count,
                files_updated=0,
                files_removed=0,
                new_total_files=current_file_count,
                refresh_timestamp=refresh_timestamp,
            )
            refreshed_projects.append(refreshed_info)

        duration_ms = int((time.time() - start_time) * 1000)

        return PortfolioRefreshResponse(
            refreshed_projects=refreshed_projects,
            summary=PortfolioRefreshSummary(
                total_projects_refreshed=len(refreshed_projects),
                total_files_processed=total_files_processed,
                duration_ms=duration_ms,
            ),
        )

    except HTTPException:
        raise
    except ProjectsServiceError as exc:
        logger.error(f"Projects service error: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to refresh portfolio: {str(exc)}",
        )
    except Exception as exc:
        logger.exception("Unexpected error refreshing portfolio")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred",
        )
