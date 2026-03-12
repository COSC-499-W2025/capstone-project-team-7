"""User Resume API routes - full resume document CRUD."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from api.dependencies import AuthContext, get_auth_context
from services.services.user_resume_service import UserResumeService, UserResumeServiceError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/user-resumes", tags=["User Resumes"])


def get_user_resume_service() -> UserResumeService:
    """Create a UserResumeService instance."""
    try:
        return UserResumeService()
    except UserResumeServiceError as exc:
        logger.error("Failed to initialize UserResumeService: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "service_unavailable", "message": str(exc)},
        )


# ============================================================================
# Request/Response Models
# ============================================================================

class ErrorResponse(BaseModel):
    code: str
    message: str


class Pagination(BaseModel):
    limit: int
    offset: int
    total: int


class ResumeTemplateMeta(BaseModel):
    """Metadata about a resume template."""
    id: str
    name: str
    description: str
    preview_url: Optional[str] = None


class UserResumeSummary(BaseModel):
    """Summary of a user resume (for list view)."""
    id: str
    name: str
    template: str
    is_latex_mode: bool
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class UserResumeRecord(UserResumeSummary):
    """Full user resume record with content."""
    latex_content: Optional[str] = None
    structured_data: Dict[str, Any] = Field(default_factory=dict)


class UserResumeListResponse(BaseModel):
    """Response for listing user resumes."""
    items: List[UserResumeSummary] = Field(default_factory=list)
    page: Pagination


class UserResumeCreateRequest(BaseModel):
    """Request to create a new resume."""
    name: str = "Untitled Resume"
    template: str = "jake"
    latex_content: Optional[str] = None
    structured_data: Optional[Dict[str, Any]] = None
    is_latex_mode: bool = True
    metadata: Optional[Dict[str, Any]] = None


class UserResumeUpdateRequest(BaseModel):
    """Request to update a resume."""
    name: Optional[str] = None
    template: Optional[str] = None
    latex_content: Optional[str] = None
    structured_data: Optional[Dict[str, Any]] = None
    is_latex_mode: Optional[bool] = None
    metadata: Optional[Dict[str, Any]] = None


class UserResumeDuplicateRequest(BaseModel):
    """Request to duplicate a resume."""
    new_name: Optional[str] = None


class TemplatesListResponse(BaseModel):
    """Response for listing available templates."""
    templates: List[ResumeTemplateMeta] = Field(default_factory=list)


# ============================================================================
# Template Definitions
# ============================================================================

AVAILABLE_TEMPLATES: List[ResumeTemplateMeta] = [
    ResumeTemplateMeta(
        id="jake",
        name="Jake's Resume",
        description="Clean, ATS-friendly single-column LaTeX template. Great for software engineering roles.",
        preview_url=None,
    ),
    ResumeTemplateMeta(
        id="classic",
        name="Classic",
        description="Traditional professional resume layout with serif fonts.",
        preview_url=None,
    ),
    ResumeTemplateMeta(
        id="modern",
        name="Modern",
        description="Contemporary design with a sidebar for contact info and skills.",
        preview_url=None,
    ),
    ResumeTemplateMeta(
        id="minimal",
        name="Minimal",
        description="Ultra-clean minimalist design focused on content.",
        preview_url=None,
    ),
    ResumeTemplateMeta(
        id="custom",
        name="Custom",
        description="Start from scratch with your own LaTeX code.",
        preview_url=None,
    ),
]


# ============================================================================
# Routes
# ============================================================================

@router.get(
    "/templates",
    response_model=TemplatesListResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Unauthorized"},
    },
)
def list_templates(
    auth: AuthContext = Depends(get_auth_context),
) -> TemplatesListResponse:
    """List all available resume templates."""
    return TemplatesListResponse(templates=AVAILABLE_TEMPLATES)


@router.get(
    "",
    response_model=UserResumeListResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        500: {"model": ErrorResponse, "description": "Resume retrieval failed"},
    },
)
def list_user_resumes(
    limit: int = 20,
    offset: int = 0,
    auth: AuthContext = Depends(get_auth_context),
    service: UserResumeService = Depends(get_user_resume_service),
) -> UserResumeListResponse:
    """List all resumes for the authenticated user."""
    try:
        service.apply_access_token(auth.access_token)
        records = service.list_resumes(auth.user_id)
    except UserResumeServiceError as exc:
        logger.exception("Failed to list user resumes")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "resume_list_error", "message": str(exc)},
        ) from exc

    total = len(records)
    items = records[offset : offset + limit]
    summaries = [
        UserResumeSummary(
            id=item["id"],
            name=item.get("name") or "Untitled Resume",
            template=item.get("template") or "jake",
            is_latex_mode=item.get("is_latex_mode", True),
            metadata=item.get("metadata") or {},
            created_at=item.get("created_at"),
            updated_at=item.get("updated_at"),
        )
        for item in items
    ]
    return UserResumeListResponse(
        items=summaries,
        page=Pagination(limit=limit, offset=offset, total=total),
    )


@router.post(
    "",
    response_model=UserResumeRecord,
    status_code=status.HTTP_201_CREATED,
    responses={
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        422: {"model": ErrorResponse, "description": "Validation error"},
        500: {"model": ErrorResponse, "description": "Resume creation failed"},
    },
)
def create_user_resume(
    payload: UserResumeCreateRequest,
    auth: AuthContext = Depends(get_auth_context),
    service: UserResumeService = Depends(get_user_resume_service),
) -> UserResumeRecord:
    """Create a new resume document."""
    try:
        service.apply_access_token(auth.access_token)
        record = service.create_resume(
            auth.user_id,
            name=payload.name,
            template=payload.template,
            latex_content=payload.latex_content,
            structured_data=payload.structured_data,
            is_latex_mode=payload.is_latex_mode,
            metadata=payload.metadata,
        )
    except UserResumeServiceError as exc:
        if "Invalid template" in str(exc):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={"code": "invalid_template", "message": str(exc)},
            ) from exc
        logger.exception("Failed to create user resume")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "resume_create_error", "message": str(exc)},
        ) from exc

    return UserResumeRecord(
        id=record["id"],
        name=record.get("name") or "Untitled Resume",
        template=record.get("template") or "jake",
        is_latex_mode=record.get("is_latex_mode", True),
        metadata=record.get("metadata") or {},
        created_at=record.get("created_at"),
        updated_at=record.get("updated_at"),
        latex_content=record.get("latex_content"),
        structured_data=record.get("structured_data") or {},
    )


@router.get(
    "/{resume_id}",
    response_model=UserResumeRecord,
    responses={
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        404: {"model": ErrorResponse, "description": "Resume not found"},
        500: {"model": ErrorResponse, "description": "Resume retrieval failed"},
    },
)
def get_user_resume(
    resume_id: str,
    auth: AuthContext = Depends(get_auth_context),
    service: UserResumeService = Depends(get_user_resume_service),
) -> UserResumeRecord:
    """Fetch a single resume with full content."""
    try:
        service.apply_access_token(auth.access_token)
        record = service.get_resume(auth.user_id, resume_id)
    except UserResumeServiceError as exc:
        logger.exception("Failed to fetch user resume")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "resume_fetch_error", "message": str(exc)},
        ) from exc

    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "resume_not_found", "message": "Resume not found."},
        )

    return UserResumeRecord(
        id=record["id"],
        name=record.get("name") or "Untitled Resume",
        template=record.get("template") or "jake",
        is_latex_mode=record.get("is_latex_mode", True),
        metadata=record.get("metadata") or {},
        created_at=record.get("created_at"),
        updated_at=record.get("updated_at"),
        latex_content=record.get("latex_content"),
        structured_data=record.get("structured_data") or {},
    )


@router.patch(
    "/{resume_id}",
    response_model=UserResumeRecord,
    responses={
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        404: {"model": ErrorResponse, "description": "Resume not found"},
        422: {"model": ErrorResponse, "description": "Validation error"},
        500: {"model": ErrorResponse, "description": "Resume update failed"},
    },
)
def update_user_resume(
    resume_id: str,
    payload: UserResumeUpdateRequest,
    auth: AuthContext = Depends(get_auth_context),
    service: UserResumeService = Depends(get_user_resume_service),
) -> UserResumeRecord:
    """Update an existing resume."""
    # Check if any fields provided
    if all(
        v is None
        for v in [
            payload.name,
            payload.template,
            payload.latex_content,
            payload.structured_data,
            payload.is_latex_mode,
            payload.metadata,
        ]
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "invalid_payload", "message": "No fields provided for update."},
        )

    try:
        service.apply_access_token(auth.access_token)
        record = service.update_resume(
            auth.user_id,
            resume_id,
            name=payload.name,
            template=payload.template,
            latex_content=payload.latex_content,
            structured_data=payload.structured_data,
            is_latex_mode=payload.is_latex_mode,
            metadata=payload.metadata,
        )
    except UserResumeServiceError as exc:
        if "Invalid template" in str(exc):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={"code": "invalid_template", "message": str(exc)},
            ) from exc
        logger.exception("Failed to update user resume")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "resume_update_error", "message": str(exc)},
        ) from exc

    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "resume_not_found", "message": "Resume not found."},
        )

    return UserResumeRecord(
        id=record["id"],
        name=record.get("name") or "Untitled Resume",
        template=record.get("template") or "jake",
        is_latex_mode=record.get("is_latex_mode", True),
        metadata=record.get("metadata") or {},
        created_at=record.get("created_at"),
        updated_at=record.get("updated_at"),
        latex_content=record.get("latex_content"),
        structured_data=record.get("structured_data") or {},
    )


@router.delete(
    "/{resume_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
    responses={
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        404: {"model": ErrorResponse, "description": "Resume not found"},
        500: {"model": ErrorResponse, "description": "Resume deletion failed"},
    },
)
def delete_user_resume(
    resume_id: str,
    auth: AuthContext = Depends(get_auth_context),
    service: UserResumeService = Depends(get_user_resume_service),
) -> None:
    """Delete a resume."""
    try:
        service.apply_access_token(auth.access_token)
        deleted = service.delete_resume(auth.user_id, resume_id)
    except UserResumeServiceError as exc:
        logger.exception("Failed to delete user resume")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "resume_delete_error", "message": str(exc)},
        ) from exc

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "resume_not_found", "message": "Resume not found."},
        )


@router.post(
    "/{resume_id}/duplicate",
    response_model=UserResumeRecord,
    status_code=status.HTTP_201_CREATED,
    responses={
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        404: {"model": ErrorResponse, "description": "Resume not found"},
        500: {"model": ErrorResponse, "description": "Resume duplication failed"},
    },
)
def duplicate_user_resume(
    resume_id: str,
    payload: UserResumeDuplicateRequest,
    auth: AuthContext = Depends(get_auth_context),
    service: UserResumeService = Depends(get_user_resume_service),
) -> UserResumeRecord:
    """Duplicate an existing resume."""
    try:
        service.apply_access_token(auth.access_token)
        record = service.duplicate_resume(auth.user_id, resume_id, payload.new_name)
    except UserResumeServiceError as exc:
        if "not found" in str(exc).lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"code": "resume_not_found", "message": str(exc)},
            ) from exc
        logger.exception("Failed to duplicate user resume")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "resume_duplicate_error", "message": str(exc)},
        ) from exc

    return UserResumeRecord(
        id=record["id"],
        name=record.get("name") or "Untitled Resume",
        template=record.get("template") or "jake",
        is_latex_mode=record.get("is_latex_mode", True),
        metadata=record.get("metadata") or {},
        created_at=record.get("created_at"),
        updated_at=record.get("updated_at"),
        latex_content=record.get("latex_content"),
        structured_data=record.get("structured_data") or {},
    )
