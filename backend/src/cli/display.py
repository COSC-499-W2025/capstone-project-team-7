from __future__ import annotations

from pathlib import Path

from ..scanner.models import ParseResult


def format_bytes(size: int) -> str:
    """Represent file sizes with a readable binary unit."""
    step = 1024.0
    units = ["B", "KB", "MB", "GB", "TB", "PB"]
    value = float(size)
    for unit in units:
        if value < step or unit == units[-1]:
            return f"{value:.2f} {unit}"
        value /= step
    return f"{value:.2f} PB"


def format_rows(rows: list[tuple[str, str, str]]) -> str:
    """Build an aligned two-space padded table for readability."""
    col_widths = [0, 0, 0]
    for path, mime, size in rows:
        col_widths[0] = max(col_widths[0], len(path))
        col_widths[1] = max(col_widths[1], len(mime))
        col_widths[2] = max(col_widths[2], len(size))
    header = ("PATH", "MIME TYPE", "SIZE")
    col_widths = [max(col_widths[i], len(header[i])) for i in range(3)]
    line = (
        f"{header[0]:<{col_widths[0]}}  "
        f"{header[1]:<{col_widths[1]}}  "
        f"{header[2]:<{col_widths[2]}}"
    )
    separator = "-" * len(line)
    formatted_rows = [
        f"{path:<{col_widths[0]}}  {mime:<{col_widths[1]}}  {size:<{col_widths[2]}}"
        for path, mime, size in rows
    ]
    return "\n".join([line, separator, *formatted_rows])


def render_table(archive_path: Path, result: ParseResult) -> list[str]:
    """Render human-readable lines describing the parse result."""
    rows = [
        (meta.path, meta.mime_type, format_bytes(meta.size_bytes))
        for meta in result.files
    ]
    lines: list[str] = [
        f"Archive parsed: {archive_path}",
        f"Files: {len(rows)}",
    ]
    if rows:
        lines.append(format_rows(rows))
    lines.append(f"Issues: {len(result.issues)}")
    for issue in result.issues:
        lines.append(f"{issue.code} {issue.path} {issue.message}")
    summary = result.summary
    processed = summary.get("bytes_processed", 0)
    filtered = summary.get("filtered_out")
    extra = f", filtered_out={filtered}" if filtered is not None else ""
    lines.append(
        "Summary: "
        f"files_processed={summary.get('files_processed', len(result.files))}, "
        f"bytes_processed={processed} ({format_bytes(processed)}), "
        f"issues_count={summary.get('issues_count', len(result.issues))}"
        f"{extra}"
    )
    return lines
