import { describe, expect, it, vi, type Mock } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import SettingsPage from "../app/(dashboard)/settings/page";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn() }),
}));

vi.mock("@/lib/theme", () => ({
  loadTheme: vi.fn(() => "dark"),
  saveTheme: vi.fn(),
  applyTheme: vi.fn(),
}));

vi.mock("@/lib/settings", () => ({
  loadSettings: vi.fn(() => ({})),
  saveSettings: vi.fn(() => true),
}));

vi.mock("@/lib/auth", () => ({
  auth: {
    getSession: vi.fn(),
  },
  clearStoredRefreshToken: vi.fn(),
  clearStoredToken: vi.fn(),
  getStoredRefreshToken: vi.fn(() => null),
  getStoredToken: vi.fn(() => null),
  setStoredToken: vi.fn(),
}));

vi.mock("@/lib/api", () => ({
  consent: {
    get: vi.fn(),
    set: vi.fn(),
    notice: vi.fn(),
  },
  config: {
    get: vi.fn(),
    listProfiles: vi.fn(),
    saveProfile: vi.fn(),
    update: vi.fn(),
  },
  encryption: {
    status: vi.fn(),
  },
}));

import { encryption } from "@/lib/api";

const mockEncryptionStatus = encryption.status as Mock;

describe("Settings encryption status panel", () => {
  it("renders ready state when encryption is configured", async () => {
    mockEncryptionStatus.mockResolvedValue({
      ok: true,
      data: { enabled: true, ready: true, error: null },
    });

    render(<SettingsPage />);

    await waitFor(() => {
      expect(screen.getByText("Encryption ready")).toBeInTheDocument();
    });

    expect(screen.getByText("Encryption is active.")).toBeInTheDocument();
  });

  it("renders warning state when encryption is not ready", async () => {
    mockEncryptionStatus.mockResolvedValue({
      ok: true,
      data: { enabled: false, ready: false, error: "missing key" },
    });

    render(<SettingsPage />);

    await waitFor(() => {
      expect(screen.getByText("Action required")).toBeInTheDocument();
    });

    expect(screen.getByText(/Set ENCRYPTION_MASTER_KEY/i)).toBeInTheDocument();
    expect(screen.getByText(/Details: missing key/i)).toBeInTheDocument();
  });
});
