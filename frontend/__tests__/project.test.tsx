import { beforeEach, describe, expect, it, vi, type Mock } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
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
  useRouter: () => ({
    back: vi.fn(),
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

vi.mock("@/lib/api", () => ({
  consent: {
    get: vi.fn(),
  },
  secrets: {
    verify: vi.fn(),
  },
}));

import { getStoredToken } from "@/lib/auth";
import {
  getProjects,
  getProjectById,
  getProjectSkillTimeline,
  generateProjectSkillSummary,
} from "@/lib/api/projects";
import { consent, secrets } from "@/lib/api";

const mockGetStoredToken = getStoredToken as Mock;
const mockGetProjects = getProjects as Mock;
const mockGetProjectById = getProjectById as Mock;
const mockGetProjectSkillTimeline = getProjectSkillTimeline as Mock;
const mockGenerateProjectSkillSummary = generateProjectSkillSummary as Mock;
const mockConsentGet = consent.get as Mock;
const mockSecretsVerify = secrets.verify as Mock;

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
  mockConsentGet.mockResolvedValue({
    ok: true,
    data: {
      user_id: "user-123",
      data_access: true,
      external_services: true,
      updated_at: "2026-02-10T18:35:00Z",
    },
  });
  mockSecretsVerify.mockResolvedValue({
    ok: true,
    data: {
      valid: true,
      message: "API key verified successfully",
    },
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

  it("blocks AI analysis when external consent is disabled", async () => {
    mockConsentGet.mockResolvedValue({
      ok: true,
      data: {
        user_id: "user-123",
        data_access: true,
        external_services: false,
        updated_at: "2026-02-10T18:35:00Z",
      },
    });

    render(<ProjectPage />);

    await waitFor(() => {
      expect(screen.getByRole("heading", { name: "Project: Accurate Portfolio" })).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("button", { name: "AI Analysis" }));

    await waitFor(() => {
      expect(
        screen.getByText(/External Data consent is not enabled/i)
      ).toBeInTheDocument();
    });

    expect(mockSecretsVerify).not.toHaveBeenCalled();
    expect(screen.getByRole("button", { name: "Generate" })).toBeDisabled();
  });

  it("blocks AI analysis when OpenAI key is invalid", async () => {
    mockSecretsVerify.mockResolvedValue({
      ok: true,
      data: {
        valid: false,
        message: "Your OpenAI API key is invalid.",
      },
    });

    render(<ProjectPage />);

    await waitFor(() => {
      expect(screen.getByRole("heading", { name: "Project: Accurate Portfolio" })).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("button", { name: "AI Analysis" }));

    await waitFor(() => {
      expect(screen.getByText(/api key is invalid/i)).toBeInTheDocument();
    });

    expect(screen.getByRole("button", { name: "Generate" })).toBeDisabled();
  });

  it("allows AI summary generation when consent and key are valid", async () => {
    mockGenerateProjectSkillSummary.mockResolvedValueOnce({
      project_id: "project-1",
      note: null,
      summary: {
        overview: "Strong backend growth",
        validation_warning: null,
        timeline: ["Expanded test coverage"],
        skills_focus: ["TypeScript"],
        suggested_next_steps: ["Add integration tests"],
      },
    });

    render(<ProjectPage />);

    await waitFor(() => {
      expect(screen.getByRole("heading", { name: "Project: Accurate Portfolio" })).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("button", { name: "AI Analysis" }));

    await waitFor(() => {
      expect(screen.getByRole("button", { name: "Generate" })).toBeEnabled();
    });

    fireEvent.click(screen.getByRole("button", { name: "Generate" }));

    await waitFor(() => {
      expect(mockGenerateProjectSkillSummary).toHaveBeenCalledWith("token-123", "project-1");
    });
  });
});
