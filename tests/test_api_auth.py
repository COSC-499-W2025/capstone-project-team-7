from fastapi.testclient import TestClient
import pytest

from backend.src.main import app
from api.dependencies import AuthContext, get_auth_context
import api.auth_routes as auth_routes
from auth.session import Session


client = TestClient(app)


async def _override_auth() -> AuthContext:
    return AuthContext(
        user_id="user-123",
        access_token="test-token",
        email="user@example.com",
    )


@pytest.fixture(autouse=True)
def override_auth_context():
    app.dependency_overrides[get_auth_context] = _override_auth
    yield
    app.dependency_overrides.clear()


def _make_session() -> Session:
    return Session(
        user_id="user-123",
        email="user@example.com",
        access_token="access-token",
        refresh_token="refresh-token",
    )


def test_login_returns_session(monkeypatch):
    session = _make_session()

    class DummyAuth:
        def login(self, email: str, password: str) -> Session:
            return session

    monkeypatch.setattr(auth_routes, "SupabaseAuth", lambda: DummyAuth())
    response = client.post(
        "/api/auth/login",
        json={"email": "user@example.com", "password": "secret"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["user_id"] == session.user_id
    assert payload["access_token"] == session.access_token
    assert payload["refresh_token"] == session.refresh_token


def test_signup_returns_session(monkeypatch):
    session = _make_session()

    class DummyAuth:
        def signup(self, email: str, password: str) -> Session:
            return session

    monkeypatch.setattr(auth_routes, "SupabaseAuth", lambda: DummyAuth())
    response = client.post(
        "/api/auth/signup",
        json={"email": "user@example.com", "password": "secret"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["user_id"] == session.user_id
    assert payload["email"] == session.email


def test_refresh_returns_session(monkeypatch):
    session = _make_session()

    class DummyAuth:
        def refresh_session(self, refresh_token: str) -> Session:
            return session

    monkeypatch.setattr(auth_routes, "SupabaseAuth", lambda: DummyAuth())
    response = client.post(
        "/api/auth/refresh",
        json={"refresh_token": "refresh-token"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["access_token"] == session.access_token
    assert payload["refresh_token"] == session.refresh_token


def test_get_session():
    response = client.get("/api/auth/session")
    assert response.status_code == 200
    payload = response.json()
    assert payload["user_id"] == "user-123"
    assert payload["email"] == "user@example.com"


def test_expired_token_returns_unauthorized(monkeypatch):
    """Test that expired or invalid tokens are rejected with 401 Unauthorized"""
    
    # Override auth context to raise exception simulating expired token
    async def override_auth_expired() -> AuthContext:
        from fastapi import HTTPException, status
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "unauthorized", "message": "Invalid or expired access token"},
        )
    
    app.dependency_overrides[get_auth_context] = override_auth_expired
    
    try:
        response = client.get("/api/auth/session")
        # Should return 401 Unauthorized when token is expired
        assert response.status_code == 401
        payload = response.json()
        assert "detail" in payload
    finally:
        app.dependency_overrides.clear()
