import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { FileTreeView } from "@/components/project/file-tree-view";
import type { FileEntry } from "@/lib/file-tree";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function makeFile(
  path: string,
  size_bytes = 100,
  mime_type = "text/plain"
): FileEntry {
  return { path, size_bytes, mime_type };
}

const sampleFiles: FileEntry[] = [
  makeFile("src/index.ts", 500, "text/typescript"),
  makeFile("src/components/Button.tsx", 1200, "text/tsx"),
  makeFile("src/components/Card.tsx", 800, "text/tsx"),
  makeFile("README.md", 300, "text/markdown"),
];

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("FileTreeView", () => {
  it("shows empty state when no files", () => {
    render(<FileTreeView files={[]} />);
    expect(screen.getByText("No files available.")).toBeInTheDocument();
  });

  it("renders file summary with count and size", () => {
    render(<FileTreeView files={sampleFiles} />);
    expect(screen.getByText(/4 files/)).toBeInTheDocument();
  });

  it("renders top-level directory names", () => {
    render(<FileTreeView files={sampleFiles} />);
    expect(screen.getByText("src")).toBeInTheDocument();
    expect(screen.getByText("README.md")).toBeInTheDocument();
  });

  it("expands first-level directories by default and shows children", () => {
    render(<FileTreeView files={sampleFiles} />);
    // src is default-open so index.ts and components should be visible
    expect(screen.getByText("index.ts")).toBeInTheDocument();
    expect(screen.getByText("components")).toBeInTheDocument();
  });

  it("collapses a directory when clicked", async () => {
    const user = userEvent.setup();
    render(<FileTreeView files={sampleFiles} />);

    // src dir button
    const srcButton = screen.getByRole("button", { name: /src/i });
    await user.click(srcButton);

    // children should no longer be visible
    expect(screen.queryByText("index.ts")).not.toBeInTheDocument();
  });

  it("expands a nested directory when clicked", async () => {
    const user = userEvent.setup();
    render(<FileTreeView files={sampleFiles} />);

    // components dir is not default-open (only root children are)
    expect(screen.queryByText("Button.tsx")).not.toBeInTheDocument();

    // Click to expand
    const componentsButton = screen.getByRole("button", {
      name: /components/i,
    });
    await user.click(componentsButton);

    expect(screen.getByText("Button.tsx")).toBeInTheDocument();
    expect(screen.getByText("Card.tsx")).toBeInTheDocument();
  });

  it("filters files by search input", async () => {
    const user = userEvent.setup();
    render(<FileTreeView files={sampleFiles} />);

    const input = screen.getByPlaceholderText("Filter files…");
    await user.type(input, "Button");

    // Only Button.tsx-related nodes should be visible
    expect(screen.getByText("Button.tsx")).toBeInTheDocument();
    expect(screen.queryByText("README.md")).not.toBeInTheDocument();
  });

  it("shows file sizes", () => {
    render(<FileTreeView files={[makeFile("small.txt", 512)]} />);
    expect(screen.getByText("512 B")).toBeInTheDocument();
  });

  it("shows mime type badges for files", async () => {
    const user = userEvent.setup();
    render(
      <FileTreeView
        files={[makeFile("src/app.tsx", 100, "text/tsx")]}
      />
    );

    // Expand src (default open)
    expect(screen.getByText("text/tsx")).toBeInTheDocument();
  });
});
