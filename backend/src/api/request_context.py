from __future__ import annotations

from contextvars import ContextVar
from typing import Optional


_request_access_token: ContextVar[Optional[str]] = ContextVar("request_access_token", default=None)


def set_request_access_token(token: Optional[str]) -> None:
    _request_access_token.set(token)


def get_request_access_token() -> Optional[str]:
    return _request_access_token.get()


def clear_request_access_token() -> None:
    _request_access_token.set(None)
