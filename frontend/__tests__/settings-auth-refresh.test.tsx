import { beforeEach, describe, expect, it, vi, type Mock } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import SettingsPage from "../app/(dashboard)/settings/page";

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
  getStoredRefreshToken: vi.fn(),
  getStoredToken: vi.fn(),
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
}));

import { auth, getStoredRefreshToken, getStoredToken } from "@/lib/auth";
import { config, consent } from "@/lib/api";

const mockGetSession = auth.getSession as Mock;
const mockGetStoredToken = getStoredToken as Mock;
const mockGetStoredRefreshToken = getStoredRefreshToken as Mock;
const mockConsentGet = consent.get as Mock;
const mockConfigGet = config.get as Mock;
const mockListProfiles = config.listProfiles as Mock;

describe("Settings page auth recovery", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockConsentGet.mockResolvedValue({ ok: false, status: 401, error: "Unauthorized" });
    mockConfigGet.mockResolvedValue({ ok: false, status: 401, error: "Unauthorized" });
    mockListProfiles.mockResolvedValue({ ok: false, status: 401, error: "Unauthorized" });
  });

  it("checks session when only a refresh token exists", async () => {
    mockGetStoredToken.mockReturnValue(null);
    mockGetStoredRefreshToken.mockReturnValue("legacy-refresh-token");
    mockGetSession.mockResolvedValue({
      ok: true,
      data: { user_id: "user-123", email: "user@example.com" },
    });

    render(<SettingsPage />);

    await waitFor(() => {
      expect(mockGetSession).toHaveBeenCalledTimes(1);
    });

    expect(screen.getByText("Logged in as")).toBeInTheDocument();
    expect(screen.getByText("user@example.com")).toBeInTheDocument();
  });

  it("stays in guest mode when no access or refresh token exists", async () => {
    mockGetStoredToken.mockReturnValue(null);
    mockGetStoredRefreshToken.mockReturnValue(null);

    render(<SettingsPage />);

    await waitFor(() => {
      expect(screen.getByText("Guest mode")).toBeInTheDocument();
    });

    expect(mockGetSession).not.toHaveBeenCalled();
  });
});
