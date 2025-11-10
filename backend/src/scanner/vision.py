from __future__ import annotations

import io
import logging
import re
import tempfile
from collections import Counter
from pathlib import Path
from typing import List, Sequence

from .media_types import ContentLabel

logger = logging.getLogger(__name__)

try:  # Pillow is mandatory for image decoding
    from PIL import Image
except ImportError:  # pragma: no cover - optional dependency
    Image = None  # type: ignore[assignment]

try:  # Heavy optional dependencies for local inference
    import torch
    from torchvision import transforms
    from torchvision.io import read_video
    from torchvision.models import resnet50, ResNet50_Weights
except Exception:  # pragma: no cover - torch/torchvision missing
    torch = None  # type: ignore[assignment]
    transforms = None  # type: ignore[assignment]
    read_video = None  # type: ignore[assignment]
    resnet50 = None  # type: ignore[assignment]
    ResNet50_Weights = None  # type: ignore[assignment]

try:  # Optional speech model for audio insights.
    import torchaudio
    from torchaudio.pipelines import WAV2VEC2_ASR_BASE_960H
except Exception:  # pragma: no cover - torchaudio missing
    torchaudio = None  # type: ignore[assignment]
    WAV2VEC2_ASR_BASE_960H = None  # type: ignore[assignment]

try:  # Optional DSP helpers for tempo/genre heuristics.
    import librosa
except Exception:  # pragma: no cover - librosa missing
    librosa = None  # type: ignore[assignment]


DEFAULT_TOP_K = 3
MAX_VIDEO_FRAME_SAMPLES = 8

_WORD_PATTERN = re.compile(r"[a-zA-Z']+")
_STOP_WORDS = {
    "the",
    "a",
    "an",
    "and",
    "or",
    "but",
    "with",
    "without",
    "to",
    "in",
    "on",
    "at",
    "for",
    "of",
    "it",
    "is",
    "are",
    "be",
    "was",
    "were",
    "as",
    "that",
    "this",
    "these",
    "those",
}


def image_content_labels(data: bytes, *, top_k: int = DEFAULT_TOP_K) -> List[ContentLabel]:
    """Return the top-k ImageNet labels detected in the supplied image bytes."""
    if Image is None:
        return []
    try:
        with Image.open(io.BytesIO(data)) as image:
            image.load()
            rgb_image = image.convert("RGB")
    except Exception as exc:  # pragma: no cover - depends on Pillow internals
        logger.debug("Image decode failed for content insights: %s", exc)
        return []
    return _classify_image(rgb_image, top_k=top_k)


def video_content_labels(
    data: bytes,
    suffix: str,
    *,
    top_k: int = DEFAULT_TOP_K,
    frame_samples: int = MAX_VIDEO_FRAME_SAMPLES,
) -> List[ContentLabel]:
    """Detect recurring concepts in a video by sampling frames and classifying them."""
    engine = _get_engine()
    if engine is None or read_video is None or torch is None or Image is None:
        return []

    suffix = suffix or ".mp4"
    temp_file_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(data)
            temp_file_path = Path(tmp.name)
        frames, _, _ = read_video(str(temp_file_path), pts_unit="sec")
    except Exception as exc:  # pragma: no cover - depends on platform codecs
        logger.debug("Video decode failed for content insights: %s", exc)
        return []
    finally:
        if temp_file_path and temp_file_path.exists():
            temp_file_path.unlink(missing_ok=True)

    if frames.numel() == 0:
        return []

    num_frames = frames.shape[0]
    samples = min(frame_samples, num_frames)
    if samples <= 0:
        return []

    # Evenly distributed frame indices to get a quick overview of the clip.
    indices = _linspace_indices(num_frames, samples)
    aggregated: dict[str, float] = {}

    for idx in indices:
        frame = frames[int(idx)]
        try:
            image = Image.fromarray(frame.to("cpu").byte().numpy())
        except Exception:  # pragma: no cover - numpy/PIL edge cases
            continue
        labels = engine.classify(image, top_k=top_k)
        if not labels:
            continue
        for entry in labels:
            aggregated[entry["label"]] = aggregated.get(entry["label"], 0.0) + entry["confidence"]

    if not aggregated:
        return []

    normalized = sorted(aggregated.items(), key=lambda item: item[1], reverse=True)[:top_k]
    scale = max(len(indices), 1)
    return [
        {"label": label, "confidence": min(score / scale, 1.0)}
        for label, score in normalized
    ]


def audio_content_insights(
    data: bytes,
    suffix: str,
    *,
    top_k: int = DEFAULT_TOP_K,
) -> dict[str, object]:
    """Transcribe audio locally and surface tempo/genre heuristics."""
    engine = _get_audio_engine()
    if engine is None:
        return {}
    insights = engine.analyze(data, suffix=suffix or ".wav", top_k=top_k)
    labels: List[ContentLabel] = insights.get("labels", [])  # type: ignore[assignment]
    if labels:
        insights["summary"] = summarize_labels(labels, prefix="Likely mentions")
    return insights


def summarize_labels(labels: Sequence[ContentLabel], *, prefix: str = "Likely contains") -> str:
    """Convert label/confidence pairs into a short human-readable sentence."""
    if not labels:
        return ""
    fragments = [f"{entry['label']} ({entry['confidence']:.0%})" for entry in labels]
    return f"{prefix} {', '.join(fragments)}"


def _classify_image(image: "Image.Image", *, top_k: int) -> List[ContentLabel]:
    engine = _get_engine()
    if engine is None:
        return []
    return engine.classify(image, top_k=top_k)


def _linspace_indices(size: int, samples: int) -> List[int]:
    if samples <= 1:
        return [0]
    step = (size - 1) / float(samples - 1)
    return [min(int(round(i * step)), size - 1) for i in range(samples)]


def _get_engine() -> "_TorchVisionEngine | None":
    # Lazy import keeps heavy torch weights out of memory when unavailable.
    if getattr(_get_engine, "_initialized", False):
        return getattr(_get_engine, "_cached", None)
    if torch is None or resnet50 is None:
        logger.debug("PyTorch/Torchvision not available; content insights disabled.")
        _get_engine._cached = None  # type: ignore[attr-defined]
        _get_engine._initialized = True  # type: ignore[attr-defined]
        return None
    try:
        engine = _TorchVisionEngine()
    except Exception as exc:  # pragma: no cover - depends on torch build
        logger.warning("Failed to initialize Torch vision engine: %s", exc)
        engine = None
    _get_engine._cached = engine  # type: ignore[attr-defined]
    _get_engine._initialized = True  # type: ignore[attr-defined]
    return engine


def _get_audio_engine() -> "_AudioInsightEngine | None":
    if getattr(_get_audio_engine, "_initialized", False):
        return getattr(_get_audio_engine, "_cached", None)
    if torch is None or torchaudio is None or WAV2VEC2_ASR_BASE_960H is None:
        logger.debug("Torchaudio not available; audio insights disabled.")
        _get_audio_engine._cached = None  # type: ignore[attr-defined]
        _get_audio_engine._initialized = True  # type: ignore[attr-defined]
        return None
    try:
        engine = _AudioInsightEngine()
    except Exception as exc:  # pragma: no cover - torchaudio specific
        logger.warning("Failed to initialize audio ASR engine: %s", exc)
        engine = None
    _get_audio_engine._cached = engine  # type: ignore[attr-defined]
    _get_audio_engine._initialized = True  # type: ignore[attr-defined]
    return engine


class _TorchVisionEngine:
    """Thin wrapper around a pretrained ResNet classifier for reuse."""

    def __init__(self) -> None:
        if torch is None or resnet50 is None:
            raise RuntimeError("Torch/Torchvision unavailable")

        if ResNet50_Weights is not None:
            weights = ResNet50_Weights.DEFAULT  # type: ignore[attr-defined]
            self.model = resnet50(weights=weights)
            self.preprocess = weights.transforms()
            self.labels: Sequence[str] = weights.meta.get("categories", [])
        else:  # pragma: no cover - fallback for very old torchvision
            self.model = resnet50(pretrained=True)
            if transforms is None:
                raise RuntimeError("Torchvision transforms unavailable")
            self.preprocess = transforms.Compose(
                [
                    transforms.Resize(256),
                    transforms.CenterCrop(224),
                    transforms.ToTensor(),
                    transforms.Normalize(
                        mean=[0.485, 0.456, 0.406],
                        std=[0.229, 0.224, 0.225],
                    ),
                ]
            )
            self.labels = tuple()

        self.model.eval()

    def classify(self, image: "Image.Image", *, top_k: int) -> List[ContentLabel]:
        if torch is None:
            return []
        tensor = self.preprocess(image).unsqueeze(0)
        inference_ctx = getattr(torch, "inference_mode", torch.no_grad)
        with inference_ctx():  # type: ignore[misc]
            logits = self.model(tensor)
            probabilities = torch.softmax(logits, dim=1)
            limit = max(1, min(int(top_k), probabilities.shape[1]))
            scores, indices = torch.topk(probabilities, limit, dim=1)

        labels: List[ContentLabel] = []
        for score, index in zip(scores[0], indices[0]):
            idx = int(index.cpu().item())
            label = self.labels[idx] if idx < len(self.labels) else f"class_{idx}"
            labels.append({"label": label, "confidence": float(score.cpu().item())})
        return labels


class _AudioInsightEngine:
    """Audio transcription plus lightweight tempo/genre inference."""

    def __init__(self) -> None:
        if torch is None or torchaudio is None or WAV2VEC2_ASR_BASE_960H is None:
            raise RuntimeError("Torchaudio wav2vec bundle unavailable")
        self.bundle = WAV2VEC2_ASR_BASE_960H
        self.model = self.bundle.get_model()
        self.labels = self.bundle.get_labels()
        self.sample_rate = int(self.bundle.sample_rate)
        self.blank_symbol = self.labels[0] if self.labels else "-"
        self.model.eval()

    def analyze(self, data: bytes, *, suffix: str, top_k: int) -> dict[str, object]:
        waveform, sample_rate = self._load_waveform(data, suffix)
        if waveform is None:
            return []
        if waveform.dim() == 1:
            waveform = waveform.unsqueeze(0)
        if waveform.size(0) > 1:
            waveform = waveform.mean(dim=0, keepdim=True)
        if sample_rate != self.sample_rate:
            waveform = torchaudio.functional.resample(waveform, sample_rate, self.sample_rate)
        inference_ctx = getattr(torch, "inference_mode", torch.no_grad)
        with inference_ctx():  # type: ignore[misc]
            emissions, _ = self.model(waveform)
        transcript = self._greedy_decode(emissions[0])
        labels = self._labels_from_transcript(transcript, top_k)
        tempo_bpm, centroid = self._tempo_and_centroid(waveform)
        genre_tags = self._infer_genre_tags(tempo_bpm, centroid)
        return {
            "labels": labels,
            "tempo_bpm": tempo_bpm,
            "genre_tags": genre_tags,
            "transcript": transcript,
        }

    def _load_waveform(self, data: bytes, suffix: str) -> tuple["torch.Tensor", int] | tuple[None, None]:
        if torchaudio is None:
            return (None, None)
        suffix = suffix or ".wav"
        temp_file: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
                tmp.write(data)
                temp_file = Path(tmp.name)
            waveform, sample_rate = torchaudio.load(str(temp_file))
            return waveform, int(sample_rate)
        except Exception as exc:  # pragma: no cover - backend codec errors
            logger.debug("Audio decode failed for content insights: %s", exc)
            return (None, None)
        finally:
            if temp_file and temp_file.exists():
                temp_file.unlink(missing_ok=True)

    def _greedy_decode(self, emission: "torch.Tensor") -> str:
        indices = torch.argmax(emission, dim=-1).tolist()
        transcript: list[str] = []
        prev_symbol: str | None = None
        for idx in indices:
            if idx >= len(self.labels):
                continue
            symbol = self.labels[idx]
            if symbol == self.blank_symbol:
                prev_symbol = symbol
                continue
            if symbol == prev_symbol:
                continue
            if symbol == "|":
                if transcript and transcript[-1] != " ":
                    transcript.append(" ")
            else:
                transcript.append(symbol.lower())
            prev_symbol = symbol
        return "".join(transcript).strip()

    def _labels_from_transcript(self, transcript: str, top_k: int) -> List[ContentLabel]:
        if not transcript:
            return []
        tokens = [
            word
            for word in _WORD_PATTERN.findall(transcript)
            if word and word not in _STOP_WORDS
        ]
        if not tokens:
            return []
        counts = Counter(tokens)
        total = sum(counts.values()) or 1
        top = counts.most_common(max(1, top_k))
        return [
            {"label": word, "confidence": min(count / total, 1.0)}
            for word, count in top
        ]

    def _tempo_and_centroid(self, waveform: "torch.Tensor") -> tuple[float | None, float | None]:
        if librosa is None:
            return (None, None)
        try:
            samples = waveform.squeeze(0).cpu().numpy()
        except Exception:
            return (None, None)
        if samples.size == 0:
            return (None, None)
        try:
            tempo, _ = librosa.beat.beat_track(y=samples, sr=self.sample_rate)
            centroid = librosa.feature.spectral_centroid(y=samples, sr=self.sample_rate)
            centroid_mean = float(centroid.mean()) if centroid.size else None
            tempo_value = float(tempo) if tempo else None
            return (tempo_value, centroid_mean)
        except Exception as exc:  # pragma: no cover - librosa backend
            logger.debug("Tempo/centroid extraction failed: %s", exc)
            return (None, None)

    def _infer_genre_tags(
        self, tempo_bpm: float | None, centroid: float | None, limit: int = 3
    ) -> List[str]:
        tags: list[str] = []
        if tempo_bpm:
            if tempo_bpm >= 140:
                tags.append("electronic/dance")
            elif tempo_bpm >= 115:
                tags.append("pop")
            elif tempo_bpm >= 90:
                tags.append("hip hop/R&B")
            elif tempo_bpm >= 60:
                tags.append("downtempo/ballad")
            else:
                tags.append("ambient/slow")
        if centroid:
            if centroid >= 4000:
                tags.append("rock/bright")
            elif centroid <= 1500:
                tags.append("lofi/mellow")
        seen: set[str] = set()
        ordered: list[str] = []
        for tag in tags:
            if tag not in seen:
                ordered.append(tag)
                seen.add(tag)
            if len(ordered) >= limit:
                break
        return ordered
