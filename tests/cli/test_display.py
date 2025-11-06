from __future__ import annotations

from backend.src.cli.display import format_media_summary


def test_format_media_summary_image():
    summary = format_media_summary(
        {"width": 120, "height": 90, "mode": "RGB", "format": "PNG"}
    )
    assert summary.startswith("image 120x90 px")
    assert "mode=RGB" in summary
    assert "format=PNG" in summary


def test_format_media_summary_audio():
    summary = format_media_summary(
        {"duration_seconds": 1.5, "sample_rate": 44100, "channels": 2}
    )
    assert "duration=1.5s" in summary
    assert "sample_rate=44100 Hz" in summary
    assert "channels=2" in summary


def test_format_media_summary_fallback():
    summary = format_media_summary({"foo": "bar"})
    assert summary == "foo=bar"
