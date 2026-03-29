/**
 * Shared utility for determining whether a file path is a test file,
 * generated package file, or non-implementation file.
 */

const TEST_PATH_RE = /(^|[\\/])(test|tests|__tests__|spec)([\\/]|$)|(^|[._-])(test|spec)([._-]|$)/i;

const GENERATED_OR_PACKAGE_MARKERS = new Set([
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
  "vendor",
  "site-packages",
  "dist-packages",
]);

const NON_IMPLEMENTATION_BASENAMES = new Set([
  "package.json",
  "package-lock.json",
  "pnpm-lock.yaml",
  "yarn.lock",
  "tsconfig.json",
  "jsconfig.json",
  "next.config.mjs",
  "next.config.js",
  "vite.config.ts",
  "vite.config.js",
  "docker-compose.yml",
  "docker-compose.yaml",
  "dockerfile",
  "readme.md",
]);

const NON_IMPLEMENTATION_EXTS = new Set([
  ".md", ".markdown", ".txt", ".rst", ".log",
  ".json", ".yml", ".yaml", ".toml", ".ini", ".cfg", ".conf",
  ".css", ".scss", ".sass", ".less", ".xml", ".svg", ".lock",
]);

const NON_IMPLEMENTATION_PATH_MARKERS = [
  "/docs/",
  "/doc/",
  "/assets/",
  "/styles/",
  "/css/",
  "/migrations/",
  "/scripts/",
  "/config/",
  "/settings/",
  "/.github/",
];

/**
 * Returns true if the path is likely a test or spec file.
 */
export const isTestPath = (pathValue?: string | null): boolean => {
  if (!pathValue) return false;
  return TEST_PATH_RE.test(pathValue);
};

/**
 * Returns true if the path is part of a generated directory, build output, or dependency package.
 */
export const isGeneratedOrPackagePath = (pathValue?: string | null): boolean => {
  if (!pathValue) return false;
  const normalized = pathValue.replace(/\\/g, "/").toLowerCase().replace(/^\/+|\/+$/g, "");
  if (!normalized) return false;

  const parts = normalized.split("/").filter(Boolean);
  
  if (parts.some((segment) => GENERATED_OR_PACKAGE_MARKERS.has(segment))) {
    return true;
  }

  // Check if any parent directory is a hidden folder
  return parts.slice(0, -1).some((segment) => segment.startsWith(".") && segment.length > 1);
};

/**
 * Returns true if the path is a config, doc, asset or other non-implementation file.
 */
export const isNonImplementationPath = (pathValue?: string | null): boolean => {
  if (!pathValue) return false;
  const normalized = pathValue.replace(/\\/g, "/").toLowerCase().replace(/^\/+|\/+$/g, "");
  if (!normalized) return false;

  const parts = normalized.split("/").filter(Boolean);
  const basename = parts[parts.length - 1] ?? "";

  if (NON_IMPLEMENTATION_BASENAMES.has(basename)) return true;
  
  if (
    basename.endsWith(".config.ts") || 
    basename.endsWith(".config.js") || 
    basename.endsWith(".config.mjs") || 
    basename.endsWith(".config.cjs")
  ) {
    return true;
  }
  
  const normalizedForMarker = `/${normalized}`;
  if (NON_IMPLEMENTATION_PATH_MARKERS.some((marker) => normalizedForMarker.includes(marker))) {
    return true;
  }

  const dotIdx = basename.lastIndexOf(".");
  const ext = dotIdx >= 0 ? basename.slice(dotIdx) : "";
  return NON_IMPLEMENTATION_EXTS.has(ext);
};
