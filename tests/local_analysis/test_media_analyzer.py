from __future__ import annotations

from datetime import datetime, timezone

import pytest

from src.local_analysis.media_analyzer import MediaAnalyzer, MediaAnalyzerConfig
from src.scanner.models import FileMetadata


def _file_meta(path: str, mime: str, media_info: dict) -> FileMetadata:
    now = datetime.now(timezone.utc)
    return FileMetadata(
        path=path,
        size_bytes=123,
        mime_type=mime,
        created_at=now,
        modified_at=now,
        media_info=media_info,
    )


def test_media_analyzer_summarizes_all_types():
    analyzer = MediaAnalyzer()
    files = [
        _file_meta(
            "assets/banner.png",
            "image/png",
            {"width": 1200, "height": 900, "mode": "RGB"},
        ),
        _file_meta(
            "assets/logo.png",
            "image/png",
            {"width": 400, "height": 200, "mode": "RGBA"},
        ),
        _file_meta(
            "audio/theme.wav",
            "audio/x-wav",
            {"duration_seconds": 42.5, "channels": 2, "sample_rate": 44100, "bitrate": 192000},
        ),
        _file_meta(
            "video/demo.mp4",
            "video/mp4",
            {"duration_seconds": 120.0, "bitrate": 3500000},
        ),
    ]

    result = analyzer.analyze(files)

    assert result["summary"]["total_media_files"] == 4
    assert result["summary"]["image_files"] == 2
    assert result["metrics"]["images"]["count"] == 2
    assert result["metrics"]["audio"]["count"] == 1
    assert result["metrics"]["video"]["count"] == 1
    assert result["metrics"]["images"]["max_resolution"]["path"] == "assets/banner.png"
    assert result["metrics"]["audio"]["total_duration_seconds"] == pytest.approx(42.5, rel=1e-3)
    assert result["metrics"]["video"]["total_duration_seconds"] == pytest.approx(120.0, rel=1e-3)
    assert any("Largest image" in insight for insight in result["insights"])


def test_media_analyzer_flags_low_resolution_and_short_clips():
    config = MediaAnalyzerConfig(
        image_low_resolution_threshold=(800, 600),
        audio_short_clip_threshold=30.0,
        video_short_clip_threshold=60.0,
    )
    analyzer = MediaAnalyzer(config)
    files = [
        _file_meta(
            "assets/small.png",
            "image/png",
            {"width": 640, "height": 360, "mode": "RGB"},
        ),
        _file_meta(
            "audio/intro.wav",
            "audio/x-wav",
            {"duration_seconds": 12.0},
        ),
        _file_meta(
            "video/preview.mp4",
            "video/mp4",
            {"duration_seconds": 25.0},
        ),
    ]

    result = analyzer.analyze(files)

    assert result["summary"]["total_media_files"] == 3
    assert len(result["issues"]) >= 2
    assert any("image(s) below" in issue for issue in result["issues"])
    assert any("audio clip(s) shorter" in issue for issue in result["issues"])
    assert any("video clip(s) shorter" in issue for issue in result["issues"])
