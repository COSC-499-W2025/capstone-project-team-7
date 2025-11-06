from __future__ import annotations

import contextlib
import io
import wave
import logging
from dataclasses import dataclass
from typing import Optional, Tuple

from .media_types import AudioMetadata, ImageMetadata, MediaMetadata, VideoMetadata

# Optional imports – downstream code handles None gracefully when dependencies are missing.
try:
    from PIL import Image  # type: ignore
except ImportError:  # pragma: no cover - exercised in dependency missing environments
    Image = None  # type: ignore

try:
    from mutagen import File as MutagenFile  # type: ignore
except ImportError:  # pragma: no cover - exercised in dependency missing environments
    MutagenFile = None  # type: ignore


@dataclass(frozen=True)
class MediaExtractionResult:
    """Container for extracted media metadata and optional warning message.

    The `metadata` payload conforms to the typed dictionaries defined in
    `scanner.media_types` to describe images, audio, or video files.
    """

    metadata: Optional[MediaMetadata]
    error: Optional[str] = None


# Primary extensions / MIME associations we recognize.
IMAGE_EXTENSIONS: Tuple[str, ...] = (".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tiff", ".webp")
AUDIO_EXTENSIONS: Tuple[str, ...] = (".mp3", ".wav", ".flac", ".aac", ".m4a", ".ogg")
VIDEO_EXTENSIONS: Tuple[str, ...] = (".mp4", ".m4v", ".mov", ".avi", ".mkv", ".webm")

logger = logging.getLogger(__name__)


def is_media_candidate(path: str) -> bool:
    """Return True when the file extension suggests we can extract media metadata."""
    extension = _normalized_extension(path)
    return extension in IMAGE_EXTENSIONS + AUDIO_EXTENSIONS + VIDEO_EXTENSIONS


def extract_media_metadata(path: str, mime_type: Optional[str], data: bytes) -> MediaExtractionResult:
    """
    Attempt to extract metadata for supported media formats.

    Returns a MediaExtractionResult containing a dictionary of metadata or an error message if
    extraction failed. Both `data` and `error` can be None when extraction is not supported.
    """
    extension = _normalized_extension(path)

    if extension in IMAGE_EXTENSIONS:
        return _extract_image_metadata(data)
    if extension in AUDIO_EXTENSIONS:
        return _extract_audio_metadata(path, extension, data, mime_type)
    if extension in VIDEO_EXTENSIONS:
        return _extract_video_metadata(path, extension, data, mime_type)
    return MediaExtractionResult(metadata=None)


def _normalized_extension(path: str) -> str:
    parts = path.lower().rsplit(".", 1)
    return f".{parts[1]}" if len(parts) == 2 else ""


def _extract_image_metadata(data: bytes) -> MediaExtractionResult:
    if Image is None:
        return MediaExtractionResult(metadata=None, error="Pillow not installed")

    try:
        with Image.open(io.BytesIO(data)) as image:
            image.load()  # Force actual decoding to populate size, etc.
            width = int(image.width)
            height = int(image.height)
            if width <= 0 or height <= 0:
                return MediaExtractionResult(
                    metadata=None,
                    error=f"Invalid image dimensions width={width}, height={height}",
                )
            metadata: ImageMetadata = {
                "width": width,
                "height": height,
                "mode": image.mode,
                "format": image.format,
            }
            if "dpi" in image.info:
                metadata["dpi"] = image.info["dpi"]
            logger.debug(
                "Extracted image metadata: width=%s height=%s mode=%s format=%s",
                metadata["width"],
                metadata["height"],
                metadata.get("mode"),
                metadata.get("format"),
            )
            return MediaExtractionResult(metadata=metadata)
    except Exception as exc:  # pragma: no cover - PIL specific failures
        return MediaExtractionResult(metadata=None, error=f"Failed to extract image metadata: {exc}")


def _extract_audio_metadata(
    path: str, extension: str, data: bytes, mime_type: Optional[str]
) -> MediaExtractionResult:
    if extension == ".wav" or mime_type in {"audio/wav", "audio/x-wav", "audio/wave"}:
        return _extract_wav_metadata(data)

    if MutagenFile is None:
        return MediaExtractionResult(metadata=None, error="mutagen not installed")

    try:
        buffer = io.BytesIO(data)
        buffer.name = path  # type: ignore[attr-defined]
        audio = MutagenFile(buffer)
    except Exception as exc:  # pragma: no cover - Mutagen specific errors
        return MediaExtractionResult(metadata=None, error=f"Failed to parse audio file: {exc}")

    if audio is None or not getattr(audio, "info", None):
        return MediaExtractionResult(metadata=None, error="Unrecognized audio format")

    info = audio.info
    metadata: AudioMetadata = {}

    duration = getattr(info, "length", None)
    if duration is not None:
        metadata["duration_seconds"] = round(float(duration), 3)

    bitrate = getattr(info, "bitrate", None)
    if bitrate:
        metadata["bitrate"] = int(bitrate)

    sample_rate = getattr(info, "sample_rate", None)
    if sample_rate:
        metadata["sample_rate"] = int(sample_rate)

    channels = getattr(info, "channels", None)
    if channels:
        metadata["channels"] = int(channels)

    if metadata:
        logger.debug(
            "Extracted audio metadata: duration=%s bitrate=%s sample_rate=%s channels=%s",
            metadata.get("duration_seconds"),
            metadata.get("bitrate"),
            metadata.get("sample_rate"),
            metadata.get("channels"),
        )
    return MediaExtractionResult(metadata=metadata if metadata else None)


def _extract_wav_metadata(data: bytes) -> MediaExtractionResult:
    try:
        with contextlib.closing(wave.open(io.BytesIO(data))) as wav_file:
            frame_count = wav_file.getnframes()
            framerate = wav_file.getframerate()
            channels = wav_file.getnchannels()
            sample_width = wav_file.getsampwidth()
            duration = frame_count / framerate if framerate else 0
            metadata: AudioMetadata = {
                "duration_seconds": round(duration, 3),
                "channels": channels,
                "sample_rate": framerate,
                "sample_width": sample_width,
            }
            logger.debug(
                "Extracted WAV metadata: duration=%s sample_rate=%s channels=%s",
                metadata["duration_seconds"],
                metadata["sample_rate"],
                metadata["channels"],
            )
            return MediaExtractionResult(metadata=metadata)
    except wave.Error as exc:
        return MediaExtractionResult(metadata=None, error=f"WAV parse error: {exc}")


def _extract_video_metadata(
    path: str, extension: str, data: bytes, mime_type: Optional[str]
) -> MediaExtractionResult:
    if MutagenFile is None:
        return MediaExtractionResult(metadata=None, error="mutagen not installed")

    try:
        buffer = io.BytesIO(data)
        buffer.name = path  # type: ignore[attr-defined]
        media = MutagenFile(buffer)
    except Exception as exc:  # pragma: no cover - Mutagen specific errors
        return MediaExtractionResult(metadata=None, error=f"Failed to parse video file: {exc}")

    if media is None or not getattr(media, "info", None):
        return MediaExtractionResult(metadata=None, error="Unrecognized video format")

    info = media.info
    metadata: VideoMetadata = {}

    duration = getattr(info, "length", None)
    if duration is not None:
        metadata["duration_seconds"] = round(float(duration), 3)

    bitrate = getattr(info, "bitrate", None)
    if bitrate:
        metadata["bitrate"] = int(bitrate)

    if metadata:
        logger.debug(
            "Extracted video metadata: duration=%s bitrate=%s",
            metadata.get("duration_seconds"),
            metadata.get("bitrate"),
        )
    return MediaExtractionResult(metadata=metadata if metadata else None)
