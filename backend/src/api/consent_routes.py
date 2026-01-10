"""Consent API routes for standalone service usage."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from auth import consent as consent_store
from auth.consent_validator import ConsentValidator
from api.dependencies import AuthContext, get_auth_context


router = APIRouter(prefix="/api/consent", tags=["Consent"])


class ConsentStatus(BaseModel):
    user_id: str
    data_access: bool
    external_services: bool
    updated_at: datetime


class ConsentUpdateRequest(BaseModel):
    data_access: bool = Field(..., description="Consent for file analysis + metadata storage")
    external_services: bool = Field(..., description="Consent for external services (LLM)")
    notice_acknowledged_at: Optional[datetime] = Field(
        default=None,
        description="Timestamp when the privacy notice was acknowledged",
    )


class ConsentNotice(BaseModel):
    service: str
    privacy_notice: str
    implications: List[str] = Field(default_factory=list)
    options: List[str] = Field(default_factory=list)
    version: str


_NOTICE_IMPLICATIONS = [
    "Data may be sent to external providers for processing.",
    "External providers may store data per their privacy policies.",
    "Avoid sending personal or sensitive data.",
]


def _parse_timestamp(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _latest_timestamp(values: List[Optional[str]]) -> datetime:
    parsed = [ts for ts in (_parse_timestamp(value) for value in values) if ts]
    return max(parsed) if parsed else datetime.now(timezone.utc)


def _build_status(user_id: str, access_token: str) -> ConsentStatus:
    validator = ConsentValidator()
    file_consent = consent_store.get_consent(
        user_id, validator.SERVICE_FILE_ANALYSIS, access_token=access_token
    )
    metadata_consent = consent_store.get_consent(
        user_id, validator.SERVICE_METADATA, access_token=access_token
    )
    external_consent = consent_store.get_consent(
        user_id, validator.SERVICE_EXTERNAL, access_token=access_token
    )
    data_access = bool(
        file_consent
        and file_consent.get("consent_given")
        and metadata_consent
        and metadata_consent.get("consent_given")
    )
    external_services = bool(external_consent and external_consent.get("consent_given"))
    updated_at = _latest_timestamp(
        [
            file_consent.get("consent_timestamp") if file_consent else None,
            metadata_consent.get("consent_timestamp") if metadata_consent else None,
            external_consent.get("consent_timestamp") if external_consent else None,
        ]
    )
    return ConsentStatus(
        user_id=user_id,
        data_access=data_access,
        external_services=external_services,
        updated_at=updated_at,
    )


def _raise_validation_error(message: str) -> None:
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail={"code": "validation_error", "message": message},
    )


@router.get("", response_model=ConsentStatus)
def get_consent_status(auth: AuthContext = Depends(get_auth_context)) -> ConsentStatus:
    return _build_status(auth.user_id, auth.access_token)


@router.post("", response_model=ConsentStatus)
def set_consent_status(
    payload: ConsentUpdateRequest,
    auth: AuthContext = Depends(get_auth_context),
) -> ConsentStatus:
    if payload.external_services and not payload.data_access:
        _raise_validation_error("External services consent requires data_access")

    validator = ConsentValidator()
    consent_store.save_consent(
        user_id=auth.user_id,
        service_name=validator.SERVICE_FILE_ANALYSIS,
        consent_given=payload.data_access,
        access_token=auth.access_token,
    )
    consent_store.save_consent(
        user_id=auth.user_id,
        service_name=validator.SERVICE_METADATA,
        consent_given=payload.data_access,
        access_token=auth.access_token,
    )
    consent_store.save_consent(
        user_id=auth.user_id,
        service_name=validator.SERVICE_EXTERNAL,
        consent_given=payload.external_services,
        access_token=auth.access_token,
    )

    return _build_status(auth.user_id, auth.access_token)


@router.get("/notice", response_model=ConsentNotice)
def get_consent_notice(
    service: str = Query(..., description="Service name (e.g., external_services)"),
    auth: AuthContext = Depends(get_auth_context),
) -> ConsentNotice:
    notice = consent_store.request_consent(auth.user_id, service)
    return ConsentNotice(
        service=notice.get("service", service),
        privacy_notice=notice.get("privacy_notice", ""),
        implications=_NOTICE_IMPLICATIONS,
        options=notice.get("options", []),
        version="v1.0",
    )
