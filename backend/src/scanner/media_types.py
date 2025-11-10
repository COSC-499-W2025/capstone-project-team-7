from __future__ import annotations

from typing import List, Tuple, TypedDict, Union


class ContentLabel(TypedDict):
    label: str
    confidence: float


class ImageMetadata(TypedDict, total=False):
    width: int
    height: int
    mode: str
    format: str
    dpi: Tuple[float, float]
    content_labels: List[ContentLabel]
    content_summary: str


class AudioMetadata(TypedDict, total=False):
    duration_seconds: float
    bitrate: int
    sample_rate: int
    channels: int
    sample_width: int
    content_labels: List[ContentLabel]
    content_summary: str
    tempo_bpm: float
    genre_tags: List[str]
    transcript_excerpt: str


class VideoMetadata(TypedDict, total=False):
    duration_seconds: float
    bitrate: int
    content_labels: List[ContentLabel]
    content_summary: str


MediaMetadata = Union[ImageMetadata, AudioMetadata, VideoMetadata]
