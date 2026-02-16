"""Backward-compatible state exports.

Legacy tests and modules import ``state`` directly.
Keep this thin wrapper while moving implementation to ``services.state``.
"""

from services.state import *  # noqa: F401,F403
