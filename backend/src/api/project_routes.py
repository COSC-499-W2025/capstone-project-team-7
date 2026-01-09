# Project API Routes Helper Module
# Provides models, services, and utilities for project scan CRUD operations
# To be integrated into spec_routes.py

from fastapi import HTTPException, status, Header
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

logger = logging.getLogger(__name__)

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
    languages: List[str] = []
    has_media_analysis: bool = False
    has_pdf_analysis: bool = False
    has_code_analysis: bool = False
    has_git_analysis: bool = False
    has_contribution_metrics: bool = False
    has_skills_analysis: bool = False
    has_document_analysis: bool = False
    has_skills_progress: bool = False
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
# Note: Endpoint implementations are in spec_routes.py
# ============================================================================
# This module provides reusable models, services, and utilities
# The actual @router.post/@router.get/@router.delete endpoints
# are registered in spec_routes.py and integrated with the shared router.
# This keeps all API endpoints consolidated in one place per the team's
# architecture while maintaining modular helper code here.
