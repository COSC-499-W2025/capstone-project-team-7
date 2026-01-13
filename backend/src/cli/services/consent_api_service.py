from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional
import os

import httpx

from ...auth.consent_validator import ConsentRecord


class ConsentAPIServiceError(Exception):
    """Raised when consent API calls fail."""


def _parse_timestamp(value: Optional[str]) -> datetime:
    if not value:
        return datetime.now(timezone.utc)
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return datetime.now(timezone.utc)


class ConsentAPIService:
    """HTTP client for consent endpoints used by the TUI."""

    def __init__(self, base_url: Optional[str] = None, timeout: float = 10.0) -> None:
        self._base_url = base_url or os.getenv("PORTFOLIO_API_URL", "http://127.0.0.1:8000")
        self._timeout = timeout

    def fetch_status(self, access_token: str) -> Dict[str, Any]:
        return self._request(
            "GET",
            "/api/consent",
            access_token=access_token,
        )

    def update_status(
        self,
        access_token: str,
        *,
        data_access: bool,
        external_services: bool,
    ) -> Dict[str, Any]:
        payload = {
            "data_access": data_access,
            "external_services": external_services,
        }
        return self._request(
            "POST",
            "/api/consent",
            access_token=access_token,
            json=payload,
        )

    def fetch_notice(self, access_token: str, service: str) -> Dict[str, Any]:
        return self._request(
            "GET",
            "/api/consent/notice",
            access_token=access_token,
            params={"service": service},
        )

    def status_to_record(self, status: Dict[str, Any]) -> Optional[ConsentRecord]:
        if not status.get("data_access"):
            return None
        created_at = _parse_timestamp(status.get("updated_at"))
        return ConsentRecord(
            id="api-consent",
            user_id=str(status.get("user_id", "")),
            analyze_uploaded_only=True,
            process_store_metadata=True,
            privacy_ack=True,
            allow_external_services=bool(status.get("external_services")),
            created_at=created_at,
            privacy_notice_version="v1.0",
        )

    def _request(
        self,
        method: str,
        path: str,
        *,
        access_token: str,
        json: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        if not access_token:
            raise ConsentAPIServiceError("Access token required for consent API calls.")
        headers = {"Authorization": f"Bearer {access_token}"}
        try:
            with httpx.Client(base_url=self._base_url, timeout=self._timeout) as client:
                response = client.request(
                    method,
                    path,
                    headers=headers,
                    json=json,
                    params=params,
                )
        except httpx.RequestError as exc:
            raise ConsentAPIServiceError(f"Consent API request failed: {exc}") from exc

        payload: Dict[str, Any]
        try:
            payload = response.json()
        except ValueError:
            payload = {}

        if response.status_code >= 400:
            detail = payload.get("detail") if isinstance(payload, dict) else payload
            raise ConsentAPIServiceError(
                f"Consent API error ({response.status_code}): {detail or response.text}"
            )

        return payload
