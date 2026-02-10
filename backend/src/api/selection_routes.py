"""Selection API routes for managing user preferences."""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional
import logging
import sys
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

sys.path.insert(0, str(Path(__file__).parent.parent))

from api.dependencies import AuthContext, get_auth_context
from services.services.selection_service import SelectionService, SelectionServiceError


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/selection", tags=["Selection"])

# Global service instance
_selection_service: Optional[SelectionService] = None


def get_selection_service() -> SelectionService:
    """Get or create the SelectionService singleton."""
    global _selection_service
    if _selection_service is None:
        try:
            _selection_service = SelectionService()
        except SelectionServiceError as exc:
            logger.error(f"Failed to initialize SelectionService: {exc}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={"code": "service_unavailable", "message": str(exc)},
            )
    return _selection_service


class SelectionRequest(BaseModel):
    """Request model for saving user selections."""
    project_order: Optional[List[str]] = Field(default=None, description="Ordered list of project IDs")
    skill_order: Optional[List[str]] = Field(default=None, description="Ordered list of skill names")
    selected_project_ids: Optional[List[str]] = Field(default=None, description="Project IDs selected for showcase")
    selected_skill_ids: Optional[List[str]] = Field(default=None, description="Skill names selected for showcase")


class SelectionResponse(BaseModel):
    """Response model for user selections."""
    user_id: str
    project_order: List[str] = Field(default_factory=list)
    skill_order: List[str] = Field(default_factory=list)
    selected_project_ids: List[str] = Field(default_factory=list)
    selected_skill_ids: List[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


@router.post("", response_model=SelectionResponse, status_code=status.HTTP_200_OK)
async def save_selection(
    payload: SelectionRequest,
    auth: AuthContext = Depends(get_auth_context),
    service: SelectionService = Depends(get_selection_service),
) -> SelectionResponse:
    """
    Save or update user's selection preferences.
    
    Stores custom ordering for projects and skills, and tracks which items
    are selected for showcase in the portfolio display.
    
    - **project_order**: Custom display order for projects (list of project IDs)
    - **skill_order**: Custom display order for skills (list of skill names)
    - **selected_project_ids**: Projects to showcase in portfolio
    - **selected_skill_ids**: Skills to showcase in portfolio
    
    The selection persists and is used by the display logic to control
    ordering and showcase visibility.
    
    Args:
        payload: Selection preferences to save
        auth: Authenticated user context
        service: Selection service instance
    
    Returns:
        Saved selection record with all fields
    
    Raises:
        401: If authentication fails
        500: If database operation fails
    """
    try:
        # Save selections to database
        result = service.save_user_selections(
            user_id=auth.user_id,
            project_order=payload.project_order,
            skill_order=payload.skill_order,
            selected_project_ids=payload.selected_project_ids,
            selected_skill_ids=payload.selected_skill_ids,
        )
        
        # Convert to response model
        return SelectionResponse(
            user_id=result["user_id"],
            project_order=result.get("project_order") or [],
            skill_order=result.get("skill_order") or [],
            selected_project_ids=result.get("selected_project_ids") or [],
            selected_skill_ids=result.get("selected_skill_ids") or [],
            created_at=result["created_at"],
            updated_at=result["updated_at"],
        )
        
    except SelectionServiceError as exc:
        logger.error(f"Failed to save selections for user {auth.user_id}: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "save_failed", "message": str(exc)},
        )


@router.get("", response_model=SelectionResponse, status_code=status.HTTP_200_OK)
async def get_selection(
    auth: AuthContext = Depends(get_auth_context),
    service: SelectionService = Depends(get_selection_service),
) -> SelectionResponse:
    """
    Get user's current selection preferences.
    
    Returns the stored ordering and showcase selection for projects and skills.
    If no selections have been saved yet, returns empty lists for all fields.
    
    Args:
        auth: Authenticated user context
        service: Selection service instance
    
    Returns:
        User's selection preferences
    
    Raises:
        401: If authentication fails
        500: If database query fails
    """
    try:
        result = service.get_user_selections(auth.user_id)
        
        if not result:
            # Return empty selections if none exist yet
            return SelectionResponse(
                user_id=auth.user_id,
                project_order=[],
                skill_order=[],
                selected_project_ids=[],
                selected_skill_ids=[],
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
        
        return SelectionResponse(
            user_id=result["user_id"],
            project_order=result.get("project_order") or [],
            skill_order=result.get("skill_order") or [],
            selected_project_ids=result.get("selected_project_ids") or [],
            selected_skill_ids=result.get("selected_skill_ids") or [],
            created_at=result["created_at"],
            updated_at=result["updated_at"],
        )
        
    except SelectionServiceError as exc:
        logger.error(f"Failed to retrieve selections for user {auth.user_id}: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "retrieval_failed", "message": str(exc)},
        )


@router.delete("", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
async def delete_selection(
    auth: AuthContext = Depends(get_auth_context),
    service: SelectionService = Depends(get_selection_service),
) -> None:
    """
    Delete user's selection preferences.
    
    Removes all stored ordering and showcase preferences. This is useful
    for resetting to defaults.
    
    Args:
        auth: Authenticated user context
        service: Selection service instance
    
    Raises:
        401: If authentication fails
        500: If database operation fails
    """
    try:
        service.delete_user_selections(auth.user_id)
    except SelectionServiceError as exc:
        logger.error(f"Failed to delete selections for user {auth.user_id}: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "deletion_failed", "message": str(exc)},
        )
