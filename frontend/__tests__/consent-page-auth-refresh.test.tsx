import { beforeEach, describe, expect, it, vi, type Mock } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import ConsentManagementPage from "../app/(dashboard)/settings/consent/page";

vi.mock("@/lib/auth", () => ({
  auth: {
    getSession: vi.fn(),
  },
}));

vi.mock("@/lib/api", () => ({
  consent: {
    get: vi.fn(),
    notice: vi.fn(),
    set: vi.fn(),
  },
}));

import { auth } from "@/lib/auth";
import { consent } from "@/lib/api";

const mockGetSession = auth.getSession as Mock;
const mockConsentGet = consent.get as Mock;
const mockConsentNotice = consent.notice as Mock;

describe("Consent page auth recovery", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("loads consent view when session recovers from refresh-token-only state", async () => {
    mockGetSession.mockResolvedValue({
      ok: true,
      data: { user_id: "user-123", email: "user@example.com" },
    });
    mockConsentGet.mockResolvedValue({
      ok: true,
      data: {
        data_access: true,
        external_services: false,
        updated_at: "2026-02-10T00:00:00Z",
        data_access_updated_at: "2026-02-10T00:00:00Z",
        external_services_updated_at: null,
      },
    });
    mockConsentNotice.mockImplementation(async (service: string) => ({
      ok: true,
      data: {
        service,
        privacy_notice: "Notice text",
        implications: [],
      },
    }));

    render(<ConsentManagementPage />);

    await waitFor(() => {
      expect(mockGetSession).toHaveBeenCalledTimes(1);
      expect(mockConsentGet).toHaveBeenCalledTimes(1);
      expect(mockConsentNotice).toHaveBeenCalledTimes(2);
    });

    expect(screen.getByRole("heading", { name: "File Access" })).toBeInTheDocument();
    expect(screen.queryByText("Authentication Required")).not.toBeInTheDocument();
  });

  it("shows authentication-required state when session cannot be restored", async () => {
    mockGetSession.mockResolvedValue({ ok: false, status: 401, error: "Unauthorized" });
    mockConsentGet.mockResolvedValue({ ok: false, status: 401, error: "Unauthorized" });
    mockConsentNotice.mockResolvedValue({ ok: false, status: 401, error: "Unauthorized" });

    render(<ConsentManagementPage />);

    await waitFor(() => {
      expect(screen.getByText("Authentication Required")).toBeInTheDocument();
    });

    expect(screen.queryByText("Loading consent preferences...")).not.toBeInTheDocument();
  });
});
