from __future__ import annotations

from pathlib import Path
from shutil import make_archive


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
    make_archive(
        base_name=str(archive_base),
        format="zip",
        root_dir=resolved.parent,
        base_dir=resolved.name,
    )
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
