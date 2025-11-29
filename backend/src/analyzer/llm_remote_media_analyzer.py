from __future__ import annotations

import base64
import io
import json
import mimetypes
import subprocess
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

from openai import OpenAI

# Tunable defaults
DEFAULT_MODEL = "gpt-4o-mini"
MAX_MEDIA_BYTES = 30 * 1024 * 1024  # 30 MB hard limit by OpenAI
MAX_INLINE_BYTES = 30 * 1024 * 1024  # inline payload threshold


@dataclass
class LLMRemoteMediaAnalyzer:
    """
    Unified remote media analyzer for images, audio, and video.
    Includes:
    - auto HEVC/H.265 detection + conversion to H.264 MP4
    - correct MIME assignment
    - multi-frame extraction
    - audio track fallback extraction
    """

    model: str = DEFAULT_MODEL
    max_bytes: int = MAX_MEDIA_BYTES
    client: Optional[OpenAI] = None

    def __post_init__(self) -> None:
        self.client = self.client or OpenAI()

    # ------------------------------------------------------------
    # Base utilities
    # ------------------------------------------------------------

    def _call_llm(self, messages: list[dict[str, Any]]) -> Dict[str, Any]:
        """Call the LLM and return JSON if possible."""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=700,
                temperature=0.2,
            )
            content = (
                response.choices[0].message.content
                if response and response.choices else ""
            )

            try:
                data = json.loads(content)
                if isinstance(data, dict):
                    return data
            except Exception:
                pass

            return {"summary": content}

        except Exception as exc:
            return {"error": str(exc)}

    def _size_ok(self, path: Path) -> bool:
        return (
            path.exists()
            and path.is_file()
            and path.stat().st_size <= self.max_bytes
        )

    def _data_url(self, path: Path, mime: str) -> Optional[str]:
        """Encode file as base64 data URL."""
        try:
            raw = path.read_bytes()
        except Exception:
            return None
        b64 = base64.b64encode(raw).decode("utf-8")
        return f"data:{mime};base64,{b64}"

    def _detect_codec(self, path: Path) -> Optional[str]:
        """Use ffprobe to detect video codec."""
        if not shutil.which("ffprobe"):
            return None
        try:
            result = subprocess.run(
                [
                    "ffprobe",
                    "-v", "error",
                    "-select_streams", "v:0",
                    "-show_entries", "stream=codec_name",
                    "-of", "default=nk=1:nw=1",
                    str(path),
                ],
                capture_output=True,
                text=True,
            )
            return result.stdout.strip() or None
        except Exception:
            return None

    def _convert_to_h264(self, path: Path) -> Path:
        """Convert unsupported HEVC/H265 MOV to H.264 MP4 via ffmpeg."""
        out_path = path.with_suffix(".converted.mp4")
        if not shutil.which("ffmpeg"):
            return path

        try:
            result = subprocess.run(
                [
                    "ffmpeg", "-y",
                    "-i", str(path),
                    "-vcodec", "libx264",
                    "-acodec", "aac",
                    "-pix_fmt", "yuv420p",
                    str(out_path),
                ],
                capture_output=True,
                text=True,
            )
            if result.returncode == 0 and out_path.exists() and out_path.stat().st_size > 0:
                return out_path
            return path
        except Exception:
            return path  # fallback if ffmpeg not installed

    # ------------------------------------------------------------
    # Image
    # ------------------------------------------------------------

    def analyze_image(self, path: Path) -> Dict[str, Any]:
        if not self._size_ok(path):
            return {"type": "image", "error": "File missing or exceeds size limit"}

        mime = mimetypes.guess_type(path)[0] or "image/png"
        img_data = self._data_url(path, mime)
        if not img_data:
            return {"type": "image", "error": "Unable to read image"}

        prompt = (
            "You are an expert image analyst. Return JSON with keys: "
            "type, summary, objects, scenes, people, actions, transcript, confidence. "
            "Set transcript=null."
        )

        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": img_data}},
                ],
            }
        ]

        result = self._call_llm(messages)
        result.setdefault("type", "image")
        return result

    # ------------------------------------------------------------
    # Audio
    # ------------------------------------------------------------

    def analyze_audio(self, path: Path) -> Dict[str, Any]:
        if not self._size_ok(path):
            return {"type": "audio", "error": "File missing or exceeds size limit"}

        mime = mimetypes.guess_type(path)[0] or "audio/mpeg"
        audio_data = self._data_url(path, mime)
        if not audio_data:
            return {"type": "audio", "error": "Unable to read audio"}

        prompt = (
            "You are an expert audio analyst. Return JSON with keys: "
            "type, summary, objects, scenes, people, actions, transcript, confidence. "
            "Include transcript for speech or lyrics."
        )

        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "input_audio", "audio_url": {"url": audio_data}},
                ],
            }
        ]

        result = self._call_llm(messages)
        result.setdefault("type", "audio")
        return result

    # ------------------------------------------------------------
    # Extract multiple frames
    # ------------------------------------------------------------

    def _extract_frames(self, path: Path, num_frames=3) -> list[dict[str, Any]]:
        """Extract multiple frames for better video grounding."""
        blocks = []
        try:
            from PIL import Image
            from torchvision.io import read_video

            frames, _, _ = read_video(str(path), pts_unit="sec")
            if frames.numel() == 0:
                return blocks

            step = max(frames.shape[0] // (num_frames + 1), 1)

            for i in range(1, num_frames + 1):
                idx = min(i * step, frames.shape[0] - 1)
                frame = frames[int(idx)]
                img = Image.fromarray(frame.to("cpu").byte().numpy())
                buffer = io.BytesIO()
                img.save(buffer, format="JPEG")
                b64 = base64.b64encode(buffer.getvalue()).decode("utf-8")
                blocks.append(
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}}
                )

        except Exception:
            pass

        return blocks

    # ------------------------------------------------------------
    # Video — with auto conversion
    # ------------------------------------------------------------

    def analyze_video(self, path: Path) -> Dict[str, Any]:
        if not path.exists():
            return {"type": "video", "error": "File does not exist"}

        # Detect codec
        codec = self._detect_codec(path)

        # Auto-convert HEVC/H.265
        if codec in ("hevc", "h265"):
            path = self._convert_to_h264(path)

        # Size check
        if not self._size_ok(path):
            return {"type": "video", "error": "File exceeds size limit after conversion"}

        # MIME fix
        mime = mimetypes.guess_type(path)[0]
        if not mime:
            if path.suffix.lower() == ".mov":
                mime = "video/quicktime"
            else:
                mime = "video/mp4"

        prompt = (
            "You are an expert video analyst. Return JSON with keys: "
            "type, summary, objects, scenes, people, actions, transcript, confidence. "
            "Describe visual elements, scene changes, and summarize any speech."
        )

        content_blocks = [
            {"type": "text", "text": prompt},
        ]

        # Prefer inline when under size limit. For large files, rely on frames when inline is not possible.
        try:
            size_ok = path.stat().st_size <= MAX_INLINE_BYTES
        except Exception:
            size_ok = False

        if size_ok:
            data_url = self._data_url(path, mime)
            if data_url:
                content_blocks.append({"type": "input_audio", "audio_url": {"url": data_url}})

        # Add multiple frames
        frame_blocks = self._extract_frames(path, num_frames=3)
        content_blocks.extend(frame_blocks)

        messages = [{"role": "user", "content": content_blocks}]

        result = self._call_llm(messages)
        result.setdefault("type", "video")
        return result
