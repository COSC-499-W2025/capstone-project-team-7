# Project API Routes Helper Module
# Provides models, services, and utilities for project scan CRUD operations
# Endpoints are registered in this module's router

from fastapi import APIRouter, HTTPException, status, Header, Depends
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
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
