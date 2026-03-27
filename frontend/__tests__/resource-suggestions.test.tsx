import { describe, it, expect, vi, beforeEach, type Mock } from "vitest";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ResourceSuggestions } from "@/components/portfolio/resource-suggestions";

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------

vi.mock("@/lib/auth", () => ({
  getStoredToken: vi.fn(() => "mock-token"),
}));

vi.mock("@/lib/api/portfolio", () => ({
  getResourceSuggestions: vi.fn(),
}));

// Radix Select is hard to test in happy-dom — stub it to a native <select>
vi.mock("@/components/ui/select", () => ({
  Select: ({
    children,
    value,
    onValueChange,
  }: {
    children: React.ReactNode;
    value: string;
    onValueChange: (v: string) => void;
  }) => (
    <div data-testid="select-root">
      <select
        data-testid="role-select"
        value={value}
        onChange={(e) => onValueChange(e.target.value)}
      >
        {children}
      </select>
    </div>
  ),
  SelectTrigger: ({ children }: { children: React.ReactNode }) => <>{children}</>,
  SelectContent: ({ children }: { children: React.ReactNode }) => <>{children}</>,
  SelectItem: ({
    children,
    value,
  }: {
    children: React.ReactNode;
    value: string;
  }) => <option value={value}>{children}</option>,
  SelectValue: ({ placeholder }: { placeholder?: string }) => (
    <span>{placeholder}</span>
  ),
}));

vi.mock("@/components/ui/loading-state", () => ({
  LoadingState: ({ message }: { message: string }) => (
    <div data-testid="loading-state">{message}</div>
  ),
}));

import { getResourceSuggestions } from "@/lib/api/portfolio";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const FLAT_SUGGESTIONS = [
  {
    skill_name: "React",
    current_tier: "beginner",
    target_tier: "intermediate",
    reason: "Build interactive UIs",
    importance: null,
    resources: [
      {
        title: "React Docs",
        url: "https://react.dev",
        type: "docs" as const,
        level: "beginner" as const,
      },
    ],
  },
  {
    skill_name: "TypeScript",
    current_tier: "beginner",
    target_tier: "advanced",
    reason: "Type-safe code",
    importance: null,
    resources: [
      {
        title: "TS Handbook",
        url: "https://typescriptlang.org",
        type: "article" as const,
        level: "intermediate" as const,
      },
    ],
  },
];

const GROUPED_SUGGESTIONS = [
  {
    skill_name: "React",
    current_tier: "beginner",
    target_tier: "intermediate",
    reason: "Core framework",
    importance: "critical",
    resources: [
      {
        title: "React Docs",
        url: "https://react.dev",
        type: "docs" as const,
        level: "beginner" as const,
      },
    ],
  },
  {
    skill_name: "CSS",
    current_tier: "beginner",
    target_tier: "intermediate",
    reason: "Styling skills",
    importance: "recommended",
    resources: [
      {
        title: "CSS Guide",
        url: "https://css.dev",
        type: "article" as const,
        level: "beginner" as const,
      },
    ],
  },
  {
    skill_name: "Testing",
    current_tier: "beginner",
    target_tier: "intermediate",
    reason: "Write tests",
    importance: "nice_to_have",
    resources: [
      {
        title: "Testing Library",
        url: "https://testing-library.com",
        type: "docs" as const,
        level: "intermediate" as const,
      },
    ],
  },
];

function mockAPI(suggestions: typeof FLAT_SUGGESTIONS) {
  (getResourceSuggestions as Mock).mockResolvedValue({ suggestions });
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("ResourceSuggestions", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  // ── Flat (ungrouped) rendering ──────────────────────────────────────

  it("renders resources in a flat grid when no importance values exist", async () => {
    mockAPI(FLAT_SUGGESTIONS);
    render(<ResourceSuggestions />);

    await waitFor(() => {
      expect(screen.getByText("React Docs")).toBeInTheDocument();
    });
    expect(screen.getByText("TS Handbook")).toBeInTheDocument();

    // No group headers should be present
    expect(screen.queryByText("Critical")).not.toBeInTheDocument();
    expect(screen.queryByText("Recommended")).not.toBeInTheDocument();
    expect(screen.queryByText("Nice to Have")).not.toBeInTheDocument();
  });

  // ── Grouped rendering ──────────────────────────────────────────────

  it("renders resources grouped by importance when importance values exist", async () => {
    mockAPI(GROUPED_SUGGESTIONS);
    render(<ResourceSuggestions />);

    await waitFor(() => {
      expect(screen.getByText("React Docs")).toBeInTheDocument();
    });

    // Group header buttons should be present (these are the toggle buttons)
    expect(
      screen.getByRole("button", { name: /Critical/i }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /Recommended/i }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /Nice to Have/i }),
    ).toBeInTheDocument();
  });

  // ── Collapse toggle ────────────────────────────────────────────────

  it("collapses and expands an importance group on click", async () => {
    mockAPI(GROUPED_SUGGESTIONS);
    const user = userEvent.setup();
    render(<ResourceSuggestions />);

    const criticalBtn = await screen.findByRole("button", {
      name: /Critical/i,
    });

    // Critical defaults to open
    expect(criticalBtn).toHaveAttribute("aria-expanded", "true");
    expect(screen.getByText("React Docs")).toBeInTheDocument();

    // Collapse it
    await user.click(criticalBtn);
    expect(criticalBtn).toHaveAttribute("aria-expanded", "false");

    // Expand again
    await user.click(criticalBtn);
    expect(criticalBtn).toHaveAttribute("aria-expanded", "true");
  });

  it("renders Nice to Have collapsed by default", async () => {
    mockAPI(GROUPED_SUGGESTIONS);
    render(<ResourceSuggestions />);

    const niceBtn = await screen.findByRole("button", {
      name: /Nice to Have/i,
    });
    expect(niceBtn).toHaveAttribute("aria-expanded", "false");
  });

  // ── aria-expanded ──────────────────────────────────────────────────

  it("sets aria-expanded on all group toggle buttons", async () => {
    mockAPI(GROUPED_SUGGESTIONS);
    render(<ResourceSuggestions />);

    await screen.findByRole("button", { name: /Critical/i });

    const buttons = screen.getAllByRole("button");
    const groupButtons = buttons.filter((b) => b.hasAttribute("aria-expanded"));
    expect(groupButtons.length).toBeGreaterThanOrEqual(3);
  });

  // ── Empty state ────────────────────────────────────────────────────

  it("renders empty state when no suggestions are returned", async () => {
    mockAPI([]);
    render(<ResourceSuggestions />);

    await waitFor(() => {
      expect(
        screen.getByText("No resource suggestions available"),
      ).toBeInTheDocument();
    });
  });

  // ── Error state ────────────────────────────────────────────────────

  it("renders error state when the API call fails", async () => {
    (getResourceSuggestions as Mock).mockRejectedValue(
      new Error("Network error"),
    );
    render(<ResourceSuggestions />);

    await waitFor(() => {
      expect(screen.getByText("Network error")).toBeInTheDocument();
    });
  });

  // ── Null importance mixed with valid importance ─────────────────────

  it("groups null-importance items into the Other section", async () => {
    const mixed = [
      ...GROUPED_SUGGESTIONS,
      {
        skill_name: "Docker",
        current_tier: "beginner",
        target_tier: "intermediate",
        reason: "Containerization",
        importance: null,
        resources: [
          {
            title: "Docker Guide",
            url: "https://docker.com",
            type: "article" as const,
            level: "beginner" as const,
          },
        ],
      },
    ];
    mockAPI(mixed);
    render(<ResourceSuggestions />);

    await waitFor(() => {
      expect(screen.getByText("Other")).toBeInTheDocument();
    });
    expect(screen.getByText("Docker Guide")).toBeInTheDocument();
  });
});
