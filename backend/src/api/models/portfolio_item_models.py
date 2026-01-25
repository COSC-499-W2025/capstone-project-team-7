from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class PortfolioItemBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    summary: Optional[str] = Field(None, max_length=1000)
    role: Optional[str] = Field(None, max_length=255)
    evidence: Optional[str] = Field(None, max_length=2048)
    thumbnail: Optional[str] = Field(None, max_length=1024)


class PortfolioItemCreate(PortfolioItemBase):
    pass


class PortfolioItemUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    summary: Optional[str] = Field(None, max_length=1000)
    role: Optional[str] = Field(None, max_length=255)
    evidence: Optional[str] = Field(None, max_length=2048)
    thumbnail: Optional[str] = Field(None, max_length=1024)


class PortfolioItem(PortfolioItemBase):
    id: UUID
    user_id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
