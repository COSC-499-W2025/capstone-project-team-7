"""
Tests for the skill progress AI action handler (backend only, no TUI).
"""

from pathlib import Path
import sys
import json
import types
import pytest

# Add backend/src to path
backend_src_path = Path(__file__).parent.parent / "backend" / "src"
sys.path.insert(0, str(backend_src_path))

# Stub textual modules used in textual_app to avoid optional dependency
if "textual" not in sys.modules:  # pragma: no cover
    sys.modules["textual"] = types.SimpleNamespace()
    class _StubApp:
        def __init__(self, *args, **kwargs):
            pass
    class _StubBinding:
        def __init__(self, *args, **kwargs):
            pass
    sys.modules["textual.app"] = types.SimpleNamespace(App=_StubApp, ComposeResult=None)
    sys.modules["textual.binding"] = types.SimpleNamespace(Binding=_StubBinding)
    sys.modules["textual.containers"] = types.SimpleNamespace(Vertical=object, Horizontal=object, ScrollableContainer=object)
    sys.modules["textual.events"] = types.SimpleNamespace(Mount=object, Key=object)
    sys.modules["textual.driver"] = types.SimpleNamespace(Driver=object)
    sys.modules["textual.message"] = types.SimpleNamespace(Message=object)
    sys.modules["textual.message_pump"] = types.SimpleNamespace(MessagePump=object)
    modal_cls = type("ModalScreen", (object,), {"__class_getitem__": classmethod(lambda cls, item: cls)})
    sys.modules["textual.screen"] = types.SimpleNamespace(ModalScreen=modal_cls)
    sys.modules["textual.widgets"] = types.SimpleNamespace(
        Footer=object,
        Header=object,
        Label=object,
        ListItem=object,
        ListView=object,
        ProgressBar=object,
        Static=object,
        Button=object,
        Switch=object,
        Input=object,
        Log=object,
        TextLog=object,
    )
if "pypdf" not in sys.modules:  # pragma: no cover - optional dep stub
    errors_module = types.SimpleNamespace(PdfReadError=Exception)
    sys.modules["pypdf"] = types.SimpleNamespace(PdfReader=lambda *args, **kwargs: None, errors=errors_module)
    sys.modules["pypdf.errors"] = errors_module

from backend.src.cli.textual_app import PortfolioTextualApp
from backend.src.cli.state import ScanState, AIState


class FakeLLMClient:
    DEFAULT_MODEL = "gpt-4o-mini"

    def __init__(self, response: dict):
        self._response = response

    def _make_llm_call(self, messages, model=None, max_tokens=None, temperature=None):  # type: ignore
        return json.dumps(self._response)


def _make_app_with_state(timeline):
    app = PortfolioTextualApp()
    app._scan_state = ScanState()
    app._scan_state.skills_progress = {"timeline": timeline}
    app._ai_state = AIState()
    return app


class FakeScreen:
    def __init__(self):
        self.output = ""
        self.context = ""
        self.message = ""
        self.tone = ""

    def display_output(self, text, context=None, allow_horizontal=False):
        self.output = text
        self.context = context

    def set_message(self, message, tone="info"):
        self.message = message
        self.tone = tone


def test_skill_progress_ai_action_happy_path(monkeypatch):
    timeline = [{"period_label": "2024-01", "commits": 3, "top_skills": ["Testing"], "languages": {"Python": 1}}]
    app = _make_app_with_state(timeline)
    app._ai_state.client = FakeLLMClient(
        {
            "narrative": "January focused on testing.",
            "milestones": ["Added tests"],
            "strengths": ["Testing discipline"],
            "gaps": ["Coverage breadth"],
        }
    )

    # Stub out status updates to avoid UI dependencies
    monkeypatch.setattr(app, "_show_status", lambda *args, **kwargs: None)

    app._handle_skill_progress_summary()

    assert app._scan_state.skills_progress is not None
    summary = app._scan_state.skills_progress.get("summary")
    assert summary
    assert summary["narrative"].startswith("January")
    assert summary["milestones"] == ["Added tests"]


def test_skill_progress_ai_action_handles_missing_timeline(monkeypatch):
    app = _make_app_with_state([])
    app._ai_state.client = FakeLLMClient({})
    messages = []
    monkeypatch.setattr(app, "_show_status", lambda msg, tone="info": messages.append((msg, tone)))

    app._handle_skill_progress_summary()

    assert any("No skill progression timeline" in msg for msg, _ in messages)


@pytest.mark.asyncio
async def test_skill_progress_action_formats_timeline_and_summary(monkeypatch):
    timeline = [{"period_label": "2024-01", "commits": 3, "top_skills": ["Testing"], "languages": {"Python": 1}}]
    app = _make_app_with_state(timeline)
    app._ai_state.client = FakeLLMClient(
        {
            "narrative": "January focused on testing.",
            "milestones": ["Added tests"],
            "strengths": ["Testing discipline"],
            "gaps": ["Coverage breadth"],
        }
    )
    screen = FakeScreen()
    await app._handle_skill_progress_action(screen)

    assert "Skill progression timeline" in screen.output
    assert "AI summary" in screen.output
    assert screen.message.startswith("Skill progression and AI summary ready")

    summary = app._scan_state.skills_progress.get("summary")
    assert summary
    assert summary["strengths"] == ["Testing discipline"]


@pytest.mark.asyncio
async def test_skill_progress_action_handles_missing_timeline():
    app = _make_app_with_state([])
    screen = FakeScreen()

    await app._handle_skill_progress_action(screen)

    assert "No skill progression timeline available." in screen.output
    assert screen.tone == "warning"


@pytest.mark.asyncio
async def test_prepare_skill_progress_generates_summary(monkeypatch):
    timeline = [{"period_label": "2024-01", "commits": 3, "top_skills": ["Testing"], "languages": {"Python": 1}}]
    app = _make_app_with_state(timeline)
    app._ai_state.client = FakeLLMClient(
        {
            "narrative": "January focused on testing.",
            "milestones": ["Added tests"],
            "strengths": ["Testing discipline"],
            "gaps": ["Coverage breadth"],
        }
    )

    timeline_out, summary, note = await app._prepare_skill_progress()

    assert timeline_out
    assert summary is not None
    assert summary.narrative.startswith("January")
    assert note is None
    assert app._scan_state.skills_progress.get("summary")


@pytest.mark.asyncio
async def test_prepare_skill_progress_handles_no_code():
    app = PortfolioTextualApp()
    app._scan_state = ScanState()
    app._scan_state.code_file_count = 0
    app._ai_state = AIState()

    timeline, summary, note = await app._prepare_skill_progress()

    assert timeline is None
    assert summary is None
    assert note and "Run a scan" in note


@pytest.mark.asyncio
async def test_prepare_skill_progress_handles_bad_ai_json(monkeypatch):
    timeline = [{"period_label": "2024-01", "commits": 3, "top_skills": ["Testing"], "languages": {"Python": 1}}]
    app = _make_app_with_state(timeline)
    app._ai_state.client = FakeLLMClient("not-json")  # type: ignore[arg-type]

    timeline_out, summary, note = await app._prepare_skill_progress()

    assert timeline_out
    assert summary is None
    assert note == "AI summary unavailable: the response was not valid JSON. Please retry."
