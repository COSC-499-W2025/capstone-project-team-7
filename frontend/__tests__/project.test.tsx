import { beforeEach, describe, expect, it, vi, type Mock } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import ProjectPage from "../app/(dashboard)/project/page";

vi.mock("next/link", () => ({
  __esModule: true,
  default: ({ href, children, ...props }: any) => (
    <a href={href} {...props}>
      {children}
    </a>
  ),
}));

vi.mock("next/navigation", () => ({
  useSearchParams: () => ({
    get: vi.fn(() => null),
  }),
}));

vi.mock("@/lib/auth", () => ({
  getStoredToken: vi.fn(),
}));

vi.mock("@/lib/api/projects", () => ({
  getProjects: vi.fn(),
  getProjectById: vi.fn(),
  getProjectSkillTimeline: vi.fn(),
  generateProjectSkillSummary: vi.fn(),
}));

import { getStoredToken } from "@/lib/auth";
import {
  getProjects,
  getProjectById,
  getProjectSkillTimeline,
  generateProjectSkillSummary,
} from "@/lib/api/projects";

const mockGetStoredToken = getStoredToken as Mock;
const mockGetProjects = getProjects as Mock;
const mockGetProjectById = getProjectById as Mock;
const mockGetProjectSkillTimeline = getProjectSkillTimeline as Mock;
const mockGenerateProjectSkillSummary = generateProjectSkillSummary as Mock;

const PROJECT_DETAIL = {
  id: "project-1",
  project_name: "Accurate Portfolio",
  project_path: "/workspace/accurate-portfolio",
  scan_timestamp: "2026-02-10T18:35:00Z",
  total_files: 42,
  total_lines: 12100,
  scan_data: {
    summary: {
      total_files: 42,
      total_lines: 12100,
      bytes_processed: 2048,
      issue_count: 3,
      scan_duration_seconds: 5.78,
    },
    languages: {
      TypeScript: { lines: 8000 },
      Python: { lines: 4100 },
    },
    git_analysis: {
      repositories: [{ name: "origin" }],
    },
    media_analysis: [{ id: "m1" }],
    pdf_analysis: [{ id: "p1" }],
    document_analysis: [{ id: "d1" }],
  },
};

beforeEach(() => {
  vi.clearAllMocks();
  mockGetStoredToken.mockReturnValue("token-123");
  mockGetProjects.mockResolvedValue({
    count: 1,
    projects: [{ id: "project-1" }],
  });
  mockGetProjectById.mockResolvedValue(PROJECT_DETAIL);
  mockGetProjectSkillTimeline.mockResolvedValue({
    project_id: "project-1",
    timeline: [],
    note: null,
    summary: null,
  });
  mockGenerateProjectSkillSummary.mockResolvedValue({
    project_id: "project-1",
    summary: null,
    note: null,
  });
});

describe("Project page data accuracy", () => {
  it("uses scan_duration_seconds from the API payload", async () => {
    render(<ProjectPage />);

    await waitFor(() => {
      expect(screen.getByRole("heading", { name: "Project: Accurate Portfolio" })).toBeInTheDocument();
    });

    expect(screen.getByText("5.8 seconds")).toBeInTheDocument();
    expect(screen.queryByText("3.2 seconds")).not.toBeInTheDocument();
  });

  it("does not render fake fallback project values", async () => {
    render(<ProjectPage />);

    await waitFor(() => {
      expect(screen.getByText("Accurate Portfolio")).toBeInTheDocument();
    });

    expect(screen.queryByText("My Capstone App")).not.toBeInTheDocument();
    expect(screen.queryByText("/home/user/projects/capstone-app")).not.toBeInTheDocument();
    expect(screen.queryByText("4.8 MB")).not.toBeInTheDocument();
  });

  it("shows a clear empty state when no projects are available", async () => {
    mockGetProjects.mockResolvedValue({ count: 0, projects: [] });

    render(<ProjectPage />);

    await waitFor(() => {
      expect(screen.getByText("No project selected")).toBeInTheDocument();
    });

    expect(screen.getByText("Go to projects").closest("a")).toHaveAttribute("href", "/projects");
    expect(screen.queryByText("Show Overview")).not.toBeInTheDocument();
  });

  it("keeps the not-authenticated error state", async () => {
    mockGetStoredToken.mockReturnValue(null);

    render(<ProjectPage />);

    await waitFor(() => {
      expect(screen.getByText("Not authenticated. Please log in through Settings.")).toBeInTheDocument();
    });
  });
});
