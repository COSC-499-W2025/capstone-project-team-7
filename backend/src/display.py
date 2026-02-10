from __future__ import annotations

from typing import Any, Mapping


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
        summary_suffix = f" - {summary}" if summary else ""
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
        return ", ".join(details) if details else "duration unavailable"

    pairs = [f"{key}={value}" for key, value in sorted(media_info.items())]
    return ", ".join(pairs) if pairs else "metadata unavailable"
