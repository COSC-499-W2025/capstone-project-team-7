import { describe, it, expect, vi, beforeEach, type Mock } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import ResumesPage from "../app/(dashboard)/resumes/page";

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------

const MOCK_ITEMS = [
  {
    id: "item-1",
    project_name: "Capstone Project",
    start_date: "Sep 2024",
    end_date: "Apr 2025",
    created_at: "2025-04-01T10:00:00Z",
    metadata: {},
  },
  {
    id: "item-2",
    project_name: "Backend API",
    start_date: "Jan 2024",
    end_date: null,
    created_at: "2024-06-15T08:30:00Z",
    metadata: {},
  },
];

const MOCK_ITEM_DETAIL = {
  ...MOCK_ITEMS[0],
  content: "# Capstone Project\n\nBuilt a full-stack application.",
  bullets: [
    "Built REST API with FastAPI and Supabase",
    "Reduced scan time by 40% via parallel processing",
  ],
  source_path: null,
};

vi.mock("@/lib/api/resume", () => ({
  listResumeItems: vi.fn(),
  getResumeItem: vi.fn(),
  createResumeItem: vi.fn(),
  updateResumeItem: vi.fn(),
  deleteResumeItem: vi.fn(),
}));

vi.mock("@/lib/auth", () => ({
  getStoredToken: vi.fn(),
}));

import {
  listResumeItems,
  getResumeItem,
  createResumeItem,
  updateResumeItem,
  deleteResumeItem,
} from "@/lib/api/resume";
import { getStoredToken } from "@/lib/auth";

const mockListResumeItems = listResumeItems as Mock;
const mockGetResumeItem = getResumeItem as Mock;
const mockCreateResumeItem = createResumeItem as Mock;
const mockUpdateResumeItem = updateResumeItem as Mock;
const mockDeleteResumeItem = deleteResumeItem as Mock;
const mockGetStoredToken = getStoredToken as Mock;

// Mock window.confirm
const confirmMock = vi.fn();
Object.defineProperty(window, "confirm", {
  value: confirmMock,
  writable: true,
});

// ---------------------------------------------------------------------------
// Setup
// ---------------------------------------------------------------------------

beforeEach(() => {
  vi.clearAllMocks();
  confirmMock.mockReturnValue(false);

  mockGetStoredToken.mockReturnValue("test-token");
  mockListResumeItems.mockResolvedValue({
    items: [...MOCK_ITEMS],
    page: { limit: 50, offset: 0, total: 2 },
  });
  mockGetResumeItem.mockResolvedValue(MOCK_ITEM_DETAIL);
  mockCreateResumeItem.mockResolvedValue({
    id: "item-new",
    project_name: "New Project",
    start_date: null,
    end_date: null,
    created_at: "2026-02-21T00:00:00Z",
    metadata: {},
    content: "",
    bullets: ["Did something cool"],
    source_path: null,
  });
  mockUpdateResumeItem.mockResolvedValue(MOCK_ITEM_DETAIL);
  mockDeleteResumeItem.mockResolvedValue(undefined);
});

// ---------------------------------------------------------------------------
// Helper
// ---------------------------------------------------------------------------

async function renderAndWait() {
  render(<ResumesPage />);
  await waitFor(() => {
    expect(screen.queryByText("Loading resume items...")).not.toBeInTheDocument();
  });
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("ResumesPage", () => {
  it("renders loading state initially", () => {
    mockListResumeItems.mockReturnValue(new Promise(() => {})); // never resolves
    render(<ResumesPage />);
    expect(screen.getByText("Loading resume items...")).toBeInTheDocument();
  });

  it("shows error if no token", async () => {
    mockGetStoredToken.mockReturnValue(null);
    render(<ResumesPage />);

    await waitFor(() => {
      expect(screen.getByText(/Not authenticated/i)).toBeInTheDocument();
    });
  });

  it("renders resume items after load", async () => {
    await renderAndWait();
    expect(screen.getByText("Capstone Project")).toBeInTheDocument();
    expect(screen.getByText("Backend API")).toBeInTheDocument();
  });

  it("displays date range for item with both dates", async () => {
    await renderAndWait();
    expect(screen.getByText("Sep 2024 – Apr 2025")).toBeInTheDocument();
  });

  it("displays 'From start_date' when only start date is present", async () => {
    await renderAndWait();
    expect(screen.getByText("From Jan 2024")).toBeInTheDocument();
  });

  it("shows item count in header", async () => {
    await renderAndWait();
    expect(screen.getByText("2 items")).toBeInTheDocument();
  });

  it("shows empty state when no items", async () => {
    mockListResumeItems.mockResolvedValue({
      items: [],
      page: { limit: 50, offset: 0, total: 0 },
    });

    render(<ResumesPage />);
    await waitFor(() => {
      expect(screen.queryByText("Loading resume items...")).not.toBeInTheDocument();
    });

    expect(screen.getAllByText(/No resume items yet/i).length).toBeGreaterThan(0);
  });

  it("opens create dialog when 'New Item' button clicked", async () => {
    await renderAndWait();

    const newItemButtons = screen.getAllByText("New Item");
    await userEvent.click(newItemButtons[0]);

    expect(screen.getByText("New Resume Item")).toBeInTheDocument();
    expect(screen.getByLabelText(/Project Name/i)).toBeInTheDocument();
  });

  it("does not delete when confirm dialog is cancelled", async () => {
    confirmMock.mockReturnValue(false);
    await renderAndWait();

    const deleteButtons = screen.getAllByText("Delete");
    await userEvent.click(deleteButtons[0]);

    expect(confirmMock).toHaveBeenCalledWith(
      "Delete this resume item? This cannot be undone."
    );
    expect(mockDeleteResumeItem).not.toHaveBeenCalled();
    expect(screen.getByText("Capstone Project")).toBeInTheDocument();
  });

  it("deletes item when confirmed", async () => {
    confirmMock.mockReturnValue(true);
    await renderAndWait();

    const deleteButtons = screen.getAllByText("Delete");
    await userEvent.click(deleteButtons[0]);

    await waitFor(() => {
      expect(mockDeleteResumeItem).toHaveBeenCalledWith("test-token", "item-1");
    });

    await waitFor(() => {
      expect(screen.queryByText("Capstone Project")).not.toBeInTheDocument();
    });
  });

  it("opens edit dialog with pre-filled data when Edit clicked", async () => {
    await renderAndWait();

    const editButtons = screen.getAllByText("Edit");
    await userEvent.click(editButtons[0]);

    await waitFor(() => {
      expect(mockGetResumeItem).toHaveBeenCalledWith("test-token", "item-1");
    });

    await waitFor(() => {
      expect(screen.getByText("Edit Resume Item")).toBeInTheDocument();
    });

    const projectNameInput = screen.getByLabelText(/Project Name/i) as HTMLInputElement;
    expect(projectNameInput.value).toBe("Capstone Project");
  });

  it("pre-fills bullets in edit dialog", async () => {
    await renderAndWait();

    const editButtons = screen.getAllByText("Edit");
    await userEvent.click(editButtons[0]);

    await waitFor(() => {
      expect(screen.getByText("Edit Resume Item")).toBeInTheDocument();
    });

    const bulletsTextarea = screen.getByRole("textbox", { name: /Bullet Points/i }) as HTMLTextAreaElement;
    expect(bulletsTextarea.value).toContain("Built REST API with FastAPI and Supabase");
  });

  it("creates a new resume item via the dialog", async () => {
    await renderAndWait();

    const newItemButtons = screen.getAllByText("New Item");
    await userEvent.click(newItemButtons[0]);

    const projectNameInput = screen.getByLabelText(/Project Name/i);
    await userEvent.type(projectNameInput, "New Project");

    const createButton = screen.getByRole("button", { name: /Create/i });
    await userEvent.click(createButton);

    await waitFor(() => {
      expect(mockCreateResumeItem).toHaveBeenCalledWith(
        "test-token",
        expect.objectContaining({ project_name: "New Project" })
      );
    });
  });

  it("shows form validation error when project name is empty", async () => {
    await renderAndWait();

    const newItemButtons = screen.getAllByText("New Item");
    await userEvent.click(newItemButtons[0]);

    // Submit without filling in project name
    const createButton = screen.getByRole("button", { name: /Create/i });
    await userEvent.click(createButton);

    expect(screen.getByText("Project name is required.")).toBeInTheDocument();
    expect(mockCreateResumeItem).not.toHaveBeenCalled();
  });

  it("closes dialog when Cancel is clicked", async () => {
    await renderAndWait();

    const newItemButtons = screen.getAllByText("New Item");
    await userEvent.click(newItemButtons[0]);

    expect(screen.getByText("New Resume Item")).toBeInTheDocument();

    const cancelButton = screen.getByRole("button", { name: /Cancel/i });
    await userEvent.click(cancelButton);

    await waitFor(() => {
      expect(screen.queryByText("New Resume Item")).not.toBeInTheDocument();
    });
  });

  it("displays error banner on fetch failure", async () => {
    mockListResumeItems.mockRejectedValue(new Error("Network error"));

    render(<ResumesPage />);

    await waitFor(() => {
      expect(screen.getByText("Network error")).toBeInTheDocument();
    });
  });

  it("calls listResumeItems with correct token on mount", async () => {
    await renderAndWait();
    expect(mockListResumeItems).toHaveBeenCalledWith("test-token");
  });

  it("re-fetches items when Refresh button is clicked", async () => {
    await renderAndWait();

    expect(mockListResumeItems).toHaveBeenCalledTimes(1);

    const refreshButton = screen.getByText("Refresh");
    await userEvent.click(refreshButton);

    await waitFor(() => {
      expect(mockListResumeItems).toHaveBeenCalledTimes(2);
    });
  });

  it("handles delete API error gracefully", async () => {
    confirmMock.mockReturnValue(true);
    mockDeleteResumeItem.mockRejectedValue(new Error("Delete failed"));

    await renderAndWait();

    const deleteButtons = screen.getAllByText("Delete");
    await userEvent.click(deleteButtons[0]);

    await waitFor(() => {
      expect(screen.getByText("Delete failed")).toBeInTheDocument();
    });

    // Item should still be in the list
    expect(screen.getByText("Capstone Project")).toBeInTheDocument();
  });
});
