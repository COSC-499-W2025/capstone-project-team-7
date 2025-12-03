from datetime import datetime
from types import SimpleNamespace
from pathlib import Path

import pytest

from backend.src.cli import parse_zip


class FakeAnalyzer:
    def __init__(self, *_, **__) -> None:
        self.calls = []
        self.max_bytes = 30 * 1024 * 1024

    def analyze_image(self, path: Path) -> dict:
        self.calls.append(("image", path))
        return {"type": "image", "path": path.name, "summary": "img"}

    def analyze_audio(self, path: Path) -> dict:
        self.calls.append(("audio", path))
        return {"type": "audio", "path": path.name, "summary": "audio"}

    def analyze_video(self, path: Path) -> dict:
        self.calls.append(("video", path))
        return {"type": "video", "path": path.name, "summary": "video"}


def _make_meta(path: str, mime: str = ""):
    now = datetime.utcnow()
    return SimpleNamespace(path=path, mime_type=mime, media_info=None, created_at=now, modified_at=now)


def test_run_llm_media_analyzer_invokes_analyzer(monkeypatch, tmp_path: Path):
    """Verify that images/audio/video are passed through to the remote analyzer."""
    monkeypatch.setattr(parse_zip, "LLMRemoteMediaAnalyzer", lambda: FakeAnalyzer())

    img = tmp_path / "foo.jpg"
    img.write_bytes(b"img")
    audio = tmp_path / "bar.mp3"
    audio.write_bytes(b"audio")
    video = tmp_path / "baz.mp4"
    video.write_bytes(b"video")

    parse_result = SimpleNamespace(files=[
        _make_meta("foo.jpg"),
        _make_meta("bar.mp3"),
        _make_meta("baz.mp4"),
    ])

    results = parse_zip._run_llm_media_analyzer(tmp_path, parse_result, max_bytes=10 * 1024 * 1024)
    assert len(results) == 3
    paths = {entry["path"] for entry in results}
    assert {"foo.jpg", "bar.mp3", "baz.mp4"} == paths


def test_run_llm_media_analyzer_skips_large(monkeypatch, tmp_path: Path):
    """Files over the size limit should be skipped."""
    monkeypatch.setattr(parse_zip, "LLMRemoteMediaAnalyzer", lambda: FakeAnalyzer())
    big = tmp_path / "huge.mp3"
    big.write_bytes(b"x" * (2 * 1024 * 1024))
    parse_result = SimpleNamespace(files=[_make_meta("huge.mp3")])

    results = parse_zip._run_llm_media_analyzer(tmp_path, parse_result, max_bytes=1 * 1024 * 1024)
    assert results == []
