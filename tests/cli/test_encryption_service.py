from __future__ import annotations

import base64
import pytest

pytest.importorskip("cryptography")

from backend.src.cli.services.encryption import (
    EncryptionEnvelope,
    EncryptionError,
    EncryptionService,
)


def _key_bytes() -> bytes:
    return b"0" * 32


def _set_env_key(monkeypatch):
    monkeypatch.setenv("ENCRYPTION_MASTER_KEY", base64.b64encode(_key_bytes()).decode("ascii"))


def test_encrypt_decrypt_bytes_roundtrip(monkeypatch):
    _set_env_key(monkeypatch)
    svc = EncryptionService()
    envelope = svc.encrypt_bytes(b"hello world")
    assert envelope.version == "1"
    decrypted = svc.decrypt_bytes(envelope.to_dict())
    assert decrypted == b"hello world"


def test_encrypt_decrypt_json_roundtrip(monkeypatch):
    _set_env_key(monkeypatch)
    svc = EncryptionService()
    payload = {"a": 1, "b": ["x", "y"], "c": {"nested": True}}
    envelope = svc.encrypt_json(payload)
    restored = svc.decrypt_json(envelope.to_dict())
    assert restored == payload


def test_missing_or_bad_key_raises(monkeypatch):
    monkeypatch.delenv("ENCRYPTION_MASTER_KEY", raising=False)
    with pytest.raises(EncryptionError):
        EncryptionService()

    monkeypatch.setenv("ENCRYPTION_MASTER_KEY", base64.b64encode(b"short").decode("ascii"))
    with pytest.raises(EncryptionError):
        EncryptionService()


def test_decrypt_with_wrong_key_fails(monkeypatch):
    _set_env_key(monkeypatch)
    svc = EncryptionService()
    envelope = svc.encrypt_bytes(b"secret")

    # New service with different key should fail decryption
    other_key = base64.b64encode(b"1" * 32).decode("ascii")
    monkeypatch.setenv("ENCRYPTION_MASTER_KEY", other_key)
    svc_other = EncryptionService()

    with pytest.raises(EncryptionError):
        svc_other.decrypt_bytes(envelope.to_dict())


def test_invalid_envelope_rejected(monkeypatch):
    _set_env_key(monkeypatch)
    svc = EncryptionService()
    with pytest.raises(EncryptionError):
        svc.decrypt_bytes({"iv": "bad"})
