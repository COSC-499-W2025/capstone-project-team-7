import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import ProjectPage from "../app/(dashboard)/project/page";

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------

vi.mock("next/link", () => ({
  __esModule: true,
  default: ({ href, children, ...props }: any) => (
    <a href={href} {...props}>
      {children}
    </a>
  ),
}));

// ---------------------------------------------------------------------------
// Tab labels (must match the component)
// ---------------------------------------------------------------------------

const TAB_LABELS = [
  "Show Overview",
  "View File List",
  "Language Breakdown",
  "Code Analysis",
  "Skills Analysis",
  "Skills Progression",
  "Run Git Analysis",
  "Contribution Metrics",
  "Generate Resume Item",
  "Find Duplicate Files",
  "Search and Filter Files",
  "Export JSON Report",
  "Export HTML Report",
  "Export Printable Report",
  "Analyze PDF Files",
  "Document Analysis",
  "Media Analysis",
] as const;

// ---------------------------------------------------------------------------
// Rendering tests
// ---------------------------------------------------------------------------

describe("ProjectPage — rendering", () => {
  it("renders without crashing", () => {
    render(<ProjectPage />);
    expect(screen.getByText("Project: My Capstone App")).toBeInTheDocument();
  });

  it("displays the page title", () => {
    render(<ProjectPage />);
    expect(
      screen.getByRole("heading", { name: "Project: My Capstone App" })
    ).toBeInTheDocument();
  });

  it("has a back link to /scanned-results", () => {
    render(<ProjectPage />);
    const backLink = screen.getByText("← Back");
    expect(backLink.closest("a")).toHaveAttribute("href", "/scanned-results");
  });
});

// ---------------------------------------------------------------------------
// Tab bar tests
// ---------------------------------------------------------------------------

describe("ProjectPage — tab bar", () => {
  it("renders all 17 tab triggers", () => {
    render(<ProjectPage />);
    for (const label of TAB_LABELS) {
      expect(screen.getByText(label)).toBeInTheDocument();
    }
  });

  it("'Show Overview' tab is active by default", () => {
    render(<ProjectPage />);
    const overviewBtn = screen.getByText("Show Overview").closest("button")!;
    expect(overviewBtn).toHaveAttribute("aria-pressed", "true");
  });
});

// ---------------------------------------------------------------------------
// Overview tab content tests
// ---------------------------------------------------------------------------

describe("ProjectPage — overview content", () => {
  it("shows Project Information card", () => {
    render(<ProjectPage />);
    expect(screen.getByText("Project Information")).toBeInTheDocument();
    expect(screen.getByText("My Capstone App")).toBeInTheDocument();
    expect(
      screen.getByText("/home/user/projects/capstone-app")
    ).toBeInTheDocument();
    expect(screen.getByText("2025-01-15 14:32:07")).toBeInTheDocument();
  });

  it("shows Summary Statistics card", () => {
    render(<ProjectPage />);
    expect(screen.getByText("Summary Statistics")).toBeInTheDocument();
    expect(screen.getByText("247")).toBeInTheDocument();
    expect(screen.getByText("4.8 MB")).toBeInTheDocument();
    expect(screen.getByText("12")).toBeInTheDocument();
    expect(screen.getByText("18,432")).toBeInTheDocument();
  });

  it("shows Top 5 Languages card with all languages", () => {
    render(<ProjectPage />);
    expect(screen.getByText("Top 5 Languages")).toBeInTheDocument();
    expect(screen.getByText("TypeScript")).toBeInTheDocument();
    expect(screen.getByText("Python")).toBeInTheDocument();
    expect(screen.getByText("JavaScript")).toBeInTheDocument();
    expect(screen.getByText("CSS")).toBeInTheDocument();
    expect(screen.getByText("HTML")).toBeInTheDocument();
    expect(screen.getByText("42.3%")).toBeInTheDocument();
    expect(screen.getByText("28.1%")).toBeInTheDocument();
  });

  it("shows Git Repositories, Media Files, and Documents cards", () => {
    render(<ProjectPage />);
    expect(screen.getByText("Git Repositories")).toBeInTheDocument();
    expect(screen.getByText("Media Files")).toBeInTheDocument();
    expect(screen.getByText("Documents")).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// Tab switching tests
// ---------------------------------------------------------------------------

describe("ProjectPage — tab switching", () => {
  it("clicking a non-overview tab shows placeholder message", async () => {
    const user = userEvent.setup();
    render(<ProjectPage />);

    const fileListBtn = screen.getByText("View File List").closest("button")!;
    await user.click(fileListBtn);

    expect(
      screen.getByText("View File List — This section will be available soon.")
    ).toBeInTheDocument();
  });

  it("clicking a non-overview tab hides overview content", async () => {
    const user = userEvent.setup();
    render(<ProjectPage />);

    // Overview content is visible initially
    expect(screen.getByText("Project Information")).toBeInTheDocument();

    const fileListBtn = screen.getByText("View File List").closest("button")!;
    await user.click(fileListBtn);

    // Overview content should be gone
    expect(screen.queryByText("Project Information")).not.toBeInTheDocument();
  });

  it("clicking back to 'Show Overview' restores overview content", async () => {
    const user = userEvent.setup();
    render(<ProjectPage />);

    // Switch away
    const fileListBtn = screen.getByText("View File List").closest("button")!;
    await user.click(fileListBtn);
    expect(screen.queryByText("Project Information")).not.toBeInTheDocument();

    // Switch back
    const overviewBtn = screen.getByText("Show Overview").closest("button")!;
    await user.click(overviewBtn);
    expect(screen.getByText("Project Information")).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// Placeholder tab tests
// ---------------------------------------------------------------------------

describe("ProjectPage — placeholder tabs", () => {
  const placeholderTabs = TAB_LABELS.filter(
    (label) => !["Show Overview", "Skills Progression", "Skills Analysis", "Run Git Analysis"].includes(label)
  );

  it.each(placeholderTabs)(
    "tab '%s' displays its label in the placeholder message",
    async (label) => {
      const user = userEvent.setup();
      render(<ProjectPage />);

      const btn = screen.getByText(label).closest("button")!;
      await user.click(btn);

      expect(
        screen.getByText(`${label} — This section will be available soon.`)
      ).toBeInTheDocument();
    }
  );
});

describe("ProjectPage — git analysis tab", () => {
  it("shows empty state message when no git analysis data", async () => {
    const user = userEvent.setup();
    render(<ProjectPage />);

    const gitBtn = screen.getByText("Run Git Analysis").closest("button")!;
    await user.click(gitBtn);

    expect(
      screen.getByText("No git analysis available yet.")
    ).toBeInTheDocument();
  });
});

describe("ProjectPage — skills analysis tab", () => {
  it("shows empty state message when no skills analysis data", async () => {
    const user = userEvent.setup();
    render(<ProjectPage />);

    const skillsBtn = screen.getByText("Skills Analysis").closest("button")!;
    await user.click(skillsBtn);

    expect(
      screen.getByText("No skills analysis available yet. Run a scan with skills extraction enabled.")
    ).toBeInTheDocument();
  });
});
