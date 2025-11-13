from __future__ import annotations

import asyncio
import inspect
from typing import Optional

from textual.message import Message
from textual.message_pump import MessagePump


def _log_message(pump: MessagePump, message: Message, stage: str) -> None:
    """Log dispatch diagnostics when the pump exposes _debug_log."""
    log_fn = getattr(pump, "_debug_log", None)
    if not callable(log_fn):
        app = getattr(pump, "app", None)
        log_fn = getattr(app, "_debug_log", None) if app else None
    if callable(log_fn):
        try:
            log_fn(f"[dispatch:{stage}] pump={pump.__class__.__name__} message={message.__class__.__name__}")
        except Exception:
            pass


def dispatch_message(pump: MessagePump, message: Message) -> None:
    """Post a Textual message and ensure awaitables are scheduled."""
    _log_message(pump, message, "start")
    result = pump.post_message(message)
    if inspect.isawaitable(result):
        asyncio.create_task(result)
        _log_message(pump, message, "awaitable")
    else:
        _log_message(pump, message, "posted")
