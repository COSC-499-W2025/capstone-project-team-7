"""Portfolio chronology API routes."""

from __future__ import annotations

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from api.dependencies import AuthContext, get_auth_context
from cli.services.portfolio_timeline_service import (
    PortfolioTimelineService,
    PortfolioTimelineServiceError,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Portfolio"])

_timeline_service: Optional[PortfolioTimelineService] = None


def get_portfolio_timeline_service() -> PortfolioTimelineService:
    global _timeline_service
    if _timeline_service is None:
        _timeline_service = PortfolioTimelineService()
    return _timeline_service


class ErrorResponse(BaseModel):
    code: str
    message: str


class TimelineItem(BaseModel):
    project_id: str
    name: str
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    duration_days: Optional[int] = None
    role: Optional[str] = Field(None, description="User's role in the project")


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
