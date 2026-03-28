# LLM Client Module
# Handles integration with OpenAI API for analysis tasks

import asyncio
import base64
import logging
import threading
import mimetypes
import os
import time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from typing import Optional, Dict, List, Any, Mapping, Tuple
import openai
from openai import OpenAI
import tiktoken
from pathlib import Path
import json
import re

try:
    from scanner.media import AUDIO_EXTENSIONS, IMAGE_EXTENSIONS, VIDEO_EXTENSIONS
except ImportError:  # pragma: no cover - fallback when scanner isn't on sys.path
    from ...scanner.media import AUDIO_EXTENSIONS, IMAGE_EXTENSIONS, VIDEO_EXTENSIONS


logger = logging.getLogger(__name__)

# ── Rolling context limits ────────────────────────────────────────────────────
_ROLLING_CONTEXT_MAX_CHARS = 1200  # hard cap on rolling context length
_TEST_PATH_RE = re.compile(
    r"(?:^|[\\/])(?:test|tests|__tests__|spec)(?:[\\/]|$)|(?:^|[._-])(test|spec)(?:[._-]|$)",
    re.IGNORECASE,
)
_GENERATED_OR_PACKAGE_PATH_MARKERS = {
    ".next",
    ".electron",
    ".cache",
    ".pnpm",
    ".yarn",
    ".turbo",
    ".parcel-cache",
    ".svelte-kit",
    ".nuxt",
    ".output",
    ".vercel",
    "node_modules",
    "site-packages",
    "dist-packages",
    "vendor",
}
_NON_IMPLEMENTATION_EXTS = {
    ".md", ".markdown", ".txt", ".rst", ".log",
    ".json", ".yml", ".yaml", ".toml", ".ini", ".cfg", ".conf",
    ".css", ".scss", ".sass", ".less", ".xml", ".svg", ".lock",
}
_NON_IMPLEMENTATION_BASENAMES = {
    "package.json", "package-lock.json", "pnpm-lock.yaml", "yarn.lock",
    "tsconfig.json", "jsconfig.json", "next.config.mjs", "next.config.js",
    "vite.config.ts", "vite.config.js", "docker-compose.yml", "docker-compose.yaml",
    "dockerfile", "readme.md",
}
_NON_IMPLEMENTATION_PATH_MARKERS = (
    "/docs/", "/doc/", "/assets/", "/styles/", "/css/", "/migrations/",
    "/scripts/", "/config/", "/settings/", "/.github/",
)


class LLMError(Exception):
    """Raised when LLM operations fail."""
    pass


class InvalidAPIKeyError(Exception):
    """Raised when API key is invalid or missing."""
    pass


class LLMClient:
    """
    Client for interacting with OpenAI's API.
    
    This class provides a foundation for LLM-based analysis operations.
    """
    
    DEFAULT_MODEL = "gpt-4o-mini"
    
    DEFAULT_TEMPERATURE = 0.7
    DEFAULT_MAX_TOKENS = 4000
    DEFAULT_REQUEST_TIMEOUT_SEC = 90
    DEFAULT_SINGLE_PROJECT_BATCH_SIZE = 10
    DEFAULT_BATCH_HEARTBEAT_SEC = 15
    DEFAULT_FILE_SUMMARY_TIMEOUT_SEC = 300
    DEFAULT_MAX_FILE_SUMMARY_TOKENS = 12000
    
    def __init__(
        self, 
        api_key: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ):
        """
        Initialize the LLM client.
        
        Args:
            api_key: OpenAI API key. If None, client operates in mock mode.
            temperature: Sampling temperature (0.0-2.0). Default 0.7 (recommended).
                        Lower = more focused/deterministic, higher = more creative/random.
            max_tokens: Maximum tokens in response. Default 1000 (recommended).
                       Higher values allow longer responses but cost more.
        """
        self.api_key = api_key
        self.client = None
        self.logger = logging.getLogger(__name__)
        self._tokenizer_cache: Dict[str, Any] = {}
        self._tokenizer_warning_emitted = False
        
        self.temperature = temperature if temperature is not None else self.DEFAULT_TEMPERATURE
        self.max_tokens = max_tokens if max_tokens is not None else self.DEFAULT_MAX_TOKENS
        self.request_timeout_sec = self._get_int_env(
            "LLM_REQUEST_TIMEOUT_SEC",
            self.DEFAULT_REQUEST_TIMEOUT_SEC,
            minimum=15,
            maximum=600,
        )

        if not 0.0 <= self.temperature <= 2.0:
            raise ValueError("Temperature must be between 0.0 and 2.0")
        if self.max_tokens <= 0:
            raise ValueError("Max tokens must be positive")
        
        if api_key:
            try:
                self.client = OpenAI(api_key=api_key)
                self.logger.info(
                    f"LLM client initialized (model: {self.DEFAULT_MODEL}, "
                    f"temperature: {self.temperature}, max_tokens: {self.max_tokens})"
                )
            except Exception as e:
                self.logger.error(f"Failed to initialize OpenAI client: {e}")
                raise LLMError(f"Failed to initialize LLM client: {str(e)}")
        else:
            self.logger.warning("LLM client initialized without API key (mock mode)")
    
    def set_temperature(self, temperature: float) -> None:
        """
        Update the temperature parameter for future API calls.
        
        Args:
            temperature: New temperature value (0.0-2.0)
                        0.0 = deterministic, 1.0 = balanced, 2.0 = very creative
        
        Raises:
            ValueError: If temperature is out of range
        """
        if not 0.0 <= temperature <= 2.0:
            raise ValueError("Temperature must be between 0.0 and 2.0")
        self.temperature = temperature
        self.logger.info(f"Temperature updated to: {temperature}")
    
    def set_max_tokens(self, max_tokens: int) -> None:
        """
        Update the max tokens parameter for future API calls.
        
        Args:
            max_tokens: New max tokens value (must be positive)
        
        Raises:
            ValueError: If max_tokens is not positive
        """
        if max_tokens <= 0:
            raise ValueError("Max tokens must be positive")
        self.max_tokens = max_tokens
        self.logger.info(f"Max tokens updated to: {max_tokens}")
    
    def get_config(self) -> Dict[str, Any]:
        """
        Get current client configuration.
        
        Returns:
            Dict with current model, temperature, and max_tokens settings
        """
        return {
            "model": self.DEFAULT_MODEL,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens
        }
    
    def verify_api_key(self) -> bool:
        """
        Verify that the API key is valid by making a test request.
        
        Returns:
            bool: True if API key is valid, False otherwise
            
        Raises:
            InvalidAPIKeyError: If API key is missing or invalid
            LLMError: If verification fails due to other reasons
        """
        if not self.api_key:
            raise InvalidAPIKeyError("No API key provided")
        
        if not self.client:
            raise InvalidAPIKeyError("LLM client not initialized")
        
        try:
            response = self.client.chat.completions.create(
                model=self.DEFAULT_MODEL,
                messages=[{"role": "user", "content": "test"}],
                max_tokens=5
            )
            
            if response and response.choices:
                self.logger.info("API key verified successfully")
                return True
            
            raise LLMError("Unexpected response from API")
            
        except Exception as e:
            error_msg = str(e).lower()
            self.logger.error(f"Verification error: {e}")
            
            # Check error message content to determine error type
            if (
                isinstance(e, openai.AuthenticationError)
                or "authentication" in error_msg
                or "api key" in error_msg
                or "invalid key" in error_msg
                or "unauthorized" in error_msg
            ):
                raise InvalidAPIKeyError("Invalid API key. Please verify your OpenAI API key is correct.")
            elif isinstance(e, openai.APIError) or "api error" in error_msg:
                raise LLMError(f"API error: {str(e)}")
            elif "rate limit" in error_msg or "quota" in error_msg:
                raise LLMError(f"Rate limit exceeded. Please check your API quota and try again: {str(e)}")
            elif "connection" in error_msg or "network" in error_msg:
                raise LLMError(f"Connection error. Please check your internet connection and try again: {str(e)}")
            elif "timeout" in error_msg:
                raise LLMError(f"Request timed out. Please check your internet connection and try again: {str(e)}")
            else:
                raise LLMError(f"Verification failed: {str(e)}")
    
    def is_configured(self) -> bool:
        """
        Check if the client is properly configured with an API key.
        
        Returns:
            bool: True if API key is set, False otherwise
        """
        return self.api_key is not None and self.client is not None

    @staticmethod
    def _get_int_env(name: str, default: int, minimum: int = 1, maximum: Optional[int] = None) -> int:
        """Read a bounded integer from env with safe fallback."""
        raw = os.getenv(name)
        if raw is None:
            return default
        try:
            value = int(str(raw).strip())
        except Exception:
            return default
        if value < minimum:
            return minimum
        if maximum is not None and value > maximum:
            return maximum
        return value

    def _get_tokenizer(self, model: Optional[str] = None):
        """Resolve tokenizer for a model with robust fallbacks."""
        tokenizer_model = model or self.DEFAULT_MODEL
        cached = self._tokenizer_cache.get(tokenizer_model)
        if cached is not None:
            return cached

        normalized_model = tokenizer_model.lower()
        preferred_encoding_name = None
        if normalized_model.startswith("gpt-4o") or normalized_model.startswith("o1"):
            preferred_encoding_name = "o200k_base"

        if preferred_encoding_name is not None:
            try:
                encoding = tiktoken.get_encoding(preferred_encoding_name)
                self._tokenizer_cache[tokenizer_model] = encoding
                return encoding
            except Exception:
                pass

        try:
            encoding = tiktoken.encoding_for_model(tokenizer_model)
            self._tokenizer_cache[tokenizer_model] = encoding
            return encoding
        except Exception as model_exc:
            for fallback_name in ("o200k_base", "cl100k_base"):
                try:
                    encoding = tiktoken.get_encoding(fallback_name)
                    if not self._tokenizer_warning_emitted:
                        self.logger.debug(
                            "Tokenizer mapping unavailable for %s (%s). Using %s.",
                            tokenizer_model,
                            model_exc,
                            fallback_name,
                        )
                        self._tokenizer_warning_emitted = True
                    self._tokenizer_cache[tokenizer_model] = encoding
                    return encoding
                except Exception:
                    continue

        return None
    
    def _count_tokens(self, text: str, model: Optional[str] = None) -> int:
        """
        Count the number of tokens in a text string, default to character estimate.
        
        Args:
            text: Text to count tokens for
            model: Model name for tokenizer (defaults to DEFAULT_MODEL)
            
        Returns:
            int: Number of tokens
        """
        encoding = self._get_tokenizer(model)
        if encoding is not None:
            return len(encoding.encode(text))
        self.logger.warning("Failed to resolve tokenizer. Using character estimate.")
        return len(text) // 4

    def _infer_media_type(self, path: str, mime_type: str) -> Optional[str]:
        """Infer media type from path/mime string."""
        mime = (mime_type or "").lower()
        ext = Path(path).suffix.lower()
        if ext in IMAGE_EXTENSIONS or mime.startswith("image/"):
            return "image"
        if ext in AUDIO_EXTENSIONS or mime.startswith("audio/"):
            return "audio"
        if ext in VIDEO_EXTENSIONS or mime.startswith("video/"):
            return "video"
        return None

    @staticmethod
    def _format_duration(seconds: float) -> str:
        """Convert seconds to a human readable timestamp."""
        try:
            total = int(round(seconds))
            minutes, sec = divmod(total, 60)
            hours, minutes = divmod(minutes, 60)
            if hours:
                return f"{hours:d}:{minutes:02d}:{sec:02d}"
            return f"{minutes:d}:{sec:02d}"
        except Exception:
            return f"{seconds:.1f}s"

    @staticmethod
    def _truncate_text(text: str, limit: int = 160) -> str:
        if not text:
            return ""
        if len(text) <= limit:
            return text
        return text[: max(limit - 3, 0)].rstrip() + "..."

    def _summarize_media_entry(
        self, media_type: str, path: str, info: Mapping[str, Any]
    ) -> Optional[str]:
        """Build a short, human-friendly summary string for a media asset."""
        parts: list[str] = []

        if media_type == "image":
            width = info.get("width")
            height = info.get("height")
            if isinstance(width, (int, float)) and isinstance(height, (int, float)):
                parts.append(f"{int(width)}x{int(height)}px")
            mode = info.get("mode")
            image_format = info.get("format")
            if mode and image_format:
                parts.append(f"{mode}/{image_format}")
            summary = info.get("content_summary")
            if isinstance(summary, str) and summary:
                parts.append(summary)
            else:
                labels = info.get("content_labels") or []
                label_names = [
                    str(entry.get("label"))
                    for entry in labels
                    if isinstance(entry, Mapping) and entry.get("label")
                ]
                if label_names:
                    parts.append(f"labels: {', '.join(label_names[:3])}")

        elif media_type == "audio":
            duration = info.get("duration_seconds")
            if isinstance(duration, (int, float)) and duration > 0:
                parts.append(f"duration {self._format_duration(float(duration))}")
            tempo = info.get("tempo_bpm")
            if isinstance(tempo, (int, float)):
                parts.append(f"tempo {tempo:.0f} BPM")
            genres = info.get("genre_tags") or []
            if isinstance(genres, list) and genres:
                parts.append(f"genres: {', '.join(str(g) for g in genres[:3])}")
            bitrate = info.get("bitrate")
            if isinstance(bitrate, (int, float)):
                parts.append(f"bitrate {int(bitrate)} bps")
            sample_rate = info.get("sample_rate")
            if isinstance(sample_rate, (int, float)):
                parts.append(f"{int(sample_rate)} Hz")
            channels = info.get("channels")
            if isinstance(channels, (int, float)):
                parts.append(f"{int(channels)} channel(s)")
            summary = info.get("content_summary")
            if isinstance(summary, str) and summary:
                parts.append(summary)
            else:
                labels = info.get("content_labels") or []
                label_names = [
                    str(entry.get("label"))
                    for entry in labels
                    if isinstance(entry, Mapping) and entry.get("label")
                ]
                if label_names:
                    parts.append(f"labels: {', '.join(label_names[:2])}")
            transcript = info.get("transcript_excerpt")
            if isinstance(transcript, str) and transcript.strip():
                parts.append(f"speech excerpt: \"{self._truncate_text(transcript.strip(), 140)}\"")

        elif media_type == "video":
            duration = info.get("duration_seconds")
            if isinstance(duration, (int, float)) and duration > 0:
                parts.append(f"length {self._format_duration(float(duration))}")
            bitrate = info.get("bitrate")
            if isinstance(bitrate, (int, float)):
                parts.append(f"bitrate {int(bitrate)} bps")
            summary = info.get("content_summary")
            if isinstance(summary, str) and summary:
                parts.append(summary)
            else:
                labels = info.get("content_labels") or []
                label_names = [
                    str(entry.get("label"))
                    for entry in labels
                    if isinstance(entry, Mapping) and entry.get("label")
                ]
                if label_names:
                    parts.append(f"labels: {', '.join(label_names[:2])}")

        if not parts:
            return None
        return f"{media_type.capitalize()} — {path}: " + "; ".join(parts)

    def _build_media_briefings(
        self,
        files: List[Dict[str, Any]],
        base_path: Optional[Path] = None,
        max_items: int = 12,
        max_llm_images: int = 3,
        max_llm_audio: int = 2,
        max_llm_video: int = 2,
        use_metadata: bool = True,
    ) -> List[str]:
        """Collect concise media descriptions for LLM context."""
        by_type: Dict[str, List[Tuple[str, Mapping[str, Any]]]] = {"image": [], "audio": [], "video": []}
        for meta in files:
            media_info = meta.get("media_info")
            if not isinstance(media_info, Mapping):
                media_info = {}
            path = str(meta.get("path", ""))
            media_type = self._infer_media_type(path, str(meta.get("mime_type") or ""))
            if not media_type:
                continue
            by_type.setdefault(media_type, []).append((path, media_info))

        briefings: list[str] = []
        total_candidates = sum(len(v) for v in by_type.values())

        def _ensure_path(p: str) -> Optional[Path]:
            full = (base_path / p) if base_path and not Path(p).is_absolute() else Path(p)
            return full if full.exists() and full.is_file() else None

        # Prioritize audio/video first so they are not crowded out by images.
        llm_audio_used = 0
        for path, info in by_type.get("audio", []):
            if len(briefings) >= max_items:
                break
            if base_path and self.is_configured() and llm_audio_used < max_llm_audio:
                full_path = _ensure_path(path)
                if full_path:
                    llm_summary = self._llm_describe_audio(full_path, info)
                    if llm_summary:
                        briefings.append(f"Audio — {path}: {llm_summary}")
                        llm_audio_used += 1
                        continue
            if use_metadata:
                summary = self._summarize_media_entry("audio", path, info)
                if summary:
                    briefings.append(summary)
            # If no LLM and no metadata allowed, skip to keep output LLM-only.

        llm_video_used = 0
        for path, info in by_type.get("video", []):
            if len(briefings) >= max_items:
                break
            if base_path and self.is_configured() and llm_video_used < max_llm_video:
                full_path = _ensure_path(path)
                if full_path:
                    llm_summary = self._llm_describe_video(full_path, info)
                    if llm_summary:
                        briefings.append(f"Video — {path}: {llm_summary}")
                        llm_video_used += 1
                        continue
            if use_metadata:
                summary = self._summarize_media_entry("video", path, info)
                if summary:
                    briefings.append(summary)

        llm_images_used = 0
        for path, info in by_type.get("image", []):
            if len(briefings) >= max_items:
                break
            # Prefer an LLM vision read for the first few images to improve accuracy.
            if (
                base_path
                and self.is_configured()
                and llm_images_used < max_llm_images
            ):
                full_path = _ensure_path(path)
                if full_path and full_path.stat().st_size <= 6 * 1024 * 1024:
                    llm_summary = self._llm_describe_image(full_path)
                    if llm_summary:
                        summary = f"Image — {path}: {llm_summary}"
                        llm_images_used += 1
                    else:
                        summary = None
                else:
                    summary = None
            else:
                summary = None

            if summary:
                briefings.append(summary)
                continue
            if use_metadata:
                summary = self._summarize_media_entry("image", path, info)
                if summary:
                    briefings.append(summary)

        if total_candidates > len(briefings):
            remaining = total_candidates - len(briefings)
            briefings.append(f"...and {remaining} more media file(s) detected.")

        return briefings

    def summarize_media_only(
        self,
        relevant_files: List[Dict[str, Any]],
        scan_base_path: str,
        max_items: int = 12,
        progress_callback: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """Generate media-only insights (images/audio/video) without project analysis."""
        if not self.is_configured():
            raise LLMError("LLM client is not configured")
        try:
            base_path = Path(scan_base_path) if scan_base_path else None
            briefings = self._build_media_briefings(
                relevant_files, base_path=base_path, max_items=max_items, use_metadata=False
            )
            return {
                "media_briefings": briefings,
                "files_analyzed_count": len(briefings),
            }
        except Exception as exc:
            self.logger.error(f"Media-only summary failed: {exc}")
            raise LLMError(f"Failed to summarize media: {exc}")

    def _llm_describe_image(self, path: Path) -> Optional[str]:
        """Ask the LLM (vision) to describe an image file."""
        if not self.is_configured():
            return None
        try:
            mime_type = mimetypes.guess_type(path.name)[0] or "image/png"
            return self._llm_describe_image_bytes(path.read_bytes(), mime_type=mime_type)
        except Exception as exc:  # pragma: no cover - network/API dependent
            self.logger.debug("Vision description failed for %s: %s", path, exc)
        return None

    def _llm_describe_image_bytes(self, data: bytes, mime_type: str = "image/jpeg") -> Optional[str]:
        """Ask the LLM (vision) to describe image bytes."""
        if not self.is_configured():
            return None
        try:
            encoded = base64.b64encode(data).decode("utf-8")
            messages = [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": (
                                "Describe what appears in this image, any notable objects, "
                                "text, or context, in 2-3 concise bullet points."
                            ),
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{mime_type};base64,{encoded}",
                                "detail": "auto",
                            },
                        },
                    ],
                }
            ]
            response = self.client.chat.completions.create(
                model=self.DEFAULT_MODEL,
                messages=messages,
                max_tokens=150,
                temperature=0.4,
            )
            if response and response.choices:
                return response.choices[0].message.content.strip()
        except Exception as exc:  # pragma: no cover - network/API dependent
            self.logger.debug("Vision description failed for raw bytes: %s", exc)
        return None

    def _llm_transcribe_audio(self, path: Path) -> Optional[str]:
        """Transcribe audio/video via Whisper if available."""
        if not self.is_configured():
            return None
        if not path.exists() or not path.is_file():
            return None
        size_mb = path.stat().st_size / (1024 * 1024)
        if size_mb > 15:  # keep uploads manageable
            return None
        try:
            with path.open("rb") as f:
                transcript = self.client.audio.transcriptions.create(
                    model="whisper-1",
                    file=f,
                    response_format="text",
                )
            if isinstance(transcript, str) and transcript.strip():
                return transcript.strip()
        except Exception as exc:  # pragma: no cover - network/API dependent
            self.logger.debug("Audio transcription failed for %s: %s", path, exc)
        return None

    def _llm_describe_audio(self, path: Path, media_info: Mapping[str, Any]) -> Optional[str]:
        """Summarize audio by transcribing and prompting the LLM."""
        transcript = self._llm_transcribe_audio(path)
        if not transcript:
            return None
        duration = media_info.get("duration_seconds")
        tempo = media_info.get("tempo_bpm")
        genres = media_info.get("genre_tags") or []
        meta_bits = []
        if isinstance(duration, (int, float)):
            meta_bits.append(f"duration {self._format_duration(float(duration))}")
        if isinstance(tempo, (int, float)):
            meta_bits.append(f"tempo {tempo:.0f} BPM")
        if genres:
            meta_bits.append(f"genres {', '.join(str(g) for g in genres[:3])}")
        meta_text = "; ".join(meta_bits) if meta_bits else "duration unknown"
        prompt = (
            f"Audio clip ({meta_text}). Transcript:\n{transcript}\n\n"
            "Provide a concise 2-3 sentence summary of what is spoken/sung, mood/genre hints, "
            "and any notable entities or topics."
        )
        try:
            messages = [{"role": "user", "content": prompt}]
            resp = self._make_llm_call(messages, max_tokens=180, temperature=0.5)
            return resp.strip()
        except Exception as exc:  # pragma: no cover - network/API dependent
            self.logger.debug("Audio summarize failed for %s: %s", path, exc)
        return None

    def _llm_describe_video(self, path: Path, media_info: Mapping[str, Any]) -> Optional[str]:
        """Summarize video by transcribing audio track and/or sampling a frame."""
        transcript = self._llm_transcribe_audio(path)
        duration = media_info.get("duration_seconds")
        meta_bits = []
        if isinstance(duration, (int, float)):
            meta_bits.append(f"length {self._format_duration(float(duration))}")
        meta_text = "; ".join(meta_bits) if meta_bits else "length unknown"

        # If transcript exists, prefer transcript-driven summary.
        if transcript:
            prompt = (
                f"Video ({meta_text}). Audio transcript:\n{transcript}\n\n"
                "Provide a concise 2-3 sentence summary of what the video likely shows based on the audio: "
                "setting, participants, actions, tone, and any notable events or topics."
            )
            try:
                messages = [{"role": "user", "content": prompt}]
                resp = self._make_llm_call(messages, max_tokens=220, temperature=0.45)
                if resp:
                    return resp.strip()
            except Exception as exc:  # pragma: no cover
                self.logger.debug("Video summarize (audio) failed for %s: %s", path, exc)

        # Fallback: sample a representative frame and ask vision model.
        try:
            import io
            from PIL import Image  # type: ignore
            try:
                from torchvision.io import read_video  # type: ignore
            except Exception:  # pragma: no cover - optional dep missing
                read_video = None  # type: ignore

            if read_video is not None and Image is not None:
                frames, _, _ = read_video(str(path), pts_unit="sec")
                if frames.numel() > 0:
                    # Pick middle frame for a representative shot.
                    idx = frames.shape[0] // 2
                    frame = frames[int(idx)]
                    image = Image.fromarray(frame.to("cpu").byte().numpy())
                    buffer = io.BytesIO()
                    image.save(buffer, format="JPEG")
                    vision_desc = self._llm_describe_image_bytes(buffer.getvalue(), mime_type="image/jpeg")
                    if vision_desc:
                        return vision_desc
        except Exception as exc:  # pragma: no cover
            self.logger.debug("Video vision fallback failed for %s: %s", path, exc)

        return None
    
    def _make_llm_call(
        self, 
        messages: List[Dict[str, str]], 
        model: Optional[str] = None,
        max_tokens: Optional[int] = None, 
        temperature: Optional[float] = None,
        response_format: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Make a call to the LLM API using configured defaults.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            model: Model to use
            max_tokens: Maximum tokens in response (defaults to self.max_tokens)
            temperature: Temperature for response generation (defaults to self.temperature)
            
        Returns:
            str: LLM response content
            
        Raises:
            LLMError: If API call fails
        """
        if not self.is_configured():
            raise LLMError("LLM client is not configured with an API key")
        
        model = model or self.DEFAULT_MODEL
        max_tokens = max_tokens if max_tokens is not None else self.max_tokens
        temperature = temperature if temperature is not None else self.temperature
        
        try:
            kwargs: Dict[str, Any] = dict(
                model=model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
            )
            if response_format:
                kwargs["response_format"] = response_format
            kwargs["timeout"] = self.request_timeout_sec

            response = self.client.chat.completions.create(**kwargs)
            
            if response and response.choices:
                return response.choices[0].message.content.strip()
            
            raise LLMError("Empty response from API")
            
        except Exception as e:
            error_msg = str(e).lower()
            
            # Check error message content to determine error type
            if (
                isinstance(e, openai.AuthenticationError)
                or "authentication" in error_msg
                or "api key" in error_msg
                or "unauthorized" in error_msg
                or "invalid key" in error_msg
            ):
                raise InvalidAPIKeyError("Invalid API key. Please verify your OpenAI API key is correct.")
            elif isinstance(e, openai.APIError) or "api error" in error_msg:
                raise LLMError(f"API error: {str(e)}")
            elif "rate limit" in error_msg or "quota" in error_msg:
                raise LLMError(f"Rate limit exceeded. Please wait a moment and try again, or check your API quota: {str(e)}")
            elif "connection" in error_msg or "network" in error_msg:
                raise LLMError(f"Connection error. Please check your internet connection and try again: {str(e)}")
            elif "timeout" in error_msg:
                raise LLMError(f"Request timed out. Please check your internet connection and try again: {str(e)}")
            else:
                raise LLMError(f"LLM call failed: {str(e)}")

    def make_llm_call(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        response_format: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Public wrapper around _make_llm_call for external callers."""
        return self._make_llm_call(
            messages,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            response_format=response_format,
        )

    def chunk_and_summarize(self, text: str, file_type: str = "", 
                           chunk_size: int = 2000, overlap: int = 100) -> Dict[str, Any]:
        """
        Handle large text files by splitting into chunks, summarizing each, then merging.
        
        Args:
            text: Large text content to summarize
            file_type: File type/extension for context
            chunk_size: Maximum tokens per chunk (default: 2000)
            overlap: Token overlap between chunks for context (default: 100)
            
        Returns:
            Dict containing:
                - final_summary: Merged summary
                - num_chunks: Number of chunks processed
                - chunk_summaries: List of individual chunk summaries
                
        Raises:
            LLMError: If summarization fails
        """
        if not self.is_configured():
            raise LLMError("LLM client is not configured")
        
        try:
            try:
                encoding = self._get_tokenizer(self.DEFAULT_MODEL)
                if encoding is None:
                    raise ValueError("No tokenizer available")
                tokens = encoding.encode(text)
                decode_tokens = encoding.decode
            except Exception as exc:
                # Fall back when model mapping is unavailable in tiktoken
                self.logger.warning(f"Failed to load tokenizer for {self.DEFAULT_MODEL}: {exc}. Using fallback chunking.")
                tokens = [text[i:i + 4] for i in range(0, len(text), 4)]  # Approximate 4 chars per token
                decode_tokens = lambda chunk_tokens: "".join(chunk_tokens)
            chunks = []
            
            i = 0
            while i < len(tokens):
                chunk_tokens = tokens[i:i + chunk_size]
                chunk_text = decode_tokens(chunk_tokens)
                chunks.append(chunk_text)
                i += chunk_size - overlap
            
            self.logger.info(f"Split text into {len(chunks)} chunks")
            
            chunk_summaries = []
            for idx, chunk in enumerate(chunks):
                prompt = f"""Summarize this section of a {file_type} file. Focus on key functionality and important details.
                
                Section {idx + 1}/{len(chunks)}:
                {chunk}

                Provide a concise summary of this section."""

                messages = [{"role": "user", "content": prompt}]
                summary = self._make_llm_call(messages, max_tokens=300, temperature=0.5)
                chunk_summaries.append(summary)
            
            merge_prompt = f"""You are reviewing summaries of different sections of a {file_type} file.
            Create a coherent, comprehensive summary that captures the overall purpose and key functionality.

            Section summaries:
            {chr(10).join(f"{i+1}. {s}" for i, s in enumerate(chunk_summaries))}

            Provide a unified summary (100-200 words) that captures the essence of the entire file."""

            messages = [{"role": "user", "content": merge_prompt}]
            final_summary = self._make_llm_call(messages, max_tokens=400, temperature=0.5)
            
            return {
                "final_summary": final_summary,
                "num_chunks": len(chunks),
                "chunk_summaries": chunk_summaries
            }
            
        except Exception as e:
            self.logger.error(f"Chunk and summarize failed: {e}")
            raise LLMError(f"Failed to chunk and summarize: {str(e)}")
    
    @staticmethod
    def _compute_file_metadata(content: str, file_path: str, file_type: str) -> Dict[str, Any]:
        """Compute lightweight metadata for a file to enrich LLM context."""
        lines = content.split('\n')
        line_count = len(lines)

        import_pattern = re.compile(
            r'^\s*(?:import\s|from\s+\S+\s+import|require\(|#include|using\s)',
        )
        import_count = sum(1 for line in lines if import_pattern.match(line))

        complexity_pattern = re.compile(
            r'\b(?:if|else|elif|for|while|try|except|catch|switch|case|class|def|function|async)\b',
        )
        complexity_signals = sum(1 for line in lines if complexity_pattern.search(line))

        basename = Path(file_path).name.lower()
        has_tests = any(marker in basename for marker in ('test', 'spec', '_test.', '.test.', '_spec.', '.spec.'))

        return {
            "line_count": line_count,
            "import_count": import_count,
            "complexity_signals": complexity_signals,
            "has_tests": has_tests,
            "extension": file_type,
        }

    def summarize_tagged_file(
        self,
        file_path: str,
        content: str,
        file_type: str,
        file_metadata: Optional[Dict[str, Any]] = None,
        project_context: Optional[str] = None,
    ) -> Dict[str, str]:
        """
        Create a detailed summary of a user-tagged important file.
        Automatically handles large files through chunking.
        
        Args:
            file_path: Path to the file
            content: Full file content
            file_type: File extension/type
            file_metadata: Optional lightweight file stats (line_count, imports, etc.)
            project_context: Optional rolling project context from prior batches
            
        Returns:
            Formatted text output containing:
                - summary: Concise summary (80-150 words)
                - key_functionality: Key functionality and purpose
                - notable_patterns: Notable patterns or techniques
                
        Raises:
            LLMError: If summarization fails
        """
        if not self.is_configured():
            raise LLMError("LLM client is not configured")
        
        try:
            token_count = self._count_tokens(content)
            self.logger.info(f"Summarizing {file_path} ({token_count} tokens)")

            # Guardrail: extremely large files can stall an entire batch.
            max_summary_tokens = self._get_int_env(
                "AI_MAX_FILE_SUMMARY_TOKENS",
                self.DEFAULT_MAX_FILE_SUMMARY_TOKENS,
                minimum=2000,
                maximum=80000,
            )
            truncated_for_budget = False
            if token_count > max_summary_tokens:
                approx_chars = max_summary_tokens * 4
                content = content[:approx_chars]
                token_count = self._count_tokens(content)
                truncated_for_budget = True
                self.logger.warning(
                    "Truncated oversized file for AI summary (%s): capped to %s tokens",
                    file_path,
                    max_summary_tokens,
                )
            
            if token_count > 2000:
                chunk_result = self.chunk_and_summarize(content, file_type)
                content_to_analyze = chunk_result["final_summary"]
            else:
                content_to_analyze = content

            if truncated_for_budget:
                content_to_analyze = (
                    "[Note: file content was truncated for latency budget before summarization.]\n"
                    + content_to_analyze
                )

            # ── Build metadata header ────────────────────────────────────
            meta_header = ""
            if file_metadata:
                meta_lines = [
                    f"Lines: {file_metadata.get('line_count', '?')}",
                    f"Imports/includes: {file_metadata.get('import_count', '?')}",
                    f"Complexity signals (if/for/class/def etc.): {file_metadata.get('complexity_signals', '?')}",
                    f"Is test file: {'yes' if file_metadata.get('has_tests') else 'no'}",
                ]
                meta_header = "\nFile metadata:\n" + "\n".join(f"  {l}" for l in meta_lines) + "\n"

            # ── Build project context prefix ─────────────────────────────
            context_prefix = ""
            if project_context:
                context_prefix = f"\nPROJECT CONTEXT SO FAR:\n{project_context}\n"

            prompt = f"""Analyze this {file_type} file and provide a brief structured summary.{context_prefix}
File: {file_path}{meta_header}
Content:
{content_to_analyze}

Provide a concise analysis (max 100 words total) in this format:

SUMMARY: [2-3 sentences on what this file does]

KEY FUNCTIONALITY: [3-4 bullet points of main features]

NOTABLE PATTERNS: [1-2 notable techniques or patterns used]"""

            messages = [{"role": "user", "content": prompt}]
            response = self._make_llm_call(messages, max_tokens=150, temperature=0.6)
            
            return {
                "file_path": file_path,
                "file_type": file_type,
                "analysis": response
            }
            
        except Exception as e:
            self.logger.error(f"Failed to summarize tagged file: {e}")
            raise LLMError(f"File summarization failed: {str(e)}")

    @staticmethod
    def _is_test_path(path: str) -> bool:
        return bool(_TEST_PATH_RE.search(path or ""))

    @staticmethod
    def _is_generated_or_package_path(path: str) -> bool:
        normalized = str(path or "").replace("\\", "/").strip().lower().strip("/")
        if not normalized:
            return False

        parts = [segment for segment in normalized.split("/") if segment]
        if not parts:
            return False

        if any(segment in _GENERATED_OR_PACKAGE_PATH_MARKERS for segment in parts):
            return True

        # Hidden directories (e.g. .next/.cache/.electron) are usually build/package output.
        for segment in parts[:-1]:
            if segment.startswith(".") and len(segment) > 1:
                return True

        return False

    @staticmethod
    def _is_non_implementation_path(path: str) -> bool:
        normalized = "/" + str(path or "").replace("\\", "/").lower().lstrip("/")
        basename = Path(normalized).name
        ext = Path(basename).suffix.lower()

        if basename in _NON_IMPLEMENTATION_BASENAMES:
            return True
        if ext in _NON_IMPLEMENTATION_EXTS:
            return True
        if any(marker in normalized for marker in _NON_IMPLEMENTATION_PATH_MARKERS):
            return True
        if basename.endswith(".config.ts") or basename.endswith(".config.js"):
            return True
        if basename.endswith(".config.mjs") or basename.endswith(".config.cjs"):
            return True
        return False

    @staticmethod
    def _is_logic_heavy_candidate(path: str) -> bool:
        """Heuristic to determine if a file contains core logic rather than being boilerplate."""
        path_str = str(path or "").replace("\\", "/").lower()
        if LLMClient._is_test_path(path_str):
            return False
        if LLMClient._is_generated_or_package_path(path_str):
            return False
        if LLMClient._is_non_implementation_path(path_str):
            return False

        basename = path_str.split("/")[-1]
        preferred_exts = {".py", ".ts", ".js", ".jsx", ".tsx", ".java", ".cpp", ".c", ".h", ".cs", ".go", ".rs", ".rb", ".php", ".swift", ".kt", ".m"}
        ext = Path(basename).suffix.lower()
        return ext in preferred_exts

    @staticmethod
    def _safe_int(value: Any, default: int = 0) -> int:
        try:
            return int(float(value))
        except Exception:
            return default

    @staticmethod
    def _safe_float(value: Any, default: float = 0.0) -> float:
        try:
            return float(value)
        except Exception:
            return default

    @staticmethod
    def _clamp_score(value: float) -> int:
        return max(0, min(100, int(round(value))))

    def _derive_architecture_diagram(self, tagged_files_summaries: List[Dict[str, str]]) -> Dict[str, Any]:
        paths = [
            str(item.get("file_path", ""))
            for item in tagged_files_summaries
            if isinstance(item, dict) and item.get("file_path")
        ]
        lower_paths = [p.replace("\\", "/").lower() for p in paths]

        def _has_any(markers: List[str]) -> bool:
            return any(any(marker in p for marker in markers) for p in lower_paths)

        has_ui = _has_any(["/frontend/", "/ui/", "/components/", "/pages/", "/views/", "/app/"])
        has_backend = _has_any(["/backend/", "/api/", "/server/", "/services/"])
        has_data = _has_any(["/db/", "/database/", "/migrations/", "schema", "repository", "model"])
        has_worker = _has_any(["/queue/", "/worker/", "/jobs/"])
        has_external = _has_any(["supabase", "openai", "stripe", "aws", "azure", "gcp", "firebase"])
        has_tests = any(self._is_test_path(p) for p in paths)

        nodes: List[Dict[str, str]] = []
        edges: List[Dict[str, str]] = []

        nodes.append({"id": "core", "label": "Core Application", "type": "service"})
        if has_ui:
            nodes.append({"id": "ui", "label": "UI Layer", "type": "ui"})
            edges.append({"from": "ui", "to": "core", "label": "calls"})
        if has_data:
            nodes.append({"id": "data", "label": "Data Layer", "type": "database"})
            edges.append({"from": "core", "to": "data", "label": "reads/writes"})
        if has_worker:
            nodes.append({"id": "worker", "label": "Background Jobs", "type": "service"})
            edges.append({"from": "core", "to": "worker", "label": "dispatches"})
        if has_external:
            nodes.append({"id": "external", "label": "External Services", "type": "external"})
            edges.append({"from": "core", "to": "external", "label": "integrates"})
        if has_tests:
            nodes.append({"id": "tests", "label": "Test Suite", "type": "library"})
            edges.append({"from": "tests", "to": "core", "label": "validates"})

        # Guarantee at least two nodes so the UI can render a meaningful diagram.
        if len(nodes) < 2:
            nodes.append({"id": "source", "label": "Source Modules", "type": "library"})
            edges.append({"from": "source", "to": "core", "label": "contains logic"})

        return {
            "nodes": nodes[:6],
            "edges": edges[:8],
        }

    def _compute_project_scores(
        self,
        local_analysis: Dict[str, Any],
        tagged_files_summaries: List[Dict[str, str]],
    ) -> Dict[str, int]:
        code_metrics = local_analysis.get("code_metrics") if isinstance(local_analysis.get("code_metrics"), dict) else {}
        file_profile = local_analysis.get("file_profile") if isinstance(local_analysis.get("file_profile"), dict) else {}

        total_files = self._safe_int(local_analysis.get("total_files"), default=len(tagged_files_summaries))
        total_lines = self._safe_int(code_metrics.get("total_lines"), default=self._safe_int(local_analysis.get("total_lines"), 0))
        comment_lines = self._safe_int(code_metrics.get("comment_lines"), default=self._safe_int(local_analysis.get("comment_lines"), 0))
        avg_complexity = self._safe_float(code_metrics.get("avg_complexity"), 0.0)
        dead_code_total = self._safe_int(code_metrics.get("dead_code_total"), 0)

        paths = [
            str(item.get("file_path", ""))
            for item in tagged_files_summaries
            if isinstance(item, dict) and item.get("file_path")
        ]
        test_file_count = self._safe_int(file_profile.get("test_file_count"), default=sum(1 for p in paths if self._is_test_path(p)))
        doc_file_count = self._safe_int(file_profile.get("doc_file_count"), default=sum(1 for p in paths if Path(p).suffix.lower() in {".md", ".markdown", ".rst", ".txt"}))

        comment_ratio = (comment_lines / total_lines) if total_lines > 0 else 0.0
        test_ratio = (test_file_count / total_files) if total_files > 0 else 0.0
        doc_ratio = (doc_file_count / total_files) if total_files > 0 else 0.0

        unique_dirs = len(
            {
                "/".join(Path(p).parts[:2]).lower()
                for p in paths
                if p
            }
        )

        text_blob = " ".join(str(item.get("analysis", "")).lower() for item in tagged_files_summaries if isinstance(item, dict))
        security_hits = sum(
            1
            for marker in ["auth", "token", "permission", "sanitize", "validation", "encryption", "csrf", "xss"]
            if marker in text_blob
        )

        code_quality = self._clamp_score(58 - (avg_complexity * 4.2) - (dead_code_total * 1.1) + (comment_ratio * 22) + min(total_files / 20, 9))
        modularity = self._clamp_score(52 + min(unique_dirs * 5.0, 24) + min(total_files / 25, 8) - (avg_complexity * 2.4))
        readability = self._clamp_score(56 + (comment_ratio * 32) - (avg_complexity * 3.0) - min(dead_code_total, 10) * 0.7)
        test_coverage = self._clamp_score(20 + (test_ratio * 95) + (8 if "integration test" in text_blob or "unit test" in text_blob else 0))
        documentation = self._clamp_score(36 + (doc_ratio * 82) + (comment_ratio * 20))
        security = self._clamp_score(48 + min(security_hits * 4.5, 24) + (4 if test_ratio > 0.15 else 0) - min(dead_code_total, 8) * 0.6)

        overall = self._clamp_score(
            (code_quality * 0.24)
            + (modularity * 0.16)
            + (readability * 0.16)
            + (test_coverage * 0.16)
            + (documentation * 0.12)
            + (security * 0.16)
        )

        return {
            "overall": overall,
            "code_quality": code_quality,
            "modularity": modularity,
            "readability": readability,
            "test_coverage": test_coverage,
            "documentation": documentation,
            "security": security,
        }

    def _normalize_llm_project_scores(self, payload_scores: Any) -> Dict[str, int]:
        score_keys = [
            "overall",
            "code_quality",
            "modularity",
            "readability",
            "test_coverage",
            "documentation",
            "security",
        ]

        normalized: Dict[str, int] = {}
        provided_overall: Optional[int] = None
        if isinstance(payload_scores, dict):
            for key in score_keys:
                if payload_scores.get(key) is None:
                    continue
                coerced = self._clamp_score(self._safe_float(payload_scores.get(key), 60.0))
                normalized[key] = coerced
                if key == "overall":
                    provided_overall = coerced

        dim_keys = [k for k in score_keys if k != "overall"]
        provided_dims = [normalized[k] for k in dim_keys if k in normalized]
        provided_dim_count = len(provided_dims)
        fill_value = int(round(sum(provided_dims) / provided_dim_count)) if provided_dim_count else (provided_overall if provided_overall is not None else 60)

        for key in dim_keys:
            if key not in normalized:
                normalized[key] = fill_value

        # Make overall follow the category breakdown whenever we have enough
        # category evidence, so one repeated LLM overall value cannot dominate.
        if provided_dim_count >= 2:
            normalized["overall"] = self._clamp_score(sum(normalized[k] for k in dim_keys) / len(dim_keys))
        elif provided_overall is not None:
            normalized["overall"] = provided_overall
        else:
            normalized["overall"] = self._clamp_score(sum(normalized[k] for k in dim_keys) / len(dim_keys))

        return {key: normalized[key] for key in score_keys}

    def _normalize_llm_architecture(
        self,
        architecture_payload: Any,
        tagged_files_summaries: List[Dict[str, str]],
    ) -> Dict[str, Any]:
        architecture = architecture_payload if isinstance(architecture_payload, dict) else {}
        summary = str(architecture.get("summary") or "").strip()
        if not summary:
            summary = "Architecture inferred from the aggregated project evidence."

        patterns_raw = architecture.get("patterns") if isinstance(architecture.get("patterns"), list) else []
        patterns: List[str] = []
        for item in patterns_raw:
            text = str(item).strip()
            if not text:
                continue
            if text.lower() in {p.lower() for p in patterns}:
                continue
            patterns.append(text)

        diagram_payload = architecture.get("diagram") if isinstance(architecture.get("diagram"), dict) else {}
        raw_nodes = diagram_payload.get("nodes") if isinstance(diagram_payload.get("nodes"), list) else []
        raw_edges = diagram_payload.get("edges") if isinstance(diagram_payload.get("edges"), list) else []

        normalized_nodes: List[Dict[str, str]] = []
        node_ids: set[str] = set()
        for idx, node in enumerate(raw_nodes):
            if not isinstance(node, dict):
                continue
            node_id = str(node.get("id") or "").strip() or f"component_{idx + 1}"
            node_id = re.sub(r"[^a-zA-Z0-9_-]", "_", node_id)
            if node_id in node_ids:
                node_id = f"{node_id}_{idx + 1}"

            label = str(node.get("label") or "").strip() or node_id.replace("_", " ").title()
            node_type = str(node.get("type") or "service").strip().lower()
            if node_type not in {"ui", "service", "database", "library", "external"}:
                node_type = "service"

            normalized_nodes.append({"id": node_id, "label": label, "type": node_type})
            node_ids.add(node_id)

        normalized_edges: List[Dict[str, str]] = []
        for edge in raw_edges:
            if not isinstance(edge, dict):
                continue
            source = str(edge.get("from") or "").strip()
            target = str(edge.get("to") or "").strip()
            if source not in node_ids or target not in node_ids or source == target:
                continue
            edge_label = str(edge.get("label") or "").strip()
            normalized_edges.append({"from": source, "to": target, "label": edge_label})

        if len(normalized_nodes) < 2:
            fallback_diagram = self._derive_architecture_diagram(tagged_files_summaries)
            fallback_nodes = fallback_diagram.get("nodes") if isinstance(fallback_diagram.get("nodes"), list) else []
            fallback_edges = fallback_diagram.get("edges") if isinstance(fallback_diagram.get("edges"), list) else []
            normalized_nodes = [
                {
                    "id": str(node.get("id") or f"component_{idx + 1}"),
                    "label": str(node.get("label") or f"Component {idx + 1}"),
                    "type": str(node.get("type") or "service"),
                }
                for idx, node in enumerate(fallback_nodes)
                if isinstance(node, dict)
            ][:8]
            node_ids = {str(node.get("id")) for node in normalized_nodes}
            normalized_edges = [
                {
                    "from": str(edge.get("from") or ""),
                    "to": str(edge.get("to") or ""),
                    "label": str(edge.get("label") or ""),
                }
                for edge in fallback_edges
                if isinstance(edge, dict)
                and str(edge.get("from") or "") in node_ids
                and str(edge.get("to") or "") in node_ids
            ][:12]

        if not patterns and normalized_nodes:
            patterns.append("Layered architecture")

        return {
            "summary": summary,
            "patterns": patterns[:6],
            "diagram": {
                "nodes": normalized_nodes[:8],
                "edges": normalized_edges[:12],
            },
        }

    @staticmethod
    def _extract_language_names(local_analysis: Dict[str, Any]) -> List[str]:
        language_breakdown = local_analysis.get("language_breakdown")
        if not isinstance(language_breakdown, list):
            return []

        names: List[str] = []
        for entry in language_breakdown:
            if isinstance(entry, dict):
                name = entry.get("name") or entry.get("language")
                if name:
                    names.append(str(name))
            elif isinstance(entry, str):
                names.append(entry)

        deduped: List[str] = []
        seen = set()
        for name in names:
            key = name.strip().lower()
            if not key or key in seen:
                continue
            seen.add(key)
            deduped.append(name.strip())
        return deduped

    @staticmethod
    def _tokenize_text(text: str) -> List[str]:
        raw = re.findall(r"[a-zA-Z][a-zA-Z0-9_+-]{1,}", (text or "").lower())
        stop_words = {
            "the", "and", "for", "with", "that", "this", "from", "into", "across", "project", "code",
            "used", "using", "are", "was", "were", "been", "have", "has", "had", "more", "less",
            "very", "much", "many", "main", "core", "high", "low", "over", "under", "about",
        }
        return [token for token in raw if token not in stop_words]

    def _text_overlap_ratio(self, a: str, b: str) -> float:
        a_tokens = set(self._tokenize_text(a))
        b_tokens = set(self._tokenize_text(b))
        if not a_tokens or not b_tokens:
            return 0.0
        intersection = len(a_tokens.intersection(b_tokens))
        union = len(a_tokens.union(b_tokens))
        return intersection / max(1, union)

    def _normalize_project_type(
        self,
        project_type_raw: str,
        local_analysis: Dict[str, Any],
        architecture: Dict[str, Any],
    ) -> str:
        normalized_raw = str(project_type_raw or "").strip()

        file_profile = local_analysis.get("file_profile") if isinstance(local_analysis.get("file_profile"), dict) else {}
        top_extensions = file_profile.get("top_extensions") if isinstance(file_profile.get("top_extensions"), list) else []
        ext_names = {
            str(entry.get("ext", "")).lower()
            for entry in top_extensions
            if isinstance(entry, dict)
        }

        diagram = architecture.get("diagram") if isinstance(architecture.get("diagram"), dict) else {}
        nodes = diagram.get("nodes") if isinstance(diagram.get("nodes"), list) else []
        node_types = {
            str(node.get("type", "")).lower()
            for node in nodes
            if isinstance(node, dict)
        }

        has_ui = "ui" in node_types or bool(ext_names.intersection({".tsx", ".jsx", ".html", ".css", ".scss"}))
        has_data = "database" in node_types
        has_external = "external" in node_types
        has_service = "service" in node_types or bool(ext_names.intersection({".py", ".go", ".java", ".cs", ".rb", ".php"}))
        has_notebook = ".ipynb" in ext_names
        has_cli_markers = bool(ext_names.intersection({".sh", ".bat", ".ps1"}))

        inferred = "Software project"
        if has_ui and has_service and (has_data or has_external):
            inferred = "Full-stack application"
        elif has_service and (has_data or has_external):
            inferred = "Backend service"
        elif has_ui and not has_service:
            inferred = "Frontend application"
        elif has_notebook:
            inferred = "Data/ML project"
        elif has_cli_markers and not has_ui:
            inferred = "CLI/automation project"

        generic_labels = {
            "full stack web app",
            "full-stack web app",
            "web app",
            "web application",
            "application",
            "software project",
            "project",
        }
        normalized_key = normalized_raw.lower()
        if not normalized_raw:
            return inferred
        if "full-stack" in normalized_key and not (has_ui and has_service):
            return inferred
        if normalized_key in generic_labels:
            return inferred
        return normalized_raw

    def _normalize_insights(
        self,
        insights: Dict[str, Any],
        scores: Dict[str, int],
        key_modules: Optional[List[Dict[str, Any]]] = None,
        tagged_files_summaries: Optional[List[Dict[str, str]]] = None,
    ) -> Dict[str, Any]:
        if not isinstance(insights, dict):
            insights = {}
        key_modules = key_modules if isinstance(key_modules, list) else []
        tagged_files_summaries = tagged_files_summaries if isinstance(tagged_files_summaries, list) else []

        def _compact_text(text: str, max_len: int = 140) -> str:
            compact = re.sub(r"\s+", " ", str(text or "")).strip()
            if len(compact) <= max_len:
                return compact
            return compact[: max_len - 1].rstrip() + "..."

        evidence_entries: List[Dict[str, str]] = []
        for module in key_modules[:10]:
            if not isinstance(module, dict):
                continue
            module_title = str(module.get("title") or "module").strip() or "module"
            module_summary = str(module.get("summary") or "").strip()
            if module_summary:
                evidence_entries.append(
                    {
                        "source": f"module {module_title}",
                        "path": "",
                        "text": module_summary,
                    }
                )

        for item in tagged_files_summaries[:24]:
            if not isinstance(item, dict):
                continue
            path = str(item.get("file_path") or "").strip()
            analysis = str(item.get("analysis") or "").strip()
            if not path or not analysis:
                continue
            if self._is_test_path(path) or self._is_generated_or_package_path(path) or self._is_non_implementation_path(path):
                continue
            evidence_entries.append(
                {
                    "source": path,
                    "path": path,
                    "text": analysis,
                }
            )

        category_keywords = {
            "code_quality": ["complex", "nested", "dense", "duplicate", "dead code", "long function", "refactor", "branch"],
            "modularity": ["coupling", "cross-module", "shared", "boundary", "layer", "service", "module", "separation"],
            "readability": ["readability", "naming", "clarity", "unclear", "verbose", "mixed concern", "implicit"],
            "test_coverage": ["test", "coverage", "assert", "integration", "unit", "mock", "regression"],
            "documentation": ["readme", "doc", "documentation", "comment", "guide", "usage", "onboarding"],
            "security": ["auth", "token", "permission", "sanitize", "validation", "secret", "encryption", "csrf", "xss", "sql"],
        }

        def _matches_category(entry: Dict[str, str], category: str) -> bool:
            haystack = f"{entry.get('source', '')} {entry.get('path', '')} {entry.get('text', '')}".lower()
            if category == "test_coverage":
                path = str(entry.get("path") or "").lower()
                if self._is_test_path(path):
                    return True
            if category == "documentation":
                path = str(entry.get("path") or "").lower()
                if any(marker in path for marker in ["readme", "/docs/", ".md", ".rst", ".txt"]):
                    return True
            return any(keyword in haystack for keyword in category_keywords.get(category, []))

        def _build_evidence_weakness(category: str, entry: Dict[str, str]) -> str:
            source = entry.get("source") or "a key area"
            snippet = _compact_text(entry.get("text") or "")
            templates = {
                "code_quality": f"{source} shows dense implementation details ({snippet}), which may increase maintenance overhead.",
                "modularity": f"{source} indicates responsibilities that appear tightly grouped ({snippet}), reducing modular flexibility.",
                "readability": f"{source} contains logic that may be harder to parse quickly ({snippet}), which can slow future iteration.",
                "test_coverage": f"Signals around {source} suggest verification depth may be uneven ({snippet}).",
                "documentation": f"Developer-facing documentation signals in {source} appear limited or uneven ({snippet}).",
                "security": f"{source} includes boundary-sensitive behavior ({snippet}) where stronger security hardening may be needed.",
            }
            return templates.get(category, f"{source} reveals a potential engineering gap ({snippet}).")

        def _build_evidence_improvement(category: str, entry: Dict[str, str]) -> str:
            source = entry.get("source") or "key modules"
            templates = {
                "code_quality": f"Refactor the heaviest paths in {source} into smaller units and add targeted quality checks around complex branches.",
                "modularity": f"Split cross-cutting concerns observed in {source} into clearer module boundaries to reduce coupling.",
                "readability": f"Improve naming and flow clarity in {source} so key behavior is easier to understand at a glance.",
                "test_coverage": f"Add focused behavioral tests around the most integration-critical paths surfaced in {source}.",
                "documentation": f"Add concise module-level documentation for {source}, especially setup, contracts, and expected behavior.",
                "security": f"Strengthen validation and authorization checks at the boundaries highlighted by {source}.",
            }
            return templates.get(category, f"Apply a focused improvement pass in {source} based on the observed implementation signals.")

        def _infer_theme_from_text(text: str) -> str:
            haystack = str(text or "").lower()
            if not haystack:
                return ""

            best_category = ""
            best_score = 0
            for category, keywords in category_keywords.items():
                score = sum(1 for keyword in keywords if keyword in haystack)
                if score > best_score:
                    best_score = score
                    best_category = category
            return best_category

        raw_weaknesses = insights.get("weaknesses") if isinstance(insights.get("weaknesses"), list) else []
        raw_improvements = insights.get("improvements") if isinstance(insights.get("improvements"), list) else []

        weaknesses: List[Dict[str, Any]] = []
        weakness_themes: set[str] = set()
        for item in raw_weaknesses:
            if not isinstance(item, dict):
                continue
            text = str(item.get("text") or "").strip()
            if not text:
                continue
            if any(self._text_overlap_ratio(text, existing.get("text", "")) >= 0.68 for existing in weaknesses):
                continue
            weaknesses.append({"text": text, "confidence": self._safe_float(item.get("confidence"), 0.68)})
            theme = _infer_theme_from_text(text)
            if theme:
                weakness_themes.add(theme)

        improvements: List[Dict[str, Any]] = []
        improvement_themes: set[str] = set()
        for item in raw_improvements:
            if not isinstance(item, dict):
                continue
            text = str(item.get("text") or "").strip()
            if not text:
                continue
            theme = _infer_theme_from_text(text)
            # Keep improvements action-oriented and distinct from weaknesses.
            if any(self._text_overlap_ratio(text, weakness.get("text", "")) >= 0.45 for weakness in weaknesses):
                continue
            if any(self._text_overlap_ratio(text, existing.get("text", "")) >= 0.68 for existing in improvements):
                continue
            if theme and theme in improvement_themes:
                continue
            # Keep at least one improvement on a different topic than identified weaknesses.
            if theme and theme in weakness_themes and len(improvements) >= 1:
                continue
            improvements.append({"text": text, "confidence": self._safe_float(item.get("confidence"), 0.7)})
            if theme:
                improvement_themes.add(theme)

        score_priority = sorted(
            [
                ("code_quality", "Refactor high-complexity paths into smaller composable units and tighten static quality checks."),
                ("modularity", "Separate cross-cutting concerns into dedicated modules to reduce coupling between features."),
                ("readability", "Standardize naming and function boundaries so intent is immediately clear in core flows."),
                ("test_coverage", "Target behavioral tests for integration-critical flows rather than broad generic coverage."),
                ("documentation", "Add concise developer-oriented docs for setup, module contracts, and key workflows."),
                ("security", "Introduce stricter input validation and explicit authorization checks at high-risk boundaries."),
            ],
            key=lambda entry: scores.get(entry[0], 50),
        )

        # Prefer project-specific evidence-derived fallbacks before generic templates.
        for category, _ in score_priority:
            if len(weaknesses) >= 2 and len(improvements) >= 2:
                break
            evidence = next((entry for entry in evidence_entries if _matches_category(entry, category)), None)
            if evidence is None:
                continue

            if len(weaknesses) < 2:
                weakness_text = _build_evidence_weakness(category, evidence)
                if not any(self._text_overlap_ratio(weakness_text, existing.get("text", "")) >= 0.65 for existing in weaknesses):
                    weaknesses.append({"text": weakness_text, "confidence": 0.71})

            if len(improvements) < 2:
                improvement_text = _build_evidence_improvement(category, evidence)
                if any(self._text_overlap_ratio(improvement_text, weakness.get("text", "")) >= 0.45 for weakness in weaknesses):
                    continue
                if any(self._text_overlap_ratio(improvement_text, existing.get("text", "")) >= 0.6 for existing in improvements):
                    continue
                if category in improvement_themes:
                    continue
                if category in weakness_themes and len(improvements) >= 1:
                    continue
                improvements.append({"text": improvement_text, "confidence": 0.73})
                improvement_themes.add(category)

        # Use generic score-based templates only if evidence-derived fallbacks are still insufficient.
        for key, improvement_text in score_priority:
            if len(improvements) >= 2:
                break
            if any(self._text_overlap_ratio(improvement_text, weakness.get("text", "")) >= 0.4 for weakness in weaknesses):
                continue
            if any(self._text_overlap_ratio(improvement_text, existing.get("text", "")) >= 0.6 for existing in improvements):
                continue
            if key in improvement_themes:
                continue
            if key in weakness_themes and len(improvements) >= 1:
                continue
            improvements.append({"text": improvement_text, "confidence": 0.72})
            improvement_themes.add(key)

        weakness_templates = [
            ("code_quality", "Some core implementation paths are still too dense, which increases maintenance risk over time."),
            ("modularity", "A few responsibilities remain tightly coupled, limiting flexibility when features evolve."),
            ("readability", "Important behavior is occasionally hidden in large blocks, reducing day-to-day readability."),
            ("test_coverage", "Critical integration paths do not appear to be uniformly validated with focused tests."),
            ("documentation", "Developer-facing documentation appears uneven across setup and module-level expectations."),
            ("security", "Security hardening signals exist, but protection depth is not uniform across all boundaries."),
        ]
        weakness_templates = sorted(weakness_templates, key=lambda entry: scores.get(entry[0], 50))
        for _, weakness_text in weakness_templates:
            if len(weaknesses) >= 2:
                break
            if any(self._text_overlap_ratio(weakness_text, existing.get("text", "")) >= 0.65 for existing in weaknesses):
                continue
            weaknesses.append({"text": weakness_text, "confidence": 0.68})

        surprise = insights.get("surprising_observation") if isinstance(insights.get("surprising_observation"), dict) else None
        if not isinstance(surprise, dict) or not str(surprise.get("text") or "").strip():
            surprise = {
                "text": "Despite uneven maturity across areas, the project shows clear engineering intent and a coherent implementation direction.",
                "confidence": 0.66,
            }

        return {
            "weaknesses": weaknesses[:2],
            "improvements": improvements[:2],
            "surprising_observation": {
                "text": str(surprise.get("text") or ""),
                "confidence": self._safe_float(surprise.get("confidence"), 0.66),
            },
        }

    def _normalize_security_and_vulnerability(
        self,
        payload_security: Any,
        key_modules: Optional[List[Dict[str, Any]]] = None,
        tagged_files_summaries: Optional[List[Dict[str, str]]] = None,
        insights: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        key_modules = key_modules if isinstance(key_modules, list) else []
        tagged_files_summaries = tagged_files_summaries if isinstance(tagged_files_summaries, list) else []
        insights = insights if isinstance(insights, dict) else {}

        def _compact_text(text: str, max_len: int = 140) -> str:
            compact = re.sub(r"\s+", " ", str(text or "")).strip()
            if len(compact) <= max_len:
                return compact
            return compact[: max_len - 1].rstrip() + "..."

        security_keywords = [
            "auth", "token", "permission", "sanitize", "validation", "secret", "encryption",
            "csrf", "xss", "sql", "credential", "oauth", "jwt", "session", "injection",
            "cve", "vulnerability", "security",
        ]

        findings_raw: List[Any] = []
        if isinstance(payload_security, dict):
            if isinstance(payload_security.get("findings"), list):
                findings_raw = payload_security.get("findings") or []
            elif isinstance(payload_security.get("items"), list):
                findings_raw = payload_security.get("items") or []
        elif isinstance(payload_security, list):
            findings_raw = payload_security

        findings: List[Dict[str, Any]] = []
        for item in findings_raw:
            text = ""
            confidence = 0.68
            if isinstance(item, dict):
                text = str(item.get("text") or "").strip()
                confidence = self._safe_float(item.get("confidence"), 0.68)
            elif isinstance(item, str):
                text = item.strip()
            if not text:
                continue
            if any(self._text_overlap_ratio(text, existing.get("text", "")) >= 0.68 for existing in findings):
                continue
            findings.append({"text": text, "confidence": confidence})
            if len(findings) >= 2:
                break

        evidence_entries: List[Dict[str, str]] = []
        for module in key_modules[:8]:
            if not isinstance(module, dict):
                continue
            module_title = str(module.get("title") or "module").strip() or "module"
            module_summary = str(module.get("summary") or "").strip()
            if module_summary:
                evidence_entries.append({
                    "source": f"module {module_title}",
                    "text": module_summary,
                })

        for item in tagged_files_summaries[:24]:
            if not isinstance(item, dict):
                continue
            path = str(item.get("file_path") or "").strip()
            analysis = str(item.get("analysis") or "").strip()
            if not path or not analysis:
                continue
            if self._is_test_path(path) or self._is_generated_or_package_path(path) or self._is_non_implementation_path(path):
                continue
            evidence_entries.append({
                "source": path,
                "text": analysis,
            })

        security_evidence = [
            entry for entry in evidence_entries
            if any(keyword in f"{entry.get('source', '')} {entry.get('text', '')}".lower() for keyword in security_keywords)
        ]

        for entry in security_evidence:
            if len(findings) >= 2:
                break
            source = entry.get("source") or "key modules"
            snippet = _compact_text(entry.get("text") or "")
            text = (
                f"{source} includes security-sensitive behavior ({snippet}); verify input validation, "
                "authorization checks, and boundary hardening are consistently enforced."
            )
            if any(self._text_overlap_ratio(text, existing.get("text", "")) >= 0.62 for existing in findings):
                continue
            findings.append({"text": text, "confidence": 0.72})

        insight_texts: List[str] = []
        for group_name in ("weaknesses", "improvements"):
            group_items = insights.get(group_name) if isinstance(insights.get(group_name), list) else []
            for item in group_items:
                if isinstance(item, dict):
                    text = str(item.get("text") or "").strip()
                    if text and any(keyword in text.lower() for keyword in security_keywords):
                        insight_texts.append(text)

        for text in insight_texts:
            if len(findings) >= 2:
                break
            candidate = f"Security implication from broader analysis: {_compact_text(text)}"
            if any(self._text_overlap_ratio(candidate, existing.get("text", "")) >= 0.62 for existing in findings):
                continue
            findings.append({"text": candidate, "confidence": 0.67})

        fallback_templates = [
            "No explicit critical vulnerability was confirmed from sampled files, but externally reachable handlers should be reviewed for consistent input validation and authorization enforcement.",
            "Dependency and secret-management risk remains possible in large codebases; run SCA/secret scans and patch vulnerable packages as part of routine security hardening.",
        ]
        for fallback_text in fallback_templates:
            if len(findings) >= 2:
                break
            if any(self._text_overlap_ratio(fallback_text, existing.get("text", "")) >= 0.62 for existing in findings):
                continue
            findings.append({"text": fallback_text, "confidence": 0.64})

        return {
            "findings": findings[:2],
        }

    def _build_technical_highlights(
        self,
        local_analysis: Dict[str, Any],
        architecture: Dict[str, Any],
        key_modules: List[Dict[str, Any]],
        tagged_files_summaries: List[Dict[str, str]],
        overview: Optional[Dict[str, Any]] = None,
        insights: Optional[Dict[str, Any]] = None,
        payload_tech: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        overview_context = overview if isinstance(overview, dict) else {}
        insights = insights if isinstance(insights, dict) else {}
        payload_tech = payload_tech if isinstance(payload_tech, dict) else {}
        technologies = payload_tech.get("technologies") if isinstance(payload_tech.get("technologies"), list) else []
        patterns = payload_tech.get("patterns") if isinstance(payload_tech.get("patterns"), list) else []
        highlights = payload_tech.get("highlights") if isinstance(payload_tech.get("highlights"), list) else []

        language_names = self._extract_language_names(local_analysis)
        if not technologies:
            technologies = [
                {
                    "name": name,
                    "usage": "Used in core implementation paths and module-level business logic.",
                }
                for name in language_names[:5]
            ]

        if not patterns:
            text_blob = " ".join(
                str(item.get("analysis", "")).lower()
                for item in tagged_files_summaries
                if isinstance(item, dict)
            )
            pattern_signals = [
                (("async", "await", "queue", "worker", "background"), "Asynchronous processing"),
                (("middleware", "pipeline", "interceptor"), "Middleware pipeline"),
                (("dependency injection", "inject", "provider"), "Dependency injection"),
                (("repository", "data access", "dao"), "Repository abstraction"),
                (("event", "pubsub", "message"), "Event-driven integration"),
                (("state", "store", "reducer"), "State management"),
                (("validation", "schema", "contract"), "Contract-based validation"),
            ]
            detected_patterns: List[str] = []
            for keywords, label in pattern_signals:
                if any(keyword in text_blob for keyword in keywords):
                    detected_patterns.append(label)
            if len(key_modules) >= 3 and "Modular decomposition" not in detected_patterns:
                detected_patterns.append("Modular decomposition")
            arch_patterns = architecture.get("patterns") if isinstance(architecture.get("patterns"), list) else []
            for item in arch_patterns:
                pattern_name = str(item).strip()
                if pattern_name and pattern_name not in detected_patterns:
                    detected_patterns.append(pattern_name)
            patterns = detected_patterns[:6]

        if not highlights:
            text_blob = " ".join(
                str(item.get("analysis", "")).lower()
                for item in tagged_files_summaries
                if isinstance(item, dict)
            )

            generated: List[str] = []
            if technologies:
                primary = technologies[0]
                generated.append(
                    f"The implementation is anchored in {primary.get('name', 'the primary stack')} for core project workflows."
                )
            if "api" in text_blob or "endpoint" in text_blob:
                generated.append("API-oriented flows are implemented with clear separation between request handling and business logic.")
            if "async" in text_blob or "queue" in text_blob or "worker" in text_blob:
                generated.append("Asynchronous execution patterns are used to keep long-running tasks isolated from interactive flows.")
            if patterns:
                generated.append("Recurring coding patterns include " + ", ".join(patterns[:3]) + ".")
            generated.append("Technical choices generally prioritize maintainability by combining framework conventions with explicit module boundaries.")
            highlights = generated[:5]

        overview_text = payload_tech.get("overview")
        if not overview_text:
            overview_text = (
                "Technical highlights focus on how the stack is applied in code, "
                "which implementation patterns recur, and where the strongest engineering decisions appear."
            )

        normalized_technologies = []
        for item in technologies:
            if not isinstance(item, dict):
                continue
            name = str(item.get("name") or "").strip()
            usage = str(item.get("usage") or "").strip()
            if name and usage:
                normalized_technologies.append({"name": name, "usage": usage})

        normalized_patterns = [str(item).strip() for item in patterns if str(item).strip()][:6]

        reference_texts: List[str] = []
        for candidate in [overview_context.get("summary"), architecture.get("summary")]:
            text = str(candidate or "").strip()
            if text:
                reference_texts.append(text)
        for module in key_modules:
            if not isinstance(module, dict):
                continue
            summary_text = str(module.get("summary") or "").strip()
            title_text = str(module.get("title") or "").strip()
            if summary_text:
                reference_texts.append(summary_text)
            if title_text:
                reference_texts.append(title_text)
        for group_name in ("weaknesses", "improvements"):
            group_items = insights.get(group_name) if isinstance(insights.get(group_name), list) else []
            for item in group_items:
                if isinstance(item, dict):
                    text = str(item.get("text") or "").strip()
                    if text:
                        reference_texts.append(text)

        normalized_highlights: List[str] = []
        for item in highlights:
            text = str(item).strip()
            if not text:
                continue
            if any(self._text_overlap_ratio(text, existing) >= 0.68 for existing in normalized_highlights):
                continue
            if any(self._text_overlap_ratio(text, reference) >= 0.46 for reference in reference_texts):
                continue
            normalized_highlights.append(text)
            if len(normalized_highlights) >= 5:
                break

        if len(normalized_highlights) < 3:
            fallback_highlights: List[str] = []
            if normalized_technologies:
                for tech in normalized_technologies[:3]:
                    fallback_highlights.append(
                        f"{tech['name']} is applied in a targeted way: {tech['usage']}"
                    )
            if normalized_patterns:
                fallback_highlights.append("Observed implementation patterns include " + ", ".join(normalized_patterns[:3]) + ".")
            for item in fallback_highlights:
                if any(self._text_overlap_ratio(item, existing) >= 0.68 for existing in normalized_highlights):
                    continue
                normalized_highlights.append(item)
                if len(normalized_highlights) >= 5:
                    break

        return {
            "overview": str(overview_text).strip(),
            "technologies": normalized_technologies,
            "patterns": normalized_patterns,
            "highlights": normalized_highlights,
        }

    def _normalize_structured_report(
        self,
        payload: Dict[str, Any],
        local_analysis: Dict[str, Any],
        tagged_files_summaries: List[Dict[str, str]],
    ) -> Dict[str, Any]:
        if not isinstance(payload, dict):
            payload = {}

        payload.pop("issues_and_risks", None)

        overview = payload.get("overview") if isinstance(payload.get("overview"), dict) else {}
        architecture_payload = payload.get("architecture") if isinstance(payload.get("architecture"), dict) else {}
        technical_highlights_payload = payload.get("technical_highlights") if isinstance(payload.get("technical_highlights"), dict) else {}
        insights = payload.get("insights") if isinstance(payload.get("insights"), dict) else {}
        security_payload = payload.get("security_and_vulnerability")

        key_modules_raw = payload.get("key_modules") if isinstance(payload.get("key_modules"), list) else []
        key_modules: List[Dict[str, Any]] = []
        for module in key_modules_raw:
            if not isinstance(module, dict):
                continue
            key_files = module.get("key_files") if isinstance(module.get("key_files"), list) else []
            filtered_files = [
                str(path)
                for path in key_files
                if path
                and not self._is_test_path(str(path))
                and not self._is_generated_or_package_path(str(path))
                and not self._is_non_implementation_path(str(path))
            ]
            key_modules.append(
                {
                    "title": module.get("title"),
                    "summary": module.get("summary"),
                    "key_files": filtered_files,
                    "issues": module.get("issues") if isinstance(module.get("issues"), list) else [],
                }
            )

        architecture = self._normalize_llm_architecture(architecture_payload, tagged_files_summaries)
        project_scores = self._normalize_llm_project_scores(payload.get("project_scores"))
        overview["project_type"] = self._normalize_project_type(
            project_type_raw=str(overview.get("project_type") or ""),
            local_analysis=local_analysis,
            architecture=architecture,
        )
        insights = self._normalize_insights(
            insights,
            project_scores,
            key_modules=key_modules,
            tagged_files_summaries=tagged_files_summaries,
        )
        security_and_vulnerability = self._normalize_security_and_vulnerability(
            payload_security=security_payload,
            key_modules=key_modules,
            tagged_files_summaries=tagged_files_summaries,
            insights=insights,
        )
        technical_highlights = self._build_technical_highlights(
            local_analysis=local_analysis,
            architecture=architecture,
            key_modules=key_modules,
            tagged_files_summaries=tagged_files_summaries,
            overview=overview,
            insights=insights,
            payload_tech=technical_highlights_payload,
        )

        if not overview.get("summary"):
            overview["summary"] = "This project contains meaningful implementation depth across core modules and demonstrates practical software engineering patterns."

        return {
            "overview": overview,
            "technical_highlights": technical_highlights,
            "architecture": architecture,
            "key_modules": key_modules,
            "insights": insights,
            "security_and_vulnerability": security_and_vulnerability,
            "project_scores": project_scores,
            "analysis": payload.get("analysis") or overview.get("summary") or "Structured AI analysis generated.",
        }
    
    def analyze_project(
        self,
        local_analysis: Dict[str, Any],
        tagged_files_summaries: List[Dict[str, str]],
        media_briefings: Optional[List[str]] = None,
        project_context: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Generate a comprehensive structured JSON project report.
        
        Returns a dict with structured sections: overview, technical_highlights, architecture,
        key_modules, insights, and project_scores.
        """
        if not self.is_configured():
            raise LLMError("LLM client is not configured")
        
        try:
            files_info = "\n\n".join([
                f"File: {f.get('file_path', 'Unknown')}\n{f.get('analysis', '')}"
                for f in tagged_files_summaries
            ])

            media_context = ""
            if media_briefings:
                media_lines = "\n".join(f"- {entry}" for entry in media_briefings)
                media_context = f"\nMEDIA ASSETS (images/audio/video):\n{media_lines}\n"

            context_section = ""
            if project_context:
                context_section = f"\nACCUMULATED PROJECT CONTEXT:\n{project_context}\n"

            prompt = f"""You are analyzing a software project to produce a structured, data-driven report.

LOCAL ANALYSIS RESULTS:
{local_analysis}

IMPORTANT FILES ANALYSIS:
{files_info if files_info else 'No tagged files provided'}{media_context}{context_section}

Return a single JSON object with EXACTLY these keys. Return ONLY valid JSON, no markdown fences.

{{
  "overview": {{
    "summary": "3-5 sentence portfolio-ready overview of the project",
    "tech_stack": ["language/framework names detected"],
        "project_type": "specific type inferred from evidence (e.g. Backend service, Frontend application, CLI/automation project, Library)"
  }},
  "architecture": {{
    "summary": "2-3 sentence description of how the codebase is organized",
    "patterns": ["architectural patterns detected, e.g. MVC, microservices"],
    "diagram": {{
      "nodes": [
        {{"id": "unique_id", "label": "Human-readable name", "type": "ui|service|database|library|external"}}
      ],
      "edges": [
        {{"from": "source_id", "to": "target_id", "label": "relationship description"}}
      ]
    }}
  }},
    "technical_highlights": {{
        "overview": "2-3 sentence technical analysis focused on implementation",
        "technologies": [
            {{"name": "Technology name", "usage": "How it is used in the project"}}
        ],
        "patterns": ["coding patterns used in implementation"],
        "highlights": ["3-5 concise technical observations"]
    }},
  "key_modules": [
    {{
      "title": "Module name",
      "summary": "What this module does",
      "key_files": ["path/to/file.py"],
      "issues": ["any issues found in this module"]
    }}
  ],
  "insights": {{
    "weaknesses": [
      {{"text": "Weakness description", "confidence": 0.88}},
      {{"text": "Weakness description", "confidence": 0.82}}
    ],
    "improvements": [
      {{"text": "Improvement suggestion", "confidence": 0.92}},
      {{"text": "Improvement suggestion", "confidence": 0.85}}
    ],
    "surprising_observation": {{
      "text": "Something unexpected or noteworthy about this codebase",
      "confidence": 0.78
    }}
  }},
    "security_and_vulnerability": {{
        "findings": [
            {{"text": "Security concern or potential vulnerability", "confidence": 0.73}},
            {{"text": "Security concern or potential vulnerability", "confidence": 0.68}}
        ]
    }},
  "project_scores": {{
        "overall": 0,
        "code_quality": 0,
        "modularity": 0,
        "readability": 0,
        "test_coverage": 0,
        "documentation": 0,
        "security": 0
    }}
}}

Rules:
- All scores are integers 0-100.
- confidence values are floats 0.0-1.0.
- Provide exactly 2 weaknesses, 2 improvements, and 1 surprising observation.
- Provide exactly 2 security_and_vulnerability.findings.
- Include 2-5 key_modules.
- Keep technical_highlights focused on technology usage and coding patterns.
- Do not repeat architecture summaries or insights text in technical_highlights.
- In insights, weaknesses must describe current gaps; improvements must be distinct action-oriented recommendations, not paraphrases of weaknesses.
- Ensure weaknesses and improvements are topic-distinct: improvements should focus on actionable next steps on at least one theme not used by weaknesses when evidence allows.
- security_and_vulnerability findings must be security-focused, concrete, and distinct (no duplicates/rephrases).
- Architecture diagram must be your inferred architecture from all evidence, with 2-8 meaningful components and explicit relationship labels.
- Only list implementation files in key_modules.key_files; do not include test/spec files, generated/build output folders (e.g. .next, .electron, .cache), or package dependency directories (e.g. node_modules, vendor, site-packages).
- project_scores must be your qualitative judgment from pooled evidence (not static defaults), represented as integers 0-100.
- Do not default project_type to "Full-stack" unless there is direct evidence of both UI and backend/service layers.
- If there is not enough information for a section, provide a conservative inference with lower confidence.
- Return ONLY valid JSON."""

            messages = [{"role": "user", "content": prompt}]
            response = self._make_llm_call(
                messages,
                max_tokens=3000,
                temperature=0.6,
                response_format={"type": "json_object"},
            )

            try:
                result = json.loads(response)
            except json.JSONDecodeError:
                self.logger.warning("Failed to parse structured JSON from analyze_project; falling back to text")
                result = {"analysis": response}

            normalized_result = self._normalize_structured_report(
                payload=result,
                local_analysis=local_analysis,
                tagged_files_summaries=tagged_files_summaries,
            )
            if "analysis" not in normalized_result:
                normalized_result["analysis"] = response
            return normalized_result
            
        except Exception as e:
            self.logger.error(f"Project analysis failed: {e}")
            raise LLMError(f"Failed to analyze project: {str(e)}")
    
    def suggest_feedback(self, local_analysis: Dict[str, Any],
                        llm_analysis: Dict[str, Any],
                        career_goal: str) -> Dict[str, str]:
        """
        Generate personalized, actionable recommendations for entire portfolio
        improvements and career development.
        
        Args:
            local_analysis: Local analysis results for the entire portfolio
            llm_analysis: LLM analysis results for the entire portfolio
            career_goal: User's career goal (e.g., "frontend developer")
            
        Returns:
            Formatted text output containing:
                - portfolio_overview: Overall assessment with strengths and improvements
                - specific_recommendations: Portfolio structuring, new projects, and existing project enhancements
                - career_alignment_analysis: Market-aligned analysis of portfolio fit for career goal
                
        Raises:
            LLMError: If feedback generation fails
        """
        if not self.is_configured():
            raise LLMError("LLM client is not configured")
        
        try:
            prompt = f"""You are an experienced senior software engineer and career mentor. Provide personalized feedback for a developer based on their entire portfolio.

            CAREER GOAL: {career_goal}

            LOCAL ANALYSIS RESULTS:
            {local_analysis}

            LLM ANALYSIS RESULTS:
            {llm_analysis}

            Provide actionable feedback in the following format:

            PORTFOLIO OVERVIEW:
            [Provide an overall assessment of the portfolio's current state, highlighting strengths and areas for improvement. Include specific suggestions on current industry trends, best practices, and features that would make the portfolio more impressive and professional.]

            SPECIFIC RECOMMENDATIONS:
            - Portfolio Structuring: [Advice on how to organize, present, and document the portfolio effectively]
            - New Projects to Build: [Specific project ideas that would complement the existing portfolio and align with the career goal]
            - Existing Project Enhancements: [Actionable suggestions for improving or building upon current projects - new features, refactoring, testing, deployment, etc.]

            CAREER ALIGNMENT ANALYSIS:
            [Analyze how well the portfolio aligns with the career goal in the context of current market trends and industry requirements for {career_goal} positions. 
            Address: what skills are demonstrated, what's missing based on current job market demands, what technologies or practices are trending in this field, and 
            what specific steps to take next to be competitive in today's job market]"""

            messages = [{"role": "user", "content": prompt}]
            response = self._make_llm_call(messages, max_tokens=800, temperature=0.7)
            
            return {
                "career_goal": career_goal,
                "feedback": response
            }
            
        except Exception as e:
            self.logger.error(f"Feedback generation failed: {e}")
            raise LLMError(f"Failed to generate feedback: {str(e)}")
    
    def _run_async_in_thread(
        self,
        coro,
        heartbeat_callback: Optional[Any] = None,
        heartbeat_interval_sec: int = 15,
    ):
        """Run an async coroutine in a dedicated thread with its own event loop.
        
        This prevents conflicts with existing event loops and is safe to call
        from synchronous code.
        
        Args:
            coro: The coroutine to run
            
        Returns:
            The result of the coroutine
        """
        result = None
        exception = None
        
        def run_in_thread():
            nonlocal result, exception
            try:
                # Create a new event loop for this thread
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    result = loop.run_until_complete(coro)
                finally:
                    loop.close()
            except Exception as e:
                exception = e
        
        thread = threading.Thread(target=run_in_thread)
        thread.start()

        heartbeat_every = max(1, int(heartbeat_interval_sec))
        while thread.is_alive():
            thread.join(timeout=heartbeat_every)
            if thread.is_alive() and callable(heartbeat_callback):
                try:
                    heartbeat_callback()
                except Exception:
                    # Best effort progress signal.
                    pass
        
        if exception:
            raise exception
        return result
    
    async def _summarize_file_batch(
        self,
        files_batch: List[tuple],
        base_path,
        per_file_timeout_sec: int = 120,
        skipped_files: Optional[List[Dict[str, Any]]] = None,
        project_context: Optional[str] = None,
    ) -> List[Dict[str, str]]:
        """Process a batch of files in parallel.
        
        Args:
            files_batch: List of (file_path, full_path, file_type, file_size) tuples
            base_path: Base path for file reading
            project_context: Optional rolling project context from prior batches
            
        Returns:
            List of file summary results
        """
        
        async def analyze_single_file(file_info):
            file_path, full_path, file_type, file_size = file_info
            try:
                content = full_path.read_text(encoding='utf-8', errors='ignore')

                # Compute lightweight metadata
                file_metadata = self._compute_file_metadata(content, file_path, file_type)

                # Run the synchronous summarize in thread pool
                loop = asyncio.get_event_loop()
                summary_result = await asyncio.wait_for(
                    loop.run_in_executor(
                        None,
                        lambda: self.summarize_tagged_file(
                            file_path,
                            content,
                            file_type,
                            file_metadata=file_metadata,
                            project_context=project_context,
                        ),
                    ),
                    timeout=per_file_timeout_sec,
                )
                self.logger.info(f"Summarized: {file_path}")
                return summary_result
            except asyncio.TimeoutError:
                self.logger.warning(
                    "Timed out summarizing %s after %ss",
                    file_path,
                    per_file_timeout_sec,
                )
                if skipped_files is not None:
                    skipped_files.append({
                        'path': file_path,
                        'size_mb': file_size / (1024 * 1024),
                        'reason': f'Summarization timed out after {per_file_timeout_sec}s',
                    })
                return None
            except Exception as e:
                self.logger.error(f"Error analyzing {file_path}: {e}")
                return None
        
        # Process batch in parallel
        results = await asyncio.gather(*[analyze_single_file(f) for f in files_batch])
        return [r for r in results if r is not None]
    
    def summarize_scan_with_ai(self, scan_summary: Dict[str, Any], 
                               relevant_files: List[Dict[str, Any]],
                               scan_base_path: str,
                               max_file_size_mb: int = 10,
                               project_dirs: Optional[List[str]] = None,
                               progress_callback: Optional[Any] = None,
                               include_media: bool = True) -> Dict[str, Any]:
        """
        Comprehensive AI analysis workflow for CLI integration.
        
        Args:
            scan_summary: Dict with file_count, total_size, language_breakdown, etc.
            relevant_files: List of file metadata dicts (path, size, mime_type, etc.)
            scan_base_path: Base path where original files are located for reading content
            max_file_size_mb: Maximum file size in MB to process (default: 10MB)
            project_dirs: Optional list of project directory paths (e.g., Git repo roots).
                         If provided, files are grouped by project and analyzed separately.
            progress_callback: Optional callback function for progress updates
            
        Returns:
            Dict containing:
                - project_analysis: Result from analyze_project() (single project mode)
                - projects: List of per-project analyses (multi-project mode)
                - file_summaries: List of results from summarize_tagged_file()
                - summary_text: Combined formatted output for display
                - skipped_files: List of files skipped due to size limits
                - media_briefings: Optional human-friendly summaries of media assets
                
        Raises:
            LLMError: If analysis fails
        """
        if not self.is_configured():
            raise LLMError("LLM client is not configured")
        
        try:
            from pathlib import Path
            
            self.logger.info("Starting LLM analysis")
            
            if progress_callback:
                progress_callback(f"Initializing analysis for {len(relevant_files)} files…")
            
            if project_dirs:
                self.logger.info(f"Multi-project mode: {len(project_dirs)} projects")
                if progress_callback:
                    progress_callback(f"Multi-project mode: analyzing {len(project_dirs)} projects…")
                return self._analyze_multiple_projects(
                    scan_summary=scan_summary,
                    relevant_files=relevant_files,
                    scan_base_path=scan_base_path,
                    project_dirs=project_dirs,
                    max_file_size_mb=max_file_size_mb,
                    progress_callback=progress_callback,
                    include_media=include_media,
                )

            media_briefings: list[str] = []
            if include_media:
                self.logger.info(f"Building media briefings for single-project mode (include_media=True)")
                media_briefings = self._build_media_briefings(
                    relevant_files, base_path=Path(scan_base_path) if scan_base_path else None
                )
            else:
                self.logger.info(f"Skipping media briefings for single-project mode (include_media=False)")
            
            max_file_size_bytes = max_file_size_mb * 1024 * 1024
            file_summaries = []
            skipped_files = []
            project_context_so_far = ""  # Rolling context across batches
            
            total_files = len(relevant_files)
            
            # Prepare files for batch processing
            files_to_analyze = []
            for file_meta in relevant_files:
                file_path = file_meta.get('path', '')
                if not file_path:
                    continue

                full_path = Path(scan_base_path) / file_path

                if full_path.exists() and full_path.is_file():
                    file_size = full_path.stat().st_size
                    if file_size > max_file_size_bytes:
                        self.logger.warning(f"Skipping large file ({file_size / (1024*1024):.2f}MB): {file_path}")
                        skipped_files.append({
                            'path': file_path,
                            'size_mb': file_size / (1024 * 1024),
                            'reason': f'Exceeds maximum file size limit of {max_file_size_mb}MB'
                        })
                        continue

                mime_type = file_meta.get('mime_type', '')
                if not (mime_type.startswith('text/') or 
                       mime_type in ['application/json', 'application/xml', 'application/javascript']):
                    self.logger.info(f"Skipping non-text file: {file_path}")
                    continue
                
                if full_path.exists() and full_path.is_file():
                    file_type = full_path.suffix or 'unknown'
                    files_to_analyze.append((file_path, full_path, file_type, file_size))
            
            batch_size = self._get_int_env(
                "AI_SINGLE_PROJECT_BATCH_SIZE",
                self.DEFAULT_SINGLE_PROJECT_BATCH_SIZE,
                minimum=1,
                maximum=8,
            )
            heartbeat_sec = self._get_int_env(
                "AI_BATCH_HEARTBEAT_SEC",
                self.DEFAULT_BATCH_HEARTBEAT_SEC,
                minimum=5,
                maximum=120,
            )
            per_file_timeout_sec = self._get_int_env(
                "AI_FILE_SUMMARY_TIMEOUT_SEC",
                self.DEFAULT_FILE_SUMMARY_TIMEOUT_SEC,
                minimum=20,
                maximum=900,
            )

            # Balance heavier files across batches and apply smart ranking.
            files_to_analyze.sort(key=lambda item: (
                1 if LLMClient._is_logic_heavy_candidate(item[0]) else 0,
                int(item[3])
            ), reverse=True)
            
            # Smart ranking: cap the logic to the top 80 most critical files
            if len(files_to_analyze) > 80:
                self.logger.info(f"Capping single-project file summarization to 80 files (was {len(files_to_analyze)})")
                for f in files_to_analyze[80:]:
                    skipped_files.append({
                        'path': f[0],
                        'size_mb': f[3] / (1024 * 1024),
                        'reason': 'Skipped by 80 file smart ranking cap'
                    })
                files_to_analyze = files_to_analyze[:80]
            total_batches = (len(files_to_analyze) + batch_size - 1) // batch_size
            balanced_batches: List[List[tuple]] = [[] for _ in range(total_batches)]
            batch_weight = [0] * total_batches
            for file_tuple in files_to_analyze:
                idx = min(
                    range(total_batches),
                    key=lambda i: (len(balanced_batches[i]), batch_weight[i]),
                )
                balanced_batches[idx].append(file_tuple)
                batch_weight[idx] += int(file_tuple[3])

            processed_count = 0
            
            for batch_num, batch in enumerate(balanced_batches, start=1):
                batch_size_mb = sum(int(item[3]) for item in batch) / (1024 * 1024)
                batch_started_at = time.monotonic()
                
                if progress_callback:
                    progress_callback(
                        f"Single-project: Batch {batch_num}/{total_batches} ({len(batch)} files, {batch_size_mb:.2f}MB)…"
                    )
                
                try:
                    # Process batch in parallel using dedicated thread
                    batch_results = self._run_async_in_thread(
                        self._summarize_file_batch(
                            batch,
                            scan_base_path,
                            per_file_timeout_sec=per_file_timeout_sec,
                            skipped_files=skipped_files,
                            project_context=project_context_so_far or None,
                        ),
                        heartbeat_interval_sec=heartbeat_sec,
                        heartbeat_callback=(
                            (lambda bn=batch_num, tb=total_batches, bs=batch_started_at:
                                progress_callback(
                                    f"Single-project: Batch {bn}/{tb} still running ({int(time.monotonic() - bs)}s elapsed)…"
                                )
                            ) if progress_callback else None
                        ),
                    )
                    file_summaries.extend(batch_results)
                    processed_count += len(batch_results)
                    
                    if progress_callback:
                        duration = int(time.monotonic() - batch_started_at)
                        progress_callback(
                            f"Single-project: Completed {processed_count}/{len(files_to_analyze)} files (batch {batch_num} in {duration}s)…"
                        )

                    # ── Removed rolling project context update per optimization plan ─────

                except Exception as e:
                    self.logger.error(f"Error processing batch: {e}")
                    continue
            
            if progress_callback:
                progress_callback("Generating project insights…")
            
            project_analysis = self.analyze_project(
                local_analysis=scan_summary,
                tagged_files_summaries=file_summaries,
                media_briefings=media_briefings if media_briefings else None,
                project_context=project_context_so_far or None,
            )
            
            result = {
                "project_analysis": project_analysis,
                "file_summaries": file_summaries,
                "files_analyzed_count": len(file_summaries),
                "local_analysis": scan_summary,
            }

            if media_briefings:
                result["media_briefings"] = media_briefings
            
            if skipped_files:
                result["skipped_files"] = skipped_files
                self.logger.info(f"Skipped {len(skipped_files)} files due to size limits")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Scan AI analysis failed: {e}")
            raise LLMError(f"Failed to analyze scan: {str(e)}")
    
    def _analyze_multiple_projects(self, scan_summary: Dict[str, Any],
                                   relevant_files: List[Dict[str, Any]],
                                   scan_base_path: str,
                                   project_dirs: List[str],
                                   max_file_size_mb: int = 10,
                                   progress_callback: Optional[Any] = None,
                                   include_media: bool = True) -> Dict[str, Any]:
        """
        Analyze multiple projects separately (e.g., multiple Git repos in one scan).
        
        Args:
            scan_summary: Global scan summary
            relevant_files: All files from scan
            scan_base_path: Base path for file reading
            project_dirs: List of project root directories (e.g., Git repo paths)
            max_file_size_mb: Max file size to process
            progress_callback: Optional callback for progress updates
            
        Returns:
            Dict with per-project analyses and overall summary
        """
        from pathlib import Path
        from datetime import datetime
        
        self.logger.info(f"Analyzing {len(project_dirs)} separate projects (include_media={include_media})")
        
        if progress_callback:
            progress_callback(f"Grouping files across {len(project_dirs)} projects…")
        
        max_file_size_bytes = max_file_size_mb * 1024 * 1024
        base_path = Path(scan_base_path)
        
        # Normalize project dirs to relative paths
        project_dirs_normalized = []
        for proj_dir in project_dirs:
            proj_path = Path(proj_dir)
            
            try:
                # Make paths relative to base_path
                rel_path = proj_path.relative_to(base_path)
                normalized = str(rel_path)
                project_dirs_normalized.append(normalized)
                self.logger.info(f"Normalized project path: {proj_dir} -> {normalized}")
            except ValueError:
                # Not relative to base_path, skip
                self.logger.warning(f"Project path {proj_dir} is not under base_path {base_path}, skipping")
                continue
        
        files_by_project = {proj: [] for proj in project_dirs_normalized}
        files_by_project['_unassigned'] = [] 
        
        self.logger.info(f"Starting file grouping. Projects: {project_dirs_normalized}")
        self.logger.info(f"Sample file paths (first 5): {[f.get('path', '') for f in relevant_files[:5]]}")
        
        import os
        debug_log_path = os.path.expanduser("~/.textual_ai_debug.log")
        try:
            with open(debug_log_path, "a") as f:
                timestamp = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
                f.write(f"{timestamp} | [LLM Client] Projects normalized: {project_dirs_normalized}\n")
                f.write(f"{timestamp} | [LLM Client] Sample files: {[f.get('path', '') for f in relevant_files[:5]]}\n")
                f.write(f"{timestamp} | [LLM Client] Total files to group: {len(relevant_files)}\n")
        except OSError:
            self.logger.debug("Unable to write debug log to %s; continuing without it.", debug_log_path)
        
        for file_meta in relevant_files:
            file_path = file_meta.get('path', '')
            if not file_path:
                continue
            
            assigned = False
            for proj_dir in project_dirs_normalized:
                # Special case: "." means this is the root project (project path == base path)
                # In this case, all files belong to this project
                if proj_dir == ".":
                    files_by_project[proj_dir].append(file_meta)
                    assigned = True
                    break
                # Check if file path starts with project directory
                elif file_path.startswith(proj_dir + '/') or file_path.startswith(proj_dir + '\\'):
                    files_by_project[proj_dir].append(file_meta)
                    assigned = True
                    break
            
            if not assigned:
                files_by_project['_unassigned'].append(file_meta)
        
        # Log file grouping results
        for proj_dir, proj_files in files_by_project.items():
            self.logger.info(f"Project '{proj_dir}': {len(proj_files)} files")
        
        try:
            with open(debug_log_path, "a") as f:
                timestamp = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
                for proj_dir, proj_files in files_by_project.items():
                    f.write(f"{timestamp} | [LLM Client] Project '{proj_dir}': {len(proj_files)} files\n")
        except OSError:
            self.logger.debug("Unable to append grouped file stats to %s; continuing.", debug_log_path)
        
        project_analyses = []
        all_file_summaries = []
        all_skipped_files = []
        unassigned_analysis = None  # Track unassigned files separately
        all_media_briefings: list[str] = []
        
        project_index = 0
        total_projects = len([p for p in files_by_project.keys() if p != '_unassigned' and files_by_project[p]])
        
        for proj_dir, proj_files in files_by_project.items():
            if proj_dir == '_unassigned':
                if not proj_files:
                    continue
                proj_name = "Unassigned Files"
            else:
                proj_name = Path(proj_dir).name or proj_dir
            
            if not proj_files:
                self.logger.info(f"Skipping empty project: {proj_name}")
                continue
            
            if proj_dir != '_unassigned':
                project_index += 1
                if progress_callback:
                    progress_callback(f"Multi-project [{project_index}/{total_projects}]: {proj_name}…")
            
            self.logger.info(f"Analyzing project '{proj_name}' ({len(proj_files)} files)")
            
            # Prepare files for batch processing
            media_briefings: list[str] = []
            if include_media:
                media_briefings = self._build_media_briefings(
                    proj_files, base_path=base_path
                )
            file_summaries = []
            skipped_files = []
            files_to_analyze = []
            
            for file_meta in proj_files:
                file_path = file_meta.get('path', '')
                full_path = base_path / file_path
                
                if not full_path.exists() or not full_path.is_file():
                    self.logger.warning(f"File not found: {full_path}")
                    continue
                
                file_size = full_path.stat().st_size
                if file_size > max_file_size_bytes:
                    skipped_files.append({
                        'path': file_path,
                        'size_mb': file_size / (1024 * 1024),
                        'reason': f'Exceeds {max_file_size_mb}MB limit'
                    })
                    continue
                
                # Skip lock files and other non-essential files
                if any(skip in file_path.lower() for skip in ['package-lock.json', 'yarn.lock', 'poetry.lock', '.lock']):
                    self.logger.info(f"[{proj_name}] Skipping lock file: {file_path}")
                    continue
                
                mime_type = file_meta.get('mime_type', '')
                if not (mime_type.startswith('text/') or 
                       mime_type in ['application/json', 'application/xml', 'application/javascript']):
                    continue
                
                file_type = full_path.suffix or 'unknown'
                files_to_analyze.append((file_path, full_path, file_type))
            
            # Apply smart ranking and cap before processing
            files_to_analyze.sort(key=lambda item: (
                1 if LLMClient._is_logic_heavy_candidate(item[0]) else 0,
                0
            ), reverse=True)
            
            if len(files_to_analyze) > 80:
                self.logger.info(f"Capping multi-project file summarization to 80 files (was {len(files_to_analyze)})")
                for f in files_to_analyze[80:]:
                    skipped_files.append({
                        'path': f[0],
                        'size_mb': 0.0,
                        'reason': 'Skipped by 80 file smart ranking cap'
                    })
                files_to_analyze = files_to_analyze[:80]
                
            # Process files in batches for parallel execution
            BATCH_SIZE = 10
            processed_count = 0
            
            for i in range(0, len(files_to_analyze), BATCH_SIZE):
                batch = files_to_analyze[i:i + BATCH_SIZE]
                batch_num = (i // BATCH_SIZE) + 1
                total_batches = (len(files_to_analyze) + BATCH_SIZE - 1) // BATCH_SIZE
                
                if progress_callback:
                    if proj_dir != '_unassigned':
                        progress_callback(f"Project {project_index}/{total_projects} - Batch {batch_num}/{total_batches} ({len(batch)} files)…")
                    else:
                        progress_callback(f"[{proj_name}] Batch {batch_num}/{total_batches} ({len(batch)} files)…")
                
                try:
                    # Process batch in parallel using dedicated thread
                    batch_results = self._run_async_in_thread(
                        self._summarize_file_batch(batch, base_path)
                    )
                    file_summaries.extend(batch_results)
                    processed_count += len(batch_results)
                    
                    if progress_callback:
                        progress_callback(f"[{proj_name}] Completed {processed_count}/{len(files_to_analyze)} files…")
                except Exception as e:
                    self.logger.error(f"[{proj_name}] Error processing batch: {e}")
                    continue
            
            project_summary = {
                "project_name": proj_name,
                "project_path": proj_dir,
                "total_files": len(proj_files),
                "files_analyzed": len(file_summaries),
                "total_size_bytes": sum(f.get('size', 0) for f in proj_files)
            }
            
            if file_summaries or media_briefings:
                project_analysis = self.analyze_project(
                    local_analysis=project_summary,
                    tagged_files_summaries=file_summaries,
                    media_briefings=media_briefings if media_briefings else None,
                )
                
                analysis_result = {
                    "project_name": proj_name,
                    "project_path": proj_dir,
                    "file_count": len(proj_files),
                    "files_analyzed": len(file_summaries),
                    "analysis": project_analysis.get("analysis", ""),
                    "file_summaries": file_summaries,
                }
                if media_briefings:
                    analysis_result["media_briefings"] = media_briefings
                
                if proj_dir == '_unassigned':
                    unassigned_analysis = analysis_result
                    self.logger.info(f"Stored unassigned files analysis separately (not counted as project)")
                else:
                    project_analyses.append(analysis_result)
            
            all_file_summaries.extend(file_summaries)
            all_skipped_files.extend(skipped_files)
            if media_briefings:
                all_media_briefings.extend(media_briefings)
        
        portfolio_summary = None
        if len(project_analyses) > 1:
            portfolio_summary = self._generate_portfolio_summary(
                project_analyses, 
                unassigned_analysis=unassigned_analysis
            )
        
        result = {
            "mode": "multi_project",
            "projects": project_analyses,
            "project_count": len(project_analyses),
            "total_files_analyzed": len(all_file_summaries),
            "file_summaries": all_file_summaries,
            "files_analyzed_count": len(all_file_summaries)
        }
        
        if portfolio_summary:
            result["portfolio_summary"] = portfolio_summary
        
        # Include unassigned files as additional context (not a project)
        if unassigned_analysis:
            result["unassigned_files"] = unassigned_analysis
        
        if all_skipped_files:
            result["skipped_files"] = all_skipped_files
            self.logger.info(f"Skipped {len(all_skipped_files)} files across all projects")

        if all_media_briefings:
            capped_media = all_media_briefings[:12]
            if len(all_media_briefings) > 12:
                capped_media.append(f"...and {len(all_media_briefings) - 12} more media file(s) detected.")
            result["media_briefings"] = capped_media
        
        return result
    
    def _generate_portfolio_summary(self, project_analyses: List[Dict[str, Any]], 
                                    unassigned_analysis: Optional[Dict[str, Any]] = None) -> Dict[str, str]:
        """
        Generate a high-level portfolio summary from multiple project analyses.
        
        Args:
            project_analyses: List of individual project analysis results
            unassigned_analysis: Optional analysis of unassigned files (supporting docs, etc.)
            
        Returns:
            Dict with portfolio-level summary
        """
        if not self.is_configured():
            raise LLMError("LLM client is not configured")
        
        try:
            projects_overview = "\n\n".join([
                f"PROJECT: {p['project_name']}\n"
                f"Path: {p.get('project_path', 'N/A')}\n"
                f"Files analyzed: {p['files_analyzed']}\n"
                f"Analysis:\n{p['analysis']}"
                for p in project_analyses
            ])
            
            unassigned_context = ""
            if unassigned_analysis:
                unassigned_context = f"""

SUPPORTING FILES (not counted as a project):
Files analyzed: {unassigned_analysis['files_analyzed']}
These are documentation, configuration, and other supporting files found outside the main project directories.
Analysis:
{unassigned_analysis['analysis']}"""
            
            prompt = f"""You are reviewing a developer's portfolio containing {len(project_analyses)} separate projects.

INDIVIDUAL PROJECT ANALYSES:
{projects_overview}{unassigned_context}

Create a comprehensive PORTFOLIO-LEVEL summary in the following format:

PORTFOLIO OVERVIEW:
[2-3 sentences capturing the overall breadth and depth of the portfolio, highlighting the variety of projects and technologies]

KEY STRENGTHS:
[Main strengths demonstrated across projects - technical diversity, depth in certain areas, etc.]

TECHNICAL BREADTH:
[Summary of the range of technologies, frameworks, and domains covered across all projects]

STANDOUT PROJECTS:
[Identify 2-3 most impressive or notable projects and why they stand out]

PORTFOLIO COHERENCE:
[How well the projects work together to tell a cohesive story about the developer's skills and interests]"""

            messages = [{"role": "user", "content": prompt}]
            response = self._make_llm_call(messages, max_tokens=800, temperature=0.7)
            
            return {
                "summary": response,
                "project_count": len(project_analyses)
            }
            
        except Exception as e:
            self.logger.error(f"Portfolio summary generation failed: {e}")
            raise LLMError(f"Failed to generate portfolio summary: {str(e)}")
        
        
    def generate_and_apply_improvements(
    self,
    file_path: str,
    content: str,
    file_type: str
) -> Dict[str, Any]:
        """
        Generate AI-suggested improvements for text-based files.
        
        Handles:
        - Code files (Python, JavaScript, etc.)
        - PDFs (extracts text first)
        - Word documents (extracts text first)
        
        Args:
            file_path: Path to the file
            content: File content as string
            file_type: MIME type or file extension
        
        Returns:
            Dict with:
            - success: bool
            - suggestions: List of improvement dicts
            - improved_code: str (improved content)
            - original_code: str (original content)
            - error: str (if failed)
        """
        if not self.is_configured():
            raise LLMError("LLM client is not configured")
        
        try:
            token_count = self._count_tokens(content)
            self.logger.info(f"Generating improvements for {file_path} ({token_count} tokens)")
            
            # Truncate if too large
            if token_count > 3000:
                try:
                    encoding = self._get_tokenizer(self.DEFAULT_MODEL)
                    if encoding is None:
                        raise ValueError("No tokenizer available")
                    tokens = encoding.encode(content)
                    truncated_tokens = tokens[:3000]
                    content = encoding.decode(truncated_tokens)
                    self.logger.warning(f"Truncated {file_path} from {token_count} to 3000 tokens")
                except Exception:
                    # Fallback: truncate by characters
                    content = content[:12000]
            
            # Determine file category and appropriate improvements
            improvement_focus = self._get_improvement_focus(file_path, file_type)
            
            # Build adaptive prompt
            prompt = f"""You are an expert code and document reviewer. Analyze this file and suggest improvements.

    File: {file_path}

    Original Content:
    ```
    {content}
    ```

    {improvement_focus}

    Format your response as JSON:
    {{
    "suggestions": [
        {{
        "type": "documentation|refactoring|clarity|consistency|best-practices",
        "description": "Brief description of the improvement",
        "line_range": "Lines affected (e.g., '10-15' or 'general')"
        }}
    ],
    "improved_code": "The complete improved content here"
    }}

    CRITICAL: Return ONLY valid JSON. No markdown code blocks, no extra text, ONLY the JSON object."""

            messages = [{"role": "user", "content": prompt}]
            
            # Call OpenAI API
            response = self._make_llm_call(
                messages, 
                max_tokens=2500,
                temperature=0.3
            )
            
            # Parse JSON response with retry logic
            result = self._parse_json_response(response, file_path, content, improvement_focus)
            
            if result.get("success"):
                return {
                    "success": True,
                    "suggestions": result.get("suggestions", []),
                    "improved_code": result.get("improved_code", content),
                    "original_code": content
                }
            else:
                return result
            
        except Exception as e:
            self.logger.error(f"Failed to generate improvements: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def _parse_json_response(
        self,
        response: str,
        file_path: str,
        original_content: str,
        improvement_focus: str,
        retry: bool = True
    ) -> Dict[str, Any]:
        """
        Robustly parse JSON response from LLM with fallback strategies.
        
        Strategies:
        1. Try to parse response as-is
        2. Strip markdown code fences
        3. Extract JSON from text
        4. Retry with stricter prompt if initial parse fails
        
        Args:
            response: Raw response from LLM
            file_path: File being analyzed (for error context)
            original_content: Original file content
            improvement_focus: Improvement focus instructions
            retry: Whether to retry with stricter prompt on failure
        
        Returns:
            Dict with success status and parsed result or error
        """
        # Strategy 1: Try direct parsing
        try:
            result = json.loads(response.strip())
            self.logger.info(f"Successfully parsed JSON for {file_path}")
            return {"success": True, **result}
        except json.JSONDecodeError:
            self.logger.debug(f"Direct JSON parsing failed for {file_path}")
        
        # Strategy 2: Strip markdown code fences
        response_text = response.strip()
        response_text = re.sub(r'^```(?:json)?\s*\n?', '', response_text)  # Opening ```
        response_text = re.sub(r'\n?```\s*$', '', response_text)           # Closing ```
        response_text = response_text.strip()
        
        try:
            result = json.loads(response_text)
            self.logger.info(f"Successfully parsed JSON after stripping fences for {file_path}")
            return {"success": True, **result}
        except json.JSONDecodeError:
            self.logger.debug(f"Markdown stripping didn't help for {file_path}")
        
        # Strategy 3: Extract JSON block from text
        json_match = re.search(r'\{[\s\S]*\}', response_text)
        if json_match:
            try:
                json_str = json_match.group(0)
                result = json.loads(json_str)
                self.logger.info(f"Successfully extracted JSON from text for {file_path}")
                return {"success": True, **result}
            except json.JSONDecodeError:
                self.logger.debug(f"Extracted JSON was invalid for {file_path}")
        
        # Strategy 4: Retry with stricter prompt
        if retry:
            self.logger.warning(f"JSON parsing failed for {file_path}, retrying with stricter prompt")
            return self._retry_with_stricter_prompt(
                file_path,
                original_content,
                improvement_focus,
                response  # Include original response in context
            )
        
        # All strategies failed
        self.logger.error(f"All JSON parsing strategies failed for {file_path}")
        return {
            "success": False,
            "error": "Failed to parse AI response after multiple strategies",
            "raw_response": response[:500]
        }

    def _retry_with_stricter_prompt(
        self,
        file_path: str,
        content: str,
        improvement_focus: str,
        previous_response: str
    ) -> Dict[str, Any]:
        """
        Retry with a stricter, more explicit prompt if initial parsing failed.
        
        This helps when the model adds extra text, uses wrong format, etc.
        """
        stricter_prompt = f"""You are an expert code reviewer. Analyze this file ONLY.

File: {file_path}

Content:
```
{content}
```

{improvement_focus}

RESPOND WITH ONLY THIS JSON FORMAT. NO OTHER TEXT. NO MARKDOWN BLOCKS:
{{"suggestions": [{{"type": "string", "description": "string", "line_range": "string"}}], "improved_code": "string"}}"""

        try:
            messages = [{"role": "user", "content": stricter_prompt}]
            response = self._make_llm_call(
                messages,
                max_tokens=2500,
                temperature=0.3
            )
            
            # Try parsing strategies again on new response
            response_text = response.strip()
            response_text = re.sub(r'^```(?:json)?\s*\n?', '', response_text)
            response_text = re.sub(r'\n?```\s*$', '', response_text)
            response_text = response_text.strip()
            
            try:
                result = json.loads(response_text)
                self.logger.info(f"Successfully parsed JSON on retry for {file_path}")
                return {"success": True, **result}
            except json.JSONDecodeError:
                # Try to extract JSON
                json_match = re.search(r'\{[\s\S]*\}', response_text)
                if json_match:
                    try:
                        result = json.loads(json_match.group(0))
                        self.logger.info(f"Successfully extracted JSON on retry for {file_path}")
                        return {"success": True, **result}
                    except json.JSONDecodeError:
                        pass
            
            self.logger.error(f"Retry also failed for {file_path}")
            return {
                "success": False,
                "error": "Failed to parse AI response even after retry with stricter prompt",
                "raw_response": response[:500]
            }
            
        except Exception as e:
            self.logger.error(f"Retry failed with exception: {e}")
            return {
                "success": False,
                "error": f"Error during retry: {str(e)}"
            }

    def _get_improvement_focus(self, file_path: str, file_type: str) -> str:
        """
        Get appropriate improvement instructions based on file type.
        
        Returns different guidance for:
        - Programming code
        - PDF documents
        - Word documents
        """
        extension = Path(file_path).suffix.lower()
        filename = Path(file_path).name.lower()
        
        # PDF files
        if extension == '.pdf':
            return """Focus on DOCUMENT IMPROVEMENTS:
    - Improve document structure and organization
    - Enhance clarity and readability
    - Fix grammar and spelling errors
    - Improve formatting and layout suggestions
    - Add missing sections or context
    - Ensure consistent style"""
        
        # Word documents
        elif extension == '.docx':
            return """Focus on DOCUMENT IMPROVEMENTS:
    - Improve document structure and organization
    - Enhance clarity and readability
    - Fix grammar and spelling errors
    - Improve formatting and layout suggestions
    - Add missing sections or context
    - Ensure consistent style and tone"""
        
        # Programming languages
        code_extensions = {
            '.py', '.js', '.jsx', '.ts', '.tsx', '.java', '.cpp', '.c', 
            '.cs', '.rb', '.go', '.rs', '.php', '.swift', '.kt', '.scala'
        }
        
        if extension in code_extensions:
            return """Focus on CODE IMPROVEMENTS:
    - Add clear comments and docstrings
    - Improve variable and function names for clarity
    - Add error handling and input validation
    - Follow language-specific best practices
    - Improve code structure and readability
    - Add type hints where applicable
    - Remove code duplication"""
        
        # Web files
        web_extensions = {'.html', '.css', '.scss', '.sass'}
        
        if extension in web_extensions:
            return """Focus on WEB FILE IMPROVEMENTS:
    - Add helpful comments
    - Improve naming conventions
    - Follow modern best practices
    - Improve accessibility
    - Optimize structure
    - Add documentation comments"""
        
        # Configuration files
        config_extensions = {'.json', '.yaml', '.yml', '.toml', '.ini', '.env'}
        
        if extension in config_extensions:
            return """Focus on CONFIGURATION IMPROVEMENTS:
    - Add helpful comments explaining each setting
    - Organize settings into logical groups
    - Add default values and examples
    - Improve key names for clarity
    - Add validation comments
    - Document required vs optional settings"""
        
        # Documentation files
        doc_extensions = {'.md', '.txt', '.rst'}
        
        if extension in doc_extensions:
            return """Focus on DOCUMENTATION IMPROVEMENTS:
    - Improve clarity and readability
    - Add missing sections (installation, usage, examples)
    - Fix grammar and spelling
    - Add code examples where helpful
    - Improve formatting and structure
    - Add links and references"""
        
        # SQL files
        elif extension == '.sql':
            return """Focus on SQL IMPROVEMENTS:
    - Add comments explaining queries
    - Improve query structure and formatting
    - Optimize query performance
    - Add error handling
    - Use consistent naming conventions
    - Add documentation for complex logic"""
        
        else:
            # Generic text file
            return """Focus on TEXT FILE IMPROVEMENTS:
    - Improve clarity and readability
    - Fix grammar and spelling
    - Add helpful comments or explanations
    - Improve formatting and structure
    - Ensure consistency"""