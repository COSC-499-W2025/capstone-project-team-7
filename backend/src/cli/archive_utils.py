from __future__ import annotations

import json
import os
import zipfile
from pathlib import Path
from typing import Any, Dict, Iterator, Set, Tuple

from ..scanner.models import ScanPreferences

_ZIP_EXCLUDE_DIRS = {
    ".git",
    ".hg",
    ".svn",
    ".idea",
    ".vscode",
    ".venv",
    "venv",
    "env",
    "__pycache__",
    "node_modules",
    "dist",
    "build",
    ".tmp_archives",
}

_ZIP_EXCLUDE_FILES = {".DS_Store"}


def _derive_excluded_dirs(preferences: ScanPreferences | None) -> Set[str]:
    if preferences and preferences.excluded_dirs is not None:
        # Treat user configuration as authoritative; always keep tmp archive cache out.
        return set(preferences.excluded_dirs) | {".tmp_archives"}
    return set(_ZIP_EXCLUDE_DIRS)


def ensure_zip(target: Path, *, preferences: ScanPreferences | None = None) -> Path:
    """Return a zip path, archiving directories into .tmp_archives/ when needed."""
    resolved = target.expanduser().resolve()
    if resolved.suffix.lower() == ".zip" and resolved.is_file():
        return resolved
    if not resolved.exists():
        raise ValueError(f"{resolved} does not exist")
    if not resolved.is_dir():
        raise ValueError(f"{resolved} is neither a directory nor a .zip file")

    project_root = _project_root()
    cache_dir = project_root / ".tmp_archives"
    cache_dir.mkdir(parents=True, exist_ok=True)

    archive_base = cache_dir / resolved.name
    archive_path = archive_base.with_suffix(".zip")
    metadata_path = archive_base.with_suffix(".json")

    exclude_dirs = _derive_excluded_dirs(preferences)
    follow_symlinks = (
        preferences.follow_symlinks
        if preferences and preferences.follow_symlinks is not None
        else False
    )

    cached_metadata = _load_cached_metadata(metadata_path)
    if archive_path.exists() and cached_metadata:
        snapshot = _compute_snapshot(resolved, exclude_dirs, follow_symlinks)
        if _snapshot_matches(snapshot, cached_metadata):
            return archive_path

    if archive_path.exists():
        archive_path.unlink()

    snapshot = _zip_directory(resolved, archive_path, exclude_dirs, follow_symlinks)
    _write_cached_metadata(metadata_path, snapshot)
    return archive_path


def _iter_project_files(
    root: Path,
    exclude_dirs: Set[str],
    follow_symlinks: bool,
) -> Iterator[Tuple[Path, Path]]:
    root_name = root.name
    for current_root, dirs, files in os.walk(root, followlinks=follow_symlinks):
        dirs[:] = [d for d in dirs if d not in exclude_dirs]
        current_path = Path(current_root)
        rel_dir = current_path.relative_to(root)
        for filename in files:
            if filename in _ZIP_EXCLUDE_FILES:
                continue
            full_path = current_path / filename
            archive_rel = Path(root_name) / rel_dir / filename
            yield full_path, archive_rel


def _compute_snapshot(
    root: Path,
    exclude_dirs: Set[str],
    follow_symlinks: bool,
) -> Dict[str, Any]:
    total_files = 0
    total_bytes = 0
    latest_mtime = 0.0
    for full_path, _ in _iter_project_files(root, exclude_dirs, follow_symlinks):
        try:
            stat = full_path.stat()
        except OSError:
            continue
        total_files += 1
        total_bytes += stat.st_size
        if stat.st_mtime > latest_mtime:
            latest_mtime = stat.st_mtime
    return _build_snapshot_dict(root, total_files, total_bytes, latest_mtime, exclude_dirs, follow_symlinks)


def _zip_directory(
    root: Path,
    archive_path: Path,
    exclude_dirs: Set[str],
    follow_symlinks: bool,
) -> Dict[str, Any]:
    total_files = 0
    total_bytes = 0
    latest_mtime = 0.0

    with zipfile.ZipFile(
        archive_path,
        mode="w",
        compression=zipfile.ZIP_DEFLATED,
        allowZip64=True,
    ) as zf:
        for full_path, archive_rel in _iter_project_files(root, exclude_dirs, follow_symlinks):
            try:
                stat = full_path.stat()
            except OSError:
                # Skip files that disappear during archive creation.
                continue
            # Persist the relative path inside the archive so parse_zip sees the project structure.
            zf.write(full_path, archive_rel.as_posix())
            total_files += 1
            total_bytes += stat.st_size
            if stat.st_mtime > latest_mtime:
                latest_mtime = stat.st_mtime

    return _build_snapshot_dict(root, total_files, total_bytes, latest_mtime, exclude_dirs, follow_symlinks)


def _build_snapshot_dict(
    root: Path,
    total_files: int,
    total_bytes: int,
    latest_mtime: float,
    exclude_dirs: Set[str],
    follow_symlinks: bool,
) -> Dict[str, Any]:
    return {
        "source": str(root),
        "files": total_files,
        "bytes": total_bytes,
        "latest_mtime": latest_mtime,
        "excluded_dirs": sorted(exclude_dirs),
        "follow_symlinks": follow_symlinks,
    }


def _load_cached_metadata(metadata_path: Path) -> Dict[str, Any] | None:
    try:
        with metadata_path.open("r", encoding="utf-8") as fp:
            return json.load(fp)
    except FileNotFoundError:
        return None
    except json.JSONDecodeError:
        return None


def _write_cached_metadata(metadata_path: Path, payload: Dict[str, Any]) -> None:
    try:
        with metadata_path.open("w", encoding="utf-8") as fp:
            json.dump(payload, fp)
    except Exception:
        # Caching is best-effort; ignore filesystem errors.
        pass


def _snapshot_matches(snapshot: Dict[str, Any], metadata: Dict[str, Any]) -> bool:
    required_keys = ("source", "files", "bytes", "latest_mtime", "excluded_dirs", "follow_symlinks")
    for key in required_keys:
        if metadata.get(key) != snapshot.get(key):
            return False
    return True


def _project_root() -> Path:
    """Best-effort project root detection for placing cached archives."""
    here = Path(__file__).resolve()
    candidates = [Path.cwd()]
    parents = list(here.parents)
    if len(parents) >= 3:
        candidates.append(parents[3])
    for candidate in candidates:
        if candidate.exists() and candidate.is_dir():
            return candidate
    return Path.cwd()
