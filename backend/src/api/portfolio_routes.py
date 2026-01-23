"""Portfolio chronology API routes."""

from __future__ import annotations

import logging
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from api.dependencies import AuthContext, get_auth_context
from api.models.portfolio_item_models import PortfolioItem, PortfolioItemCreate, PortfolioItemUpdate
from cli.services.portfolio_item_service import (
    PortfolioItemService,
    PortfolioItemServiceError,
)
from cli.services.portfolio_timeline_service import (
    PortfolioTimelineService,
    PortfolioTimelineServiceError,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Portfolio"])

_timeline_service: Optional[PortfolioTimelineService] = None
_portfolio_item_service: Optional[PortfolioItemService] = None


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


class ErrorResponse(BaseModel):
    code: str
    message: str


class TimelineItem(BaseModel):
    project_id: str
    name: str
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    duration_days: Optional[int] = None


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
        ) from exc
