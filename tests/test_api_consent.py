from fastapi.testclient import TestClient
import pytest

from backend.src.main import app
from api.dependencies import AuthContext, get_auth_context
from backend.src.auth import consent as consent_store


client = TestClient(app)


async def _override_auth() -> AuthContext:
    return AuthContext(user_id="user-123", access_token="test-token")


@pytest.fixture(autouse=True)
def override_auth_context():
    app.dependency_overrides[get_auth_context] = _override_auth
    yield
    app.dependency_overrides.clear()
    consent_store.clear_user_consents_cache("user-123")


def test_get_consent_defaults_to_false():
    response = client.get("/api/consent")
    assert response.status_code == 200
    payload = response.json()
    assert payload["user_id"] == "user-123"
    assert payload["data_access"] is False
    assert payload["external_services"] is False
    assert payload["updated_at"]


def test_set_consent_updates_status():
    response = client.post(
        "/api/consent",
        json={"data_access": True, "external_services": False},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["data_access"] is True
    assert payload["external_services"] is False

    follow_up = client.get("/api/consent")
    assert follow_up.status_code == 200
    follow_payload = follow_up.json()
    assert follow_payload["data_access"] is True
    assert follow_payload["external_services"] is False


def test_set_consent_rejects_external_without_data_access():
    response = client.post(
        "/api/consent",
        json={"data_access": False, "external_services": True},
    )
    assert response.status_code == 400
    payload = response.json()
    assert payload["detail"]["code"] == "validation_error"


def test_get_consent_notice():
    response = client.get("/api/consent/notice?service=external_services")
    assert response.status_code == 200
    payload = response.json()
    assert payload["service"] == "external_services"
    assert payload["privacy_notice"]
    assert payload["options"]


def test_missing_auth_header_returns_401():
    app.dependency_overrides.clear()
    response = client.get("/api/consent")
    assert response.status_code == 401
    payload = response.json()
    assert payload["detail"]["code"] == "unauthorized"
