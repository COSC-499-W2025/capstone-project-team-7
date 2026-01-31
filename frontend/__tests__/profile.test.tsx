import { describe, it, expect, vi, beforeEach, type Mock } from "vitest";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import ProfilePage from "../app/profile/page";

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------

const MOCK_PROFILE = {
  user_id: "u1",
  display_name: "Jane Doe",
  email: "jane@example.com",
  education: "B.Sc. CS",
  career_title: "Engineer",
  avatar_url: "",
  schema_url: "https://schema.example.com",
  drive_url: "https://drive.google.com/example",
  updated_at: null,
};

vi.mock("@/lib/api", () => ({
  api: {
    profile: {
      get: vi.fn(),
      update: vi.fn(),
      uploadAvatar: vi.fn(),
      changePassword: vi.fn(),
    },
  },
}));

import { api } from "@/lib/api";

const mockGet = api.profile.get as Mock;
const mockUpdate = api.profile.update as Mock;
const mockChangePassword = api.profile.changePassword as Mock;

// Mock localStorage
const localStorageMock = (() => {
  let store: Record<string, string> = {};
  return {
    getItem: vi.fn((key: string) => store[key] ?? null),
    setItem: vi.fn((key: string, value: string) => { store[key] = value; }),
    removeItem: vi.fn((key: string) => { delete store[key]; }),
    clear: vi.fn(() => { store = {}; }),
    get length() { return Object.keys(store).length; },
    key: vi.fn((i: number) => Object.keys(store)[i] ?? null),
  };
})();

Object.defineProperty(window, "localStorage", { value: localStorageMock });

// Mock window.location
const locationMock = { href: "" };
Object.defineProperty(window, "location", {
  value: locationMock,
  writable: true,
});

// Mock window.history.back
const historyBackMock = vi.fn();
Object.defineProperty(window, "history", {
  value: { back: historyBackMock },
  writable: true,
});

// Mock URL.createObjectURL / revokeObjectURL
URL.createObjectURL = vi.fn(() => "blob:mock-url");
URL.revokeObjectURL = vi.fn();

// ---------------------------------------------------------------------------
// Setup
// ---------------------------------------------------------------------------

beforeEach(() => {
  vi.clearAllMocks();
  localStorageMock.clear();
  localStorageMock.setItem("access_token", "test-token");
  locationMock.href = "";

  mockGet.mockResolvedValue({ ok: true, data: { ...MOCK_PROFILE } });
  mockUpdate.mockResolvedValue({ ok: true, data: { ...MOCK_PROFILE } });
  mockChangePassword.mockResolvedValue({ ok: true, data: { ok: true, message: "done" } });
});

// ---------------------------------------------------------------------------
// Helper
// ---------------------------------------------------------------------------

async function renderAndWait() {
  render(<ProfilePage />);
  await waitFor(() => {
    expect(screen.queryByText("Loading profile...")).not.toBeInTheDocument();
  });
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("ProfilePage", () => {
  it("renders loading state initially", () => {
    mockGet.mockReturnValue(new Promise(() => {})); // never resolves
    render(<ProfilePage />);
    expect(screen.getByText("Loading profile...")).toBeInTheDocument();
  });

  it("renders profile form after load", async () => {
    await renderAndWait();
    expect(screen.getByLabelText("Display Name")).toHaveValue("Jane Doe");
    expect(screen.getByLabelText("Email")).toHaveValue("jane@example.com");
    expect(screen.getByLabelText("Education")).toHaveValue("B.Sc. CS");
    expect(screen.getByLabelText("Career Title")).toHaveValue("Engineer");
    expect(screen.getByLabelText("GitHub Profile URL")).toHaveValue("https://schema.example.com");
    expect(screen.getByLabelText("Team Google Drive URL")).toHaveValue("https://drive.google.com/example");
  });

  it("email field is read-only", async () => {
    await renderAndWait();
    const emailInput = screen.getByLabelText("Email");
    expect(emailInput).toHaveAttribute("readonly");
  });

  it("back button calls history.back()", async () => {
    await renderAndWait();
    const backBtn = screen.getByRole("button", { name: "Back" });
    await userEvent.click(backBtn);
    expect(historyBackMock).toHaveBeenCalledTimes(1);
  });

  it("editing fields enables Save button", async () => {
    await renderAndWait();
    const saveBtn = screen.getByRole("button", { name: "Save Changes" });
    expect(saveBtn).toBeDisabled();

    const nameInput = screen.getByLabelText("Display Name");
    await userEvent.clear(nameInput);
    await userEvent.type(nameInput, "New Name");
    expect(saveBtn).toBeEnabled();
  });

  it("cancel resets fields to original values", async () => {
    await renderAndWait();
    const nameInput = screen.getByLabelText("Display Name");
    await userEvent.clear(nameInput);
    await userEvent.type(nameInput, "Changed");

    const cancelBtn = screen.getByRole("button", { name: "Cancel" });
    await userEvent.click(cancelBtn);
    expect(nameInput).toHaveValue("Jane Doe");
  });

  it("save calls API with changed fields", async () => {
    mockUpdate.mockResolvedValue({
      ok: true,
      data: { ...MOCK_PROFILE, display_name: "New Name" },
    });

    await renderAndWait();
    const nameInput = screen.getByLabelText("Display Name");
    await userEvent.clear(nameInput);
    await userEvent.type(nameInput, "New Name");

    const saveBtn = screen.getByRole("button", { name: "Save Changes" });
    await userEvent.click(saveBtn);

    await waitFor(() => {
      expect(mockUpdate).toHaveBeenCalledWith("test-token", {
        display_name: "New Name",
      });
    });
  });

  it("avatar change button triggers file input", async () => {
    await renderAndWait();
    const changeBtn = screen.getByRole("button", { name: "Change" });
    const fileInput = screen.getByTestId("avatar-file-input") as HTMLInputElement;
    const clickSpy = vi.spyOn(fileInput, "click");

    await userEvent.click(changeBtn);
    expect(clickSpy).toHaveBeenCalled();
  });

  it("avatar remove clears preview", async () => {
    mockGet.mockResolvedValue({
      ok: true,
      data: { ...MOCK_PROFILE, avatar_url: "https://avatar.example.com/img.png" },
    });

    await renderAndWait();
    // Remove button should be present when there's an avatar
    const removeBtn = screen.getByRole("button", { name: "Remove" });
    await userEvent.click(removeBtn);

    // After removal, the Remove button should be gone
    expect(screen.queryByRole("button", { name: "Remove" })).not.toBeInTheDocument();
  });

  it("password validation - mismatch error", async () => {
    await renderAndWait();
    const newPwInput = screen.getByLabelText("New Password");
    const confirmPwInput = screen.getByLabelText("Confirm New Password");

    await userEvent.type(newPwInput, "password123");
    await userEvent.type(confirmPwInput, "different456");

    const updatePwBtn = screen.getByRole("button", { name: "Update Password" });
    await userEvent.click(updatePwBtn);

    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent("New passwords do not match.");
    });
  });

  it("password validation - too short error", async () => {
    await renderAndWait();
    const newPwInput = screen.getByLabelText("New Password");
    const confirmPwInput = screen.getByLabelText("Confirm New Password");

    await userEvent.type(newPwInput, "abc");
    await userEvent.type(confirmPwInput, "abc");

    const updatePwBtn = screen.getByRole("button", { name: "Update Password" });
    await userEvent.click(updatePwBtn);

    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent("New password must be at least 6 characters.");
    });
  });

  it("password validation - empty fields error", async () => {
    await renderAndWait();
    const updatePwBtn = screen.getByRole("button", { name: "Update Password" });
    await userEvent.click(updatePwBtn);

    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent("Please fill in all password fields.");
    });
  });

  it("password change calls API on success", async () => {
    await renderAndWait();
    const newPwInput = screen.getByLabelText("New Password");
    const confirmPwInput = screen.getByLabelText("Confirm New Password");

    await userEvent.type(newPwInput, "newpass123");
    await userEvent.type(confirmPwInput, "newpass123");

    const updatePwBtn = screen.getByRole("button", { name: "Update Password" });
    await userEvent.click(updatePwBtn);

    await waitFor(() => {
      expect(mockChangePassword).toHaveBeenCalledWith("test-token", "newpass123");
    });
    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent("Password updated successfully.");
    });
  });

  it("logout clears localStorage and redirects", async () => {
    await renderAndWait();
    const logoutBtn = screen.getByRole("button", { name: "Log out" });
    await userEvent.click(logoutBtn);

    expect(localStorageMock.removeItem).toHaveBeenCalledWith("access_token");
    expect(localStorageMock.removeItem).toHaveBeenCalledWith("refresh_token");
    expect(localStorageMock.removeItem).toHaveBeenCalledWith("user_id");
    expect(localStorageMock.removeItem).toHaveBeenCalledWith("email");
    expect(locationMock.href).toBe("/");
  });

  it("shows error message on API failure", async () => {
    mockUpdate.mockResolvedValue({ ok: false, error: "Server error" });

    await renderAndWait();
    const nameInput = screen.getByLabelText("Display Name");
    await userEvent.clear(nameInput);
    await userEvent.type(nameInput, "Changed");

    const saveBtn = screen.getByRole("button", { name: "Save Changes" });
    await userEvent.click(saveBtn);

    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent("Server error");
    });
  });

  it("shows success message on save", async () => {
    mockUpdate.mockResolvedValue({
      ok: true,
      data: { ...MOCK_PROFILE, display_name: "Updated" },
    });

    await renderAndWait();
    const nameInput = screen.getByLabelText("Display Name");
    await userEvent.clear(nameInput);
    await userEvent.type(nameInput, "Updated");

    const saveBtn = screen.getByRole("button", { name: "Save Changes" });
    await userEvent.click(saveBtn);

    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent("Profile saved.");
    });
  });
});
