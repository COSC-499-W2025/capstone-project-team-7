import pytest
import asyncio
from backend.src.cli.textual_app import PortfolioTextualApp
from backend.src.cli.screens import SignupSubmitted

class DummySession:
    def __init__(self):
        self.email = "newuser@example.com"
        self.access_token = "token123"
        self.user_id = "abc123"

@pytest.mark.asyncio
async def test_handle_signup_success(monkeypatch):
    app = PortfolioTextualApp()

    # Mock _get_auth() to return an object with a signup method
    class DummyAuth:
        def signup(self, email, password):
            return DummySession()

    monkeypatch.setattr(app, "_get_auth", lambda: DummyAuth())

    # Capture whether finalize was called
    called = {}

    def fake_finalize(session, msg):
        called["session"] = session
        called["msg"] = msg

    monkeypatch.setattr(app, "_finalize_session", fake_finalize)

    # Run the signup handler
    await app._handle_signup("newuser@example.com", "password123")

    assert called["session"].email == "newuser@example.com"
    assert "Account created for" in called["msg"]

@pytest.mark.asyncio
async def test_handle_signup_invalid_input(monkeypatch):
    app = PortfolioTextualApp()

    # Track what status message is shown
    messages = []
    monkeypatch.setattr(app, "_show_status", lambda m, t: messages.append(m))

    await app._handle_signup("", "short")

    assert "Enter both email and password" in messages[0]