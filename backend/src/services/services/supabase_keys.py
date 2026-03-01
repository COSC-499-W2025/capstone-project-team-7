from __future__ import annotations

import os
from typing import Any, Optional

try:
    from postgrest._sync.client import SyncPostgrestClient
except Exception:
    SyncPostgrestClient = None


_PLACEHOLDER_PREFIXES = (
    "your-",
    "changeme",
    "replace-me",
    "example",
)


def _is_placeholder(value: Optional[str]) -> bool:
    if value is None:
        return True

    raw = value.strip()
    if not raw:
        return True

    lowered = raw.lower()
    if lowered in {"none", "null", "undefined"}:
        return True

    return lowered.startswith(_PLACEHOLDER_PREFIXES)


def is_placeholder_key(value: Optional[str]) -> bool:
    return _is_placeholder(value)


def is_jwt_like(value: Optional[str]) -> bool:
    return bool(value and value.count(".") >= 2)


def resolve_supabase_api_key(
    explicit_key: Optional[str] = None,
    *,
    prefer_anon_for_python_client: bool = False,
) -> Optional[str]:
    service_role = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    generic_key = os.getenv("SUPABASE_KEY")
    anon_key = os.getenv("SUPABASE_ANON_KEY")

    if not _is_placeholder(explicit_key):
        return explicit_key

    if not _is_placeholder(service_role):
        return service_role

    if (
        prefer_anon_for_python_client
        and generic_key
        and generic_key.startswith("sb_publishable_")
        and is_jwt_like(anon_key)
    ):
        return anon_key

    if not _is_placeholder(generic_key):
        return generic_key

    if not _is_placeholder(anon_key):
        return anon_key

    return None


def create_postgrest_client(supabase_url: str, apikey: str) -> Any:
    if SyncPostgrestClient is None:
        raise RuntimeError("postgrest client is not available")

    base_url = f"{supabase_url.rstrip('/')}/rest/v1"
    return SyncPostgrestClient(
        base_url,
        headers={
            "Accept": "application/json",
            "Content-Type": "application/json",
            "apikey": apikey,
        },
        timeout=10,
    )


def apply_client_access_token(client: Any, token: Optional[str]) -> None:
    if client is None:
        return

    try:
        if hasattr(client, "postgrest"):
            if token:
                client.postgrest.auth(token)
            else:
                client.postgrest.auth(None)
            return
        if hasattr(client, "auth"):
            client.auth(token)
    except Exception:
        return
