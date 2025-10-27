from __future__ import annotations

import json
import os
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

from src.cli.archive_utils import ensure_zip
from src.cli.language_stats import summarize_languages
from src.scanner.errors import CorruptArchiveError, UnsupportedArchiveError
from src.scanner.models import FileMetadata, ParseResult
from src.scanner.parser import parse_zip


def _make_project(tmp_path: Path) -> tuple[Path, dict[str, Path]]:
    root = tmp_path / "project"
    src = root / "src"
    docs = root / "docs"
    src.mkdir(parents=True)
    docs.mkdir(parents=True)

    files = {
        "src/main.py": src / "main.py",
        "docs/README.md": docs / "README.md",
    }
    files["src/main.py"].write_text("print('hello world')\n")
    files["docs/README.md"].write_text("# Documentation\n")

    return root, files


@pytest.fixture
def project_tree(tmp_path: Path) -> tuple[Path, dict[str, Path]]:
    return _make_project(tmp_path)


@pytest.fixture
def nested_zip(tmp_path: Path) -> tuple[Path, dict[str, Path]]:
    root, files = _make_project(tmp_path)

    archive = tmp_path / "project.zip"
    with zipfile.ZipFile(archive, "w") as zf:
        for arcname, file_path in files.items():
            zf.write(file_path, arcname)

    return archive, files


def test_parse_zip_collects_metadata(nested_zip: tuple[Path, dict[str, Path]]):
    archive, files = nested_zip

    result = parse_zip(archive)

    assert isinstance(result, ParseResult)
    assert result.issues == []
    assert len(result.files) == len(files)
    paths = {meta.path for meta in result.files}
    assert paths == set(files.keys())

    sample_meta = next(meta for meta in result.files if meta.path == "src/main.py")
    assert isinstance(sample_meta, FileMetadata)
    assert sample_meta.size_bytes == files["src/main.py"].stat().st_size
    assert sample_meta.mime_type in {"text/x-python", "text/plain"}
    assert sample_meta.modified_at.tzinfo is not None
    assert sample_meta.created_at.tzinfo is not None
    assert result.summary["files_processed"] == len(files)


def test_parse_zip_rejects_non_zip(tmp_path: Path):
    fake_archive = tmp_path / "data.txt"
    fake_archive.write_text("not a zip")

    with pytest.raises(UnsupportedArchiveError) as exc_info:
        parse_zip(fake_archive)

    assert exc_info.value.code == "UNSUPPORTED_FILE_TYPE"


def test_parse_zip_rejects_corrupted_zip(tmp_path: Path):
    archive = tmp_path / "bad.zip"
    archive.write_bytes(b"\x50\x4b\x03")  # truncated header

    with pytest.raises(CorruptArchiveError) as exc_info:
        parse_zip(archive)

    assert exc_info.value.code == "CORRUPT_OR_UNZIP_ERROR"


def test_parse_zip_blocks_path_traversal(tmp_path: Path):
    archive = tmp_path / "unsafe.zip"
    with zipfile.ZipFile(archive, "w") as zf:
        info = zipfile.ZipInfo("../../evil.txt")
        zf.writestr(info, "malicious")

    with pytest.raises(CorruptArchiveError) as exc_info:
        parse_zip(archive)

    assert exc_info.value.code == "CORRUPT_OR_UNZIP_ERROR"


def test_cli_outputs_json(
    nested_zip: tuple[Path, dict[str, Path]], project_root: Path, backend_root: Path
):
    archive, files = nested_zip
    command = [
        sys.executable,
        "-m",
        "src.cli.parse_zip",
        "--json",
        str(archive),
    ]
    env = os.environ.copy()
    env["PYTHONPATH"] = (
        f"{backend_root}{os.pathsep}{env['PYTHONPATH']}"
        if "PYTHONPATH" in env
        else str(backend_root)
    )
    proc = subprocess.run(
        command,
        capture_output=True,
        text=True,
        cwd=project_root,
        env=env,
    )

    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    assert payload["summary"]["files_processed"] == len(files)
    returned_paths = {item["path"] for item in payload["files"]}
    assert returned_paths == set(files.keys())


def test_cli_accepts_directory(
    project_tree: tuple[Path, dict[str, Path]], project_root: Path, backend_root: Path
):
    root, files = project_tree
    command = [
        sys.executable,
        "-m",
        "src.cli.parse_zip",
        "--json",
        str(root),
    ]
    env = os.environ.copy()
    env["PYTHONPATH"] = (
        f"{backend_root}{os.pathsep}{env['PYTHONPATH']}"
        if "PYTHONPATH" in env
        else str(backend_root)
    )
    proc = subprocess.run(
        command,
        capture_output=True,
        text=True,
        cwd=project_root,
        env=env,
    )

    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    returned_paths = {item["path"] for item in payload["files"]}
    normalized = {
        path.split("/", 1)[1] if path.startswith(f"{root.name}/") else path
        for path in returned_paths
    }
    assert normalized == set(files.keys())


@pytest.fixture
def zip_with_dummy_files(tmp_path: Path) -> tuple[Path, dict[str, Path], dict[str, Path]]:
    root = tmp_path / "complex_project"
    relevant = {
        "src/app.py": root / "src" / "app.py",
        "docs/README.md": root / "docs" / "README.md",
        "reports/project_overview.pdf": root / "reports" / "project_overview.pdf",
        "presentations/demo_pitch.pptx": root / "presentations" / "demo_pitch.pptx",
    }
    irrelevant = {
        "__pycache__/app.cpython-311.pyc": root / "__pycache__" / "app.cpython-311.pyc",
        "dist/bundle.js": root / "dist" / "bundle.js",
        "node_modules/pkg/index.js": root / "node_modules" / "pkg" / "index.js",
        "assets/logo.png": root / "assets" / "logo.png",
        "tmp/archive.bin": root / "tmp" / "archive.bin",
    }

    for path in list(relevant.values()) + list(irrelevant.values()):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("placeholder\n")

    archive = tmp_path / "complex_project.zip"
    with zipfile.ZipFile(archive, "w") as zf:
        for arcname, file_path in {**relevant, **irrelevant}.items():
            zf.write(file_path, arcname)

    return archive, relevant, irrelevant


def test_parse_zip_relevant_only_filters(zip_with_dummy_files):
    archive, relevant, irrelevant = zip_with_dummy_files

    result = parse_zip(archive, relevant_only=True)

    paths = {meta.path for meta in result.files}
    assert paths == set(relevant.keys())
    assert result.summary["files_processed"] == len(relevant)
    assert result.summary["filtered_out"] == len(irrelevant)


def test_ensure_zip_skips_excluded_dirs(tmp_path: Path):
    project = tmp_path / "sample"
    src = project / "src"
    src.mkdir(parents=True)
    ignored_dir = project / ".venv"
    ignored_dir.mkdir()
    (src / "app.py").write_text("print('hi')\n")
    (ignored_dir / "ignored.txt").write_text("do not zip\n")

    archive = ensure_zip(project)

    try:
        with zipfile.ZipFile(archive) as zf:
            names = set(zf.namelist())
        assert f"{project.name}/src/app.py" in names
        assert f"{project.name}/.venv/ignored.txt" not in names
    finally:
        archive.unlink(missing_ok=True)


def test_language_stats_ignores_unknown_extensions(tmp_path: Path):
    from datetime import datetime, timezone

    meta_known = FileMetadata(
        path="src/app.py",
        size_bytes=10,
        mime_type="text/x-python",
        created_at=datetime.now(timezone.utc),
        modified_at=datetime.now(timezone.utc),
    )
    meta_unknown = FileMetadata(
        path="assets/logo.png",
        size_bytes=5000,
        mime_type="image/png",
        created_at=datetime.now(timezone.utc),
        modified_at=datetime.now(timezone.utc),
    )

    breakdown = summarize_languages([meta_known, meta_unknown])
    assert len(breakdown) == 1
    assert breakdown[0]["language"] == "Python"
    assert breakdown[0]["files"] == 1


def test_cli_respects_relevant_only_flag(
    zip_with_dummy_files: tuple[Path, dict[str, Path], dict[str, Path]],
    project_root: Path,
    backend_root: Path,
):
    archive, relevant, irrelevant = zip_with_dummy_files
    command = [
        sys.executable,
        "-m",
        "src.cli.parse_zip",
        "--relevant-only",
        "--json",
        str(archive),
    ]
    env = os.environ.copy()
    env["PYTHONPATH"] = (
        f"{backend_root}{os.pathsep}{env['PYTHONPATH']}"
        if "PYTHONPATH" in env
        else str(backend_root)
    )
    proc = subprocess.run(
        command,
        capture_output=True,
        text=True,
        cwd=project_root,
        env=env,
    )

    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    assert payload["summary"]["files_processed"] == len(relevant)
    assert payload["summary"]["filtered_out"] == len(irrelevant)
    returned_paths = {item["path"] for item in payload["files"]}
    assert returned_paths == set(relevant.keys())


def test_cli_code_flag_reports_languages(
    zip_with_dummy_files: tuple[Path, dict[str, Path], dict[str, Path]],
    project_root: Path,
    backend_root: Path,
):
    archive, relevant, _ = zip_with_dummy_files
    command = [
        sys.executable,
        "-m",
        "src.cli.parse_zip",
        "--relevant-only",
        "--json",
        "--code",
        str(archive),
    ]
    env = os.environ.copy()
    env["PYTHONPATH"] = (
        f"{backend_root}{os.pathsep}{env['PYTHONPATH']}"
        if "PYTHONPATH" in env
        else str(backend_root)
    )
    proc = subprocess.run(
        command,
        capture_output=True,
        text=True,
        cwd=project_root,
        env=env,
    )

    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    languages = payload["summary"].get("languages")
    assert languages, "Expected language breakdown in summary"
    language_map = {entry["language"]: entry for entry in languages}
    assert "Python" in language_map
    assert language_map["Python"]["files"] == 1
    total_percent = sum(entry["file_percent"] for entry in languages)
    assert pytest.approx(total_percent, rel=1e-3, abs=0.05) == 100


def test_parse_archive_script_accepts_relevant_only(
    zip_with_dummy_files: tuple[Path, dict[str, Path], dict[str, Path]],
    project_root: Path,
    backend_root: Path,
):
    archive, relevant, irrelevant = zip_with_dummy_files
    script = project_root / "scripts" / "parse_archive.py"
    command = [
        sys.executable,
        str(script),
        "--json",
        "--relevant-only",
        "--code",
        str(archive),
    ]
    env = os.environ.copy()
    env["PYTHONPATH"] = (
        f"{backend_root}{os.pathsep}{env['PYTHONPATH']}"
        if "PYTHONPATH" in env
        else str(backend_root)
    )
    proc = subprocess.run(
        command,
        capture_output=True,
        text=True,
        cwd=project_root,
        env=env,
    )

    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    summary = payload["summary"]
    assert summary["files_processed"] == len(relevant)
    assert summary["filtered_out"] == len(irrelevant)
    languages = summary.get("languages")
    assert languages, "Expected language breakdown in script output"
    language_map = {entry["language"]: entry for entry in languages}
    assert "Python" in language_map
    paths = {item["path"] for item in payload["files"]}
    assert paths == set(relevant.keys())
