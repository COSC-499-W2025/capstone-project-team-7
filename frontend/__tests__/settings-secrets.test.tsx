import { beforeEach, describe, expect, it, vi, type Mock } from "vitest";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
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

vi.mock("@/hooks/use-auth", () => ({
  useAuth: () => ({ logout: vi.fn() }),
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
  encryption: {
    status: vi.fn(),
  },
  secrets: {
    getStatus: vi.fn(),
    save: vi.fn(),
    remove: vi.fn(),
    verify: vi.fn(),
  },
}));

import { auth, getStoredToken, getStoredRefreshToken } from "@/lib/auth";
import { config, consent, encryption, secrets } from "@/lib/api";

const mockGetSession = auth.getSession as Mock;
const mockGetStoredToken = getStoredToken as Mock;
const mockGetStoredRefreshToken = getStoredRefreshToken as Mock;
const mockConsentGet = consent.get as Mock;
const mockConfigGet = config.get as Mock;
const mockListProfiles = config.listProfiles as Mock;
const mockEncryptionStatus = encryption.status as Mock;
const mockSecretsGetStatus = secrets.getStatus as Mock;
const mockSecretsSave = secrets.save as Mock;
const mockSecretsRemove = secrets.remove as Mock;
const mockSecretsVerify = secrets.verify as Mock;

function setupLoggedIn(opts?: { externalConsent?: boolean; hasKey?: boolean }) {
  const externalConsent = opts?.externalConsent ?? true;
  const hasKey = opts?.hasKey ?? false;

  mockGetStoredToken.mockReturnValue("tok-abc");
  mockGetStoredRefreshToken.mockReturnValue(null);
  mockGetSession.mockResolvedValue({
    ok: true,
    data: { user_id: "user-123", email: "user@test.com" },
  });
  mockConsentGet.mockResolvedValue({
    ok: true,
    data: { data_access: true, external_services: externalConsent },
  });
  mockConfigGet.mockResolvedValue({
    ok: true,
    data: { current_profile: "all", max_file_size_mb: 100, follow_symlinks: false },
  });
  mockListProfiles.mockResolvedValue({
    ok: true,
    data: { profiles: { all: { description: "All files" } }, current_profile: "all" },
  });
  mockEncryptionStatus.mockResolvedValue({ ok: true, data: { enabled: false, ready: false } });
  mockSecretsGetStatus.mockResolvedValue({
    ok: true,
    data: {
      secrets: hasKey
        ? [{ secret_key: "openai_api_key", has_value: true, provider: "openai", updated_at: "2026-03-06T00:00:00Z" }]
        : [],
    },
  });
}

async function openSecurityAndPrivacyTab() {
  fireEvent.click(await screen.findByRole("button", { name: "Security & Privacy" }));
}

describe("Settings — External Services (secrets)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("shows 'Not configured' when no secret exists", async () => {
    setupLoggedIn({ externalConsent: true, hasKey: false });
    render(<SettingsPage />);
    await openSecurityAndPrivacyTab();

    await waitFor(() => {
      expect(screen.getByText("Not configured")).toBeInTheDocument();
    });
  });

  it("shows 'Configured' when secret exists", async () => {
    setupLoggedIn({ externalConsent: true, hasKey: true });
    render(<SettingsPage />);
    await openSecurityAndPrivacyTab();

    await waitFor(() => {
      expect(screen.getByText("Configured")).toBeInTheDocument();
    });
  });

  it("does not show External Services card when not logged in", async () => {
    mockGetStoredToken.mockReturnValue(null);
    mockGetStoredRefreshToken.mockReturnValue(null);
    render(<SettingsPage />);

    await waitFor(() => {
      expect(screen.getByText("Guest mode")).toBeInTheDocument();
    });
    expect(screen.queryByText("External Services")).not.toBeInTheDocument();
  });

  it("shows consent required banner when external services not enabled", async () => {
    setupLoggedIn({ externalConsent: false, hasKey: false });
    render(<SettingsPage />);
    await openSecurityAndPrivacyTab();

    await waitFor(() => {
      expect(
        screen.getByText(/Enable external services in Privacy & Consent/)
      ).toBeInTheDocument();
    });
  });

  it("calls save API when Save Key is clicked", async () => {
    setupLoggedIn({ externalConsent: true, hasKey: false });
    mockSecretsSave.mockResolvedValue({
      ok: true,
      data: { secret_key: "openai_api_key", has_value: true },
    });
    // After save, refresh returns the new key
    mockSecretsGetStatus
      .mockResolvedValueOnce({ ok: true, data: { secrets: [] } })
      .mockResolvedValueOnce({
        ok: true,
        data: { secrets: [{ secret_key: "openai_api_key", has_value: true, provider: "openai" }] },
      });

    render(<SettingsPage />);
    await openSecurityAndPrivacyTab();

    await waitFor(() => {
      expect(screen.getByText("Not configured")).toBeInTheDocument();
    });

    const input = screen.getByPlaceholderText("sk-...");
    fireEvent.change(input, { target: { value: "sk-test-key-123" } });

    const saveBtn = screen.getByRole("button", { name: "Save Key" });
    fireEvent.click(saveBtn);

    await waitFor(() => {
      expect(mockSecretsSave).toHaveBeenCalledWith({
        secret_key: "openai_api_key",
        value: "sk-test-key-123",
        provider: "openai",
      });
    });
  });

  it("calls verify API when Verify Key is clicked", async () => {
    setupLoggedIn({ externalConsent: true, hasKey: true });
    mockSecretsVerify.mockResolvedValue({
      ok: true,
      data: { valid: true, message: "API key verified successfully" },
    });

    render(<SettingsPage />);
    await openSecurityAndPrivacyTab();

    await waitFor(() => {
      expect(screen.getByText("Configured")).toBeInTheDocument();
    });

    const verifyBtn = screen.getByRole("button", { name: "Verify Key" });
    fireEvent.click(verifyBtn);

    await waitFor(() => {
      expect(mockSecretsVerify).toHaveBeenCalled();
    });
  });

  it("calls remove API when Clear Key is confirmed", async () => {
    setupLoggedIn({ externalConsent: true, hasKey: true });
    mockSecretsRemove.mockResolvedValue({ ok: true, data: { ok: true, message: "Removed" } });
    mockSecretsGetStatus
      .mockResolvedValueOnce({
        ok: true,
        data: { secrets: [{ secret_key: "openai_api_key", has_value: true, provider: "openai" }] },
      })
      .mockResolvedValueOnce({ ok: true, data: { secrets: [] } });

    render(<SettingsPage />);
    await openSecurityAndPrivacyTab();

    await waitFor(() => {
      expect(screen.getByText("Configured")).toBeInTheDocument();
    });

    const clearBtn = screen.getByRole("button", { name: "Clear Key" });
    fireEvent.click(clearBtn);

    // Confirmation dialog should appear
    await waitFor(() => {
      expect(screen.getByText("Remove Key")).toBeInTheDocument();
    });

    const confirmBtn = screen.getByRole("button", { name: "Remove Key" });
    fireEvent.click(confirmBtn);

    await waitFor(() => {
      expect(mockSecretsRemove).toHaveBeenCalledWith("openai_api_key");
    });
  });
});
