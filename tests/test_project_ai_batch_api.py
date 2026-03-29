import base64
import json
from pathlib import Path
from typing import Any, Dict, Optional
import sys
import types

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

# Stub python-magic for environments where libmagic is unavailable.
if "magic" not in sys.modules:
    fake_magic = types.ModuleType("magic")

    class _FakeMagic:
        def __init__(self, *args, **kwargs):
            pass

        def from_buffer(self, *_args, **_kwargs):
            return "application/zip"

    fake_magic.Magic = _FakeMagic
    sys.modules["magic"] = fake_magic

import api.project_routes as project_routes


app = FastAPI()
app.include_router(project_routes.router)
client = TestClient(app)


def _make_token(sub: str) -> str:
    def b64u(obj: str) -> str:
        return base64.urlsafe_b64encode(obj.encode()).decode().rstrip("=")

    header = b64u(json.dumps({"alg": "HS256", "typ": "JWT"}))
    payload = b64u(json.dumps({"sub": sub}))
    return f"{header}.{payload}.sig"


class FakeProjectsService:
    def __init__(self, project: Dict[str, Any]):
        self.project = project

    def apply_access_token(self, _token: Optional[str]) -> None:
        return None

    def get_project_scan(self, _user_id: str, project_id: str):
        if project_id == self.project["id"]:
            return self.project
        return None

    def patch_ai_batch(self, _user_id: str, project_id: str, ai_batch: Dict[str, Any]) -> None:
        if project_id != self.project["id"]:
            raise RuntimeError("project not found")
        scan_data = self.project.setdefault("scan_data", {})
        scan_data["ai_batch"] = ai_batch

    def patch_ai_analysis(self, _user_id: str, project_id: str, ai_analysis: Dict[str, Any]) -> None:
        if project_id != self.project["id"]:
            raise RuntimeError("project not found")
        scan_data = self.project.setdefault("scan_data", {})
        scan_data["ai_analysis"] = ai_analysis


class FakeConsentValidator:
    def validate_external_services_consent(self, _user_id: str) -> bool:
        return True


class FakeClient:
    def __init__(self, batch_result: Optional[Dict[str, Any]] = None, llm_json: Optional[Dict[str, Any]] = None):
        self.batch_result = batch_result or {}
        self.llm_json = llm_json or {}

    def summarize_scan_with_ai(self, **_kwargs):
        progress_callback = _kwargs.get("progress_callback")
        if callable(progress_callback):
            progress_callback("Initializing analysis for 1 files…")
            progress_callback("Single-project: Batch 1/1 (1 files)…")
        return self.batch_result

    def _make_llm_call(self, *_args, **_kwargs):
        return json.dumps(self.llm_json)

    def make_llm_call(self, *_args, **_kwargs):
        return self._make_llm_call(*_args, **_kwargs)


@pytest.fixture
def setup_project_service(monkeypatch, tmp_path: Path):
    project_id = "11111111-1111-1111-1111-111111111111"
    source_dir = tmp_path / "repo"
    source_dir.mkdir(parents=True, exist_ok=True)
    (source_dir / "main.py").write_text("print('hello')\n", encoding="utf-8")

    project = {
        "id": project_id,
        "project_name": "AI Batch Project",
        "scan_data": {
            "project_source_path": str(source_dir),
            "summary": {"total_files": 1, "total_size_bytes": 20},
            "languages": ["Python"],
            "files": [{"path": "main.py", "size_bytes": 20, "mime_type": "text/x-python"}],
            "code_analysis": {"total_files": 1},
        },
    }

    fake_service = FakeProjectsService(project)
    monkeypatch.setattr(project_routes, "_projects_service", fake_service)
    monkeypatch.setattr(project_routes, "ConsentValidator", FakeConsentValidator)

    async def fake_hydrate(_user_id: str, _access_token: str):
        return FakeClient(
            batch_result={
                "project_analysis": {"analysis": "Batch project summary."},
                "file_summaries": [
                    {
                        "file_path": "main.py",
                        "analysis": "Main entrypoint and core flow.",
                    }
                ],
                "media_briefings": [],
            }
        )

    monkeypatch.setattr(project_routes, "get_or_hydrate_llm_client", fake_hydrate)
    return fake_service


@pytest.fixture(autouse=True)
def clear_batch_progress_state():
    with project_routes._ai_batch_progress_lock:
        project_routes._ai_batch_progress.clear()
    yield
    with project_routes._ai_batch_progress_lock:
        project_routes._ai_batch_progress.clear()


def test_run_ai_batch_and_fetch_cached(setup_project_service):
    token = _make_token("user-1")
    project_id = setup_project_service.project["id"]

    run_resp = client.post(
        f"/api/projects/{project_id}/ai-batch",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert run_resp.status_code == 200
    run_data = run_resp.json()
    assert run_data["status"] == "used:batch"
    assert run_data["cached"] is False
    assert run_data["result"] is not None
    assert isinstance(run_data.get("status_messages"), list)
    assert any("Batch" in msg or "Initializing" in msg for msg in run_data.get("status_messages", []))

    get_resp = client.get(
        f"/api/projects/{project_id}/ai-batch",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert get_resp.status_code == 200
    get_data = get_resp.json()
    assert get_data["status"] == "used:batch_cached"
    assert get_data["cached"] is True
    assert isinstance(get_data["result"], dict)


def test_ai_batch_status_endpoint_reports_live_snapshot(setup_project_service):
    token = _make_token("user-status")
    project_id = setup_project_service.project["id"]

    before_resp = client.get(
        f"/api/projects/{project_id}/ai-batch/status",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert before_resp.status_code == 200
    before_data = before_resp.json()
    assert before_data["status"] == "idle"
    assert before_data["status_messages"] == []

    run_resp = client.post(
        f"/api/projects/{project_id}/ai-batch",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert run_resp.status_code == 200

    after_resp = client.get(
        f"/api/projects/{project_id}/ai-batch/status",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert after_resp.status_code == 200
    after_data = after_resp.json()
    assert after_data["status"] == "used:batch"
    assert isinstance(after_data["status_messages"], list)
    assert any("Batch" in msg or "Initializing" in msg for msg in after_data["status_messages"])


def test_ai_batch_status_terminal_snapshot_expires_after_ttl(setup_project_service, monkeypatch):
    token = _make_token("user-status-ttl")
    project_id = setup_project_service.project["id"]

    clock = {"now": 1000.0}
    monkeypatch.setattr(project_routes, "AI_BATCH_PROGRESS_TERMINAL_TTL_SEC", 30)
    monkeypatch.setattr(project_routes.time, "time", lambda: clock["now"])

    run_resp = client.post(
        f"/api/projects/{project_id}/ai-batch",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert run_resp.status_code == 200

    clock["now"] = 1010.0
    during_ttl_resp = client.get(
        f"/api/projects/{project_id}/ai-batch/status",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert during_ttl_resp.status_code == 200
    assert during_ttl_resp.json()["status"] == "used:batch"

    clock["now"] = 1031.0
    expired_resp = client.get(
        f"/api/projects/{project_id}/ai-batch/status",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert expired_resp.status_code == 200
    assert expired_resp.json()["status"] == "idle"


def test_ai_analysis_uses_cached_batch_result(monkeypatch, tmp_path: Path):
    project_id = "22222222-2222-2222-2222-222222222222"
    project = {
        "id": project_id,
        "project_name": "Cached Batch Project",
        "scan_data": {
            "summary": {"total_files": 2, "total_size_bytes": 100},
            "languages": ["Python"],
            "code_analysis": {"total_files": 2},
            "ai_batch": {
                "project_analysis": {"analysis": "Cached batch summary."},
                "file_summaries": [
                    {"file_path": "a.py", "analysis": "Core logic."},
                    {"file_path": "b.py", "analysis": "Helpers."},
                ],
            },
        },
    }
    fake_service = FakeProjectsService(project)
    monkeypatch.setattr(project_routes, "_projects_service", fake_service)
    monkeypatch.setattr(project_routes, "ConsentValidator", FakeConsentValidator)

    async def fake_hydrate(_user_id: str, _access_token: str):
        return FakeClient()

    monkeypatch.setattr(project_routes, "get_or_hydrate_llm_client", fake_hydrate)

    token = _make_token("user-2")
    resp = client.post(
        f"/api/projects/{project_id}/ai-analysis",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["llm_status"] == "used:batch_cached"
    assert data["cached"] is False
    assert data["result"]["overall_summary"] == "Cached batch summary."
    assert isinstance(data["result"].get("categories"), list)


def test_ai_analysis_falls_back_to_snippets_when_batch_unavailable(monkeypatch):
    project_id = "33333333-3333-3333-3333-333333333333"
    project = {
        "id": project_id,
        "project_name": "Fallback Project",
        "scan_data": {
            "summary": {"total_files": 1, "total_lines": 10},
            "languages": ["Python"],
            "code_analysis": {"total_files": 1},
            "files": [{"path": "main.py", "size_bytes": 12, "mime_type": "text/x-python"}],
            "file_snippets": [{"path": "main.py", "content": "def add(a, b):\n    return a + b\n"}],
            # no project_source_path on purpose -> batch unavailable
        },
    }
    fake_service = FakeProjectsService(project)
    monkeypatch.setattr(project_routes, "_projects_service", fake_service)
    monkeypatch.setattr(project_routes, "ConsentValidator", FakeConsentValidator)

    async def fake_hydrate(_user_id: str, _access_token: str):
        return FakeClient(
            llm_json={
                "overall_summary": "Snippet fallback summary.",
                "code_analysis": {
                    "summary": "Code looks clean.",
                    "insights": ["Simple function", "Readable logic", "No obvious issues"],
                },
            }
        )

    monkeypatch.setattr(project_routes, "get_or_hydrate_llm_client", fake_hydrate)

    token = _make_token("user-3")
    resp = client.post(
        f"/api/projects/{project_id}/ai-analysis",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["result"]["overall_summary"] == "Snippet fallback summary."
    assert data["llm_status"].startswith("fallback:snippets_batch_unavailable|")
    assert "used:path(1 files)" in data["llm_status"]


def test_run_ai_batch_missing_cached_result_returns_missing(monkeypatch):
    project_id = "44444444-4444-4444-4444-444444444444"
    project = {
        "id": project_id,
        "project_name": "No Batch Yet",
        "scan_data": {
            "summary": {"total_files": 0},
        },
    }
    fake_service = FakeProjectsService(project)
    monkeypatch.setattr(project_routes, "_projects_service", fake_service)

    token = _make_token("user-4")
    resp = client.get(
        f"/api/projects/{project_id}/ai-batch",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "missing"
    assert data["cached"] is False


def test_run_ai_batch_returns_403_when_consent_not_granted(setup_project_service, monkeypatch):
    class DeniedConsentValidator:
        def validate_external_services_consent(self, _user_id: str) -> bool:
            return False

    monkeypatch.setattr(project_routes, "ConsentValidator", DeniedConsentValidator)

    token = _make_token("user-consent-denied")
    project_id = setup_project_service.project["id"]
    resp = client.post(
        f"/api/projects/{project_id}/ai-batch",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert resp.status_code == 403
    assert resp.json().get("detail") == "External services consent not granted."


def test_run_ai_batch_returns_422_when_consent_check_fails(setup_project_service, monkeypatch):
    class BrokenConsentValidator:
        def validate_external_services_consent(self, _user_id: str) -> bool:
            raise RuntimeError("consent backend unavailable")

    monkeypatch.setattr(project_routes, "ConsentValidator", BrokenConsentValidator)

    token = _make_token("user-consent-error")
    project_id = setup_project_service.project["id"]
    resp = client.post(
        f"/api/projects/{project_id}/ai-batch",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert resp.status_code == 422
    assert resp.json().get("detail") == "Consent check failed. Please retry."


def test_run_ai_batch_returns_422_when_api_key_missing(setup_project_service, monkeypatch):
    async def fake_hydrate_none(_user_id: str, _access_token: str):
        return None

    monkeypatch.setattr(project_routes, "get_or_hydrate_llm_client", fake_hydrate_none)

    token = _make_token("user-no-key")
    project_id = setup_project_service.project["id"]
    resp = client.post(
        f"/api/projects/{project_id}/ai-batch",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert resp.status_code == 422
    assert resp.json().get("detail") == "No API key verified. Please verify your key in Settings."


def test_resolve_project_source_path_falls_back_to_project_path(tmp_path: Path):
    source_dir = tmp_path / "repo"
    source_dir.mkdir(parents=True, exist_ok=True)
    (source_dir / "main.py").write_text("print('ok')\n", encoding="utf-8")

    project = {
        "project_path": str(source_dir),
    }
    scan_data = {
        "files": [{"path": "main.py", "size_bytes": 12, "mime_type": "text/x-python"}],
    }

    resolved = project_routes._resolve_project_source_path(project, scan_data)
    assert resolved is not None
    assert resolved.resolve() == source_dir.resolve()


def test_resolve_project_source_path_rejects_non_matching_dir(tmp_path: Path):
    unrelated = tmp_path / "unrelated"
    unrelated.mkdir(parents=True, exist_ok=True)
    (unrelated / "other.py").write_text("print('x')\n", encoding="utf-8")

    project = {
        "project_path": str(unrelated),
    }
    scan_data = {
        "files": [{"path": "main.py", "size_bytes": 12, "mime_type": "text/x-python"}],
    }

    resolved = project_routes._resolve_project_source_path(project, scan_data)
    assert resolved is None


def test_resolve_project_source_path_accepts_prefixed_scan_paths(tmp_path: Path):
    source_dir = tmp_path / "capstone-project-team-7"
    (source_dir / "backend" / "src").mkdir(parents=True, exist_ok=True)
    (source_dir / "backend" / "src" / "main.py").write_text("print('ok')\n", encoding="utf-8")

    project = {
        "project_path": str(source_dir),
    }
    # Path includes duplicated root segment pattern seen from archive-like saves.
    scan_data = {
        "files": [{"path": "capstone-project-team-7/backend/src/main.py", "size_bytes": 12, "mime_type": "text/x-python"}],
    }

    resolved = project_routes._resolve_project_source_path(project, scan_data)
    assert resolved is not None
    assert resolved.resolve() == source_dir.resolve()


def test_build_relevant_files_for_batch_strips_prefixed_paths(tmp_path: Path):
    source_dir = tmp_path / "repo"
    (source_dir / "backend" / "src").mkdir(parents=True, exist_ok=True)
    (source_dir / "backend" / "src" / "main.py").write_text("print('ok')\n", encoding="utf-8")

    scan_data = {
        "files": [
            {
                "path": "repo/backend/src/main.py",
                "size_bytes": 12,
                "mime_type": "text/x-python",
            }
        ]
    }

    files = project_routes._build_relevant_files_for_batch(scan_data, source_path=source_dir)
    assert files
    assert files[0]["path"] == "backend/src/main.py"


def test_adapt_batch_to_ai_result_filters_tests_and_drops_issues():
    batch_result = {
        "project_analysis": {
            "analysis": "Structured summary",
            "overview": {"summary": "Overview text"},
            "technical_highlights": {
                "overview": "Highlights overview",
                "technologies": [{"name": "Python", "usage": "Main application logic"}],
                "patterns": ["Dependency injection"],
                "highlights": ["Clear separation of concerns"],
            },
            "key_modules": [
                {
                    "title": "Core",
                    "summary": "Main logic",
                    "key_files": [
                        "src/core.py",
                        "tests/test_core.py",
                        "src/core.spec.ts",
                        "frontend/package.json",
                        "frontend/package-lock.json",
                        "frontend/next.config.mjs",
                        "backend/setup.cfg",
                        "frontend/.next/server/app/page.js",
                        "electron/.electron/runtime/main.js",
                    ],
                }
            ],
            "issues_and_risks": [{"title": "Old issue field"}],
            "insights": {
                "surprising_observation": {
                    "text": "The codebase already has strong, extensive test automation.",
                    "confidence": 0.8,
                }
            },
            "security_and_vulnerability": {
                "findings": [
                    {
                        "text": "Authentication paths in src/core.py should be validated for consistent authorization checks.",
                        "confidence": 0.72,
                    },
                    {
                        "text": "Dependency manifests should be scanned for known CVEs during CI.",
                        "confidence": 0.68,
                    },
                ]
            },
            "project_scores": {"test_coverage": 82},
        },
        "file_summaries": [
            {"file_path": "src/core.py", "analysis": "Main logic"},
            {"file_path": "tests/test_core.py", "analysis": "Tests"},
            {"file_path": "frontend/package.json", "analysis": "Dependency manifest"},
            {"file_path": "frontend/package-lock.json", "analysis": "NPM lockfile"},
            {"file_path": "frontend/next.config.mjs", "analysis": "Next.js config"},
            {"file_path": "backend/setup.cfg", "analysis": "Tooling config"},
            {"file_path": "frontend/.next/server/app/page.js", "analysis": "Generated bundle output"},
            {"file_path": "electron/.electron/runtime/main.js", "analysis": "Packaged runtime output"},
            {"file_path": "src/helpers.ts", "analysis": "Helper logic"},
        ],
    }

    adapted = project_routes._adapt_batch_to_ai_result(batch_result, active_categories=[])

    assert "issues_and_risks" not in adapted
    assert isinstance(adapted.get("technical_highlights"), dict)
    assert adapted.get("key_files") is not None
    assert all("test" not in str(item.get("file_path", "")).lower() for item in adapted["key_files"])
    assert all("/.next/" not in str(item.get("file_path", "")).replace("\\", "/").lower() for item in adapted["key_files"])
    assert all("/.electron/" not in str(item.get("file_path", "")).replace("\\", "/").lower() for item in adapted["key_files"])
    assert all("package.json" not in str(item.get("file_path", "")).lower() for item in adapted["key_files"])
    assert all("package-lock.json" not in str(item.get("file_path", "")).lower() for item in adapted["key_files"])
    assert all("config" not in str(item.get("file_path", "")).lower() for item in adapted["key_files"])
    assert all("setup.cfg" not in str(item.get("file_path", "")).lower() for item in adapted["key_files"])

    key_modules = adapted.get("key_modules") or []
    assert key_modules
    first_mod_files = key_modules[0].get("key_files") or []
    assert "src/core.py" in first_mod_files
    assert all("test" not in f.lower() and "spec" not in f.lower() for f in first_mod_files)
    assert all("/.next/" not in f.replace("\\", "/").lower() for f in first_mod_files)
    assert all("/.electron/" not in f.replace("\\", "/").lower() for f in first_mod_files)
    assert all("package.json" not in f.lower() for f in first_mod_files)
    assert all("package-lock.json" not in f.lower() for f in first_mod_files)
    assert all("next.config" not in f.lower() and "setup.cfg" not in f.lower() for f in first_mod_files)
    security_block = adapted.get("security_and_vulnerability") or {}
    findings = security_block.get("findings") or []
    assert len(findings) == 2
    assert "suggestions" not in adapted


def test_run_ai_batch_passes_enriched_scan_summary(monkeypatch, tmp_path: Path):
    project_id = "55555555-5555-5555-5555-555555555555"
    source_dir = tmp_path / "repo"
    (source_dir / "src").mkdir(parents=True, exist_ok=True)
    (source_dir / "tests").mkdir(parents=True, exist_ok=True)
    (source_dir / "docs").mkdir(parents=True, exist_ok=True)
    (source_dir / "src" / "main.py").write_text("print('ok')\n", encoding="utf-8")
    (source_dir / "tests" / "test_main.py").write_text("def test_ok():\n    assert True\n", encoding="utf-8")
    (source_dir / "docs" / "README.md").write_text("# docs\n", encoding="utf-8")

    project = {
        "id": project_id,
        "project_name": "Enriched Summary Project",
        "scan_data": {
            "project_source_path": str(source_dir),
            "summary": {"total_files": 3, "total_size_bytes": 120, "total_lines": 50},
            "languages": ["Python"],
            "code_analysis": {
                "total_files": 3,
                "total_lines": 50,
                "comment_lines": 7,
                "functions": 5,
                "classes": 1,
                "avg_complexity": 2.0,
                "dead_code": {"total": 1},
            },
            "files": [
                {"path": "src/main.py", "size_bytes": 20, "mime_type": "text/x-python"},
                {"path": "tests/test_main.py", "size_bytes": 30, "mime_type": "text/x-python"},
                {"path": "docs/README.md", "size_bytes": 15, "mime_type": "text/markdown"},
            ],
        },
    }
    fake_service = FakeProjectsService(project)
    monkeypatch.setattr(project_routes, "_projects_service", fake_service)
    monkeypatch.setattr(project_routes, "ConsentValidator", FakeConsentValidator)

    captured_scan_summary: Dict[str, Any] = {}

    class CapturingClient(FakeClient):
        def summarize_scan_with_ai(self, **kwargs):
            nonlocal captured_scan_summary
            captured_scan_summary = kwargs.get("scan_summary", {})
            return {
                "project_analysis": {"analysis": "ok"},
                "file_summaries": [{"file_path": "src/main.py", "analysis": "logic"}],
            }

    async def fake_hydrate(_user_id: str, _access_token: str):
        return CapturingClient()

    monkeypatch.setattr(project_routes, "get_or_hydrate_llm_client", fake_hydrate)

    token = _make_token("user-enriched")
    resp = client.post(
        f"/api/projects/{project_id}/ai-batch",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert resp.status_code == 200
    assert isinstance(captured_scan_summary.get("code_metrics"), dict)
    assert isinstance(captured_scan_summary.get("file_profile"), dict)
    assert "test_file_count" in captured_scan_summary["file_profile"]
    assert "top_extensions" in captured_scan_summary["file_profile"]
