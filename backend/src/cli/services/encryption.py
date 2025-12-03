"""Shared encryption helper for storing data at rest."""

from __future__ import annotations

import base64
import json
import os
import secrets
from dataclasses import dataclass
from typing import Any, Dict, Optional

try:  # pragma: no cover - exercised in tests when available
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
except Exception as exc:  # pragma: no cover - dependency missing
    AESGCM = None  # type: ignore[assignment]
    _import_error = exc
else:
    _import_error = None


class EncryptionError(Exception):
    """Raised when encryption or decryption fails."""


@dataclass(slots=True)
class EncryptionEnvelope:
    """Serialized payload for storage."""

    version: str
    iv: str
    ciphertext: str

    def to_dict(self) -> Dict[str, str]:
        return {"v": self.version, "iv": self.iv, "ct": self.ciphertext}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EncryptionEnvelope":
        return cls(
            version=str(data.get("v")),
            iv=str(data.get("iv")),
            ciphertext=str(data.get("ct")),
        )


class EncryptionService:
    """
    AES-GCM based encryption for at-rest storage.

    - Uses a 32-byte key from ENCRYPTION_MASTER_KEY (base64)
    - Returns compact JSON-friendly envelopes
    """

    DEFAULT_VERSION = "1"
    ENV_KEY = "ENCRYPTION_MASTER_KEY"

    def __init__(self, *, key: Optional[bytes] = None) -> None:
        if AESGCM is None:  # pragma: no cover - surfaced in tests via importorskip
            raise EncryptionError(
                f"cryptography is required for encryption: {_import_error}"
            )

        key_bytes = key or self._load_key_from_env()
        if len(key_bytes) != 32:
            raise EncryptionError("Encryption key must be 32 bytes (256-bit).")
        self._key = key_bytes

    def encrypt_bytes(
        self, data: bytes, *, version: str = DEFAULT_VERSION
    ) -> EncryptionEnvelope:
        """Encrypt raw bytes and return an envelope."""
        if not isinstance(data, (bytes, bytearray)):
            raise EncryptionError("Data must be bytes.")

        iv = secrets.token_bytes(12)  # 96-bit nonce recommended for GCM
        cipher = AESGCM(self._key)
        ciphertext = cipher.encrypt(iv, bytes(data), None)

        return EncryptionEnvelope(
            version=version,
            iv=self._b64_encode(iv),
            ciphertext=self._b64_encode(ciphertext),
        )

    def decrypt_bytes(self, envelope: Dict[str, Any]) -> bytes:
        """Decrypt an envelope produced by encrypt_bytes."""
        try:
            parsed = EncryptionEnvelope.from_dict(envelope)
        except Exception as exc:
            raise EncryptionError(f"Invalid envelope: {exc}") from exc

        if parsed.version != self.DEFAULT_VERSION:
            raise EncryptionError(f"Unsupported encryption version: {parsed.version}")

        iv = self._b64_decode(parsed.iv)
        ciphertext = self._b64_decode(parsed.ciphertext)

        cipher = AESGCM(self._key)
        try:
            return cipher.decrypt(iv, ciphertext, None)
        except Exception as exc:
            raise EncryptionError(f"Decryption failed: {exc}") from exc

    def encrypt_json(self, payload: Any) -> EncryptionEnvelope:
        """Serialize to JSON then encrypt."""
        try:
            data = json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode(
                "utf-8"
            )
        except Exception as exc:
            raise EncryptionError(f"Failed to serialize payload: {exc}") from exc
        return self.encrypt_bytes(data)

    def decrypt_json(self, envelope: Dict[str, Any]) -> Any:
        """Decrypt envelope and parse JSON."""
        data = self.decrypt_bytes(envelope)
        try:
            return json.loads(data.decode("utf-8"))
        except Exception as exc:
            raise EncryptionError(f"Failed to parse decrypted JSON: {exc}") from exc

    def _load_key_from_env(self) -> bytes:
        encoded = os.getenv(self.ENV_KEY)
        if not encoded:
            raise EncryptionError(
                f"{self.ENV_KEY} is required for encryption and must be base64 encoded."
            )
        try:
            key = base64.b64decode(encoded)
        except Exception as exc:
            raise EncryptionError(f"Failed to decode {self.ENV_KEY}: {exc}") from exc
        return key

    @staticmethod
    def _b64_encode(data: bytes) -> str:
        return base64.b64encode(data).decode("ascii")

    @staticmethod
    def _b64_decode(data: str) -> bytes:
        return base64.b64decode(data.encode("ascii"))
