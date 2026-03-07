"""Tests for /api/settings/secrets endpoints."""

from __future__ import annotations

import base64
import json
import os
import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch, MagicMock

import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

# Ensure src is on path
_src = Path(__file__).resolve().parent.parent / "src"
if str(_src) not in sys.path:
    sys.path.insert(0, str(_src))

os.environ.setdefault("SUPABASE_URL", "https://test.supabase.co")
os.environ.setdefault("SUPABASE_KEY", "test-service-role-key")

# Generate a valid 32-byte key for encryption tests
_TEST_KEY = base64.b64encode(b"\x00" * 32).decode()
os.environ["ENCRYPTION_MASTER_KEY"] = _TEST_KEY

from api.dependencies import AuthContext, get_auth_context
import api.settings_routes as settings_mod


def _mock_httpx(MockClient, instance):
    instance.__aenter__ = AsyncMock(return_value=instance)
    instance.__aexit__ = AsyncMock(return_value=False)
    MockClient.return_value = instance


_FAKE_AUTH = AuthContext(user_id="user-123", access_token="tok-abc", email="user@example.com")


@pytest.fixture()
def client():
    app = FastAPI()
    app.include_router(settings_mod.router)
    app.dependency_overrides[get_auth_context] = lambda: _FAKE_AUTH
    with TestClient(app) as c:
        yield c


# ---------------------------------------------------------------------------
# GET /api/settings/secrets
# ---------------------------------------------------------------------------


class TestGetSecretsStatus:
    def test_returns_empty_list(self, client):
        fake_resp = httpx.Response(
            200, json=[], request=httpx.Request("GET", "https://test.supabase.co/rest/v1/user_secrets"),
        )
        instance = AsyncMock()
        instance.get.return_value = fake_resp
        with patch.object(settings_mod.httpx, "AsyncClient") as MC:
            _mock_httpx(MC, instance)
            resp = client.get("/api/settings/secrets", headers={"Authorization": "Bearer tok-abc"})

        assert resp.status_code == 200
        data = resp.json()
        assert data["secrets"] == []

    def test_returns_metadata_no_raw_values(self, client):
        fake_resp = httpx.Response(
            200,
            json=[{
                "secret_key": "openai_api_key",
                "provider": "openai",
                "metadata": {},
                "updated_at": "2026-03-06T00:00:00Z",
            }],
            request=httpx.Request("GET", "https://test.supabase.co/rest/v1/user_secrets"),
        )
        instance = AsyncMock()
        instance.get.return_value = fake_resp
        with patch.object(settings_mod.httpx, "AsyncClient") as MC:
            _mock_httpx(MC, instance)
            resp = client.get("/api/settings/secrets", headers={"Authorization": "Bearer tok-abc"})

        assert resp.status_code == 200
        secrets = resp.json()["secrets"]
        assert len(secrets) == 1
        assert secrets[0]["secret_key"] == "openai_api_key"
        assert secrets[0]["has_value"] is True
        assert secrets[0]["provider"] == "openai"
        # Must never contain raw value
        assert "value" not in secrets[0]
        assert "encrypted_value" not in secrets[0]


# ---------------------------------------------------------------------------
# PUT /api/settings/secrets
# ---------------------------------------------------------------------------


class TestSaveSecret:
    def test_encrypts_and_stores(self, client):
        fake_resp = httpx.Response(
            201,
            json=[{
                "secret_key": "openai_api_key",
                "provider": "openai",
                "updated_at": "2026-03-06T00:00:00Z",
            }],
            request=httpx.Request("POST", "https://test.supabase.co/rest/v1/user_secrets"),
        )
        instance = AsyncMock()
        instance.post.return_value = fake_resp
        with patch.object(settings_mod.httpx, "AsyncClient") as MC:
            _mock_httpx(MC, instance)
            resp = client.put(
                "/api/settings/secrets",
                json={"secret_key": "openai_api_key", "value": "sk-test123"},
                headers={"Authorization": "Bearer tok-abc"},
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["secret_key"] == "openai_api_key"
        assert data["has_value"] is True

        # Verify the payload sent to Supabase contains encrypted data, not raw
        call_args = instance.post.call_args
        payload = call_args.kwargs.get("json") or call_args[1].get("json")
        assert "encrypted_value" in payload
        assert "v" in payload["encrypted_value"]
        assert "iv" in payload["encrypted_value"]
        assert "ct" in payload["encrypted_value"]
        assert payload["encrypted_value"]["ct"] != "sk-test123"

    def test_invalid_key_returns_400(self, client):
        resp = client.put(
            "/api/settings/secrets",
            json={"secret_key": "invalid_key", "value": "some-value"},
            headers={"Authorization": "Bearer tok-abc"},
        )
        assert resp.status_code == 400

    def test_empty_value_returns_400(self, client):
        resp = client.put(
            "/api/settings/secrets",
            json={"secret_key": "openai_api_key", "value": "  "},
            headers={"Authorization": "Bearer tok-abc"},
        )
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# DELETE /api/settings/secrets
# ---------------------------------------------------------------------------


class TestDeleteSecret:
    def test_removes_row_and_evicts_client(self, client):
        fake_resp = httpx.Response(
            200, json=[], request=httpx.Request("DELETE", "https://test.supabase.co/rest/v1/user_secrets"),
        )
        instance = AsyncMock()
        instance.delete.return_value = fake_resp

        with patch.object(settings_mod.httpx, "AsyncClient") as MC, \
             patch.object(settings_mod, "remove_user_client") as mock_remove:
            _mock_httpx(MC, instance)
            resp = client.request(
                "DELETE",
                "/api/settings/secrets",
                json={"secret_key": "openai_api_key"},
                headers={"Authorization": "Bearer tok-abc"},
            )

        assert resp.status_code == 200
        assert resp.json()["ok"] is True
        mock_remove.assert_called_once_with("user-123")


# ---------------------------------------------------------------------------
# POST /api/settings/secrets/verify
# ---------------------------------------------------------------------------


class TestVerifyStoredKey:
    def test_verify_with_consent_and_valid_key(self, client):
        from services.services.encryption import EncryptionService
        enc = EncryptionService()
        envelope = enc.encrypt_json("sk-valid-key")

        fake_resp = httpx.Response(
            200,
            json=[{"encrypted_value": envelope.to_dict()}],
            request=httpx.Request("GET", "https://test.supabase.co/rest/v1/user_secrets"),
        )
        instance = AsyncMock()
        instance.get.return_value = fake_resp

        with patch.object(settings_mod.httpx, "AsyncClient") as MC, \
             patch.object(settings_mod, "ConsentValidator") as MockCV, \
             patch.object(settings_mod, "LLMClient") as MockLLM, \
             patch.object(settings_mod, "set_user_client") as mock_set:
            _mock_httpx(MC, instance)
            MockCV.return_value.validate_external_services_consent.return_value = True
            MockLLM.return_value.verify_api_key.return_value = True
            resp = client.post("/api/settings/secrets/verify", headers={"Authorization": "Bearer tok-abc"})

        assert resp.status_code == 200
        data = resp.json()
        assert data["valid"] is True
        mock_set.assert_called_once()

    def test_verify_without_consent_returns_403(self, client):
        with patch.object(settings_mod, "ConsentValidator") as MockCV:
            MockCV.return_value.validate_external_services_consent.return_value = False
            resp = client.post("/api/settings/secrets/verify", headers={"Authorization": "Bearer tok-abc"})

        assert resp.status_code == 403

    def test_verify_no_stored_key_returns_404(self, client):
        fake_resp = httpx.Response(
            200, json=[], request=httpx.Request("GET", "https://test.supabase.co/rest/v1/user_secrets"),
        )
        instance = AsyncMock()
        instance.get.return_value = fake_resp

        with patch.object(settings_mod.httpx, "AsyncClient") as MC, \
             patch.object(settings_mod, "ConsentValidator") as MockCV:
            _mock_httpx(MC, instance)
            MockCV.return_value.validate_external_services_consent.return_value = True
            resp = client.post("/api/settings/secrets/verify", headers={"Authorization": "Bearer tok-abc"})

        assert resp.status_code == 404

    def test_verify_invalid_key(self, client):
        from services.services.encryption import EncryptionService
        enc = EncryptionService()
        envelope = enc.encrypt_json("sk-bad")

        fake_resp = httpx.Response(
            200,
            json=[{"encrypted_value": envelope.to_dict()}],
            request=httpx.Request("GET", "https://test.supabase.co/rest/v1/user_secrets"),
        )
        instance = AsyncMock()
        instance.get.return_value = fake_resp

        with patch.object(settings_mod.httpx, "AsyncClient") as MC, \
             patch.object(settings_mod, "ConsentValidator") as MockCV, \
             patch.object(settings_mod, "LLMClient") as MockLLM:
            _mock_httpx(MC, instance)
            MockCV.return_value.validate_external_services_consent.return_value = True
            MockLLM.return_value.verify_api_key.return_value = False
            resp = client.post("/api/settings/secrets/verify", headers={"Authorization": "Bearer tok-abc"})

        assert resp.status_code == 200
        assert resp.json()["valid"] is False
