from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable, Mapping

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


def render_language_table(languages: Iterable[dict[str, object]]) -> str:
    """Render a language breakdown table."""
    entries = list(languages)
    if not entries:
        return ""

    header = ("LANGUAGE", "FILES", "FILES %", "BYTES", "BYTES %")

    def row(entry: dict[str, object]) -> tuple[str, str, str, str, str]:
        # Percentages are precomputed upstream so we only worry about formatting here.
        return (
            str(entry["language"]),
            str(entry["files"]),
            f"{entry['file_percent']:.2f}%",
            format_bytes(int(entry["bytes"])),
            f"{entry['byte_percent']:.2f}%",
        )

    formatted = [row(entry) for entry in entries]
    col_widths = [len(part) for part in header]
    for parts in formatted:
        for idx, part in enumerate(parts):
            col_widths[idx] = max(col_widths[idx], len(part))

    def join(parts: tuple[str, ...]) -> str:
        return "  ".join(part.ljust(col_widths[idx]) for idx, part in enumerate(parts))

    lines = [join(header), "-" * len(join(header))]
    lines.extend(join(parts) for parts in formatted)
    return "\n".join(lines)


def render_table(
    archive_path: Path,
    result: ParseResult,
    *,
    languages: Iterable[dict[str, object]] | None = None,
) -> list[str]:
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
    parts = [
        f"files_processed={summary.get('files_processed', len(result.files))}",
        f"bytes_processed={processed} ({format_bytes(processed)})",
        f"issues_count={summary.get('issues_count', len(result.issues))}",
    ]
    if filtered is not None:
        parts.append(f"filtered_out={filtered}")
    media_processed = summary.get("media_files_processed")
    if media_processed is not None:
        parts.append(f"media_files_processed={media_processed}")
    media_metadata_errors = summary.get("media_metadata_errors")
    if media_metadata_errors is not None:
        parts.append(f"media_metadata_errors={media_metadata_errors}")
    media_read_errors = summary.get("media_read_errors")
    if media_read_errors is not None:
        parts.append(f"media_read_errors={media_read_errors}")
    lines.append("Summary: " + ", ".join(parts))

    media_details = [meta for meta in result.files if meta.media_info]
    if media_details:
        lines.append("Media metadata:")
        for meta in media_details:
            lines.append(f"{meta.path}: {format_media_summary(meta.media_info)}")

    if languages:
        table = render_language_table(languages)
        if table:
            lines.append("Language breakdown:")
            lines.append(table)
    return lines


def format_media_summary(media_info: Mapping[str, Any] | None) -> str:
    """Provide a human-readable description of media metadata."""
    if not media_info:
        return "metadata unavailable"

    if "width" in media_info and "height" in media_info:
        extras: list[str] = []
        if media_info.get("mode"):
            extras.append(f"mode={media_info['mode']}")
        if media_info.get("format"):
            extras.append(f"format={media_info['format']}")
        if media_info.get("dpi"):
            extras.append(f"dpi={media_info['dpi']}")
        details = ", ".join(extras) if extras else ""
        suffix = f" ({details})" if details else ""
        summary = media_info.get("content_summary")
        summary_suffix = f" • {summary}" if summary else ""
        return f"image {media_info['width']}x{media_info['height']} px{suffix}{summary_suffix}"

    if "duration_seconds" in media_info:
        details: list[str] = []
        duration = media_info.get("duration_seconds")
        if duration is not None:
            details.append(f"duration={duration}s")
        if media_info.get("sample_rate"):
            details.append(f"sample_rate={media_info['sample_rate']} Hz")
        if media_info.get("channels"):
            details.append(f"channels={media_info['channels']}")
        if media_info.get("bitrate"):
            details.append(f"bitrate={media_info['bitrate']} bps")
        if media_info.get("sample_width"):
            details.append(f"sample_width={media_info['sample_width']} bytes")
        if media_info.get("tempo_bpm"):
            details.append(f"tempo={media_info['tempo_bpm']:.0f} BPM")
        if media_info.get("genre_tags"):
            genres = ", ".join(media_info["genre_tags"][:2])
            details.append(f"genres={genres}")
        if media_info.get("content_summary"):
            details.append(media_info["content_summary"])
        if media_info.get("transcript_excerpt"):
            excerpt = media_info["transcript_excerpt"]
            if len(excerpt) > 80:
                excerpt = excerpt[:77] + "..."
            details.append(f'text="{excerpt}"')
        return ", ".join(details) if details else "duration unavailable"

    # Fallback formatting for unexpected metadata shapes.
    pairs = [f"{key}={value}" for key, value in sorted(media_info.items())]
    return ", ".join(pairs) if pairs else "metadata unavailable"
