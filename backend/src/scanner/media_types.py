from __future__ import annotations

from typing import Tuple, TypedDict, Union


class ImageMetadata(TypedDict, total=False):
    width: int
    height: int
    mode: str
    format: str
    dpi: Tuple[float, float]


class AudioMetadata(TypedDict, total=False):
    duration_seconds: float
    bitrate: int
    sample_rate: int
    channels: int
    sample_width: int


class VideoMetadata(TypedDict, total=False):
    duration_seconds: float
    bitrate: int


MediaMetadata = Union[ImageMetadata, AudioMetadata, VideoMetadata]
