"""User Resume API routes - full resume document CRUD."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Response, status
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


class UserResumeAddItemsRequest(BaseModel):
    item_ids: List[str] = Field(default_factory=list)


class UserResumeExportPdfRequest(BaseModel):
    latex_content: Optional[str] = None


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
# Helper Functions
# ============================================================================

def _build_resume_record(record: Dict[str, Any]) -> UserResumeRecord:
    """Build a UserResumeRecord from a database record dict."""
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


def _build_resume_summary(record: Dict[str, Any]) -> UserResumeSummary:
    """Build a UserResumeSummary from a database record dict."""
    return UserResumeSummary(
        id=record["id"],
        name=record.get("name") or "Untitled Resume",
        template=record.get("template") or "jake",
        is_latex_mode=record.get("is_latex_mode", True),
        metadata=record.get("metadata") or {},
        created_at=record.get("created_at"),
        updated_at=record.get("updated_at"),
    )


def _translate_service_error(
    exc: UserResumeServiceError,
    *,
    default_status: int,
    default_code: str,
) -> HTTPException:
    error_map = {
        "invalid_template": (
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "invalid_template",
        ),
        "invalid_resume_item_ids": (
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "invalid_payload",
        ),
        "resume_not_found": (
            status.HTTP_404_NOT_FOUND,
            "resume_not_found",
        ),
        "missing_latex_content": (
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "invalid_payload",
        ),
    }
    status_code, code = error_map.get(exc.code, (default_status, default_code))
    return HTTPException(
        status_code=status_code,
        detail={"code": code, "message": str(exc)},
    )


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
        records, total = service.list_resumes(auth.user_id, limit=limit, offset=offset)
    except UserResumeServiceError as exc:
        logger.exception("Failed to list user resumes")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "resume_list_error", "message": str(exc)},
        ) from exc

    summaries = [_build_resume_summary(item) for item in records]
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
        logger.exception("Failed to create user resume")
        raise _translate_service_error(
            exc,
            default_status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            default_code="resume_create_error",
        ) from exc

    return _build_resume_record(record)


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

    return _build_resume_record(record)


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
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
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
        logger.exception("Failed to update user resume")
        raise _translate_service_error(
            exc,
            default_status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            default_code="resume_update_error",
        ) from exc

    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "resume_not_found", "message": "Resume not found."},
        )

    return _build_resume_record(record)


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
        logger.exception("Failed to duplicate user resume")
        raise _translate_service_error(
            exc,
            default_status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            default_code="resume_duplicate_error",
        ) from exc

    return _build_resume_record(record)


@router.post(
    "/{resume_id}/add-items",
    response_model=UserResumeRecord,
    responses={
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        404: {"model": ErrorResponse, "description": "Resume not found"},
        422: {"model": ErrorResponse, "description": "Validation error"},
        500: {"model": ErrorResponse, "description": "Resume update failed"},
    },
)
def add_items_to_user_resume(
    resume_id: str,
    payload: UserResumeAddItemsRequest,
    auth: AuthContext = Depends(get_auth_context),
    service: UserResumeService = Depends(get_user_resume_service),
) -> UserResumeRecord:
    if not payload.item_ids:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={"code": "invalid_payload", "message": "item_ids is required."},
        )

    try:
        service.apply_access_token(auth.access_token)
        record = service.add_resume_items_to_resume(
            auth.user_id,
            resume_id,
            item_ids=payload.item_ids,
        )
    except UserResumeServiceError as exc:
        logger.exception("Failed to add resume items to user resume")
        raise _translate_service_error(
            exc,
            default_status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            default_code="resume_update_error",
        ) from exc

    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "resume_not_found", "message": "Resume not found."},
        )

    return _build_resume_record(record)


@router.post(
    "/{resume_id}/detect-skills",
    response_model=UserResumeRecord,
    responses={
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        404: {"model": ErrorResponse, "description": "Resume not found"},
        500: {"model": ErrorResponse, "description": "Resume update failed"},
    },
)
def detect_skills_for_user_resume(
    resume_id: str,
    auth: AuthContext = Depends(get_auth_context),
    service: UserResumeService = Depends(get_user_resume_service),
) -> UserResumeRecord:
    try:
        service.apply_access_token(auth.access_token)
        record = service.detect_skills_from_resume_projects(auth.user_id, resume_id)
    except UserResumeServiceError as exc:
        logger.exception("Failed to auto-detect resume skills")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "resume_update_error", "message": str(exc)},
        ) from exc

    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "resume_not_found", "message": "Resume not found."},
        )

    return _build_resume_record(record)


@router.post(
    "/{resume_id}/pdf",
    response_class=Response,
    responses={
        200: {"content": {"application/pdf": {}}},
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        404: {"model": ErrorResponse, "description": "Resume not found"},
        422: {"model": ErrorResponse, "description": "Validation error"},
        500: {"model": ErrorResponse, "description": "PDF export failed"},
    },
)
def export_user_resume_pdf(
    resume_id: str,
    payload: UserResumeExportPdfRequest,
    auth: AuthContext = Depends(get_auth_context),
    service: UserResumeService = Depends(get_user_resume_service),
) -> Response:
    try:
        service.apply_access_token(auth.access_token)
        pdf_bytes = service.render_pdf_bytes(
            auth.user_id,
            resume_id,
            latex_content=payload.latex_content,
        )
    except UserResumeServiceError as exc:
        logger.exception("Failed to export user resume PDF")
        raise _translate_service_error(
            exc,
            default_status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            default_code="resume_pdf_export_error",
        ) from exc

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{resume_id}.pdf"',
        },
    )
