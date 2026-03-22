"""
Project Auto-Categorizer

Classifies projects into categories (Web Application, API, Data Science,
CLI Tool, Game, etc.) based on file patterns, directory structure, and
detected languages.  Uses a rule-based weighted scoring approach.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class CategoryResult:
    """Result of project categorization."""
    category: str
    label: str
    confidence: float
    all_scores: Dict[str, float] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Scoring rules per category
#
# Each rule set contains:
#   file_names  – exact basename matches with point values
#   extensions  – extension matches (points multiplied by min(count, 10))
#   directories – directory name matches anywhere in the path tree
#   languages   – language name matches (only scored if the language
#                 represents > 5 % of the codebase)
# ---------------------------------------------------------------------------

_RULES: Dict[str, Dict[str, Any]] = {
    "web_app": {
        "label": "Web Application",
        "file_names": {
            "next.config.js": 5, "next.config.ts": 5, "next.config.mjs": 5,
            "nuxt.config.js": 5, "nuxt.config.ts": 5,
            "angular.json": 5,
            "svelte.config.js": 5, "svelte.config.ts": 5,
            "vite.config.js": 3, "vite.config.ts": 3,
            "webpack.config.js": 2,
            "tailwind.config.js": 2, "tailwind.config.ts": 2,
            "postcss.config.js": 1,
            "index.html": 2,
        },
        "extensions": {
            ".html": 1, ".css": 1, ".scss": 1, ".sass": 1,
            ".vue": 3, ".svelte": 3, ".jsx": 2, ".tsx": 1,
        },
        "directories": {
            "components": 2, "pages": 2, "views": 2,
            "templates": 2, "public": 1, "static": 1,
        },
        "languages": {"JavaScript": 1, "TypeScript": 1},
    },
    "api_backend": {
        "label": "API / Backend Service",
        "file_names": {
            "swagger.yml": 4, "swagger.yaml": 4,
            "openapi.yml": 4, "openapi.yaml": 4, "openapi.json": 4,
        },
        "extensions": {},
        "directories": {
            "api": 3, "routes": 3, "controllers": 3,
            "middleware": 2, "handlers": 2, "endpoints": 3,
        },
        "languages": {"Python": 1, "Java": 1, "Go": 2, "Rust": 1},
    },
    "data_science": {
        "label": "Data Science / ML",
        "file_names": {},
        "extensions": {
            ".ipynb": 5, ".csv": 1, ".parquet": 2, ".h5": 3, ".pkl": 2,
        },
        "directories": {"notebooks": 4, "models": 2, "experiments": 3},
        "languages": {"Python": 1, "R": 2},
    },
    "cli_tool": {
        "label": "CLI Tool",
        "file_names": {
            "__main__.py": 3, "cli.py": 4, "cli.ts": 4, "cli.js": 4,
        },
        "extensions": {},
        "directories": {"bin": 2, "cmd": 2},
        "languages": {},
    },
    "game": {
        "label": "Game",
        "file_names": {"project.godot": 8},
        "extensions": {
            ".gd": 5, ".gdscript": 5, ".unity": 5,
            ".prefab": 3, ".shader": 2,
        },
        "directories": {
            "Assets": 3, "Scenes": 3, "Sprites": 3, "Prefabs": 3,
        },
        "languages": {},
    },
    "mobile_app": {
        "label": "Mobile App",
        "file_names": {
            "AndroidManifest.xml": 5, "Info.plist": 4,
            "pubspec.yaml": 5, "app.json": 2,
        },
        "extensions": {".swift": 2, ".kt": 2, ".dart": 3},
        "directories": {"android": 3, "ios": 3},
        "languages": {"Swift": 2, "Kotlin": 2, "Dart": 3},
    },
    "desktop_app": {
        "label": "Desktop Application",
        "file_names": {
            "electron.js": 5, "forge.config.js": 4,
        },
        "extensions": {},
        "directories": {"electron": 3},
        "languages": {},
    },
    "library": {
        "label": "Library / Package",
        "file_names": {
            "setup.py": 2, "setup.cfg": 2, "pyproject.toml": 1,
        },
        "extensions": {},
        "directories": {"src": 1, "lib": 1},
        "languages": {},
    },
    "devops": {
        "label": "DevOps / Infrastructure",
        "file_names": {
            "Jenkinsfile": 4, ".gitlab-ci.yml": 3, "cloudbuild.yaml": 3,
            "docker-compose.yml": 2, "docker-compose.yaml": 2,
            "Dockerfile": 1,
        },
        "extensions": {".tf": 5, ".tfvars": 3, ".hcl": 3},
        "directories": {
            "terraform": 5, "ansible": 5, "k8s": 4,
            "kubernetes": 4, "helm": 4, "deploy": 2, "infra": 3,
        },
        "languages": {},
    },
    "documentation": {
        "label": "Documentation / Static Site",
        "file_names": {
            "mkdocs.yml": 6, "_config.yml": 4,
            "hugo.toml": 6, "hugo.yaml": 6,
            "docusaurus.config.js": 6,
        },
        "extensions": {".md": 0.3, ".rst": 1, ".adoc": 1},
        "directories": {"docs": 1, "content": 1, "posts": 2},
        "languages": {},
    },
}

import logging

logger = logging.getLogger(__name__)


def safe_classify_project(
    files: list,
    languages: Optional[List[Dict[str, Any]]] = None,
) -> Optional[CategoryResult]:
    """
    Classify a project, returning ``None`` on failure or if the category is
    unknown.  Logs a warning on error.  This is the shared entry-point that
    route handlers should call instead of duplicating try/except blocks.
    """
    try:
        file_paths = [f.path for f in files if hasattr(f, "path")]
        result = classify_project(file_paths, languages)
        if result.category != "unknown":
            logger.info(
                "Project categorized as: %s (confidence=%s)",
                result.label, result.confidence,
            )
            return result
    except Exception as e:
        logger.warning("Project categorization failed: %s", e)
    return None


def classify_project(
    file_paths: List[str],
    languages: Optional[List[Dict[str, Any]]] = None,
) -> CategoryResult:
    """
    Classify a project into a category based on its files and languages.

    Args:
        file_paths: Relative file paths within the project.
        languages:  List of dicts with ``name`` and ``percentage`` keys
                    (as returned by the language extraction step).

    Returns:
        A :class:`CategoryResult` with category key, human-readable label,
        and confidence score (0.0 – 1.0).
    """
    scores: Dict[str, float] = {cat: 0.0 for cat in _RULES}

    # Build lookup structures from file paths
    file_names_set: set[str] = set()
    extensions_count: Dict[str, int] = {}
    directories_set: set[str] = set()

    for path in file_paths:
        base = os.path.basename(path)
        file_names_set.add(base)

        _, ext = os.path.splitext(base)
        if ext:
            ext_lower = ext.lower()
            extensions_count[ext_lower] = extensions_count.get(ext_lower, 0) + 1

        parts = path.replace("\\", "/").split("/")
        for part in parts[:-1]:
            if part:
                directories_set.add(part)

    # Language lookup
    lang_map: Dict[str, float] = {}
    if languages:
        for entry in languages:
            name = entry.get("name", "")
            pct = entry.get("percentage", 0.0)
            if name:
                lang_map[name] = float(pct)

    # Score each category
    for cat_key, rules in _RULES.items():
        score = 0.0

        for fname, weight in rules["file_names"].items():
            if fname in file_names_set:
                score += weight

        for ext, weight in rules["extensions"].items():
            count = extensions_count.get(ext, 0)
            if count > 0:
                score += weight * min(count, 10)

        for dirname, weight in rules["directories"].items():
            if dirname in directories_set:
                score += weight

        for lang, weight in rules.get("languages", {}).items():
            if lang in lang_map and lang_map[lang] > 5:
                score += weight

        scores[cat_key] = score

    best_cat = max(scores, key=lambda k: scores[k])
    best_score = scores[best_cat]

    if best_score == 0:
        return CategoryResult(
            category="unknown",
            label="Unknown",
            confidence=0.0,
            all_scores=scores,
        )

    total = sum(scores.values())
    confidence = round(best_score / total, 2) if total > 0 else 0.0

    return CategoryResult(
        category=best_cat,
        label=_RULES[best_cat]["label"],
        confidence=confidence,
        all_scores=scores,
    )
