from fastapi.testclient import TestClient

from backend.src.main import app
import api.encryption_routes as encryption_routes


def test_encryption_status_ready(monkeypatch):
    monkeypatch.setenv("ENCRYPTION_MASTER_KEY", "dummy")
    class _DummyEncryptionService:
        ENV_KEY = "ENCRYPTION_MASTER_KEY"

        def __init__(self):
            pass

    monkeypatch.setattr(encryption_routes, "EncryptionService", _DummyEncryptionService)

    client = TestClient(app)
    res = client.get("/api/encryption/status")
    payload = res.json()

    assert res.status_code == 200
    assert payload["enabled"] is True
    assert payload["ready"] is True
    assert payload.get("error") is None


def test_encryption_status_not_configured(monkeypatch):
    monkeypatch.delenv("ENCRYPTION_MASTER_KEY", raising=False)
    class _DummyEncryptionService:
        ENV_KEY = "ENCRYPTION_MASTER_KEY"

        def __init__(self):
            pass

    monkeypatch.setattr(encryption_routes, "EncryptionService", _DummyEncryptionService)

    client = TestClient(app)
    res = client.get("/api/encryption/status")
    payload = res.json()

    assert res.status_code == 200
    assert payload["enabled"] is False
    assert payload["ready"] is True
    assert payload.get("error") is None


def test_encryption_status_error(monkeypatch):
    monkeypatch.setenv("ENCRYPTION_MASTER_KEY", "dummy")

    class _FailingEncryptionService:
        ENV_KEY = "ENCRYPTION_MASTER_KEY"

        def __init__(self):
            raise RuntimeError("boom")

    monkeypatch.setattr(encryption_routes, "EncryptionService", _FailingEncryptionService)

    client = TestClient(app)
    res = client.get("/api/encryption/status")
    payload = res.json()

    assert res.status_code == 200
    assert payload["enabled"] is True
    assert payload["ready"] is False
    assert payload.get("error") == "boom"
