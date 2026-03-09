"""Encryption status API routes."""

from __future__ import annotations

import os
from typing import Optional

import logging

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from services.services.encryption import EncryptionService
from api.upload_routes import verify_auth_token


router = APIRouter(prefix="/api/encryption", tags=["Encryption"])
logger = logging.getLogger(__name__)


class EncryptionStatus(BaseModel):
    enabled: bool
    ready: bool
    error: Optional[str] = None


@router.get("/status", response_model=EncryptionStatus)
def get_encryption_status(_: str = Depends(verify_auth_token)) -> EncryptionStatus:
    enabled = bool(os.getenv(EncryptionService.ENV_KEY))
    try:
        EncryptionService()
        return EncryptionStatus(enabled=enabled, ready=True, error=None)
    except Exception as exc:
        logger.warning("Encryption initialization failed: %s", exc, exc_info=True)
        return EncryptionStatus(
            enabled=enabled,
            ready=False,
            error="Encryption is not configured or failed to initialize.",
        )
