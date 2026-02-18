import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { GitAnalysisTab, normalizeGitAnalysis, normalizeRepo } from "@/components/project/git-analysis-tab";
import { describe, expect, it, vi } from "vitest";

// ---------------------------------------------------------------------------
// Fixture data
// ---------------------------------------------------------------------------

const singleRepo = [
  {
    path: "/home/user/project",
    commit_count: 142,
    project_type: "collaborative",
    date_range: { start: "2024-06-01T10:00:00+00:00", end: "2025-01-15T14:30:00+00:00" },
    branches: ["main", "develop", "feature/auth"],
    contributors: [
      {
        name: "Alice",
        email: "alice@example.com",
        commits: 80,
        percent: 56.34,
        first_commit_date: "2024-06-01T10:00:00+00:00",
        last_commit_date: "2025-01-15T14:30:00+00:00",
        active_days: 45,
      },
      {
        name: "Bob",
        email: "bob@example.com",
        commits: 62,
        percent: 43.66,
        first_commit_date: "2024-07-10T08:00:00+00:00",
        last_commit_date: "2025-01-10T12:00:00+00:00",
        active_days: 30,
      },
    ],
    timeline: [
      {
        month: "2025-01",
        commits: 20,
        messages: ["fix auth bug", "add tests"],
        top_files: ["src/auth.ts", "tests/auth.test.ts"],
        languages: { TypeScript: 15, Python: 5 },
        contributors: 2,
      },
      {
        month: "2024-12",
        commits: 35,
        messages: ["initial release"],
        top_files: ["README.md"],
        languages: { TypeScript: 30 },
        contributors: 1,
      },
    ],
  },
];

const multiRepo = [
  ...singleRepo,
  {
    path: "/home/user/other-repo",
    commit_count: 50,
    project_type: "individual",
    date_range: { start: "2024-09-01T00:00:00+00:00", end: "2024-12-31T00:00:00+00:00" },
    branches: ["main"],
    contributors: [
      { name: "Charlie", email: "charlie@test.com", commits: 50, percent: 100, active_days: 20 },
    ],
    timeline: [],
  },
];

const repoWithError = [
  { path: "/bad-repo", error: "not a git repository" },
  ...singleRepo,
];

// ---------------------------------------------------------------------------
// Rendering tests
// ---------------------------------------------------------------------------

describe("GitAnalysisTab — summary stats", () => {
  it("renders all four summary stat cards", () => {
    render(<GitAnalysisTab loading={false} error={null} gitAnalysis={singleRepo} />);

    expect(screen.getByText("Total Commits")).toBeInTheDocument();
    expect(screen.getByText("142")).toBeInTheDocument();
    expect(screen.getByText("Project Type")).toBeInTheDocument();
    expect(screen.getByText("Collaborative")).toBeInTheDocument();
    expect(screen.getByText("Date Range")).toBeInTheDocument();
    expect(screen.getByText("Branches")).toBeInTheDocument();
    expect(screen.getByText("3")).toBeInTheDocument();
  });
});

describe("GitAnalysisTab — contributors", () => {
  it("renders contributor rows with names, emails, commits", () => {
    render(<GitAnalysisTab loading={false} error={null} gitAnalysis={singleRepo} />);

    expect(screen.getByText("Contributors (2)")).toBeInTheDocument();
    expect(screen.getByText("Alice")).toBeInTheDocument();
    expect(screen.getByText("alice@example.com")).toBeInTheDocument();
    expect(screen.getByText("Bob")).toBeInTheDocument();
    expect(screen.getByText("bob@example.com")).toBeInTheDocument();
  });
});

describe("GitAnalysisTab — branches", () => {
  it("renders branch pills", () => {
    render(<GitAnalysisTab loading={false} error={null} gitAnalysis={singleRepo} />);

    expect(screen.getByText("Branches (3)")).toBeInTheDocument();
    expect(screen.getByText("main")).toBeInTheDocument();
    expect(screen.getByText("develop")).toBeInTheDocument();
    expect(screen.getByText("feature/auth")).toBeInTheDocument();
  });
});

describe("GitAnalysisTab — timeline", () => {
  it("renders timeline entries with commit messages and top files", () => {
    render(<GitAnalysisTab loading={false} error={null} gitAnalysis={singleRepo} />);

    expect(screen.getByText("Activity Timeline")).toBeInTheDocument();
    expect(screen.getByText("fix auth bug")).toBeInTheDocument();
    expect(screen.getByText("add tests")).toBeInTheDocument();
    expect(screen.getByText("src/auth.ts")).toBeInTheDocument();
    expect(screen.getByText("initial release")).toBeInTheDocument();
  });

  it("renders language tags in timeline", () => {
    render(<GitAnalysisTab loading={false} error={null} gitAnalysis={singleRepo} />);

    expect(screen.getByText("TypeScript · 15")).toBeInTheDocument();
    expect(screen.getByText("Python · 5")).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// Loading / Error / Empty states
// ---------------------------------------------------------------------------

describe("GitAnalysisTab — loading state", () => {
  it("shows spinner when loading", () => {
    render(<GitAnalysisTab loading={true} error={null} gitAnalysis={null} />);
    expect(screen.getByText("Analyzing git repositories…")).toBeInTheDocument();
  });
});

describe("GitAnalysisTab — error state", () => {
  it("shows error message", () => {
    render(<GitAnalysisTab loading={false} error="Something went wrong" gitAnalysis={null} />);
    expect(screen.getByText("Something went wrong")).toBeInTheDocument();
  });

  it("shows retry button when onRetry provided", () => {
    const onRetry = vi.fn();
    render(
      <GitAnalysisTab loading={false} error="fail" gitAnalysis={null} onRetry={onRetry} />
    );
    expect(screen.getByRole("button", { name: "Retry" })).toBeInTheDocument();
  });
});

describe("GitAnalysisTab — empty state", () => {
  it("shows empty state when gitAnalysis is null", () => {
    render(<GitAnalysisTab loading={false} error={null} gitAnalysis={null} />);
    expect(screen.getByText("No git analysis available yet.")).toBeInTheDocument();
  });

  it("shows empty state when gitAnalysis is empty array", () => {
    render(<GitAnalysisTab loading={false} error={null} gitAnalysis={[]} />);
    expect(screen.getByText("No git analysis available yet.")).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// Multi-repo selector
// ---------------------------------------------------------------------------

describe("GitAnalysisTab — multi-repo selector", () => {
  it("renders repo selector when >1 repo", () => {
    render(<GitAnalysisTab loading={false} error={null} gitAnalysis={multiRepo} />);
    expect(screen.getByText("Repository")).toBeInTheDocument();
    expect(screen.getByRole("combobox")).toBeInTheDocument();
  });

  it("does not render selector for single repo", () => {
    render(<GitAnalysisTab loading={false} error={null} gitAnalysis={singleRepo} />);
    expect(screen.queryByText("Repository")).not.toBeInTheDocument();
  });

  it("switches displayed data when selecting another repo", async () => {
    const user = userEvent.setup();
    render(<GitAnalysisTab loading={false} error={null} gitAnalysis={multiRepo} />);

    // Initially shows first repo
    expect(screen.getByText("142")).toBeInTheDocument();

    // Select second repo
    const select = screen.getByRole("combobox");
    await user.selectOptions(select, "1");

    // Now shows second repo stats
    expect(screen.getByText("Individual")).toBeInTheDocument();
    expect(screen.getByText("Charlie")).toBeInTheDocument();
    // "50" appears in both the stat card and the contributor commits cell,
    // so verify via the stat card label being present alongside
    expect(screen.getAllByText("50").length).toBeGreaterThanOrEqual(1);
  });
});

// ---------------------------------------------------------------------------
// Error repo filtering
// ---------------------------------------------------------------------------

describe("GitAnalysisTab — error repo filtering", () => {
  it("filters out repos with errors and shows valid repo", () => {
    render(<GitAnalysisTab loading={false} error={null} gitAnalysis={repoWithError} />);

    // Should not show the errored repo, should show the valid one
    expect(screen.getByText("142")).toBeInTheDocument();
    expect(screen.getByText("Alice")).toBeInTheDocument();
  });

  it("shows empty state when all repos have errors", () => {
    const allBad = [
      { path: "/bad1", error: "not a git repository" },
      { path: "/bad2", error: "git failed" },
    ];
    render(<GitAnalysisTab loading={false} error={null} gitAnalysis={allBad} />);
    expect(screen.getByText("No git analysis available yet.")).toBeInTheDocument();
  });
});


// ---------------------------------------------------------------------------
// normalizeGitAnalysis unit tests
// ---------------------------------------------------------------------------

describe("normalizeGitAnalysis", () => {
  it("returns empty array for null/undefined", () => {
    expect(normalizeGitAnalysis(null)).toEqual([]);
    expect(normalizeGitAnalysis(undefined)).toEqual([]);
  });

  it("returns empty array for empty array", () => {
    expect(normalizeGitAnalysis([])).toEqual([]);
  });

  it("normalizes a single repo object (not wrapped in array)", () => {
    const single = {
      path: "/repo",
      commit_count: 10,
      contributors: [],
      project_type: "individual",
      date_range: null,
      branches: ["main"],
      timeline: [],
    };
    const result = normalizeGitAnalysis(single);
    expect(result).toHaveLength(1);
    expect(result[0].path).toBe("/repo");
    expect(result[0].commit_count).toBe(10);
  });

  it("normalizes an array of repo objects", () => {
    const repos = [
      { path: "/a", commit_count: 5, contributors: [], project_type: "individual", date_range: null, branches: [], timeline: [] },
      { path: "/b", commit_count: 8, contributors: [], project_type: "collaborative", date_range: null, branches: [], timeline: [] },
    ];
    const result = normalizeGitAnalysis(repos);
    expect(result).toHaveLength(2);
    expect(result[0].path).toBe("/a");
    expect(result[1].path).toBe("/b");
  });

  it("filters out repos with errors from array", () => {
    const repos = [
      { path: "/good", commit_count: 5, contributors: [], project_type: "individual", date_range: null, branches: [], timeline: [] },
      { path: "/bad", error: "not a git repository" },
    ];
    const result = normalizeGitAnalysis(repos);
    expect(result).toHaveLength(1);
    expect(result[0].path).toBe("/good");
  });

  it("returns empty array for non-object/non-array input", () => {
    expect(normalizeGitAnalysis("string")).toEqual([]);
    expect(normalizeGitAnalysis(42)).toEqual([]);
    expect(normalizeGitAnalysis(true)).toEqual([]);
  });
});

// ---------------------------------------------------------------------------
// normalizeRepo unit tests
// ---------------------------------------------------------------------------

describe("normalizeRepo", () => {
  it("returns null for null/undefined", () => {
    expect(normalizeRepo(null)).toBeNull();
    expect(normalizeRepo(undefined)).toBeNull();
  });

  it("returns null for non-object values", () => {
    expect(normalizeRepo("string")).toBeNull();
    expect(normalizeRepo(42)).toBeNull();
  });

  it("returns null for repos with an error field", () => {
    expect(normalizeRepo({ path: "/bad", error: "failed" })).toBeNull();
  });

  it("provides defaults for missing fields", () => {
    const result = normalizeRepo({ path: "/repo" });
    expect(result).not.toBeNull();
    expect(result!.path).toBe("/repo");
    expect(result!.commit_count).toBe(0);
    expect(result!.contributors).toEqual([]);
    expect(result!.project_type).toBe("unknown");
    expect(result!.date_range).toBeNull();
    expect(result!.branches).toEqual([]);
    expect(result!.timeline).toEqual([]);
  });

  it("defaults path to 'unknown' when missing", () => {
    const result = normalizeRepo({ commit_count: 5 });
    expect(result!.path).toBe("unknown");
  });

  it("preserves valid fields", () => {
    const repo = {
      path: "/my/repo",
      commit_count: 42,
      contributors: [{ name: "Dev", email: "dev@test.com", commits: 42, percent: 100 }],
      project_type: "collaborative",
      date_range: { start: "2024-01-01", end: "2024-12-31" },
      branches: ["main", "dev"],
      timeline: [{ month: "2024-01", commits: 10, messages: [], top_files: [], languages: {}, contributors: 1 }],
    };
    const result = normalizeRepo(repo);
    expect(result).toEqual(repo);
  });

  it("handles wrong types gracefully", () => {
    const result = normalizeRepo({
      path: 123,
      commit_count: "not-a-number",
      contributors: "not-an-array",
      branches: null,
      timeline: {},
    });
    expect(result!.path).toBe("unknown");
    expect(result!.commit_count).toBe(0);
    expect(result!.contributors).toEqual([]);
    expect(result!.branches).toEqual([]);
    expect(result!.timeline).toEqual([]);
  });
});
