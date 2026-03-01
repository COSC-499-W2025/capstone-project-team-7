import { describe, it, expect, vi, beforeEach, type Mock } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import PortfolioPage from "../app/(dashboard)/portfolio/page";

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------

const MOCK_ITEMS = [
  {
    id: "item-1",
    user_id: "user-1",
    created_at: "2025-04-01T10:00:00Z",
    updated_at: "2025-04-01T10:00:00Z",
    title: "E-Commerce Platform",
    role: "Lead Developer",
    summary: "Built a full-stack e-commerce app with React and FastAPI.",
    evidence: "Reduced page load time by 40%.",
    thumbnail: null,
  },
  {
    id: "item-2",
    user_id: "user-1",
    created_at: "2024-06-15T08:30:00Z",
    updated_at: "2024-06-15T08:30:00Z",
    title: "Data Pipeline",
    role: null,
    summary: null,
    evidence: null,
    thumbnail: null,
  },
];

const MOCK_SKILLS = ["FastAPI", "Python", "React", "TypeScript"];

const MOCK_CHRONOLOGY = {
  projects: [
    {
      project_id: "proj-1",
      name: "My App",
      start_date: "Jan 2024",
      end_date: "Dec 2024",
      duration_days: 365,
      role: "author",
      evidence: ["Wrote 10k lines of code", "Led team of 3"],
    },
  ],
  skills: [],
};

const MOCK_PROJECTS = [
  { id: "proj-1", project_name: "My App", project_path: "/app", total_files: 10, total_lines: 500 },
  { id: "proj-2", project_name: "Backend API", project_path: "/api", total_files: 5, total_lines: 200 },
];

vi.mock("@/lib/api/portfolio", () => ({
  listPortfolioItems: vi.fn(),
  createPortfolioItem: vi.fn(),
  updatePortfolioItem: vi.fn(),
  deletePortfolioItem: vi.fn(),
  generatePortfolioItem: vi.fn(),
  getPortfolioChronology: vi.fn(),
}));

vi.mock("@/lib/api/projects", () => ({
  getProjects: vi.fn(),
  getSkills: vi.fn(),
}));

vi.mock("@/lib/auth", () => ({
  getStoredToken: vi.fn(),
}));

import {
  listPortfolioItems,
  createPortfolioItem,
  updatePortfolioItem,
  deletePortfolioItem,
  generatePortfolioItem,
  getPortfolioChronology,
} from "@/lib/api/portfolio";
import { getProjects, getSkills } from "@/lib/api/projects";
import { getStoredToken } from "@/lib/auth";

const mockListPortfolioItems = listPortfolioItems as Mock;
const mockCreatePortfolioItem = createPortfolioItem as Mock;
const mockUpdatePortfolioItem = updatePortfolioItem as Mock;
const mockDeletePortfolioItem = deletePortfolioItem as Mock;
const mockGeneratePortfolioItem = generatePortfolioItem as Mock;
const mockGetPortfolioChronology = getPortfolioChronology as Mock;
const mockGetProjects = getProjects as Mock;
const mockGetSkills = getSkills as Mock;
const mockGetStoredToken = getStoredToken as Mock;

const confirmMock = vi.fn();
Object.defineProperty(window, "confirm", { value: confirmMock, writable: true });

// happy-dom doesn't implement pointer capture — required by Radix UI Select
Element.prototype.hasPointerCapture = vi.fn(() => false) as unknown as typeof Element.prototype.hasPointerCapture;
Element.prototype.setPointerCapture = vi.fn() as unknown as typeof Element.prototype.setPointerCapture;
Element.prototype.releasePointerCapture = vi.fn() as unknown as typeof Element.prototype.releasePointerCapture;

// ---------------------------------------------------------------------------
// Setup
// ---------------------------------------------------------------------------

beforeEach(() => {
  vi.clearAllMocks();
  confirmMock.mockReturnValue(false);

  mockGetStoredToken.mockReturnValue("test-token");
  mockListPortfolioItems.mockResolvedValue([...MOCK_ITEMS]);
  mockGetSkills.mockResolvedValue({ skills: [...MOCK_SKILLS] });
  mockGetPortfolioChronology.mockResolvedValue({ ...MOCK_CHRONOLOGY });
  mockGetProjects.mockResolvedValue({ projects: [...MOCK_PROJECTS], count: 2 });
  mockCreatePortfolioItem.mockResolvedValue({
    id: "item-new",
    user_id: "user-1",
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
    title: "New Project",
    role: null,
    summary: null,
    evidence: null,
    thumbnail: null,
  });
  mockUpdatePortfolioItem.mockResolvedValue({ ...MOCK_ITEMS[0] });
  mockDeletePortfolioItem.mockResolvedValue(undefined);
  mockGeneratePortfolioItem.mockResolvedValue({
    id: null,
    title: "Generated Title",
    role: "Developer",
    summary: "Generated summary.",
    evidence: "Generated evidence.",
    persisted: false,
  });
});

// ---------------------------------------------------------------------------
// Helper
// ---------------------------------------------------------------------------

async function renderAndWait() {
  render(<PortfolioPage />);
  await waitFor(() => {
    expect(screen.queryByText("Loading portfolio...")).not.toBeInTheDocument();
  });
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("PortfolioPage", () => {
  // --- Initial states ---

  it("renders loading state initially", () => {
    mockListPortfolioItems.mockReturnValue(new Promise(() => {}));
    render(<PortfolioPage />);
    expect(screen.getByText("Loading portfolio...")).toBeInTheDocument();
  });

  it("shows error banner if no token", async () => {
    mockGetStoredToken.mockReturnValue(null);
    render(<PortfolioPage />);
    await waitFor(() => {
      expect(screen.getByText(/Not authenticated/i)).toBeInTheDocument();
    });
  });

  it("renders portfolio items after load", async () => {
    await renderAndWait();
    expect(screen.getByText("E-Commerce Platform")).toBeInTheDocument();
    expect(screen.getByText("Data Pipeline")).toBeInTheDocument();
  });

  it("shows item count in header", async () => {
    await renderAndWait();
    expect(screen.getByText("2 items")).toBeInTheDocument();
  });

  it("shows singular item count when only one item", async () => {
    mockListPortfolioItems.mockResolvedValue([MOCK_ITEMS[0]]);
    await renderAndWait();
    expect(screen.getByText("1 item")).toBeInTheDocument();
  });

  it("shows role for items that have one", async () => {
    await renderAndWait();
    expect(screen.getByText("Lead Developer")).toBeInTheDocument();
  });

  it("shows summary for items that have one", async () => {
    await renderAndWait();
    expect(
      screen.getByText("Built a full-stack e-commerce app with React and FastAPI.")
    ).toBeInTheDocument();
  });

  // --- Empty state ---

  it("shows empty state when no items", async () => {
    mockListPortfolioItems.mockResolvedValue([]);
    await renderAndWait();
    expect(screen.getAllByText(/No portfolio items yet/i).length).toBeGreaterThan(0);
  });

  // --- Error handling ---

  it("shows error banner when fetch fails", async () => {
    mockListPortfolioItems.mockRejectedValue(new Error("Server error"));
    render(<PortfolioPage />);
    await waitFor(() => {
      expect(screen.getByText("Server error")).toBeInTheDocument();
    });
  });

  it("still renders if skills fetch fails", async () => {
    mockGetSkills.mockRejectedValue(new Error("Skills unavailable"));
    await renderAndWait();
    // Items should still show
    expect(screen.getByText("E-Commerce Platform")).toBeInTheDocument();
  });

  it("still renders if chronology fetch fails", async () => {
    mockGetPortfolioChronology.mockRejectedValue(new Error("Chronology unavailable"));
    await renderAndWait();
    expect(screen.getByText("E-Commerce Platform")).toBeInTheDocument();
  });

  // --- Skills section ---

  it("displays skills as badges", async () => {
    await renderAndWait();
    expect(screen.getByText("FastAPI")).toBeInTheDocument();
    expect(screen.getByText("React")).toBeInTheDocument();
    expect(screen.getByText("TypeScript")).toBeInTheDocument();
  });

  it("shows skill count in skills summary header", async () => {
    await renderAndWait();
    expect(screen.getByText(/4 skills across all projects/i)).toBeInTheDocument();
  });

  it("shows fallback message when no skills", async () => {
    mockGetSkills.mockResolvedValue({ skills: [] });
    await renderAndWait();
    expect(
      screen.getByText(/No skills found/i)
    ).toBeInTheDocument();
  });

  it("collapses skills section when toggle clicked", async () => {
    await renderAndWait();
    const toggleButton = screen.getByText(/Skills Summary/i);
    await userEvent.click(toggleButton);
    // Skills badges should be gone
    expect(screen.queryByText("FastAPI")).not.toBeInTheDocument();
  });

  // --- Refresh ---

  it("re-fetches data when Refresh is clicked", async () => {
    await renderAndWait();
    expect(mockListPortfolioItems).toHaveBeenCalledTimes(1);

    await userEvent.click(screen.getByText("Refresh"));

    await waitFor(() => {
      expect(mockListPortfolioItems).toHaveBeenCalledTimes(2);
    });
  });

  // --- Create dialog ---

  it("opens create dialog when 'New Item' button clicked", async () => {
    await renderAndWait();
    const newItemButtons = screen.getAllByText("New Item");
    await userEvent.click(newItemButtons[0]);
    expect(screen.getByText("New Portfolio Item")).toBeInTheDocument();
    expect(screen.getByLabelText(/Title/i)).toBeInTheDocument();
  });

  it("shows validation error when title is empty on create", async () => {
    await renderAndWait();
    const newItemButtons = screen.getAllByText("New Item");
    await userEvent.click(newItemButtons[0]);

    await userEvent.click(screen.getByRole("button", { name: /Create/i }));

    expect(screen.getByText("Title is required.")).toBeInTheDocument();
    expect(mockCreatePortfolioItem).not.toHaveBeenCalled();
  });

  it("creates a new item via the dialog", async () => {
    await renderAndWait();
    const newItemButtons = screen.getAllByText("New Item");
    await userEvent.click(newItemButtons[0]);

    const titleInput = screen.getByLabelText(/Title/i);
    await userEvent.type(titleInput, "New Project");

    await userEvent.click(screen.getByRole("button", { name: /Create/i }));

    await waitFor(() => {
      expect(mockCreatePortfolioItem).toHaveBeenCalledWith(
        "test-token",
        expect.objectContaining({ title: "New Project" })
      );
    });
  });

  it("adds created item to the list without refetch", async () => {
    await renderAndWait();
    const newItemButtons = screen.getAllByText("New Item");
    await userEvent.click(newItemButtons[0]);

    await userEvent.type(screen.getByLabelText(/Title/i), "New Project");
    await userEvent.click(screen.getByRole("button", { name: /Create/i }));

    await waitFor(() => {
      expect(screen.getByText("New Project")).toBeInTheDocument();
    });
    // Original items should still be there
    expect(screen.getByText("E-Commerce Platform")).toBeInTheDocument();
  });

  it("closes create dialog after successful create", async () => {
    await renderAndWait();
    const newItemButtons = screen.getAllByText("New Item");
    await userEvent.click(newItemButtons[0]);

    await userEvent.type(screen.getByLabelText(/Title/i), "New Project");
    await userEvent.click(screen.getByRole("button", { name: /Create/i }));

    await waitFor(() => {
      expect(screen.queryByText("New Portfolio Item")).not.toBeInTheDocument();
    });
  });

  it("shows form error when create API fails", async () => {
    mockCreatePortfolioItem.mockRejectedValue(new Error("Creation failed"));
    await renderAndWait();

    const newItemButtons = screen.getAllByText("New Item");
    await userEvent.click(newItemButtons[0]);

    await userEvent.type(screen.getByLabelText(/Title/i), "New Project");
    await userEvent.click(screen.getByRole("button", { name: /Create/i }));

    await waitFor(() => {
      expect(screen.getByText("Creation failed")).toBeInTheDocument();
    });
  });

  it("closes dialog when Cancel is clicked", async () => {
    await renderAndWait();
    const newItemButtons = screen.getAllByText("New Item");
    await userEvent.click(newItemButtons[0]);

    expect(screen.getByText("New Portfolio Item")).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: /Cancel/i }));

    await waitFor(() => {
      expect(screen.queryByText("New Portfolio Item")).not.toBeInTheDocument();
    });
  });

  // --- Edit dialog ---

  it("opens edit dialog with pre-filled data when Edit clicked", async () => {
    await renderAndWait();

    const editButtons = screen.getAllByText("Edit");
    await userEvent.click(editButtons[0]);

    expect(screen.getByText("Edit Portfolio Item")).toBeInTheDocument();
    const titleInput = screen.getByLabelText(/Title/i) as HTMLInputElement;
    expect(titleInput.value).toBe("E-Commerce Platform");
  });

  it("pre-fills role, summary, and evidence in edit dialog", async () => {
    await renderAndWait();
    const editButtons = screen.getAllByText("Edit");
    await userEvent.click(editButtons[0]);

    const roleInput = screen.getByLabelText(/Role/i) as HTMLInputElement;
    const summaryTextarea = screen.getByLabelText(/Summary/i) as HTMLTextAreaElement;
    const evidenceTextarea = screen.getByLabelText(/Key Achievements/i) as HTMLTextAreaElement;

    expect(roleInput.value).toBe("Lead Developer");
    expect(summaryTextarea.value).toContain("full-stack e-commerce app");
    expect(evidenceTextarea.value).toContain("Reduced page load time");
  });

  it("calls updatePortfolioItem with correct args on save", async () => {
    await renderAndWait();
    const editButtons = screen.getAllByText("Edit");
    await userEvent.click(editButtons[0]);

    await userEvent.click(screen.getByRole("button", { name: /Save Changes/i }));

    await waitFor(() => {
      expect(mockUpdatePortfolioItem).toHaveBeenCalledWith(
        "test-token",
        "item-1",
        expect.objectContaining({ title: "E-Commerce Platform" })
      );
    });
  });

  it("updates item in list after successful edit", async () => {
    mockUpdatePortfolioItem.mockResolvedValue({
      ...MOCK_ITEMS[0],
      title: "Updated Platform",
    });
    await renderAndWait();

    const editButtons = screen.getAllByText("Edit");
    await userEvent.click(editButtons[0]);

    // Clear and re-type title
    const titleInput = screen.getByLabelText(/Title/i);
    await userEvent.clear(titleInput);
    await userEvent.type(titleInput, "Updated Platform");

    await userEvent.click(screen.getByRole("button", { name: /Save Changes/i }));

    await waitFor(() => {
      expect(screen.getByText("Updated Platform")).toBeInTheDocument();
    });
  });

  it("shows form error when edit API fails", async () => {
    mockUpdatePortfolioItem.mockRejectedValue(new Error("Update failed"));
    await renderAndWait();

    const editButtons = screen.getAllByText("Edit");
    await userEvent.click(editButtons[0]);

    await userEvent.click(screen.getByRole("button", { name: /Save Changes/i }));

    await waitFor(() => {
      expect(screen.getByText("Update failed")).toBeInTheDocument();
    });
  });

  // --- Delete ---

  it("does not delete when confirm is cancelled", async () => {
    confirmMock.mockReturnValue(false);
    await renderAndWait();

    const deleteButtons = screen.getAllByText("Delete");
    await userEvent.click(deleteButtons[0]);

    expect(confirmMock).toHaveBeenCalledWith(
      "Delete this portfolio item? This cannot be undone."
    );
    expect(mockDeletePortfolioItem).not.toHaveBeenCalled();
    expect(screen.getByText("E-Commerce Platform")).toBeInTheDocument();
  });

  it("deletes item when confirmed", async () => {
    confirmMock.mockReturnValue(true);
    await renderAndWait();

    const deleteButtons = screen.getAllByText("Delete");
    await userEvent.click(deleteButtons[0]);

    await waitFor(() => {
      expect(mockDeletePortfolioItem).toHaveBeenCalledWith("test-token", "item-1");
    });

    await waitFor(() => {
      expect(screen.queryByText("E-Commerce Platform")).not.toBeInTheDocument();
    });
  });

  it("shows error banner when delete API fails", async () => {
    confirmMock.mockReturnValue(true);
    mockDeletePortfolioItem.mockRejectedValue(new Error("Delete failed"));

    await renderAndWait();

    const deleteButtons = screen.getAllByText("Delete");
    await userEvent.click(deleteButtons[0]);

    await waitFor(() => {
      expect(screen.getByText("Delete failed")).toBeInTheDocument();
    });

    // Item should still be in the list
    expect(screen.getByText("E-Commerce Platform")).toBeInTheDocument();
  });

  // --- Generate from project ---

  it("shows 'Generate from Project' section in create dialog when projects exist", async () => {
    await renderAndWait();
    const newItemButtons = screen.getAllByText("New Item");
    await userEvent.click(newItemButtons[0]);

    expect(screen.getByText("Generate from Project")).toBeInTheDocument();
    expect(screen.getByText("Fill from Project")).toBeInTheDocument();
  });

  it("does not show generate section when no projects are available", async () => {
    mockGetProjects.mockResolvedValue({ projects: [], count: 0 });
    await renderAndWait();

    const newItemButtons = screen.getAllByText("New Item");
    await userEvent.click(newItemButtons[0]);

    expect(screen.queryByText("Generate from Project")).not.toBeInTheDocument();
  });

  it("fills form fields after generating from project", async () => {
    await renderAndWait();
    const newItemButtons = screen.getAllByText("New Item");
    await userEvent.click(newItemButtons[0]);

    // Select a project from the dropdown
    const selectTrigger = screen.getByRole("combobox");
    await userEvent.click(selectTrigger);

    const projectOption = await screen.findByText("My App");
    await userEvent.click(projectOption);

    await userEvent.click(screen.getByText("Fill from Project"));

    await waitFor(() => {
      expect(mockGeneratePortfolioItem).toHaveBeenCalledWith(
        "test-token",
        expect.objectContaining({ project_id: "proj-1", persist: false })
      );
    });

    await waitFor(() => {
      const titleInput = screen.getByLabelText(/Title/i) as HTMLInputElement;
      expect(titleInput.value).toBe("Generated Title");
    });
  });

  it("shows error when generate from project fails", async () => {
    mockGeneratePortfolioItem.mockRejectedValue(new Error("Generation failed"));
    await renderAndWait();

    const newItemButtons = screen.getAllByText("New Item");
    await userEvent.click(newItemButtons[0]);

    const selectTrigger = screen.getByRole("combobox");
    await userEvent.click(selectTrigger);
    const projectOption = await screen.findByText("My App");
    await userEvent.click(projectOption);

    await userEvent.click(screen.getByText("Fill from Project"));

    await waitFor(() => {
      expect(screen.getByText("Generation failed")).toBeInTheDocument();
    });
  });

  // --- Project Timeline tab ---

  it("switches to Project Timeline tab", async () => {
    await renderAndWait();
    await userEvent.click(screen.getByRole("button", { name: "Project Timeline" }));
    expect(screen.getByText("My App")).toBeInTheDocument();
    expect(screen.getByText("Jan 2024 – Dec 2024")).toBeInTheDocument();
  });

  it("shows evidence bullet points in timeline", async () => {
    await renderAndWait();
    await userEvent.click(screen.getByRole("button", { name: "Project Timeline" }));
    expect(screen.getByText("Wrote 10k lines of code")).toBeInTheDocument();
    expect(screen.getByText("Led team of 3")).toBeInTheDocument();
  });

  it("shows empty timeline state when no projects in chronology", async () => {
    mockGetPortfolioChronology.mockResolvedValue({ projects: [], skills: [] });
    await renderAndWait();
    await userEvent.click(screen.getByRole("button", { name: "Project Timeline" }));
    expect(screen.getByText(/No project timeline data/i)).toBeInTheDocument();
  });

  it("truncates evidence list beyond 3 items", async () => {
    mockGetPortfolioChronology.mockResolvedValue({
      projects: [
        {
          project_id: "proj-x",
          name: "Big Project",
          start_date: null,
          end_date: null,
          duration_days: null,
          role: null,
          evidence: ["Point 1", "Point 2", "Point 3", "Point 4", "Point 5"],
        },
      ],
      skills: [],
    });
    await renderAndWait();
    await userEvent.click(screen.getByRole("button", { name: "Project Timeline" }));
    expect(screen.getByText("+2 more")).toBeInTheDocument();
  });

  // --- API calls ---

  it("calls API functions with the stored token on mount", async () => {
    await renderAndWait();
    expect(mockListPortfolioItems).toHaveBeenCalledWith("test-token");
    expect(mockGetSkills).toHaveBeenCalledWith("test-token");
    expect(mockGetPortfolioChronology).toHaveBeenCalledWith("test-token");
  });
});
