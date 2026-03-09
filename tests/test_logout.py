from fastapi.testclient import TestClient
import pytest

from backend.src.main import app
from api.dependencies import AuthContext, get_auth_context
import api.auth_routes as auth_routes
from auth.session import AuthError


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


def test_logout_returns_200_with_valid_token(monkeypatch):
    """Test that logout endpoint returns 200 with valid token"""

    class DummyAuth:
        def sign_out(self, access_token: str) -> None:
            # Mock successful logout
            if not access_token:
                raise AuthError("Access token missing")
            return None

    monkeypatch.setattr(auth_routes, "SupabaseAuth", lambda: DummyAuth())
    response = client.post("/api/auth/logout", headers={"Authorization": "Bearer test-token"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True


def test_logout_handles_invalid_token_gracefully(monkeypatch):
    """Test that logout handles invalid/expired token gracefully"""

    class DummyAuth:
        def sign_out(self, access_token: str) -> None:
            raise AuthError("Invalid or expired token")

    monkeypatch.setattr(auth_routes, "SupabaseAuth", lambda: DummyAuth())
    response = client.post("/api/auth/logout", headers={"Authorization": "Bearer test-token"})
    # Should return 401 Unauthorized for auth errors
    assert response.status_code == 401
    payload = response.json()
    assert "detail" in payload


def test_sign_out_method_calls_supabase_logout_endpoint(monkeypatch):
    """Test that sign_out method calls Supabase logout endpoint"""

    captured = {"method": None, "path": None, "data": None, "token": None}

    class DummyAuth:
        def _request_with_auth(self, method, path, data, access_token):
            captured["method"] = method
            captured["path"] = path
            captured["data"] = data
            captured["token"] = access_token
            return {}

        def sign_out(self, access_token: str) -> None:
            from auth.session import AUTH_LOGOUT_PATH

            if not access_token:
                raise AuthError("Access token missing. Cannot sign out.")
            self._request_with_auth("POST", AUTH_LOGOUT_PATH, {}, access_token)

    monkeypatch.setattr(auth_routes, "SupabaseAuth", lambda: DummyAuth())
    response = client.post("/api/auth/logout", headers={"Authorization": "Bearer test-token"})
    assert response.status_code == 200
    assert captured["method"] == "POST"
    assert captured["path"] == "/auth/v1/logout"
    assert captured["data"] == {}
    assert captured["token"] == "test-token"


def test_logout_requires_authorization_header():
    """Test that logout endpoint requires bearer auth."""

    app.dependency_overrides.clear()
    response = client.post("/api/auth/logout")
    assert response.status_code == 401
    payload = response.json()
    assert "detail" in payload
    assert payload["detail"]["code"] == "unauthorized"
