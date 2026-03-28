"""API security hardening: rate limiting, security headers, path validation."""

from __future__ import annotations

import os
from pathlib import Path

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi.responses import JSONResponse


# ---------------------------------------------------------------------------
# Rate limiter (in-memory by default; swap to Redis URI via RATELIMIT_STORAGE)
# ---------------------------------------------------------------------------

_storage_uri = os.getenv("RATELIMIT_STORAGE", "memory://")
limiter = Limiter(key_func=get_remote_address, storage_uri=_storage_uri)


def rate_limit_exceeded_handler(_request: Request, exc: RateLimitExceeded) -> JSONResponse:
    """Return a JSON 429 instead of a plain-text error."""
    return JSONResponse(
        status_code=429,
        content={
            "error": "rate_limit_exceeded",
            "message": f"Too many requests. {exc.detail}",
        },
    )


# ---------------------------------------------------------------------------
# Security response headers middleware
# ---------------------------------------------------------------------------

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Inject standard hardening headers on every response."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        # HSTS – only advertise when the caller opted in (e.g. behind TLS termination)
        if os.getenv("ENABLE_HSTS", "").lower() in ("1", "true", "yes"):
            max_age = int(os.getenv("HSTS_MAX_AGE", "31536000"))
            response.headers["Strict-Transport-Security"] = (
                f"max-age={max_age}; includeSubDomains"
            )
        return response


# ---------------------------------------------------------------------------
# Upload / storage path validation
# ---------------------------------------------------------------------------

def validate_storage_path(
    user_path: str,
    root: Path | str,
) -> Path:
    """Resolve *user_path* under *root* and reject traversal attacks.

    Returns the resolved, absolute ``Path`` that is guaranteed to live
    inside *root*.  Raises ``ValueError`` for any traversal attempt,
    null-byte injection, or otherwise invalid path.
    """
    root = Path(root).resolve()

    # Reject null bytes early (common bypass on some OSes)
    if "\x00" in user_path:
        raise ValueError("Path contains null bytes")

    # Reject absolute paths and explicit traversal fragments
    cleaned = user_path.replace("\\", "/")
    if cleaned.startswith("/") or ":" in cleaned:
        raise ValueError("Absolute paths are not allowed")

    # Resolve and ensure the result stays under root
    target = (root / cleaned).resolve()
    if not (target == root or str(target).startswith(str(root) + os.sep)):
        raise ValueError("Path escapes the upload root")

    return target
