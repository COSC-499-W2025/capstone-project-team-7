"""Persist generated resume snippets to Supabase with optional at-rest encryption."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path as _Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional
import json
import logging
import os

try:  # pragma: no cover - enforced via tests with mocks
    from supabase import Client, create_client
    SUPABASE_AVAILABLE = True
except ImportError:  # pragma: no cover - dependency missing
    SUPABASE_AVAILABLE = False
    Client = None  # type: ignore[assignment]

if TYPE_CHECKING:  # pragma: no cover - typing helper only
    from .encryption import EncryptionError, EncryptionService, EncryptionEnvelope
    from .resume_generation_service import ResumeItem

from .encryption import EncryptionError, EncryptionService


class ResumeStorageError(Exception):
    """Raised when resume storage operations fail."""


class ResumeStorageService:
    """Persist resume items to Supabase and fetch them later."""

    def __init__(
        self,
        supabase_url: Optional[str] = None,
        supabase_key: Optional[str] = None,
        *,
        encryption_service: Optional[EncryptionService] = None,
        encryption_required: bool = True,
    ):
        if not SUPABASE_AVAILABLE:
            raise ResumeStorageError("Supabase client not available. Install supabase-py.")

        self.supabase_url = supabase_url or os.getenv("SUPABASE_URL")
        self.supabase_key = (
            supabase_key
            or os.getenv("SUPABASE_SERVICE_ROLE_KEY")
            or os.getenv("SUPABASE_KEY")
            or os.getenv("SUPABASE_ANON_KEY")
        )

        if not self.supabase_url or not self.supabase_key:
            raise ResumeStorageError("Supabase credentials not configured.")

        self._access_token: Optional[str] = None
        self._encryption: Optional["EncryptionService"] = encryption_service

        if encryption_required and self._encryption is None:
            try:
                from .encryption import EncryptionError as _EncryptionError
                from .encryption import EncryptionService as _EncryptionService
            except Exception as exc:  # pragma: no cover - import side issues are environment-specific
                raise ResumeStorageError(f"Encryption unavailable: {exc}") from exc

            try:
                self._encryption = _EncryptionService()
            except _EncryptionError as exc:  # pragma: no cover - surfaced in tests
                raise ResumeStorageError(f"Encryption unavailable: {exc}") from exc

        try:
            self.client: Client = create_client(self.supabase_url, self.supabase_key)
        except Exception as exc:  # pragma: no cover - client level errors hard to simulate
            raise ResumeStorageError(f"Failed to initialize Supabase client: {exc}") from exc

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    def apply_access_token(self, token: Optional[str]) -> None:
        """Attach or clear a user's Supabase access token for RLS-aware queries."""
        self._access_token = token
        try:
            if token:
                self.client.postgrest.auth(token)
            else:
                self.client.postgrest.auth(None)
        except AttributeError:
            # Older supabase-py doesn't expose postgrest auth; fall back silently.
            pass

    def save_resume_item(
        self,
        user_id: str,
        resume_item: "ResumeItem",
        *,
        metadata: Optional[Dict[str, Any]] = None,
        target_path: Optional[_Path] = None,
    ) -> Dict[str, Any]:
        """Persist a generated resume item."""
        if not user_id:
            raise ResumeStorageError("User ID is required to save a resume.")

        payload: Dict[str, Any] = {
            "user_id": user_id,
            "project_name": resume_item.project_name,
            "start_date": resume_item.start_date,
            "end_date": resume_item.end_date,
            "content": resume_item.to_markdown(),
            "bullets": list(resume_item.bullets),
            "metadata": self._sanitize_metadata(
                {
                    **(metadata or {}),
                    "ai_generated": getattr(resume_item, "ai_generated", False),
                    "role": getattr(resume_item, "role", "") or "",
                }
            ),
            "source_path": self._path_to_str(target_path) or self._path_to_str(resume_item.output_path),
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        payload = self._encrypt_payload(payload)

        try:
            response = self.client.table("resume_items").insert(payload).execute()
        except Exception as exc:
            raise ResumeStorageError(f"Failed to save resume item: {exc}") from exc

        if not response.data:
            raise ResumeStorageError("Supabase did not return a saved resume record.")
        return response.data[0]

    def save_resume_record(
        self,
        user_id: str,
        *,
        project_name: str,
        start_date: Optional[str],
        end_date: Optional[str],
        content: str,
        bullets: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        source_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Persist a resume item record from raw values."""
        if not user_id:
            raise ResumeStorageError("User ID is required to save a resume.")
        if not project_name:
            raise ResumeStorageError("Project name is required to save a resume.")
        if not content:
            raise ResumeStorageError("Resume content is required to save a resume.")

        payload: Dict[str, Any] = {
            "user_id": user_id,
            "project_name": project_name,
            "start_date": start_date,
            "end_date": end_date,
            "content": content,
            "bullets": list(bullets or []),
            "metadata": self._sanitize_metadata(metadata),
            "source_path": source_path,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        payload = self._encrypt_payload(payload)

        try:
            response = self.client.table("resume_items").insert(payload).execute()
        except Exception as exc:
            raise ResumeStorageError(f"Failed to save resume item: {exc}") from exc

        if not response.data:
            raise ResumeStorageError("Supabase did not return a saved resume record.")
        return response.data[0]

    def get_user_resumes(self, user_id: str) -> List[Dict[str, Any]]:
        """Return lightweight resume metadata for a user."""
        if not user_id:
            return []

        try:
            response = (
                self.client.table("resume_items")
                .select("id, project_name, start_date, end_date, created_at, metadata")
                .eq("user_id", user_id)
                .order("created_at", desc=True)
                .execute()
            )
        except Exception as exc:
            raise ResumeStorageError(f"Failed to load resumes: {exc}") from exc
        return response.data or []

    def get_resume_item(self, user_id: str, resume_id: str) -> Optional[Dict[str, Any]]:
        """Fetch a single resume entry with full content."""
        if not user_id or not resume_id:
            return None

        try:
            response = (
                self.client.table("resume_items")
                .select("*")
                .eq("user_id", user_id)
                .eq("id", resume_id)
                .limit(1)
                .execute()
            )
        except Exception as exc:
            raise ResumeStorageError(f"Failed to load resume item: {exc}") from exc

        if not response.data:
            return None
        record = response.data[0]
        return self._decrypt_record(record)

    def delete_resume_item(self, user_id: str, resume_id: str) -> bool:
        """Remove a saved resume item."""
        if not user_id or not resume_id:
            return False

        try:
            response = (
                self.client.table("resume_items")
                .delete()
                .eq("user_id", user_id)
                .eq("id", resume_id)
                .execute()
            )
        except Exception as exc:
            raise ResumeStorageError(f"Failed to delete resume item: {exc}") from exc

        return bool(response.data)

    def update_resume_item(
        self,
        user_id: str,
        resume_id: str,
        *,
        project_name: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        content: Optional[str] = None,
        bullets: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        source_path: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Update an existing resume record and return the updated entry."""
        if not user_id or not resume_id:
            return None

        record = self.get_resume_item(user_id, resume_id)
        if not record:
            return None

        payload: Dict[str, Any] = {}
        if project_name is not None:
            payload["project_name"] = project_name
        if start_date is not None:
            payload["start_date"] = start_date
        if end_date is not None:
            payload["end_date"] = end_date
        if source_path is not None:
            payload["source_path"] = source_path

        needs_encrypt = self._encryption is not None and (content is not None or bullets is not None)
        existing_metadata = record.get("metadata") or {}
        if metadata is not None or needs_encrypt:
            merged_metadata = {**existing_metadata, **(metadata or {})}
            payload["metadata"] = self._sanitize_metadata(merged_metadata)

        if content is not None or bullets is not None:
            payload["content"] = content if content is not None else record.get("content") or ""
            payload["bullets"] = list(bullets) if bullets is not None else record.get("bullets") or []
            if needs_encrypt:
                payload = self._encrypt_payload(payload)

        if not payload:
            return record

        try:
            response = (
                self.client.table("resume_items")
                .update(payload)
                .eq("user_id", user_id)
                .eq("id", resume_id)
                .execute()
            )
        except Exception as exc:
            raise ResumeStorageError(f"Failed to update resume item: {exc}") from exc

        if not response.data:
            return None
        return self._decrypt_record(response.data[0])

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #

    def _sanitize_metadata(self, metadata: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        if not metadata:
            return {}
        clean: Dict[str, Any] = {}
        for key, value in metadata.items():
            clean[key] = self._clean_value(value)
        return clean

    def _clean_value(self, value: Any) -> Any:
        if isinstance(value, (_Path,)):
            return str(value)
        if isinstance(value, datetime):
            return value.isoformat()
        if isinstance(value, dict):
            return {k: self._clean_value(v) for k, v in value.items()}
        if isinstance(value, list):
            return [self._clean_value(v) for v in value]
        if isinstance(value, tuple):
            return [self._clean_value(v) for v in value]
        return value

    @staticmethod
    def _path_to_str(path: Optional[_Path]) -> Optional[str]:
        if path is None:
            return None
        return str(path)

    # ------------------------------------------------------------------ #
    # Encryption helpers
    # ------------------------------------------------------------------ #

    def _encrypt_payload(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Encrypt resume content + bullets when encryption is available."""
        if not self._encryption:
            return payload

        try:
            envelope = self._encryption.encrypt_json(
                {"content": payload["content"], "bullets": payload["bullets"]}
            )
        except Exception as exc:
            raise ResumeStorageError(f"Failed to encrypt resume content: {exc}") from exc

        payload["content"] = json.dumps(envelope.to_dict())
        payload["bullets"] = envelope.to_dict()
        metadata = payload.get("metadata") or {}
        metadata["_encrypted"] = True
        payload["metadata"] = metadata
        return payload

    def _decrypt_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Decrypt content/bullets if they are encrypted; tolerate plaintext."""
        if not record:
            return record

        maybe_encrypted_content = record.get("content")
        maybe_encrypted_bullets = record.get("bullets")

        # Quick detection: content stored as JSON string/dict with expected keys
        def _load_envelope(value: Any) -> Optional[Dict[str, Any]]:
            if isinstance(value, dict) and {"v", "iv", "ct"} <= set(value.keys()):
                return value
            if isinstance(value, str):
                try:
                    parsed = json.loads(value)
                except Exception:
                    return None
                if isinstance(parsed, dict) and {"v", "iv", "ct"} <= set(parsed.keys()):
                    return parsed
            return None

        envelope_dict = _load_envelope(maybe_encrypted_content)
        if envelope_dict and self._encryption:
            try:
                decrypted = self._encryption.decrypt_json(envelope_dict)
                record["content"] = decrypted.get("content")
                record["bullets"] = decrypted.get("bullets", [])
            except Exception as exc:
                # Leave record as-is to avoid data loss if decryption fails
                logging.warning(
                    "Failed to decrypt resume record %s, returning stored values: %s",
                    record.get("id"),
                    exc,
                )

        return record
