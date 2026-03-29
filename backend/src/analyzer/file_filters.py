import re
from pathlib import Path

# Constants for file filtering
AI_BATCH_LOGIC_EXCLUDED_EXTS = {
    ".md", ".markdown", ".txt", ".rst", ".log",
    ".json", ".yml", ".yaml", ".toml", ".ini", ".cfg", ".conf",
    ".css", ".scss", ".sass", ".less", ".xml", ".svg", ".lock",
}

AI_BATCH_LOGIC_PREFERRED_EXTS = {
    ".py", ".ts", ".tsx", ".js", ".jsx", ".java", ".go", ".rs",
    ".cs", ".cpp", ".c", ".h", ".hpp", ".kt", ".swift", ".rb", ".php",
}

AI_BATCH_LOGIC_EXCLUDED_BASENAMES = {
    "package.json", "package-lock.json", "pnpm-lock.yaml", "yarn.lock",
    "tsconfig.json", "jsconfig.json", "next.config.mjs", "next.config.js",
    "vite.config.ts", "vite.config.js", "docker-compose.yml", "docker-compose.yaml",
    "dockerfile", "readme.md",
}

AI_BATCH_LOGIC_EXCLUDED_PATH_MARKERS = (
    "/docs/", "/doc/", "/assets/", "/styles/", "/css/", "/migrations/",
    "/scripts/", "/config/", "/settings/", "/.github/",
)

AI_BATCH_TEST_PATH_RE = re.compile(
    r"(?:^|[\\/])(?:test|tests|__tests__|spec)(?:[\\/]|$)|(?:^|[._-])(test|spec)(?:[._-]|$)",
    re.IGNORECASE,
)

AI_BATCH_GENERATED_OR_PACKAGE_PATH_MARKERS = {
    ".next",
    ".electron",
    ".cache",
    ".pnpm",
    ".yarn",
    ".turbo",
    ".parcel-cache",
    ".svelte-kit",
    ".nuxt",
    ".output",
    ".vercel",
    "node_modules",
    "site-packages",
    "dist-packages",
    "vendor",
}


def is_test_path(path_value: str) -> bool:
    return bool(AI_BATCH_TEST_PATH_RE.search(path_value or ""))


def is_generated_or_package_path(path_value: str) -> bool:
    normalized = str(path_value or "").replace("\\", "/").strip().lower().strip("/")
    if not normalized:
        return False

    parts = [segment for segment in normalized.split("/") if segment]
    if not parts:
        return False

    if any(segment in AI_BATCH_GENERATED_OR_PACKAGE_PATH_MARKERS for segment in parts):
        return True

    for segment in parts[:-1]:
        if segment.startswith(".") and len(segment) > 1:
            return True

    return False


def is_non_implementation_path(path_value: str) -> bool:
    normalized = "/" + str(path_value or "").replace("\\", "/").lower().lstrip("/")
    basename = Path(normalized).name
    ext = Path(basename).suffix.lower()

    if basename in AI_BATCH_LOGIC_EXCLUDED_BASENAMES:
        return True
    if ext in AI_BATCH_LOGIC_EXCLUDED_EXTS:
        return True
    if any(marker in normalized for marker in AI_BATCH_LOGIC_EXCLUDED_PATH_MARKERS):
        return True
    if basename.endswith(".config.ts") or basename.endswith(".config.js"):
        return True
    if basename.endswith(".config.mjs") or basename.endswith(".config.cjs"):
        return True
    return False
