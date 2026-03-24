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


def generate_resume_content_from_project(
    project: Dict[str, Any],
    persist: bool,
    user_id: str,
    resume_service: ResumeStorageService
) -> Dict[str, Any]:
    """
    Helper function to generate resume item content from a project.
    Can be called synchronously from background tasks or other contexts.
    
    Args:
        project: Project data dictionary from database
        persist: Whether to save to database
        user_id: User ID string
        resume_service: ResumeStorageService instance
        
    Returns:
        Dictionary with id, project_name, start_date, end_date, bullets, content, persisted
    """
    # Extract scan_data - handle None or non-dict values
    _raw = project.get("scan_data")
    scan_data = _raw if isinstance(_raw, dict) else {}
    
    # Generate project name
    project_name = project.get("project_name", "Untitled Project")
    
    # Extract dates if available
    start_date = None
    end_date = None
    git_analysis = scan_data.get("git_analysis", [])
    if git_analysis and len(git_analysis) > 0:
        repo = git_analysis[0] if isinstance(git_analysis, list) else git_analysis
        first_commit = repo.get("first_commit_date")
        last_commit = repo.get("last_commit_date")
        if first_commit:
            # Format as "Mon YYYY"
            try:
                from datetime import datetime
                dt = datetime.fromisoformat(first_commit.replace('Z', '+00:00'))
                start_date = dt.strftime("%b %Y")
            except (ValueError, TypeError):
                pass
        if last_commit:
            try:
                from datetime import datetime
                dt = datetime.fromisoformat(last_commit.replace('Z', '+00:00'))
                end_date = dt.strftime("%b %Y")
            except (ValueError, TypeError):
                pass
    
    # Generate bullets from scan data
    bullets = []
    
    # Bullet 1: Technologies used
    languages = scan_data.get("languages") or project.get("languages", [])
    if languages:
        if isinstance(languages, list) and len(languages) > 0:
            if isinstance(languages[0], dict):
                lang_names = [l.get("name", l.get("language", "Unknown")) for l in languages[:4]]
            else:
                lang_names = languages[:4]
            if lang_names:
                bullets.append(f"Developed using {', '.join(lang_names)}")
    
    # Bullet 2: Project scope/metrics
    total_files = project.get("total_files") or scan_data.get("total_files", 0)
    total_lines = project.get("total_lines") or scan_data.get("total_lines", 0)
    code_metrics = scan_data.get("code_metrics") or scan_data.get("code_analysis", {})
    if total_files and total_lines:
        metric_parts = [f"{total_files} files", f"{total_lines:,} lines of code"]
        if code_metrics:
            functions = code_metrics.get("functions", 0)
            if functions:
                metric_parts.append(f"{functions} functions")
        bullets.append(f"Implemented {', '.join(metric_parts)}")
    
    # Bullet 3: Git contribution
    if git_analysis and len(git_analysis) > 0:
        repo = git_analysis[0] if isinstance(git_analysis, list) else git_analysis
        commit_count = repo.get("commit_count", 0)
        if commit_count:
            bullets.append(f"Contributed {commit_count} commits to the codebase")
    
    # Bullet 4: Skills demonstrated
    skills = scan_data.get("skills", [])
    if skills:
        skill_names = [s.get("name", s) if isinstance(s, dict) else s for s in skills[:4]]
        if skill_names:
            bullets.append(f"Applied skills in {', '.join(skill_names)}")
    
    # Generate markdown content
    content = _build_markdown_content(
        project_name=project_name,
        start_date=start_date,
        end_date=end_date,
        overview=None,
        bullets=bullets,
    )
    
    # Persist if requested
    item_id = None
    if persist and bullets:
        try:
            record = resume_service.save_resume_record(
                user_id=user_id,
                project_name=project_name,
                start_date=start_date,
                end_date=end_date,
                content=content,
                bullets=bullets,
                metadata={"auto_generated": True, "project_id": project.get("id")},
                source_path=project.get("project_path"),
            )
            item_id = record.get("id")
        except Exception as e:
            logger.warning(f"Failed to persist resume item: {e}")
    
    return {
        "id": item_id,
        "project_name": project_name,
        "start_date": start_date,
        "end_date": end_date,
        "bullets": bullets,
        "content": content,
        "persisted": persist,
    }


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
