# Project API Routes Helper Module
# Provides models, services, and utilities for project scan CRUD operations
# Endpoints are registered in this module's router

from fastapi import APIRouter, HTTPException, status, Header, Depends
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
import asyncio
import logging
import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

try:
    from cli.services.projects_service import ProjectsService, ProjectsServiceError
    from cli.services.encryption import EncryptionService
except ModuleNotFoundError:  # pragma: no cover - test/import fallback
    from backend.src.cli.services.projects_service import ProjectsService, ProjectsServiceError
    from backend.src.cli.services.encryption import EncryptionService

logger = logging.getLogger(__name__)

# Create router for project endpoints
router = APIRouter(prefix="/api/projects", tags=["Projects"])

# Initialize services
_projects_service: Optional[ProjectsService] = None
_encryption_service: Optional[EncryptionService] = None


def get_projects_service() -> ProjectsService:
    """Get or create the ProjectsService singleton."""
    global _projects_service
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
    """Get or create the EncryptionService singleton."""
    global _encryption_service
    if _encryption_service is None:
        try:
            _encryption_service = EncryptionService()
        except Exception:
            _encryption_service = None
    return _encryption_service


def normalize_project_data(project: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize project data from database to match model expectations.
    
    Handles None values for boolean and list fields by converting to defaults.
    """
    # Convert None boolean fields to False
    boolean_fields = [
        'has_media_analysis', 'has_pdf_analysis', 'has_code_analysis',
        'has_git_analysis', 'has_contribution_metrics', 'has_skills_analysis',
        'has_document_analysis', 'has_skills_progress'
    ]
    for field in boolean_fields:
        if field in project and project[field] is None:
            project[field] = False
    
    # Convert None languages list to empty list
    if 'languages' in project and project['languages'] is None:
        project['languages'] = []
    
    return project


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
    created_at: Optional[str] = None


class ProjectDetail(ProjectMetadata):
    """Full project details including scan data."""
    scan_data: Optional[Dict[str, Any]] = None


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


class ProjectTimelineResponse(BaseModel):
    """Response with chronologically ordered projects."""
    count: int
    timeline: List[ProjectTimelineEntry]


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
        
        # Get service and save scan
        service = get_projects_service()
        result = service.save_scan(
            user_id=user_id,
            project_name=request.project_name,
            project_path=request.project_path,
            scan_data=scan_data_dict,
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
        projects = service.get_user_projects(user_id)
        
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
    Get projects ordered chronologically by scan timestamp.
    
    Returns projects sorted by scan_timestamp (newest first).
    """
    try:
        service = get_projects_service()
        
        # Get all user projects (run in thread pool to avoid blocking event loop)
        projects = await asyncio.to_thread(service.get_user_projects, user_id)
        
        # Build timeline entries with full project objects
        timeline_entries = []
        for project in projects:
            scan_timestamp = project.get("scan_timestamp") or project.get("created_at")
            
            if not scan_timestamp:
                # Skip projects without timestamps
                continue
            
            # Parse to datetime for proper sorting
            try:
                # Handle various timestamp formats
                ts_str = scan_timestamp.replace("Z", "+00:00")
                dt = datetime.fromisoformat(ts_str)
            except Exception as e:
                # If parsing fails, try to use it as-is and log error
                print(f"Failed to parse timestamp for {project.get('project_name')}: {scan_timestamp}, error: {e}")
                continue
            
            timeline_entries.append({
                "project": project,
                "display_date": scan_timestamp,
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
        )
    
    except Exception as exc:
        logger.exception(f"Error fetching project timeline: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch project timeline: {str(exc)}",
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
    
    Acceptance Criteria:
    - Full scan data is retrievable by project ID
    - Only project owner can access their projects
    """
    try:
        service = get_projects_service()
        project = service.get_project_scan(user_id, project_id)
        
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project {project_id} not found",
            )
        
        # Normalize project data before converting to model
        project = normalize_project_data(project)
        
        # Convert to ProjectDetail object for response
        return ProjectDetail(**project)
    
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
        from cli.services.contribution_analysis_service import ContributionAnalysisService
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
