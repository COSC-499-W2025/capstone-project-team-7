from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from math import gcd
from statistics import mean
from typing import Any, Dict, Iterable, Mapping, Optional, Sequence, Tuple, Union

from ..scanner.media import AUDIO_EXTENSIONS, IMAGE_EXTENSIONS, VIDEO_EXTENSIONS
from ..scanner.models import FileMetadata


FileLike = Union[FileMetadata, Mapping[str, Any]]


@dataclass(frozen=True)
class MediaAnalyzerConfig:
    """Configuration for generating insights on media assets."""

    image_low_resolution_threshold: Tuple[int, int] = (800, 600)
    audio_short_clip_threshold: float = 15.0  # seconds
    video_short_clip_threshold: float = 30.0  # seconds


class MediaAnalyzer:
    """Compute deterministic metrics and insights for media files."""

    def __init__(self, config: Optional[MediaAnalyzerConfig] = None) -> None:
        self.config = config or MediaAnalyzerConfig()

    def analyze(self, files: Iterable[FileLike]) -> Dict[str, Any]:
        """Aggregate media metadata into metrics, summaries, and insights."""
        stats = {
            "images": _ImageStats(),
            "audio": _TimedMediaStats(),
            "video": _TimedMediaStats(),
        }
        totals = Counter()

        for meta in files:
            record = _coerce_record(meta)
            if record is None:
                continue
            media_type = record["media_type"]
            info = record["media_info"]
            if info is None:
                continue
            totals["total_media_files"] += 1
            totals[f"{media_type}_files"] += 1

            if media_type == "image":
                stats["images"].add(record["path"], info)
            elif media_type == "audio":
                stats["audio"].add(record["path"], info)
            elif media_type == "video":
                stats["video"].add(record["path"], info)

        summary = {
            "total_media_files": totals["total_media_files"],
            "image_files": totals["image_files"],
            "audio_files": totals["audio_files"],
            "video_files": totals["video_files"],
        }

        metrics = {
            "images": stats["images"].serialize(),
            "audio": stats["audio"].serialize(),
            "video": stats["video"].serialize(),
        }

        insights, issues = self._build_insights(stats, summary)

        return {
            "summary": summary,
            "metrics": metrics,
            "insights": insights,
            "issues": issues,
        }

    def _build_insights(
        self, stats: Dict[str, Union["_ImageStats", "_TimedMediaStats"]], summary: Dict[str, int]
    ) -> Tuple[Sequence[str], Sequence[str]]:
        insights: list[str] = []
        issues: list[str] = []

        image_stats: _ImageStats = stats["images"]  # type: ignore[assignment]
        if summary["image_files"]:
            if image_stats.max_resolution:
                width, height = image_stats.max_resolution["dimensions"]
                insights.append(
                    f"Largest image: {image_stats.max_resolution['path']} "
                    f"({width}x{height}, mode {image_stats.max_resolution['mode']})"
                )
            if image_stats.common_aspect_ratios:
                common_ratio, count = image_stats.common_aspect_ratios.most_common(1)[0]
                insights.append(
                    f"Most common image aspect ratio: {common_ratio} ({count} files)"
                )
            low_res = [
                entry["path"]
                for entry in image_stats.low_resolution_files(
                    self.config.image_low_resolution_threshold
                )
            ]
            if low_res:
                issues.append(
                    f"{len(low_res)} image(s) below "
                    f"{self.config.image_low_resolution_threshold[0]}x"
                    f"{self.config.image_low_resolution_threshold[1]}: {', '.join(low_res[:5])}"
                )

        audio_stats: _TimedMediaStats = stats["audio"]  # type: ignore[assignment]
        if summary["audio_files"]:
            if audio_stats.total_duration > 0:
                insights.append(
                    f"Total audio duration: {audio_stats.total_duration:.1f}s "
                    f"(avg {audio_stats.average_duration:.1f}s)"
                )
            short_audio = audio_stats.short_clips(self.config.audio_short_clip_threshold)
            if short_audio:
                issues.append(
                    f"{len(short_audio)} audio clip(s) shorter than "
                    f"{self.config.audio_short_clip_threshold}s: {', '.join(short_audio[:5])}"
                )

        video_stats: _TimedMediaStats = stats["video"]  # type: ignore[assignment]
        if summary["video_files"]:
            if video_stats.total_duration > 0:
                insights.append(
                    f"Total video duration: {video_stats.total_duration:.1f}s "
                    f"(avg {video_stats.average_duration:.1f}s)"
                )
            short_videos = video_stats.short_clips(self.config.video_short_clip_threshold)
            if short_videos:
                issues.append(
                    f"{len(short_videos)} video clip(s) shorter than "
                    f"{self.config.video_short_clip_threshold}s: {', '.join(short_videos[:5])}"
                )

        return insights, issues


def _coerce_record(meta: FileLike) -> Optional[Dict[str, Any]]:
    """Normalize file metadata from dataclass or mapping."""
    if isinstance(meta, FileMetadata):
        path = meta.path
        media_info = meta.media_info
        mime_type = meta.mime_type or ""
    elif isinstance(meta, Mapping):
        path = str(meta.get("path"))
        media_info = meta.get("media_info")
        mime_type = str(meta.get("mime_type") or "")
    else:
        return None

    if not path:
        return None

    media_type = _media_type_for(path, mime_type)
    if media_type is None:
        return None

    return {
        "path": path,
        "mime_type": mime_type,
        "media_info": media_info,
        "media_type": media_type,
    }


def _media_type_for(path: str, mime_type: str) -> Optional[str]:
    extension = path.lower().rsplit(".", 1)
    ext = f".{extension[1]}" if len(extension) == 2 else ""
    if ext in IMAGE_EXTENSIONS or mime_type.startswith("image/"):
        return "image"
    if ext in AUDIO_EXTENSIONS or mime_type.startswith("audio/"):
        return "audio"
    if ext in VIDEO_EXTENSIONS or mime_type.startswith("video/"):
        return "video"
    return None


class _ImageStats:
    def __init__(self) -> None:
        self.count = 0
        self.total_width = 0
        self.total_height = 0
        self.common_aspect_ratios: Counter[str] = Counter()
        self.max_resolution: Optional[Dict[str, Any]] = None
        self.min_resolution: Optional[Dict[str, Any]] = None
        self._records: list[Dict[str, Any]] = []

    def add(self, path: str, info: Mapping[str, Any]) -> None:
        width = int(info.get("width") or 0)
        height = int(info.get("height") or 0)
        mode = str(info.get("mode") or "")

        if width <= 0 or height <= 0:
            return

        self.count += 1
        self.total_width += width
        self.total_height += height
        ratio = _format_ratio(width, height)
        self.common_aspect_ratios[ratio] += 1

        record = {
            "path": path,
            "dimensions": (width, height),
            "mode": mode,
        }
        self._records.append(record)

        if (
            self.max_resolution is None
            or width * height > _area(self.max_resolution["dimensions"])
        ):
            self.max_resolution = record
        if (
            self.min_resolution is None
            or width * height < _area(self.min_resolution["dimensions"])
        ):
            self.min_resolution = record

    def average_dimensions(self) -> Tuple[float, float]:
        if self.count == 0:
            return (0.0, 0.0)
        return (self.total_width / self.count, self.total_height / self.count)

    def low_resolution_files(self, threshold: Tuple[int, int]) -> Sequence[Dict[str, Any]]:
        width_threshold, height_threshold = threshold
        return [
            record
            for record in self._records
            if record["dimensions"][0] < width_threshold
            or record["dimensions"][1] < height_threshold
        ]

    def serialize(self) -> Dict[str, Any]:
        avg_width, avg_height = self.average_dimensions()
        return {
            "count": self.count,
            "average_width": round(avg_width, 2),
            "average_height": round(avg_height, 2),
            "max_resolution": self.max_resolution,
            "min_resolution": self.min_resolution,
            "common_aspect_ratios": dict(self.common_aspect_ratios.most_common(5)),
        }


class _TimedMediaStats:
    def __init__(self) -> None:
        self.count = 0
        self.total_duration = 0.0
        self.durations: list[float] = []
        self.bitrates: list[int] = []
        self.sample_rates: list[int] = []
        self.channels: Counter[int] = Counter()
        self.longest: Optional[Dict[str, Any]] = None
        self.shortest: Optional[Dict[str, Any]] = None
        self.paths: list[str] = []

    def add(self, path: str, info: Mapping[str, Any]) -> None:
        duration = float(info.get("duration_seconds") or 0.0)
        if duration <= 0:
            return
        bitrate = info.get("bitrate")
        sample_rate = info.get("sample_rate")
        channels = info.get("channels")

        self.count += 1
        self.total_duration += duration
        self.durations.append(duration)
        self.paths.append(path)

        if isinstance(bitrate, (int, float)):
            self.bitrates.append(int(bitrate))
        if isinstance(sample_rate, (int, float)):
            self.sample_rates.append(int(sample_rate))
        if isinstance(channels, (int, float)):
            self.channels[int(channels)] += 1

        record = {"path": path, "duration_seconds": duration}
        if self.longest is None or duration > self.longest["duration_seconds"]:
            self.longest = record
        if self.shortest is None or duration < self.shortest["duration_seconds"]:
            self.shortest = record

    @property
    def average_duration(self) -> float:
        if not self.durations:
            return 0.0
        return sum(self.durations) / len(self.durations)

    def short_clips(self, threshold: float) -> Sequence[str]:
        return [path for path, duration in zip(self.paths, self.durations) if duration < threshold]

    def serialize(self) -> Dict[str, Any]:
        return {
            "count": self.count,
            "total_duration_seconds": round(self.total_duration, 2),
            "average_duration_seconds": round(self.average_duration, 2),
            "longest_clip": self.longest,
            "shortest_clip": self.shortest,
            "bitrate_stats": _coerce_stats(self.bitrates),
            "sample_rate_stats": _coerce_stats(self.sample_rates),
            "channel_distribution": dict(self.channels),
        }


def _format_ratio(width: int, height: int) -> str:
    divisor = gcd(width, height) or 1
    return f"{width // divisor}:{height // divisor}"


def _area(dimensions: Tuple[int, int]) -> int:
    return dimensions[0] * dimensions[1]


def _coerce_stats(values: Sequence[int]) -> Optional[Dict[str, Any]]:
    if not values:
        return None
    return {
        "min": int(min(values)),
        "max": int(max(values)),
        "average": round(mean(values), 2),
    }
