from __future__ import annotations

import sys
from pathlib import Path


def _ensure_project_on_path() -> None:
    """Make sure the installed package can locate the source tree in editable installs."""
    project_root = Path(__file__).resolve().parents[1]
    candidates = [
        project_root / "src",
        project_root.parent / "src",
        project_root.parent / "backend" / "src",
    ]
    for candidate in candidates:
        if candidate.exists():
            parent = candidate if candidate.is_dir() else candidate.parent
            sys.path.insert(0, str(parent))
            return


def main() -> int:
    try:
        from src.cli.parse_zip import main as entrypoint
    except ModuleNotFoundError:
        _ensure_project_on_path()
        from src.cli.parse_zip import main as entrypoint
    return entrypoint()


if __name__ == "__main__":
    raise SystemExit(main())
