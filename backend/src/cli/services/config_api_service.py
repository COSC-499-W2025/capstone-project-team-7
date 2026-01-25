from __future__ import annotations

from typing import Any, Dict, Optional
import os

import httpx


class ConfigAPIServiceError(Exception):
    """Raised when config API calls fail."""


class ConfigAPIService:
    """HTTP client for config/profile endpoints used by the TUI."""

    def __init__(self, base_url: Optional[str] = None, timeout: float = 10.0) -> None:
        self._base_url = (
            base_url
            or os.getenv("API_BASE_URL")
            or os.getenv("PORTFOLIO_API_URL")
            or "http://127.0.0.1:8000"
        )
        self._timeout = timeout

    def get_config(self, user_id: str, *, access_token: Optional[str] = None) -> Dict[str, Any]:
        return self._request(
            "GET",
            "/api/config",
            access_token=access_token,
            params={"user_id": user_id},
        )

    def update_config(
        self,
        user_id: str,
        *,
        access_token: Optional[str] = None,
        current_profile: Optional[str] = None,
        max_file_size_mb: Optional[int] = None,
        follow_symlinks: Optional[bool] = None,
    ) -> Dict[str, Any]:
        payload: Dict[str, Any] = {"user_id": user_id}
        if current_profile:
            payload["current_profile"] = current_profile
        if max_file_size_mb is not None:
            payload["max_file_size_mb"] = max_file_size_mb
        if follow_symlinks is not None:
            payload["follow_symlinks"] = follow_symlinks
        return self._request(
            "PUT",
            "/api/config",
            access_token=access_token,
            json=payload,
        )

    def list_profiles(self, user_id: str, *, access_token: Optional[str] = None) -> Dict[str, Any]:
        return self._request(
            "GET",
            "/api/config/profiles",
            access_token=access_token,
            params={"user_id": user_id},
        )

    def save_profile(
        self,
        user_id: str,
        name: str,
        *,
        access_token: Optional[str] = None,
        extensions: Optional[list[str]] = None,
        exclude_dirs: Optional[list[str]] = None,
        description: Optional[str] = None,
    ) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "user_id": user_id,
            "name": name,
        }
        if extensions is not None:
            payload["extensions"] = extensions
        if exclude_dirs is not None:
            payload["exclude_dirs"] = exclude_dirs
        if description is not None:
            payload["description"] = description
        return self._request(
            "POST",
            "/api/config/profiles",
            access_token=access_token,
            json=payload,
        )

    def delete_profile(
        self,
        user_id: str,
        name: str,
        *,
        access_token: Optional[str] = None,
    ) -> None:
        self._request(
            "DELETE",
            f"/api/config/profiles/{name}",
            access_token=access_token,
            params={"user_id": user_id},
        )

    def _request(
        self,
        method: str,
        path: str,
        *,
        access_token: Optional[str] = None,
        json: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        headers: Dict[str, str] = {}
        if access_token:
            headers["Authorization"] = f"Bearer {access_token}"
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
            raise ConfigAPIServiceError(f"Config API request failed: {exc}") from exc

        payload: Dict[str, Any]
        try:
            payload = response.json()
        except ValueError:
            payload = {}

        if response.status_code >= 400:
            detail = payload.get("detail") if isinstance(payload, dict) else payload
            raise ConfigAPIServiceError(
                f"Config API error ({response.status_code}): {detail or response.text}"
            )

        return payload
