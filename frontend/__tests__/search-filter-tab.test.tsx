import { render, screen, fireEvent, act } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";
import { SearchFilterTab } from "@/components/project/search-filter-tab";
import type { FileEntry } from "@/lib/file-tree";

// ---------------------------------------------------------------------------
// Fixture data
// ---------------------------------------------------------------------------

function makeFile(
  path: string,
  size_bytes = 1000,
  mime_type = "text/plain"
): FileEntry {
  return { path, size_bytes, mime_type };
}

const sampleFiles: FileEntry[] = [
  makeFile("src/index.ts", 2048, "text/typescript"),
  makeFile("src/components/Button.tsx", 1500, "text/tsx"),
  makeFile("src/components/Card.tsx", 900, "text/tsx"),
  makeFile("docs/README.md", 400, "text/markdown"),
  makeFile("assets/logo.png", 8000, "image/png"),
  makeFile("data/config.json", 512, "application/json"),
];

// Files with a large enough set to trigger pagination (>50)
const manyFiles: FileEntry[] = Array.from({ length: 55 }, (_, i) =>
  makeFile(`src/file-${i}.ts`, (i + 1) * 100, "text/typescript")
);

// ---------------------------------------------------------------------------
// Loading state
// ---------------------------------------------------------------------------

describe("SearchFilterTab — loading state", () => {
  it("shows loading message", () => {
    render(<SearchFilterTab files={[]} loading={true} error={null} onRetry={vi.fn()} />);
    expect(screen.getByText("Loading files…")).toBeInTheDocument();
  });

  it("shows Loading… in result count", () => {
    render(<SearchFilterTab files={[]} loading={true} error={null} onRetry={vi.fn()} />);
    expect(screen.getByText("Loading…")).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// Error state
// ---------------------------------------------------------------------------

describe("SearchFilterTab — error state", () => {
  it("renders error message", () => {
    render(
      <SearchFilterTab
        files={[]}
        loading={false}
        error="Failed to load files"
        onRetry={vi.fn()}
      />
    );
    expect(screen.getByText("Failed to load files")).toBeInTheDocument();
  });

  it("renders retry button that calls onRetry", async () => {
    const user = userEvent.setup();
    const onRetry = vi.fn();
    render(
      <SearchFilterTab files={[]} loading={false} error="Error" onRetry={onRetry} />
    );
    await user.click(screen.getByRole("button", { name: /try again/i }));
    expect(onRetry).toHaveBeenCalledOnce();
  });
});

// ---------------------------------------------------------------------------
// Empty state (no files, no error)
// ---------------------------------------------------------------------------

describe("SearchFilterTab — empty state", () => {
  it("shows empty state when no files provided", () => {
    render(<SearchFilterTab files={[]} loading={false} error={null} onRetry={vi.fn()} />);
    expect(screen.getByText("No files match your search.")).toBeInTheDocument();
  });

  it("shows 0 files in result count", () => {
    render(<SearchFilterTab files={[]} loading={false} error={null} onRetry={vi.fn()} />);
    expect(screen.getByText("0 files")).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// Normal rendering
// ---------------------------------------------------------------------------

describe("SearchFilterTab — normal rendering", () => {
  it("renders file names from the list", () => {
    render(<SearchFilterTab files={sampleFiles} loading={false} error={null} onRetry={vi.fn()} />);
    expect(screen.getByText("index.ts")).toBeInTheDocument();
    expect(screen.getByText("Button.tsx")).toBeInTheDocument();
    expect(screen.getByText("README.md")).toBeInTheDocument();
    expect(screen.getByText("logo.png")).toBeInTheDocument();
  });

  it("renders correct file count", () => {
    render(<SearchFilterTab files={sampleFiles} loading={false} error={null} onRetry={vi.fn()} />);
    expect(screen.getByText("6 files")).toBeInTheDocument();
  });

  it("renders subdirectory paths under filenames", () => {
    render(<SearchFilterTab files={sampleFiles} loading={false} error={null} onRetry={vi.fn()} />);
    const matches = screen.getAllByText("src/components");
    expect(matches.length).toBeGreaterThan(0);
  });

  it("renders file extension badges", () => {
    render(<SearchFilterTab files={sampleFiles} loading={false} error={null} onRetry={vi.fn()} />);
    const tsBadges = screen.getAllByText(".ts");
    expect(tsBadges.length).toBeGreaterThan(0);
  });

  it("renders file sizes", () => {
    render(<SearchFilterTab files={sampleFiles} loading={false} error={null} onRetry={vi.fn()} />);
    // 2048 bytes = 2.0 KB
    expect(screen.getByText("2.0 KB")).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// Search input (debounced)
// ---------------------------------------------------------------------------

function typeQuery(input: HTMLElement, value: string) {
  fireEvent.change(input, { target: { value } });
  act(() => { vi.advanceTimersByTime(300); });
}

describe("SearchFilterTab — search", () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("filters results after debounce", () => {
    render(<SearchFilterTab files={sampleFiles} loading={false} error={null} onRetry={vi.fn()} />);

    typeQuery(screen.getByPlaceholderText("Search by filename or path…"), "README");

    expect(screen.getByText("README.md")).toBeInTheDocument();
    expect(screen.queryByText("index.ts")).not.toBeInTheDocument();
  });

  it("shows result count with (of N total) when filtered", () => {
    render(<SearchFilterTab files={sampleFiles} loading={false} error={null} onRetry={vi.fn()} />);

    typeQuery(screen.getByPlaceholderText("Search by filename or path…"), "README");

    expect(screen.getByText(/of 6 total/)).toBeInTheDocument();
  });

  it("shows clear (X) button when query is typed", () => {
    render(<SearchFilterTab files={sampleFiles} loading={false} error={null} onRetry={vi.fn()} />);

    fireEvent.change(screen.getByPlaceholderText("Search by filename or path…"), { target: { value: "abc" } });

    expect(screen.getByRole("button", { name: /clear search/i })).toBeInTheDocument();
  });

  it("clears query when X is clicked", () => {
    render(<SearchFilterTab files={sampleFiles} loading={false} error={null} onRetry={vi.fn()} />);

    typeQuery(screen.getByPlaceholderText("Search by filename or path…"), "README");

    fireEvent.click(screen.getByRole("button", { name: /clear search/i }));
    act(() => { vi.advanceTimersByTime(300); });

    expect(screen.getByText("6 files")).toBeInTheDocument();
  });

  it("shows empty state when query matches nothing", () => {
    render(<SearchFilterTab files={sampleFiles} loading={false} error={null} onRetry={vi.fn()} />);

    typeQuery(screen.getByPlaceholderText("Search by filename or path…"), "zzznomatch");

    expect(screen.getByText("No files match your search.")).toBeInTheDocument();
  });

  it("is case-insensitive", () => {
    render(<SearchFilterTab files={sampleFiles} loading={false} error={null} onRetry={vi.fn()} />);

    typeQuery(screen.getByPlaceholderText("Search by filename or path…"), "readme");

    expect(screen.getByText("README.md")).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// Filter controls visibility
// ---------------------------------------------------------------------------

describe("SearchFilterTab — filter control visibility", () => {
  it("shows language dropdown when files have extensions", () => {
    render(<SearchFilterTab files={sampleFiles} loading={false} error={null} onRetry={vi.fn()} />);
    // Language select is rendered — "All languages" option should exist
    expect(screen.getByText("All languages")).toBeInTheDocument();
  });

  it("hides language dropdown when no files have extensions", () => {
    const noExtFiles = [makeFile("Makefile", 100, "text/plain")];
    render(<SearchFilterTab files={noExtFiles} loading={false} error={null} onRetry={vi.fn()} />);
    expect(screen.queryByText("All languages")).not.toBeInTheDocument();
  });

  it("shows type dropdown when >1 MIME category present", () => {
    // sampleFiles has text, image, json — so type filter appears
    render(<SearchFilterTab files={sampleFiles} loading={false} error={null} onRetry={vi.fn()} />);
    expect(screen.getByText("All types")).toBeInTheDocument();
  });

  it("hides type dropdown when only 1 MIME category", () => {
    const sameType = [
      makeFile("a.ts", 100, "text/typescript"),
      makeFile("b.ts", 200, "text/typescript"),
    ];
    render(<SearchFilterTab files={sameType} loading={false} error={null} onRetry={vi.fn()} />);
    expect(screen.queryByText("All types")).not.toBeInTheDocument();
  });

  it("shows directory dropdown when files have subdirectories", () => {
    render(<SearchFilterTab files={sampleFiles} loading={false} error={null} onRetry={vi.fn()} />);
    expect(screen.getByText("All directories")).toBeInTheDocument();
  });

  it("hides directory dropdown when all files are at root", () => {
    const rootFiles = [
      makeFile("README.md", 100, "text/markdown"),
      makeFile("package.json", 200, "application/json"),
    ];
    render(<SearchFilterTab files={rootFiles} loading={false} error={null} onRetry={vi.fn()} />);
    expect(screen.queryByText("All directories")).not.toBeInTheDocument();
  });

  it("always shows sort dropdown", () => {
    render(<SearchFilterTab files={sampleFiles} loading={false} error={null} onRetry={vi.fn()} />);
    expect(screen.getByText("Sort: Name")).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// Reset button
// ---------------------------------------------------------------------------

describe("SearchFilterTab — reset button", () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("does not show reset button with no active filters", () => {
    render(<SearchFilterTab files={sampleFiles} loading={false} error={null} onRetry={vi.fn()} />);
    expect(screen.queryByRole("button", { name: /reset/i })).not.toBeInTheDocument();
  });

  it("shows reset button when query is active", () => {
    render(<SearchFilterTab files={sampleFiles} loading={false} error={null} onRetry={vi.fn()} />);

    typeQuery(screen.getByPlaceholderText("Search by filename or path…"), "ts");

    expect(screen.getByRole("button", { name: /reset/i })).toBeInTheDocument();
  });

  it("shows Clear filters button in empty-results state", () => {
    render(<SearchFilterTab files={sampleFiles} loading={false} error={null} onRetry={vi.fn()} />);

    typeQuery(screen.getByPlaceholderText("Search by filename or path…"), "zzznomatch");

    expect(screen.getByRole("button", { name: /clear filters/i })).toBeInTheDocument();
  });

  it("clicking reset restores all files", () => {
    render(<SearchFilterTab files={sampleFiles} loading={false} error={null} onRetry={vi.fn()} />);

    typeQuery(screen.getByPlaceholderText("Search by filename or path…"), "README");

    expect(screen.getByText(/^1 file/)).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /reset/i }));
    act(() => { vi.advanceTimersByTime(300); });

    expect(screen.getByText("6 files")).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// Pagination
// ---------------------------------------------------------------------------

describe("SearchFilterTab — pagination", () => {
  it("does not show pagination for 6 files (under page size of 50)", () => {
    render(<SearchFilterTab files={sampleFiles} loading={false} error={null} onRetry={vi.fn()} />);
    expect(screen.queryByRole("button", { name: /previous/i })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /next/i })).not.toBeInTheDocument();
  });

  it("shows pagination when file count exceeds page size", () => {
    render(<SearchFilterTab files={manyFiles} loading={false} error={null} onRetry={vi.fn()} />);
    expect(screen.getByRole("button", { name: /next/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /previous/i })).toBeInTheDocument();
  });

  it("Previous is disabled on page 1", () => {
    render(<SearchFilterTab files={manyFiles} loading={false} error={null} onRetry={vi.fn()} />);
    expect(screen.getByRole("button", { name: /previous/i })).toBeDisabled();
  });

  it("advances to page 2 and disables Next on last page", async () => {
    const user = userEvent.setup();
    render(<SearchFilterTab files={manyFiles} loading={false} error={null} onRetry={vi.fn()} />);

    await user.click(screen.getByRole("button", { name: /next/i }));

    expect(screen.getByText(/page 2 of 2/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /next/i })).toBeDisabled();
  });

  it("shows correct page info text", () => {
    render(<SearchFilterTab files={manyFiles} loading={false} error={null} onRetry={vi.fn()} />);
    expect(screen.getByText(/page 1 of 2/i)).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// Singular/plural file count
// ---------------------------------------------------------------------------

describe("SearchFilterTab — file count label", () => {
  it("uses singular 'file' for 1 result", () => {
    vi.useFakeTimers();
    render(<SearchFilterTab files={sampleFiles} loading={false} error={null} onRetry={vi.fn()} />);

    typeQuery(screen.getByPlaceholderText("Search by filename or path…"), "README");

    expect(screen.getByText(/^1 file/)).toBeInTheDocument();
    vi.useRealTimers();
  });

  it("uses plural 'files' for multiple results", () => {
    render(<SearchFilterTab files={sampleFiles} loading={false} error={null} onRetry={vi.fn()} />);
    expect(screen.getByText("6 files")).toBeInTheDocument();
  });
});
