"""Portfolio settings and public sharing API routes."""
from __future__ import annotations

import asyncio
import logging
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

sys.path.insert(0, str(Path(__file__).parent.parent))

from api.dependencies import AuthContext, get_auth_context
from services.services.portfolio_settings_service import (
    PortfolioSettingsService,
    PortfolioSettingsError,
)
from services.services.portfolio_timeline_service import PortfolioTimelineService
from services.services.projects_service import ProjectsService

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Portfolio Settings"])

_settings_service: Optional[PortfolioSettingsService] = None


def get_settings_service() -> PortfolioSettingsService:
    global _settings_service
    if _settings_service is None:
        try:
            _settings_service = PortfolioSettingsService()
        except PortfolioSettingsError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={"code": "service_unavailable", "message": str(exc)},
            )
    return _settings_service


def get_auth_settings_service(
    auth: AuthContext = Depends(get_auth_context),
    service: PortfolioSettingsService = Depends(get_settings_service),
) -> PortfolioSettingsService:
    service.apply_access_token(auth.access_token)
    return service


# ── Request / Response models ───────────────────────────────────────────

class SettingsUpdateRequest(BaseModel):
    display_name: Optional[str] = None
    bio: Optional[str] = None
    show_heatmap: Optional[bool] = None
    show_skills_timeline: Optional[bool] = None
    show_top_projects: Optional[bool] = None
    show_all_skills: Optional[bool] = None
    showcase_count: Optional[int] = Field(default=None, ge=1, le=10)


class PublishRequest(BaseModel):
    is_public: bool


class SettingsResponse(BaseModel):
    is_public: bool = False
    share_token: Optional[str] = None
    display_name: Optional[str] = None
    bio: Optional[str] = None
    show_heatmap: bool = True
    show_skills_timeline: bool = True
    show_top_projects: bool = True
    show_all_skills: bool = True
    showcase_count: int = 3


class PublishResponse(BaseModel):
    is_public: bool
    share_token: Optional[str] = None


# ── Authenticated endpoints ─────────────────────────────────────────────

@router.get("/api/portfolio/settings", response_model=SettingsResponse)
async def get_portfolio_settings(
    auth: AuthContext = Depends(get_auth_context),
    service: PortfolioSettingsService = Depends(get_auth_settings_service),
) -> SettingsResponse:
    """Get the current user's portfolio display settings."""
    try:
        result = service.get_settings(auth.user_id)
        if not result:
            return SettingsResponse()
        return SettingsResponse(**{
            k: result[k] for k in SettingsResponse.model_fields if k in result
        })
    except PortfolioSettingsError as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.patch("/api/portfolio/settings", response_model=SettingsResponse)
async def update_portfolio_settings(
    payload: SettingsUpdateRequest,
    auth: AuthContext = Depends(get_auth_context),
    service: PortfolioSettingsService = Depends(get_auth_settings_service),
) -> SettingsResponse:
    """Update the current user's portfolio display settings."""
    try:
        updates = payload.model_dump(exclude_none=True)
        if not updates:
            result = service.get_settings(auth.user_id)
            if not result:
                return SettingsResponse()
        else:
            result = service.upsert_settings(auth.user_id, **updates)
        return SettingsResponse(**{
            k: result[k] for k in SettingsResponse.model_fields if k in result
        })
    except PortfolioSettingsError as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/api/portfolio/settings/publish", response_model=PublishResponse)
async def publish_portfolio(
    payload: PublishRequest,
    auth: AuthContext = Depends(get_auth_context),
    service: PortfolioSettingsService = Depends(get_auth_settings_service),
) -> PublishResponse:
    """Toggle portfolio public visibility. Generates a share token on first publish."""
    try:
        result = service.toggle_public(auth.user_id, payload.is_public)
        return PublishResponse(
            is_public=result.get("is_public", False),
            share_token=result.get("share_token"),
        )
    except PortfolioSettingsError as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ── Public endpoint (no auth) ───────────────────────────────────────────

class PublicPortfolioResponse(BaseModel):
    profile: Dict[str, Any]
    settings: Dict[str, Any]
    skills_timeline: List[Dict[str, Any]] = Field(default_factory=list)
    projects_timeline: List[Dict[str, Any]] = Field(default_factory=list)
    top_projects: List[Dict[str, Any]] = Field(default_factory=list)
    heatmap_data: List[Dict[str, Any]] = Field(default_factory=list)
    all_skills: List[str] = Field(default_factory=list)


def _get_projects_service_for_user(user_id: str, access_token: Optional[str] = None) -> ProjectsService:
    """Create a ProjectsService scoped to a user for public data access."""
    try:
        from services.services.encryption import EncryptionService
        encryption_service = EncryptionService()
    except Exception:
        encryption_service = None
    service = ProjectsService(encryption_service=encryption_service)
    if access_token:
        service.apply_access_token(access_token)
    return service


@router.get("/api/public/portfolio/{share_token}")
async def get_public_portfolio(share_token: str) -> JSONResponse:
    """
    Fetch a published portfolio by share token. No authentication required.

    Returns profile info, skills timeline, project timeline, top projects,
    and heatmap data for the portfolio owner.
    """
    service = get_settings_service()

    settings = service.get_by_share_token(share_token)
    if not settings:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Portfolio not found or not published.",
        )

    user_id = settings["user_id"]

    # Fetch profile (display_name, avatar, career_title, education)
    profile_data: Dict[str, Any] = {}
    p = service.get_user_profile(user_id)
    if p:
        profile_data = {
            "display_name": settings.get("display_name") or p.get("full_name") or "Anonymous",
            "career_title": p.get("career_title"),
            "education": p.get("education"),
            "avatar_url": p.get("avatar_url"),
            "bio": settings.get("bio"),
        }

    # Fetch portfolio data using service-role access
    skills_timeline: List[Dict[str, Any]] = []
    projects_timeline: List[Dict[str, Any]] = []
    all_skills: List[str] = []
    top_projects: List[Dict[str, Any]] = []
    heatmap_data: List[Dict[str, Any]] = []

    try:
        projects_service = _get_projects_service_for_user(user_id)
        timeline_service = PortfolioTimelineService(projects_service=projects_service)

        # Fetch all data in parallel
        skills_timeline, projects_timeline, all_projects = await asyncio.gather(
            asyncio.to_thread(timeline_service.get_skills_timeline, user_id),
            asyncio.to_thread(timeline_service.get_projects_timeline, user_id),
            asyncio.to_thread(projects_service.get_user_projects, user_id),
        )

        # Aggregate skills
        skill_set: set[str] = set()
        for entry in skills_timeline:
            for s in entry.get("skills", []):
                skill_set.add(s)
        all_skills = sorted(skill_set)

        # Heatmap from skills timeline
        heatmap_data = [
            {"period": e.get("period_label", ""), "commits": e.get("commits", 0)}
            for e in skills_timeline
        ]
        if all_projects:
            showcase_count = settings.get("showcase_count", 3)
            scored = [p for p in all_projects if p.get("contribution_score")]
            scored.sort(key=lambda p: p.get("contribution_score", 0), reverse=True)
            for p in scored[:showcase_count]:
                top_projects.append({
                    "project_name": p.get("project_name", ""),
                    "contribution_score": p.get("contribution_score"),
                    "total_commits": p.get("total_commits"),
                    "user_commit_share": p.get("user_commit_share"),
                    "primary_contributor": p.get("primary_contributor"),
                    "languages": p.get("languages"),
                })
    except Exception as exc:
        logger.warning("Failed to fetch portfolio data for public view: %s", exc)

    # Filter sections based on settings
    visible_settings = {
        "show_heatmap": settings.get("show_heatmap", True),
        "show_skills_timeline": settings.get("show_skills_timeline", True),
        "show_top_projects": settings.get("show_top_projects", True),
        "show_all_skills": settings.get("show_all_skills", True),
        "showcase_count": settings.get("showcase_count", 3),
    }

    return JSONResponse({
        "profile": profile_data,
        "settings": visible_settings,
        "skills_timeline": skills_timeline if visible_settings["show_skills_timeline"] else [],
        "projects_timeline": projects_timeline,
        "top_projects": top_projects if visible_settings["show_top_projects"] else [],
        "heatmap_data": heatmap_data if visible_settings["show_heatmap"] else [],
        "all_skills": all_skills if visible_settings["show_all_skills"] else [],
    })
