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


def test_media_analyzer_reports_content_labels():
    analyzer = MediaAnalyzer()
    files = [
        _file_meta(
            "assets/cat.png",
            "image/png",
            {
                "width": 1024,
                "height": 768,
                "mode": "RGB",
                "content_labels": [
                    {"label": "tabby cat", "confidence": 0.9},
                    {"label": "sofa", "confidence": 0.2},
                ],
            },
        ),
        _file_meta(
            "audio/interview.wav",
            "audio/x-wav",
            {
                "duration_seconds": 12.0,
                "content_labels": [
                    {"label": "team", "confidence": 0.7},
                    {"label": "project", "confidence": 0.4},
                ],
                "tempo_bpm": 128.0,
                "genre_tags": ["electronic/dance", "pop"],
            },
        ),
        _file_meta(
            "video/park.mp4",
            "video/mp4",
            {
                "duration_seconds": 42.0,
                "content_labels": [
                    {"label": "park", "confidence": 0.6},
                    {"label": "dog", "confidence": 0.5},
                ],
            },
        ),
    ]

    result = analyzer.analyze(files)

    image_labels = result["metrics"]["images"]["top_labels"]
    audio_labels = result["metrics"]["audio"]["top_labels"]
    video_labels = result["metrics"]["video"]["top_labels"]
    audio_tempo = result["metrics"]["audio"]["tempo_stats"]
    assert image_labels and image_labels[0]["label"] == "tabby cat"
    assert audio_labels and audio_labels[0]["label"] == "team"
    assert video_labels and video_labels[0]["label"] == "park"
    assert audio_tempo and audio_tempo["average"] == pytest.approx(128.0, rel=1e-3)
    assert any("Image content highlights" in insight for insight in result["insights"])
    assert any("Audio content highlights" in insight for insight in result["insights"])
    assert any("Audio genre highlights" in insight for insight in result["insights"])
    assert any("Video content highlights" in insight for insight in result["insights"])
