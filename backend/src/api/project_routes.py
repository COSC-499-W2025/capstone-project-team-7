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

sys.path.insert(0, str(Path(__file__).parent.parent))

from cli.services.projects_service import ProjectsService, ProjectsServiceError
from cli.services.encryption import EncryptionService
from cli.services.merge_service import MergeDeduplicationService, MergeResult

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


class AppendUploadRequest(BaseModel):
    """Request model for appending upload to project."""
    deduplication_strategy: str = Field(
        "hash",
        description="Strategy for detecting duplicates: 'hash', 'path', or 'both'"
    )
    conflict_resolution: str = Field(
        "newer",
        description="How to resolve conflicts: 'newer', 'keep_existing', or 'replace'"
    )
    dry_run: bool = Field(
        False,
        description="If true, return what would happen without applying changes"
    )


class DuplicateDetail(BaseModel):
    """Details about a detected duplicate."""
    new_file_path: str
    existing_file_path: Optional[str] = None
    resolution: str
    reason: str


class MergeResultModel(BaseModel):
    """Summary of merge operation results."""
    files_added: int = 0
    files_updated: int = 0
    duplicates_skipped: int = 0
    total_project_files: int = 0


class AppendUploadResponse(BaseModel):
    """Response model for append-upload operation."""
    project_id: str
    upload_id: str
    merge_result: MergeResultModel
    duplicate_details: List[DuplicateDetail] = []
    merge_timestamp: str
    dry_run: bool = False


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


# In-memory uploads store reference (shared with upload_routes)
# This will be replaced with database in production
_uploads_store: Optional[Dict] = None


def get_uploads_store() -> Dict:
    """Get the uploads store (shared with upload_routes module)."""
    global _uploads_store
    if _uploads_store is None:
        # Import from upload_routes to share the same store
        try:
            from api.upload_routes import uploads_store
            _uploads_store = uploads_store
        except ImportError:
            _uploads_store = {}
    return _uploads_store


@router.post(
    "/{project_id}/append-upload/{upload_id}",
    response_model=AppendUploadResponse,
    status_code=status.HTTP_200_OK,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid request"},
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        404: {"model": ErrorResponse, "description": "Project or upload not found"},
        409: {"model": ErrorResponse, "description": "Upload already merged"},
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
    Merge files from an upload into an existing project with deduplication.

    - **project_id**: UUID of the target project
    - **upload_id**: ID of the upload to merge
    - **deduplication_strategy**: 'hash', 'path', or 'both'
    - **conflict_resolution**: 'newer', 'keep_existing', or 'replace'
    - **dry_run**: If true, return preview without applying changes

    Acceptance Criteria:
    - New uploads merge correctly
    - No duplicate files created
    """
    # Validate deduplication strategy
    valid_strategies = {"hash", "path", "both"}
    if request.deduplication_strategy not in valid_strategies:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid deduplication_strategy. Must be one of: {valid_strategies}",
        )

    # Validate conflict resolution
    valid_resolutions = {"newer", "keep_existing", "replace"}
    if request.conflict_resolution not in valid_resolutions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid conflict_resolution. Must be one of: {valid_resolutions}",
        )

    try:
        service = get_projects_service()

        # Verify project exists and belongs to user
        project = service.get_project_scan(user_id, project_id)
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project {project_id} not found",
            )

        # Verify upload exists and belongs to user
        uploads_store = get_uploads_store()
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

        # Check upload status
        if upload_data.get("status") not in ("stored", "parsed"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Upload status is '{upload_data.get('status')}', expected 'stored' or 'parsed'",
            )

        # Parse the upload if not already parsed
        from pathlib import Path as FilePath
        from scanner.parser import parse_zip
        from scanner.models import FileMetadata as ScanFileMetadata

        storage_path = FilePath(upload_data.get("storage_path", ""))
        if not storage_path.exists():
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Upload file not found on disk",
            )

        # Parse the upload to get file metadata
        parse_result = parse_zip(storage_path)
        new_files = parse_result.files

        # Get existing cached files for the project
        try:
            existing_files = service.get_cached_files(user_id, project_id)
        except Exception:
            existing_files = {}

        # Analyze merge with deduplication
        merge_service = MergeDeduplicationService()
        merge_result = merge_service.analyze_merge(
            existing_files=existing_files,
            new_files=new_files,
            strategy=request.deduplication_strategy,
            conflict_resolution=request.conflict_resolution,
        )

        merge_timestamp = datetime.now().isoformat()

        # Apply merge if not dry run
        if not request.dry_run:
            # Prepare files to upsert
            files_to_upsert = []
            for candidate in merge_result.candidates:
                if candidate.resolution in ("add", "update"):
                    # Find the corresponding FileMetadata
                    file_meta = next(
                        (f for f in new_files if f.path == candidate.file_path),
                        None
                    )
                    if file_meta:
                        files_to_upsert.append({
                            "relative_path": file_meta.path,
                            "size_bytes": file_meta.size_bytes,
                            "mime_type": file_meta.mime_type,
                            "sha256": file_meta.file_hash,
                            "metadata": {},
                            "last_seen_modified_at": file_meta.modified_at.isoformat() + "Z",
                            "last_scanned_at": merge_timestamp + "Z",
                        })

            if files_to_upsert:
                service.upsert_cached_files(user_id, project_id, files_to_upsert)

        # Build response
        duplicate_details = [
            DuplicateDetail(
                new_file_path=d["new_file_path"],
                existing_file_path=d["existing_file_path"],
                resolution=d["resolution"],
                reason=d["reason"],
            )
            for d in merge_service.export_merge_details(merge_result)
        ]

        return AppendUploadResponse(
            project_id=project_id,
            upload_id=upload_id,
            merge_result=MergeResultModel(
                files_added=merge_result.files_added,
                files_updated=merge_result.files_updated,
                duplicates_skipped=merge_result.duplicates_skipped,
                total_project_files=merge_result.total_project_files,
            ),
            duplicate_details=duplicate_details,
            merge_timestamp=merge_timestamp,
            dry_run=request.dry_run,
        )

    except HTTPException:
        raise
    except ProjectsServiceError as exc:
        logger.error(f"Projects service error: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to merge upload: {str(exc)}",
        )
    except Exception as exc:
        logger.exception("Unexpected error merging upload")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred",
        )
