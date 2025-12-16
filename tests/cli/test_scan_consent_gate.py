from __future__ import annotations

import pytest

pytest.importorskip("textual")

from backend.src.auth.session import Session
from backend.src.cli.state import ConsentState, ScanState, SessionState
from backend.src.cli.textual_app import PortfolioTextualApp


@pytest.mark.asyncio
async def test_run_scan_requires_data_access_consent(tmp_path):
    """Verify scans are blocked when required consent is missing."""
    app = PortfolioTextualApp.__new__(PortfolioTextualApp)  # bypass Textual App __init__
    app._session_state = SessionState()
    app._session_state.session = Session(user_id="user-1", email="tester@example.com", access_token="token")
    app._consent_state = ConsentState()
    app._consent_state.record = None
    app._consent_state.error = "Required consent has not been granted yet."
    app._scan_state = ScanState()

    def _fail_run_scan(*args, **kwargs):
        raise AssertionError("run_scan should not be called when consent is missing")

    app._scan_service = type("StubScanService", (), {"run_scan": _fail_run_scan})()
    app._refresh_consent_state = lambda: None
    app._refresh_current_detail = lambda: None

    messages = []
    app._show_status = lambda msg, tone="info": messages.append((msg, tone))

    await app._run_scan(tmp_path, relevant_only=True)

    assert messages, "Status message should be emitted when consent is missing."
    assert any("consent" in msg.lower() for msg, _ in messages)
