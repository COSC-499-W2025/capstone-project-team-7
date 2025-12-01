from backend.src.auth.session import SupabaseAuth

class DummyResponse:
    def json(self):
        return {"user": {"email": "test@example.com"}}

def test_supabaseauth_signup_fallback(monkeypatch):
    auth = SupabaseAuth("url", "key")

    # Mocking _post to return a dummy response
    monkeypatch.setattr(auth, "_post", lambda *args, **kwargs: DummyResponse())

    # Mock login so we can assert it's called
    called = {}
    def fake_login(email, password):
        called["email"] = email
        called["password"] = password
        return "SESSION_OK"

    monkeypatch.setattr(auth, "login", fake_login)

    result = auth.signup("test@example.com", "mypassword123")

    assert result == "SESSION_OK"
    assert called["email"] == "test@example.com"
    assert called["password"] == "mypassword123"