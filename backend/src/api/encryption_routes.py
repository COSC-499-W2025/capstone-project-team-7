"""Encryption status API routes."""

from __future__ import annotations

import os
from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel

from services.services.encryption import EncryptionService


router = APIRouter(prefix="/api/encryption", tags=["Encryption"])


class EncryptionStatus(BaseModel):
    enabled: bool
    ready: bool
    error: Optional[str] = None


@router.get("/status", response_model=EncryptionStatus)
def get_encryption_status() -> EncryptionStatus:
    enabled = bool(os.getenv(EncryptionService.ENV_KEY))
    try:
        EncryptionService()
        return EncryptionStatus(enabled=enabled, ready=True, error=None)
    except Exception as exc:  # pragma: no cover - varies by env
        return EncryptionStatus(enabled=enabled, ready=False, error=str(exc))
