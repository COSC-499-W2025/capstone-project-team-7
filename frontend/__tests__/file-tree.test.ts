import { describe, expect, it } from "vitest";
import { buildFileTree, formatFileSize } from "@/lib/file-tree";
import type { FileEntry } from "@/lib/file-tree";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function makeFile(path: string, size_bytes = 100): FileEntry {
  return { path, size_bytes, mime_type: "text/plain" };
}

// ---------------------------------------------------------------------------
// buildFileTree
// ---------------------------------------------------------------------------

describe("buildFileTree", () => {
  it("returns empty root for empty array", () => {
    const root = buildFileTree([]);
    expect(root.isDirectory).toBe(true);
    expect(root.children).toEqual([]);
    expect(root.fileCount).toBe(0);
    expect(root.size_bytes).toBe(0);
  });

  it("handles a single file at root level", () => {
    const root = buildFileTree([makeFile("README.md", 500)]);
    expect(root.children).toHaveLength(1);
    expect(root.children[0].name).toBe("README.md");
    expect(root.children[0].isDirectory).toBe(false);
    expect(root.children[0].size_bytes).toBe(500);
    expect(root.fileCount).toBe(1);
    expect(root.size_bytes).toBe(500);
  });

  it("creates nested directory nodes for deep paths", () => {
    const root = buildFileTree([makeFile("src/components/Button.tsx", 200)]);
    expect(root.children).toHaveLength(1);

    const src = root.children[0];
    expect(src.name).toBe("src");
    expect(src.isDirectory).toBe(true);

    const components = src.children[0];
    expect(components.name).toBe("components");
    expect(components.isDirectory).toBe(true);

    const file = components.children[0];
    expect(file.name).toBe("Button.tsx");
    expect(file.isDirectory).toBe(false);
  });

  it("shares parent directories for files with common paths", () => {
    const root = buildFileTree([
      makeFile("src/a.ts", 100),
      makeFile("src/b.ts", 200),
    ]);

    expect(root.children).toHaveLength(1);
    const src = root.children[0];
    expect(src.name).toBe("src");
    expect(src.children).toHaveLength(2);
  });

  it("aggregates size_bytes and fileCount bottom-up", () => {
    const root = buildFileTree([
      makeFile("src/a.ts", 100),
      makeFile("src/lib/b.ts", 200),
      makeFile("docs/readme.md", 50),
    ]);

    expect(root.fileCount).toBe(3);
    expect(root.size_bytes).toBe(350);

    const src = root.children.find((c) => c.name === "src")!;
    expect(src.fileCount).toBe(2);
    expect(src.size_bytes).toBe(300);
  });

  it("sorts directories before files, then alphabetically", () => {
    const root = buildFileTree([
      makeFile("zebra.txt"),
      makeFile("alpha/file.ts"),
      makeFile("apple.txt"),
      makeFile("beta/file.ts"),
    ]);

    const names = root.children.map((c) => c.name);
    // Directories first (alpha, beta), then files (apple.txt, zebra.txt)
    expect(names).toEqual(["alpha", "beta", "apple.txt", "zebra.txt"]);
  });
});

// ---------------------------------------------------------------------------
// formatFileSize
// ---------------------------------------------------------------------------

describe("formatFileSize", () => {
  it("formats 0 bytes", () => {
    expect(formatFileSize(0)).toBe("0 B");
  });

  it("formats bytes", () => {
    expect(formatFileSize(500)).toBe("500 B");
  });

  it("formats kilobytes", () => {
    expect(formatFileSize(1024)).toBe("1.0 KB");
    expect(formatFileSize(1536)).toBe("1.5 KB");
  });

  it("formats megabytes", () => {
    expect(formatFileSize(1048576)).toBe("1.0 MB");
  });

  it("formats gigabytes", () => {
    expect(formatFileSize(1073741824)).toBe("1.0 GB");
  });
});
