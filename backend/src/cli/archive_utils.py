from __future__ import annotations

import os
import zipfile
from pathlib import Path

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


def ensure_zip(target: Path) -> Path:
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
    if archive_path.exists():
        archive_path.unlink()

    # Allow ZIP64 so large archives (e.g., screenshots/binaries) do not overflow.
    with zipfile.ZipFile(
        archive_path,
        mode="w",
        compression=zipfile.ZIP_DEFLATED,
        allowZip64=True,
    ) as zf:
        root_name = resolved.name
        for current_root, dirs, files in os.walk(resolved):
            # Prune heavyweight or user-specific directories before we descend.
            dirs[:] = [d for d in dirs if d not in _ZIP_EXCLUDE_DIRS]
            current_path = Path(current_root)
            rel_dir = current_path.relative_to(resolved)
            for filename in files:
                if filename in _ZIP_EXCLUDE_FILES:
                    continue
                full_path = current_path / filename
                archive_rel = Path(root_name) / rel_dir / filename
                # Persist the relative path inside the archive so parse_zip sees the project structure.
                zf.write(full_path, archive_rel.as_posix())
    return archive_path


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
