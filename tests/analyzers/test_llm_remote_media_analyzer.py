from pathlib import Path
from types import SimpleNamespace

import pytest

from backend.src.analyzer.llm_remote_media_analyzer import LLMRemoteMediaAnalyzer


class MockChoice:
    def __init__(self, content: str) -> None:
        self.message = SimpleNamespace(content=content)


class MockResponse:
    def __init__(self, content: str) -> None:
        self.choices = [MockChoice(content)]


class MockClient:
    def __init__(self, payload: str) -> None:
        self.payload = payload
        self.chat = SimpleNamespace(completions=self)

    def create(self, **kwargs):
        return MockResponse(self.payload)


@pytest.fixture
def tmp_media(tmp_path: Path) -> Path:
    path = tmp_path / "sample.bin"
    path.write_bytes(b"1234")
    return path


def test_analyze_image_success(tmp_media: Path):
    payload = '{"summary":"an image","objects":["a"],"confidence":0.9}'
    analyzer = LLMRemoteMediaAnalyzer(client=MockClient(payload))
    result = analyzer.analyze_image(tmp_media)
    assert result["type"] == "image"
    assert result["summary"] == "an image"


def test_analyze_audio_success(tmp_media: Path):
    payload = '{"summary":"audio","transcript":"hello","confidence":0.8}'
    analyzer = LLMRemoteMediaAnalyzer(client=MockClient(payload))
    result = analyzer.analyze_audio(tmp_media)
    assert result["type"] == "audio"
    assert "transcript" in result


def test_analyze_video_success(tmp_media: Path):
    payload = '{"summary":"video","actions":["walk"],"confidence":0.7}'
    analyzer = LLMRemoteMediaAnalyzer(client=MockClient(payload))
    result = analyzer.analyze_video(tmp_media)
    assert result["type"] == "video"
    assert result["summary"] == "video"


def test_size_limit(tmp_media: Path, monkeypatch):
    monkeypatch.setattr(Path, "stat", lambda self: SimpleNamespace(st_size=35 * 1024 * 1024, st_mode=0o100644))
    monkeypatch.setattr(Path, "is_file", lambda self: True)
    analyzer = LLMRemoteMediaAnalyzer(client=MockClient("{}"))
    result = analyzer.analyze_audio(tmp_media)
    assert "error" in result
