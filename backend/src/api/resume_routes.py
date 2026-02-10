"""Resume item CRUD API routes backed by Supabase resume storage."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from api.dependencies import AuthContext, get_auth_context
from services.services.resume_storage_service import ResumeStorageError, ResumeStorageService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/resume", tags=["Resume"])


def get_resume_service() -> ResumeStorageService:
    """Create a ResumeStorageService instance."""
    try:
        return ResumeStorageService()
    except ResumeStorageError as exc:
        logger.error("Failed to initialize ResumeStorageService: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "service_unavailable", "message": str(exc)},
        )


class ErrorResponse(BaseModel):
    code: str
    message: str


class Pagination(BaseModel):
    limit: int
    offset: int
    total: int


class ResumeItemSummary(BaseModel):
    id: str
    project_name: str
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    created_at: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ResumeItemRecord(ResumeItemSummary):
    content: str
    bullets: List[str] = Field(default_factory=list)
    source_path: Optional[str] = None


class ResumeItemListResponse(BaseModel):
    items: List[ResumeItemSummary] = Field(default_factory=list)
    page: Pagination


class ResumeItemCreateRequest(BaseModel):
    project_name: str
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    overview: Optional[str] = None
    content: Optional[str] = None
    bullets: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    source_path: Optional[str] = None


class ResumeItemUpdateRequest(BaseModel):
    project_name: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    content: Optional[str] = None
    bullets: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None
    source_path: Optional[str] = None


def _build_markdown_content(
    project_name: str,
    start_date: Optional[str],
    end_date: Optional[str],
    overview: Optional[str],
    bullets: List[str],
) -> str:
    date_span = start_date or "Unknown Dates"
    if end_date:
        date_span = f"{date_span} - {end_date}"
    lines = [f"{project_name} - {date_span}"]
    if overview:
        overview_line = overview.strip()
        if overview_line:
            lines.append(f"Overview: {overview_line}")
    for bullet in bullets:
        lines.append(f"- {bullet}")
    return "\n".join(lines)


@router.get(
    "/items",
    response_model=ResumeItemListResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        500: {"model": ErrorResponse, "description": "Resume retrieval failed"},
    },
)
def list_resume_items(
    limit: int = 20,
    offset: int = 0,
    auth: AuthContext = Depends(get_auth_context),
    service: ResumeStorageService = Depends(get_resume_service),
) -> ResumeItemListResponse:
    try:
        service.apply_access_token(auth.access_token)
        records = service.get_user_resumes(auth.user_id)
    except ResumeStorageError as exc:
        logger.exception("Failed to list resume items")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "resume_list_error", "message": str(exc)},
        ) from exc

    total = len(records)
    items = records[offset : offset + limit]
    summaries = [
        ResumeItemSummary(
            id=item["id"],
            project_name=item.get("project_name") or "",
            start_date=item.get("start_date"),
            end_date=item.get("end_date"),
            created_at=item.get("created_at"),
            metadata=item.get("metadata") or {},
        )
        for item in items
    ]
    return ResumeItemListResponse(items=summaries, page=Pagination(limit=limit, offset=offset, total=total))


@router.post(
    "/items",
    response_model=ResumeItemRecord,
    responses={
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        422: {"model": ErrorResponse, "description": "Validation error"},
        500: {"model": ErrorResponse, "description": "Resume creation failed"},
    },
)
def create_resume_item(
    payload: ResumeItemCreateRequest,
    auth: AuthContext = Depends(get_auth_context),
    service: ResumeStorageService = Depends(get_resume_service),
) -> ResumeItemRecord:
    content = (payload.content or "").strip()
    if not content:
        content = _build_markdown_content(
            project_name=payload.project_name,
            start_date=payload.start_date,
            end_date=payload.end_date,
            overview=payload.overview,
            bullets=payload.bullets,
        ).strip()

    if not content:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "invalid_payload", "message": "Resume content is required."},
        )

    try:
        service.apply_access_token(auth.access_token)
        record = service.save_resume_record(
            auth.user_id,
            project_name=payload.project_name,
            start_date=payload.start_date,
            end_date=payload.end_date,
            content=content,
            bullets=payload.bullets,
            metadata=payload.metadata,
            source_path=payload.source_path,
        )
    except ResumeStorageError as exc:
        logger.exception("Failed to save resume item")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "resume_save_error", "message": str(exc)},
        ) from exc

    record = service._decrypt_record(record)
    return ResumeItemRecord(
        id=record["id"],
        project_name=record.get("project_name") or "",
        start_date=record.get("start_date"),
        end_date=record.get("end_date"),
        created_at=record.get("created_at"),
        metadata=record.get("metadata") or {},
        content=record.get("content") or "",
        bullets=record.get("bullets") or [],
        source_path=record.get("source_path"),
    )


@router.get(
    "/items/{resume_id}",
    response_model=ResumeItemRecord,
    responses={
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        404: {"model": ErrorResponse, "description": "Resume item not found"},
        500: {"model": ErrorResponse, "description": "Resume retrieval failed"},
    },
)
def get_resume_item(
    resume_id: str,
    auth: AuthContext = Depends(get_auth_context),
    service: ResumeStorageService = Depends(get_resume_service),
) -> ResumeItemRecord:
    try:
        service.apply_access_token(auth.access_token)
        record = service.get_resume_item(auth.user_id, resume_id)
    except ResumeStorageError as exc:
        logger.exception("Failed to load resume item")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "resume_fetch_error", "message": str(exc)},
        ) from exc

    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "resume_not_found", "message": "Resume item not found."},
        )

    return ResumeItemRecord(
        id=record["id"],
        project_name=record.get("project_name") or "",
        start_date=record.get("start_date"),
        end_date=record.get("end_date"),
        created_at=record.get("created_at"),
        metadata=record.get("metadata") or {},
        content=record.get("content") or "",
        bullets=record.get("bullets") or [],
        source_path=record.get("source_path"),
    )


@router.patch(
    "/items/{resume_id}",
    response_model=ResumeItemRecord,
    responses={
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        404: {"model": ErrorResponse, "description": "Resume item not found"},
        422: {"model": ErrorResponse, "description": "Validation error"},
        500: {"model": ErrorResponse, "description": "Resume update failed"},
    },
)
def update_resume_item(
    resume_id: str,
    payload: ResumeItemUpdateRequest,
    auth: AuthContext = Depends(get_auth_context),
    service: ResumeStorageService = Depends(get_resume_service),
) -> ResumeItemRecord:
    if (
        payload.project_name is None
        and payload.start_date is None
        and payload.end_date is None
        and payload.content is None
        and payload.bullets is None
        and payload.metadata is None
        and payload.source_path is None
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "invalid_payload", "message": "No fields provided for update."},
        )

    try:
        service.apply_access_token(auth.access_token)
        record = service.update_resume_item(
            auth.user_id,
            resume_id,
            project_name=payload.project_name,
            start_date=payload.start_date,
            end_date=payload.end_date,
            content=payload.content,
            bullets=payload.bullets,
            metadata=payload.metadata,
            source_path=payload.source_path,
        )
    except ResumeStorageError as exc:
        logger.exception("Failed to update resume item")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "resume_update_error", "message": str(exc)},
        ) from exc

    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "resume_not_found", "message": "Resume item not found."},
        )

    return ResumeItemRecord(
        id=record["id"],
        project_name=record.get("project_name") or "",
        start_date=record.get("start_date"),
        end_date=record.get("end_date"),
        created_at=record.get("created_at"),
        metadata=record.get("metadata") or {},
        content=record.get("content") or "",
        bullets=record.get("bullets") or [],
        source_path=record.get("source_path"),
    )


@router.delete(
    "/items/{resume_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
    responses={
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        404: {"model": ErrorResponse, "description": "Resume item not found"},
        500: {"model": ErrorResponse, "description": "Resume deletion failed"},
    },
)
def delete_resume_item(
    resume_id: str,
    auth: AuthContext = Depends(get_auth_context),
    service: ResumeStorageService = Depends(get_resume_service),
) -> None:
    try:
        service.apply_access_token(auth.access_token)
        deleted = service.delete_resume_item(auth.user_id, resume_id)
    except ResumeStorageError as exc:
        logger.exception("Failed to delete resume item")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "resume_delete_error", "message": str(exc)},
        ) from exc

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "resume_not_found", "message": "Resume item not found."},
        )
