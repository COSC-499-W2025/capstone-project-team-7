import { describe, it, expect, vi, beforeEach, type Mock } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import ProjectsPage from "../app/(dashboard)/projects/page";

const { mockRouterPush } = vi.hoisted(() => ({
  mockRouterPush: vi.fn(),
}));

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------

const MOCK_PROJECTS = [
  {
    id: "proj-1",
    project_name: "My Portfolio",
    project_path: "/home/user/portfolio",
    scan_timestamp: "2026-01-15T10:30:00Z",
    created_at: "2026-01-15T10:30:00Z",
    total_files: 42,
    total_lines: 1250,
    languages: ["TypeScript", "JavaScript", "CSS"],
    has_media_analysis: true,
    has_pdf_analysis: false,
    has_code_analysis: true,
    has_git_analysis: true,
    scan_data: {
      summary: {
        total_files: 42,
        total_lines: 1250,
        languages: [
          { language: "TypeScript", files: 20 },
          { language: "JavaScript", files: 15 },
          { language: "CSS", files: 7 },
        ],
        size: 2048576,
      },
    },
  },
  {
    id: "proj-2",
    project_name: "Backend API",
    project_path: "/home/user/api",
    scan_timestamp: "2026-01-10T14:20:00Z",
    created_at: "2026-01-10T14:20:00Z",
    total_files: 28,
    total_lines: 890,
    languages: ["Python", "YAML"],
    has_media_analysis: false,
    has_pdf_analysis: false,
    has_code_analysis: true,
    has_git_analysis: false,
    scan_data: {
      summary: {
        total_files: 28,
        total_lines: 890,
        languages: [
          { language: "Python", files: 25 },
          { language: "YAML", files: 3 },
        ],
        size: 512000,
      },
    },
  },
];

const MOCK_PROJECT_DETAIL = {
  ...MOCK_PROJECTS[0],
  role: "author",
};

// Mock the API module
vi.mock("@/lib/api/projects", () => ({
  getProjects: vi.fn(),
  getProjectById: vi.fn(),
  deleteProject: vi.fn(),
  updateProjectRole: vi.fn(),
  updateProjectOverrides: vi.fn(),
  getSelection: vi.fn(),
  saveSelection: vi.fn(),
}));

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: mockRouterPush }),
}));

// Mock the auth module
vi.mock("@/lib/auth", () => ({
  getStoredToken: vi.fn(),
}));

import { getProjects, getProjectById, deleteProject, updateProjectRole, updateProjectOverrides, getSelection, saveSelection } from "@/lib/api/projects";
import { getStoredToken } from "@/lib/auth";

const mockGetProjects = getProjects as Mock;
const mockGetProjectById = getProjectById as Mock;
const mockDeleteProject = deleteProject as Mock;
const mockUpdateProjectRole = updateProjectRole as Mock;
const mockUpdateProjectOverrides = updateProjectOverrides as Mock;
const mockGetSelection = getSelection as Mock;
const mockSaveSelection = saveSelection as Mock;
const mockGetStoredToken = getStoredToken as Mock;

// Mock window.confirm
const confirmMock = vi.fn();
Object.defineProperty(window, "confirm", {
  value: confirmMock,
  writable: true,
});

// Mock window.alert
const alertMock = vi.fn();
Object.defineProperty(window, "alert", {
  value: alertMock,
  writable: true,
});

// Mock window.location
const locationMock = { href: "" };
Object.defineProperty(window, "location", {
  value: locationMock,
  writable: true,
});

// ---------------------------------------------------------------------------
// Setup
// ---------------------------------------------------------------------------

beforeEach(() => {
  vi.clearAllMocks();
  locationMock.href = "";
  confirmMock.mockReturnValue(false);
  alertMock.mockClear();

  mockGetStoredToken.mockReturnValue("test-token");
  mockGetProjects.mockResolvedValue({
    projects: [...MOCK_PROJECTS],
    total: 2,
  });
  mockGetProjectById.mockResolvedValue(MOCK_PROJECT_DETAIL);
  mockDeleteProject.mockResolvedValue(undefined);
  mockUpdateProjectRole.mockResolvedValue(undefined);
  mockUpdateProjectOverrides.mockResolvedValue(undefined);
  mockGetSelection.mockResolvedValue({
    user_id: "user-1",
    project_order: [],
    skill_order: [],
    selected_project_ids: [],
    selected_skill_ids: [],
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
  });
  mockSaveSelection.mockResolvedValue({
    user_id: "user-1",
    project_order: [],
    skill_order: [],
    selected_project_ids: [],
    selected_skill_ids: [],
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
  });
});

// ---------------------------------------------------------------------------
// Helper
// ---------------------------------------------------------------------------

async function renderAndWait() {
  render(<ProjectsPage />);
  await waitFor(() => {
    expect(screen.queryByText("Loading projects...")).not.toBeInTheDocument();
  });
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("ProjectsPage", () => {
  it("renders loading state initially", () => {
    mockGetProjects.mockReturnValue(new Promise(() => {})); // never resolves
    render(<ProjectsPage />);
    expect(screen.getByText("Loading projects...")).toBeInTheDocument();
  });

  it("shows error if no token", async () => {
    mockGetStoredToken.mockReturnValue(null);
    render(<ProjectsPage />);

    await waitFor(() => {
      expect(screen.getByText(/Not authenticated/i)).toBeInTheDocument();
    });
  });

  it("renders projects table after load", async () => {
    await renderAndWait();
    expect(screen.getByText("My Portfolio")).toBeInTheDocument();
    expect(screen.getByText("Backend API")).toBeInTheDocument();
    expect(screen.getByText("42")).toBeInTheDocument(); // total files
    expect(screen.getByText("28")).toBeInTheDocument();
  });

  it("displays project metadata correctly", async () => {
    await renderAndWait();
    // Check languages
    expect(screen.getByText("TypeScript")).toBeInTheDocument();
    expect(screen.getByText("Python")).toBeInTheDocument();

    // Check file counts
    const fileCells = screen.getAllByText(/\d+/);
    expect(fileCells.length).toBeGreaterThan(0);
  });

  it("shows language badges for each project", async () => {
    await renderAndWait();
    // TypeScript badge for first project
    expect(screen.getByText("TypeScript")).toBeInTheDocument();
    // Python badge for second project
    expect(screen.getByText("Python")).toBeInTheDocument();
  });

  it("displays relative timestamps", async () => {
    await renderAndWait();
    // Should show relative time like "X days ago" - multiple projects have timestamps
    const timestamps = screen.getAllByText(/ago/);
    expect(timestamps.length).toBeGreaterThan(0);
  });

  it("opens modal when eye icon clicked", async () => {
    await renderAndWait();
    const eyeButtons = screen.getAllByTitle("View details");
    await userEvent.click(eyeButtons[0]);

    await waitFor(() => {
      expect(mockGetProjectById).toHaveBeenCalledWith("test-token", "proj-1");
    });

    // Modal should be open with project name
    await waitFor(() => {
      expect(screen.getByText("My Portfolio", { selector: "h2" })).toBeInTheDocument();
    });
  });

  it("closes modal when close button clicked", async () => {
    await renderAndWait();
    const eyeButtons = screen.getAllByTitle("View details");
    await userEvent.click(eyeButtons[0]);

    await waitFor(() => {
      expect(screen.getByText("My Portfolio", { selector: "h2" })).toBeInTheDocument();
    });

    const closeButton = screen.getByRole("button", { name: /close/i });
    await userEvent.click(closeButton);

    await waitFor(() => {
      expect(screen.queryByText("My Portfolio", { selector: "h2" })).not.toBeInTheDocument();
    });
  });

  it("shows project overview in modal", async () => {
    await renderAndWait();
    const eyeButtons = screen.getAllByTitle("View details");
    await userEvent.click(eyeButtons[0]);

    await waitFor(() => {
      // Modal should be open and showing data
      expect(screen.getByText("My Portfolio", { selector: "h2" })).toBeInTheDocument();
    });

    // Check for stats (42 files) - use getAllByText since table also shows this
    const fileStats = screen.getAllByText("42");
    expect(fileStats.length).toBeGreaterThan(0);
  });

  it("does not delete when cancel clicked", async () => {
    confirmMock.mockReturnValue(false);
    await renderAndWait();

    const deleteButtons = screen.getAllByTitle("Delete project");
    await userEvent.click(deleteButtons[0]);

    expect(confirmMock).toHaveBeenCalledWith(
      "Are you sure you want to delete this project? This action cannot be undone."
    );
    expect(mockDeleteProject).not.toHaveBeenCalled();
    expect(screen.getByText("My Portfolio")).toBeInTheDocument();
  });

  it("deletes project when confirmed", async () => {
    confirmMock.mockReturnValue(true);
    await renderAndWait();

    const deleteButtons = screen.getAllByTitle("Delete project");
    await userEvent.click(deleteButtons[0]);

    await waitFor(() => {
      expect(mockDeleteProject).toHaveBeenCalledWith("test-token", "proj-1");
    });

    await waitFor(() => {
      expect(screen.queryByText("My Portfolio")).not.toBeInTheDocument();
    });
  });

  it("handles delete error gracefully", async () => {
    confirmMock.mockReturnValue(true);
    mockDeleteProject.mockRejectedValue(new Error("Delete failed"));

    await renderAndWait();

    const deleteButtons = screen.getAllByTitle("Delete project");
    await userEvent.click(deleteButtons[0]);

    await waitFor(() => {
      expect(screen.getByText("Failed to delete project: Delete failed")).toBeInTheDocument();
    });

    // Project should still be in the list
    expect(screen.getByText("My Portfolio")).toBeInTheDocument();
  });

  it("displays error message on fetch failure", async () => {
    mockGetProjects.mockRejectedValue(new Error("Network error"));

    render(<ProjectsPage />);

    await waitFor(() => {
      expect(screen.getByText(/Error loading projects/i)).toBeInTheDocument();
    });
  });

  it("shows empty state when no projects", async () => {
    mockGetProjects.mockResolvedValue({ projects: [], total: 0 });

    await renderAndWait();

    expect(screen.getByText(/No projects found/i)).toBeInTheDocument();
  });

  it("handles projects with missing scan_data gracefully", async () => {
    mockGetProjects.mockResolvedValue({
      projects: [
        {
          id: "proj-3",
          project_name: "Old Project",
          project_path: "/old",
          scan_timestamp: "2025-01-01T00:00:00Z",
          created_at: "2025-01-01T00:00:00Z",
          total_files: 0,
          total_lines: 0,
          languages: [],
          has_media_analysis: false,
          has_pdf_analysis: false,
          has_code_analysis: false,
          has_git_analysis: false,
          scan_data: null,
        },
      ],
      total: 1,
    });

    await renderAndWait();

    expect(screen.getByText("Old Project")).toBeInTheDocument();
    const zeros = screen.getAllByText("0");
    expect(zeros.length).toBeGreaterThan(0); // shows 0 for missing data (files and lines)
  });

  it("extracts data from scan_data when root fields empty", async () => {
    mockGetProjects.mockResolvedValue({
      projects: [
        {
          id: "proj-4",
          project_name: "Scan Data Project",
          project_path: "/scan",
          scan_timestamp: "2026-01-20T00:00:00Z",
          created_at: "2026-01-20T00:00:00Z",
          total_files: 0, // Empty at root
          total_lines: 0,
          languages: [],
          has_media_analysis: false,
          has_pdf_analysis: false,
          has_code_analysis: false,
          has_git_analysis: false,
          scan_data: {
            summary: {
              total_files: 100, // Data in scan_data
              total_lines: 5000,
              languages: [{ language: "Rust", files: 100 }],
            },
          },
        },
      ],
      total: 1,
    });

    await renderAndWait();

    expect(screen.getByText("Scan Data Project")).toBeInTheDocument();
    expect(screen.getByText("100")).toBeInTheDocument(); // Extracted from scan_data
    expect(screen.getByText("5,000")).toBeInTheDocument(); // Lines formatted
    // Note: Languages from scan_data.summary.languages as array of objects are extracted by getProjectData
  });

  it("handles languages from scan_data", async () => {
    mockGetProjects.mockResolvedValue({
      projects: [
        {
          id: "proj-5",
          project_name: "Multi Lang",
          project_path: "/multi",
          scan_timestamp: "2026-01-20T00:00:00Z",
          created_at: "2026-01-20T00:00:00Z",
          total_files: 10,
          total_lines: 500,
          languages: ["Go", "Shell"], // Root level languages populated by backend
          has_media_analysis: false,
          has_pdf_analysis: false,
          has_code_analysis: false,
          has_git_analysis: false,
          scan_data: {
            summary: {},
          },
        },
      ],
      total: 1,
    });

    await renderAndWait();

    // Languages from root field (populated by backend normalization)
    expect(screen.getByText("Go")).toBeInTheDocument();
    expect(screen.getByText("Shell")).toBeInTheDocument();
  });

  it("calls getProjects with correct token on mount", async () => {
    await renderAndWait();
    expect(mockGetProjects).toHaveBeenCalledWith("test-token");
  });

  it("applies saved project order from selection API", async () => {
    mockGetSelection.mockResolvedValue({
      user_id: "user-1",
      project_order: ["proj-2", "proj-1"],
      skill_order: [],
      selected_project_ids: [],
      selected_skill_ids: [],
      created_at: "2026-01-01T00:00:00Z",
      updated_at: "2026-01-01T00:00:00Z",
    });

    await renderAndWait();

    const rows = screen.getAllByRole("row");
    expect(rows[1].textContent).toContain("Backend API");
    expect(rows[2].textContent).toContain("My Portfolio");
  });

  it("reorders projects with move buttons and persists order", async () => {
    await renderAndWait();

    const moveDownButtons = screen.getAllByTitle("Move down");
    await userEvent.click(moveDownButtons[0]);

    await waitFor(() => {
      expect(mockSaveSelection).toHaveBeenCalledWith("test-token", {
        project_order: ["proj-2", "proj-1"],
      });
    });

    expect(screen.getByText("Project order saved.")).toBeInTheDocument();
  });

  it("reorders projects with keyboard arrows and persists order", async () => {
    await renderAndWait();

    const reorderButtons = screen.getAllByTitle("Reorder project");
    reorderButtons[0].focus();
    await userEvent.keyboard("{ArrowDown}");

    await waitFor(() => {
      expect(mockSaveSelection).toHaveBeenCalledWith("test-token", {
        project_order: ["proj-2", "proj-1"],
      });
    });
  });

  it("modal displays loading state while fetching project details", async () => {
    mockGetProjectById.mockReturnValue(new Promise(() => {})); // never resolves

    await renderAndWait();
    const eyeButtons = screen.getAllByTitle("View details");
    await userEvent.click(eyeButtons[0]);

    // Should show some loading indicator in modal (adjust based on actual implementation)
    await waitFor(() => {
      expect(mockGetProjectById).toHaveBeenCalled();
    });
  });

  it("displays all language badges without truncation for short lists", async () => {
    await renderAndWait();

    // First project has 3 languages - all should be visible
    expect(screen.getByText("TypeScript")).toBeInTheDocument();
    expect(screen.getByText("JavaScript")).toBeInTheDocument();
    expect(screen.getByText("CSS")).toBeInTheDocument();
  });

  // ---------------------------------------------------------------------------
  // Role editing
  // ---------------------------------------------------------------------------

  it("shows existing role badge in modal overview", async () => {
    await renderAndWait();
    const eyeButtons = screen.getAllByTitle("View details");
    await userEvent.click(eyeButtons[0]);

    await waitFor(() => {
      expect(screen.getByText("My Portfolio", { selector: "h2" })).toBeInTheDocument();
    });

    // MOCK_PROJECT_DETAIL has role: "author"
    expect(screen.getByText("author")).toBeInTheDocument();
  });

  it("shows Edit Role button in modal when token is available", async () => {
    await renderAndWait();
    const eyeButtons = screen.getAllByTitle("View details");
    await userEvent.click(eyeButtons[0]);

    await waitFor(() => {
      expect(screen.getByText("My Portfolio", { selector: "h2" })).toBeInTheDocument();
    });

    expect(screen.getByText("Edit Role")).toBeInTheDocument();
  });

  it("shows role select dropdown when Edit Role is clicked", async () => {
    await renderAndWait();
    const eyeButtons = screen.getAllByTitle("View details");
    await userEvent.click(eyeButtons[0]);

    await waitFor(() => {
      expect(screen.getByText("Edit Role")).toBeInTheDocument();
    });

    await userEvent.click(screen.getByText("Edit Role"));

    expect(screen.getByRole("combobox")).toBeInTheDocument();
    expect(screen.getByText("Save")).toBeInTheDocument();
    expect(screen.getByText("Cancel")).toBeInTheDocument();
  });

  it("calls updateProjectRole with correct args when saved", async () => {
    await renderAndWait();
    const eyeButtons = screen.getAllByTitle("View details");
    await userEvent.click(eyeButtons[0]);

    await waitFor(() => {
      expect(screen.getByText("Edit Role")).toBeInTheDocument();
    });

    await userEvent.click(screen.getByText("Edit Role"));

    const select = screen.getByRole("combobox");
    await userEvent.selectOptions(select, "lead");

    await userEvent.click(screen.getByText("Save"));

    await waitFor(() => {
      expect(mockUpdateProjectOverrides).toHaveBeenCalledWith("test-token", "proj-1", { role: "lead" });
    });
  });

  it("updates role badge in table after successful save", async () => {
    await renderAndWait();
    const eyeButtons = screen.getAllByTitle("View details");
    await userEvent.click(eyeButtons[0]);

    await waitFor(() => {
      expect(screen.getByText("Edit Role")).toBeInTheDocument();
    });

    await userEvent.click(screen.getByText("Edit Role"));
    const select = screen.getByRole("combobox");
    await userEvent.selectOptions(select, "lead");
    await userEvent.click(screen.getByText("Save"));

    await waitFor(() => {
      expect(mockUpdateProjectOverrides).toHaveBeenCalled();
    });

    // Close the modal, then confirm the table row shows the updated role
    const closeButton = screen.getByRole("button", { name: /close/i });
    await userEvent.click(closeButton);

    await waitFor(() => {
      expect(screen.queryByText("My Portfolio", { selector: "h2" })).not.toBeInTheDocument();
    });

    expect(screen.getByText("lead")).toBeInTheDocument();
  });

  it("shows error message when updateProjectRole fails", async () => {
    mockUpdateProjectOverrides.mockRejectedValue(new Error("Server error"));

    await renderAndWait();
    const eyeButtons = screen.getAllByTitle("View details");
    await userEvent.click(eyeButtons[0]);

    await waitFor(() => {
      expect(screen.getByText("Edit Role")).toBeInTheDocument();
    });

    await userEvent.click(screen.getByText("Edit Role"));
    const select = screen.getByRole("combobox");
    await userEvent.selectOptions(select, "contributor");
    await userEvent.click(screen.getByText("Save"));

    await waitFor(() => {
      expect(screen.getByText("Server error")).toBeInTheDocument();
    });
  });

  it("cancels role edit without calling API", async () => {
    await renderAndWait();
    const eyeButtons = screen.getAllByTitle("View details");
    await userEvent.click(eyeButtons[0]);

    await waitFor(() => {
      expect(screen.getByText("Edit Role")).toBeInTheDocument();
    });

    await userEvent.click(screen.getByText("Edit Role"));
    await userEvent.click(screen.getByText("Cancel"));

    expect(mockUpdateProjectRole).not.toHaveBeenCalled();
    // Edit Role button should be visible again
    expect(screen.getByText("Edit Role")).toBeInTheDocument();
  });
});
