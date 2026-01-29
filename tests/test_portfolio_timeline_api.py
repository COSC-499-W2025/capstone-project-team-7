from fastapi.testclient import TestClient
import pytest
import sys
import types
from pathlib import Path

# Stub python-magic for environments without the optional dependency.
if "magic" not in sys.modules:
    sys.modules["magic"] = types.SimpleNamespace(
        from_buffer=lambda *args, **kwargs: "application/zip"
    )

PROJECT_ROOT = Path(__file__).resolve().parent.parent
BACKEND_SRC = PROJECT_ROOT / "backend" / "src"
if str(BACKEND_SRC) not in sys.path:
    sys.path.insert(0, str(BACKEND_SRC))
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

sys.modules["cli"] = types.ModuleType("cli")
sys.modules["cli"].__path__ = [str(BACKEND_SRC / "cli")]

from backend.src.main import app
from api.dependencies import AuthContext, get_auth_context
from api.portfolio_routes import get_portfolio_timeline_service


client = TestClient(app)


class FakeTimelineService:
    def get_skills_timeline(self, user_id):
        return [
            {
                "period_label": "2024-01",
                "skills": ["Python"],
                "commits": 3,
                "projects": ["Alpha"],
            }
        ]

    def get_portfolio_chronology(self, user_id):
        return {
            "projects": [
                {
                    "project_id": "p1",
                    "name": "Alpha",
                    "start_date": "2024-01-15T00:00:00Z",
                    "end_date": None,
                    "duration_days": None,
                }
            ],
            "skills": [
                {
                    "period_label": "2024-01",
                    "skills": ["Python"],
                    "commits": 3,
                    "projects": ["Alpha"],
                }
            ],
        }


async def _override_auth() -> AuthContext:
    return AuthContext(user_id="user-123", access_token="test-token")


@pytest.fixture(autouse=True)
def override_dependencies():
    app.dependency_overrides[get_auth_context] = _override_auth
    app.dependency_overrides[get_portfolio_timeline_service] = lambda: FakeTimelineService()
    yield
    app.dependency_overrides.clear()


def test_skills_timeline_schema():
    response = client.get("/api/skills/timeline")
    assert response.status_code == 200
    payload = response.json()
    assert "items" in payload
    assert isinstance(payload["items"], list)
    assert payload["items"][0]["period_label"] == "2024-01"
    assert payload["items"][0]["skills"] == ["Python"]


def test_portfolio_chronology_schema():
    response = client.get("/api/portfolio/chronology")
    assert response.status_code == 200
    payload = response.json()
    assert "projects" in payload
    assert "skills" in payload
    assert payload["projects"][0]["project_id"] == "p1"
    assert payload["skills"][0]["period_label"] == "2024-01"


def test_missing_auth_returns_401():
    app.dependency_overrides.clear()
    response = client.get("/api/skills/timeline")
    assert response.status_code == 401
