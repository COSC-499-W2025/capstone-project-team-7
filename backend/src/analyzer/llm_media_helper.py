from __future__ import annotations

from pathlib import Path
from typing import Any

from .llm_remote_media_analyzer import LLMRemoteMediaAnalyzer
from ..scanner.media import AUDIO_EXTENSIONS, IMAGE_EXTENSIONS, VIDEO_EXTENSIONS


def run_llm_media_analyzer(
    base_path: Path,
    parse_result: Any,
    max_bytes: int = 20 * 1024 * 1024,
) -> list[dict]:
    """Run the remote LLM media analyzer over supported media files."""
    analyzer = LLMRemoteMediaAnalyzer()
    results: list[dict] = []
    media_exts = set(IMAGE_EXTENSIONS + AUDIO_EXTENSIONS + VIDEO_EXTENSIONS)
    for meta in getattr(parse_result, "files", []):
        path_value = getattr(meta, "path", None)
        if not path_value:
            continue
        suffix = Path(path_value).suffix.lower()
        if suffix not in media_exts:
            continue
        full_path = base_path / path_value
        try:
            if not full_path.exists() or full_path.stat().st_size > max_bytes:
                continue
        except OSError:
            continue
        if suffix in IMAGE_EXTENSIONS:
            result = analyzer.analyze_image(full_path)
        elif suffix in AUDIO_EXTENSIONS:
            result = analyzer.analyze_audio(full_path)
        else:
            result = analyzer.analyze_video(full_path)
        result["path"] = path_value
        results.append(result)
    return results
