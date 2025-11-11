from __future__ import annotations

import asyncio
import inspect

from textual.message import Message
from textual.message_pump import MessagePump


def dispatch_message(pump: MessagePump, message: Message) -> None:
    """Post a Textual message and ensure awaitables are scheduled."""
    result = pump.post_message(message)
    if inspect.isawaitable(result):
        asyncio.create_task(result)
