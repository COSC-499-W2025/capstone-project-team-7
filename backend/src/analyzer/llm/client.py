# LLM Client Module
# Handles integration with OpenAI API for analysis tasks

import asyncio
import base64
import logging
import threading
import mimetypes
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
        
        self.temperature = temperature if temperature is not None else self.DEFAULT_TEMPERATURE
        self.max_tokens = max_tokens if max_tokens is not None else self.DEFAULT_MAX_TOKENS

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
    
    def _count_tokens(self, text: str, model: Optional[str] = None) -> int:
        """
        Count the number of tokens in a text string, default to character estimate.
        
        Args:
            text: Text to count tokens for
            model: Model name for tokenizer (defaults to DEFAULT_MODEL)
            
        Returns:
            int: Number of tokens
        """
        if model is None:
            model = self.DEFAULT_MODEL
        try:
            encoding = tiktoken.encoding_for_model(model)
            return len(encoding.encode(text))
        except Exception as e:
            self.logger.warning(f"Failed to count tokens: {e}. Using character estimate.")
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
        temperature: Optional[float] = None
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
            response = self.client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature
            )
            
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
                encoding = tiktoken.encoding_for_model(self.DEFAULT_MODEL)
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
    
    def summarize_tagged_file(self, file_path: str, content: str, file_type: str) -> Dict[str, str]:
        """
        Create a detailed summary of a user-tagged important file.
        Automatically handles large files through chunking.
        
        Args:
            file_path: Path to the file
            content: Full file content
            file_type: File extension/type
            
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
            
            if token_count > 2000:
                chunk_result = self.chunk_and_summarize(content, file_type)
                content_to_analyze = chunk_result["final_summary"]
            else:
                content_to_analyze = content
            
            prompt = f"""Analyze this {file_type} file and provide a brief structured summary.

File: {file_path}

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
    
    def analyze_project(
        self,
        local_analysis: Dict[str, Any],
        tagged_files_summaries: List[Dict[str, str]],
        media_briefings: Optional[List[str]] = None,
    ) -> Dict[str, str]:
        """
        Generate a comprehensive, resume-friendly project report.
        
        Args:
            local_analysis: Dict with stats, metrics, file_counts
            tagged_files_summaries: List of summaries from summarize_tagged_file()
            media_briefings: Optional list of media asset summaries (images/audio/video)
            
        Returns:
            Dict containing:
                - analysis result: Formatted output text
                
        Raises:
            LLMError: If analysis fails
        """
        if not self.is_configured():
            raise LLMError("LLM client is not configured")
        
        try:
            files_info = "\n\n".join([
                f"File: {f.get('file_path', 'Unknown')}\n{f.get('analysis', '')}"
                for f in tagged_files_summaries
            ])

            media_context = ""
            media_section_prompt = ""
            if media_briefings:
                media_lines = "\n".join(f"- {entry}" for entry in media_briefings)
                media_context = f"""

MEDIA ASSETS (images/audio/video):
{media_lines}
"""
                media_section_prompt = """

MEDIA INSIGHTS:
[1-3 concise bullet points describing the listed media assets: what appears or is heard, notable timestamps/durations, any genre/label hints, and key transcript snippets.]"""
            
            prompt = f"""You are analyzing a software project to create a professional, resume-worthy report.

            LOCAL ANALYSIS RESULTS:
            {local_analysis}

            IMPORTANT FILES ANALYSIS:
            {files_info if files_info else 'No tagged files provided'}{media_context}

            Create a comprehensive analysis in the following format:

            EXECUTIVE SUMMARY:
            [2-3 sentences capturing the project's essence and main value proposition]

            TECHNICAL HIGHLIGHTS:
            [Key features, capabilities, and technical achievements in bullet points]

            TECHNOLOGIES USED:
            [Summary of the tech stack and how technologies are used]

            PROJECT QUALITY:
            [Assessment of completeness, production-readiness, code quality, and overall maturity]{media_section_prompt}

            Only include the MEDIA INSIGHTS section when media assets are provided above; omit it when none are available."""

            messages = [{"role": "user", "content": prompt}]
            response = self._make_llm_call(messages, max_tokens=800, temperature=0.7)
            
            return {
                "analysis": response
            }
            
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
    
    def _run_async_in_thread(self, coro):
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
        thread.join()
        
        if exception:
            raise exception
        return result
    
    async def _summarize_file_batch(self, files_batch: List[tuple], base_path) -> List[Dict[str, str]]:
        """Process a batch of files in parallel.
        
        Args:
            files_batch: List of (file_path, full_path, file_type) tuples
            base_path: Base path for file reading
            
        Returns:
            List of file summary results
        """
        
        async def analyze_single_file(file_info):
            file_path, full_path, file_type = file_info
            try:
                content = full_path.read_text(encoding='utf-8', errors='ignore')
                # Run the synchronous summarize in thread pool
                loop = asyncio.get_event_loop()
                summary_result = await loop.run_in_executor(
                    None,
                    self.summarize_tagged_file,
                    file_path,
                    content,
                    file_type
                )
                self.logger.info(f"Summarized: {file_path}")
                return summary_result
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
                )

            media_briefings: list[str] = []
            if include_media:
                media_briefings = self._build_media_briefings(
                    relevant_files, base_path=Path(scan_base_path) if scan_base_path else None
                )
            
            max_file_size_bytes = max_file_size_mb * 1024 * 1024
            file_summaries = []
            skipped_files = []
            
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
                    files_to_analyze.append((file_path, full_path, file_type))
            
            # Process files in batches of 5 for parallel execution
            BATCH_SIZE = 5
            processed_count = 0
            
            for i in range(0, len(files_to_analyze), BATCH_SIZE):
                batch = files_to_analyze[i:i + BATCH_SIZE]
                batch_num = (i // BATCH_SIZE) + 1
                total_batches = (len(files_to_analyze) + BATCH_SIZE - 1) // BATCH_SIZE
                
                if progress_callback:
                    progress_callback(f"Single-project: Batch {batch_num}/{total_batches} ({len(batch)} files)…")
                
                try:
                    # Process batch in parallel using dedicated thread
                    batch_results = self._run_async_in_thread(
                        self._summarize_file_batch(batch, scan_base_path)
                    )
                    file_summaries.extend(batch_results)
                    processed_count += len(batch_results)
                    
                    if progress_callback:
                        progress_callback(f"Single-project: Completed {processed_count}/{len(files_to_analyze)} files…")
                except Exception as e:
                    self.logger.error(f"Error processing batch: {e}")
                    continue
            
            if progress_callback:
                progress_callback("Generating project insights…")
            
            project_analysis = self.analyze_project(
                local_analysis=scan_summary,
                tagged_files_summaries=file_summaries,
                media_briefings=media_briefings if media_briefings else None,
            )
            
            result = {
                "project_analysis": project_analysis,
                "file_summaries": file_summaries,
                "files_analyzed_count": len(file_summaries)
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
                                   progress_callback: Optional[Any] = None) -> Dict[str, Any]:
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
        
        self.logger.info(f"Analyzing {len(project_dirs)} separate projects")
        
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
            
            # Process files in batches of 5 for parallel execution
            BATCH_SIZE = 5
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
                    import tiktoken
                    encoding = tiktoken.encoding_for_model(self.DEFAULT_MODEL)
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