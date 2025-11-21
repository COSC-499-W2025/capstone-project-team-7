from __future__ import annotations

from typing import Any

from textual.drivers import linux_driver as linux_module
from textual.drivers.linux_driver import LinuxDriver as BaseLinuxDriver


class DaemonLinuxDriver(BaseLinuxDriver):
    """Linux driver variant that marks the input thread as daemon.

    Textual keeps a dedicated thread alive to read keyboard events. On some
    Python builds (notably macOS arm64), that non-daemon thread prevents the
    interpreter from shutting down cleanly and causes a hang inside
    ``threading._shutdown``. This wrapper temporarily swaps Textual's thread
    factory so the ``textual-input`` worker starts as a daemon.
    """

    def start_application_mode(self) -> None:
        original_thread_cls = linux_module.Thread

        class _PatchedThread(original_thread_cls):  # type: ignore[misc]
            def __init__(self, *args: Any, **kwargs: Any) -> None:
                if (
                    kwargs.get("name") == "textual-input"
                    and not kwargs.get("daemon")
                ):
                    kwargs["daemon"] = True
                super().__init__(*args, **kwargs)

        linux_module.Thread = _PatchedThread  # type: ignore[assignment]
        try:
            super().start_application_mode()
        finally:
            linux_module.Thread = original_thread_cls
