from __future__ import annotations

from textual.widgets import Markdown


class ScanMarkdown(Markdown):
    """Markdown widget with defaults suited for scan results."""

    DEFAULT_CSS = """
    ScanMarkdown {
        background: transparent;
        color: #e5e7eb;
    }

    ScanMarkdown > .markdown h1,
    ScanMarkdown > .markdown h2,
    ScanMarkdown > .markdown h3 {
        color: #f8fafc;
    }
    """
