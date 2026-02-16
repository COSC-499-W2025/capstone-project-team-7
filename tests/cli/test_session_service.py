from __future__ import annotations

import base64
import json
import time
from pathlib import Path

from backend.src.auth.consent_validator import ConsentValidator
from backend.src.auth.session import Session
from services.session_service import SessionService


def test_load_session_round_trip(tmp_path: Path) -> None:
    session_path = tmp_path / "session.json"
    session_data = {
        "user_id": "abc123",
        "email": "test@example.com",
        "access_token": "token",
        "refresh_token": "refresh",
    }
    session_path.write_text(json.dumps(session_data), encoding="utf-8")

    service = SessionService()
    loaded = service.load_session(session_path)

    assert loaded is not None
    assert loaded.user_id == "abc123"
    assert loaded.email == "test@example.com"
    assert loaded.refresh_token == "refresh"


def test_persist_and_clear_session(tmp_path: Path) -> None:
    session_path = tmp_path / "session.json"
    service = SessionService()
    service.persist_session(
        session_path,
        Session(user_id="u", email="e@example.com", access_token="tok", refresh_token="ref"),
    )
    assert session_path.exists()

    service.clear_session(session_path)
    assert not session_path.exists()


def test_refresh_consent_translates_errors(monkeypatch) -> None:
    validator = ConsentValidator()

    def fake_check(user_id: str):
        raise ValueError("boom")

    monkeypatch.setattr(validator, "check_required_consent", fake_check)
    service = SessionService()
    record, error = service.refresh_consent(validator, "user")

    assert record is None
    assert "Unable to verify consent" in error


def test_needs_refresh_detects_expiration() -> None:
    service = SessionService()

    def make_token(exp_offset: int) -> str:
        header = base64.urlsafe_b64encode(json.dumps({"alg": "none", "typ": "JWT"}).encode()).rstrip(b"=").decode()
        payload = base64.urlsafe_b64encode(json.dumps({"exp": int(time.time()) + exp_offset}).encode()).rstrip(b"=").decode()
        return f"{header}.{payload}."

    expired_session = Session(
        user_id="u",
        email="e@example.com",
        access_token=make_token(-120),
        refresh_token="ref",
    )
    fresh_session = Session(
        user_id="u",
        email="e@example.com",
        access_token=make_token(3600),
        refresh_token="ref",
    )

    assert service.needs_refresh(expired_session) is True
    assert service.needs_refresh(fresh_session) is False
