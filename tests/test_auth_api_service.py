import httpx
import pytest

from backend.src.cli.services.auth_api_service import AuthAPIService
from backend.src.auth.session import AuthError


class DummyResponse:
    def __init__(self, status_code=200, payload=None, text="") -> None:
        self.status_code = status_code
        self._payload = payload
        self.text = text

    def json(self):
        if self._payload is None:
            raise ValueError("No JSON")
        return self._payload


class DummyClient:
    def __init__(self, response: DummyResponse) -> None:
        self._response = response
        self.requests = []

    def request(self, method, path, json=None):
        self.requests.append((method, path, json))
        return self._response

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


def test_login_returns_session(monkeypatch):
    response = DummyResponse(
        payload={
            "user_id": "user-123",
            "email": "user@example.com",
            "access_token": "token",
            "refresh_token": "refresh",
        }
    )
    client = DummyClient(response)
    monkeypatch.setattr(httpx, "Client", lambda *args, **kwargs: client)

    service = AuthAPIService(base_url="http://test")
    session = service.login("user@example.com", "secret")

    assert session.user_id == "user-123"
    assert session.email == "user@example.com"
    assert session.access_token == "token"
    assert session.refresh_token == "refresh"
    assert client.requests == [
        ("POST", "/api/auth/login", {"email": "user@example.com", "password": "secret"})
    ]


def test_refresh_requires_token():
    service = AuthAPIService(base_url="http://test")
    with pytest.raises(AuthError, match="Refresh token missing"):
        service.refresh_session("")


def test_login_handles_error_response(monkeypatch):
    response = DummyResponse(status_code=401, payload={"detail": {"message": "Invalid"}})
    client = DummyClient(response)
    monkeypatch.setattr(httpx, "Client", lambda *args, **kwargs: client)

    service = AuthAPIService(base_url="http://test")
    with pytest.raises(AuthError, match="Invalid"):
        service.login("user@example.com", "secret")


def test_login_requires_session_fields(monkeypatch):
    response = DummyResponse(payload={"email": "user@example.com"})
    client = DummyClient(response)
    monkeypatch.setattr(httpx, "Client", lambda *args, **kwargs: client)

    service = AuthAPIService(base_url="http://test")
    with pytest.raises(AuthError, match="missing session data"):
        service.login("user@example.com", "secret")
