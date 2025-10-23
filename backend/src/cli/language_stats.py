from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Iterable

from ..scanner.models import FileMetadata

LANGUAGE_EXTENSIONS: dict[str, str] = {
    ".py": "Python",
    ".pyi": "Python",
    ".js": "JavaScript",
    ".mjs": "JavaScript",
    ".cjs": "JavaScript",
    ".jsx": "JavaScript",
    ".ts": "TypeScript",
    ".tsx": "TypeScript",
    ".java": "Java",
    ".kt": "Kotlin",
    ".kts": "Kotlin",
    ".cs": "C#",
    ".c": "C",
    ".h": "C/C++ Header",
    ".hpp": "C++",
    ".hh": "C++",
    ".cpp": "C++",
    ".cc": "C++",
    ".go": "Go",
    ".rs": "Rust",
    ".rb": "Ruby",
    ".php": "PHP",
    ".swift": "Swift",
    ".scala": "Scala",
    ".sh": "Shell",
    ".bash": "Shell",
    ".zsh": "Shell",
    ".ps1": "PowerShell",
    ".bat": "Batch",
    ".sql": "SQL",
    ".r": "R",
    ".jl": "Julia",
    ".lua": "Lua",
    ".json": "JSON",
    ".jsonc": "JSON",
    ".yaml": "YAML",
    ".yml": "YAML",
    ".xml": "XML",
    ".html": "HTML",
    ".htm": "HTML",
    ".css": "CSS",
    ".scss": "Sass",
    ".sass": "Sass",
    ".less": "Less",
    ".md": "Markdown",
    ".mdx": "Markdown",
    ".txt": "Text",
}


def summarize_languages(files: Iterable[FileMetadata]) -> list[dict[str, object]]:
    """Aggregate language statistics (files, bytes, percentages) for the given metadata."""
    totals: dict[str, dict[str, float]] = defaultdict(lambda: {"files": 0, "bytes": 0})

    for meta in files:
        extension = Path(meta.path).suffix.lower()
        # Only keep files we can confidently map; binary/artifact assets are ignored.
        language = LANGUAGE_EXTENSIONS.get(extension)
        if language is None:
            continue
        stats = totals[language]
        stats["files"] += 1
        stats["bytes"] += meta.size_bytes

    total_files = sum(stats["files"] for stats in totals.values())
    total_bytes = sum(stats["bytes"] for stats in totals.values())

    breakdown: list[dict[str, object]] = []
    if total_files == 0:
        return breakdown
    for language, stats in totals.items():
        files_count = int(stats["files"])
        bytes_count = int(stats["bytes"])
        file_percent = (files_count / total_files * 100) if total_files else 0.0
        byte_percent = (bytes_count / total_bytes * 100) if total_bytes else 0.0
        breakdown.append(
            {
                "language": language,
                "files": files_count,
                "file_percent": round(file_percent, 2),
                "bytes": bytes_count,
                "byte_percent": round(byte_percent, 2),
            }
        )

    breakdown.sort(key=lambda item: item["bytes"], reverse=True)
    return breakdown
