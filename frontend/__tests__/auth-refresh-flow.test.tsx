import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  auth,
  clearStoredRefreshToken,
  clearStoredToken,
  getStoredRefreshToken,
  getStoredToken,
  refreshAccessToken,
} from "@/lib/auth";
import { consent } from "@/lib/api";

describe("auth refresh flow", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  afterEach(() => {
    vi.restoreAllMocks();
    localStorage.clear();
  });

  it("refreshes access token when only legacy refresh token key exists", async () => {
    localStorage.setItem("refresh token", "legacy-refresh-token");

    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        json: vi.fn().mockResolvedValue({
          access_token: "new-access-token",
          refresh_token: "new-refresh-token",
        }),
      })
    );

    const token = await refreshAccessToken();

    expect(token).toBe("new-access-token");
    expect(getStoredToken()).toBe("new-access-token");
    expect(getStoredRefreshToken()).toBe("new-refresh-token");
    expect(localStorage.getItem("refresh token")).toBe("new-refresh-token");
  });

  it("retries session request after refresh when initial session call is unauthorized", async () => {
    localStorage.setItem("refresh_token", "refresh-token");

    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce({
        ok: false,
        status: 401,
        statusText: "Unauthorized",
        text: vi.fn().mockResolvedValue("Unauthorized"),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: vi.fn().mockResolvedValue({
          access_token: "fresh-access-token",
          refresh_token: "fresh-refresh-token",
        }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: vi.fn().mockResolvedValue({
          user_id: "user-123",
          email: "user@example.com",
        }),
      });

    vi.stubGlobal("fetch", fetchMock);

    const result = await auth.getSession();

    expect(result.ok).toBe(true);
    if (result.ok) {
      expect(result.data.user_id).toBe("user-123");
    }

    expect(getStoredToken()).toBe("fresh-access-token");
    expect(getStoredRefreshToken()).toBe("fresh-refresh-token");
    expect(fetchMock).toHaveBeenCalledTimes(3);
    expect(fetchMock.mock.calls[1]?.[0]).toContain("/api/auth/refresh");
    expect(fetchMock.mock.calls[2]?.[0]).toContain("/api/auth/session");
  });

  it("clears access and refresh tokens when refresh endpoint rejects token", async () => {
    localStorage.setItem("auth_access_token", "stale-access-token");
    localStorage.setItem("refresh token", "stale-refresh-token");

    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: false,
        status: 401,
        statusText: "Unauthorized",
        text: vi.fn().mockResolvedValue("Unauthorized"),
      })
    );

    const token = await refreshAccessToken();

    expect(token).toBeNull();
    expect(getStoredToken()).toBeNull();
    expect(getStoredRefreshToken()).toBeNull();
    clearStoredToken();
    clearStoredRefreshToken();
  });

  it("retries consent request after refresh when access token is missing", async () => {
    localStorage.setItem("refresh token", "legacy-refresh-token");

    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce({
        ok: false,
        status: 401,
        statusText: "Unauthorized",
        text: vi.fn().mockResolvedValue("Unauthorized"),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: vi.fn().mockResolvedValue({
          access_token: "new-access-token",
          refresh_token: "new-refresh-token",
        }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: vi.fn().mockResolvedValue({
          data_access: true,
          external_services: false,
          updated_at: "2026-02-10T00:00:00Z",
          data_access_updated_at: "2026-02-10T00:00:00Z",
          external_services_updated_at: null,
        }),
      });

    vi.stubGlobal("fetch", fetchMock);

    const result = await consent.get();

    expect(result.ok).toBe(true);
    if (result.ok) {
      expect(result.data.data_access).toBe(true);
    }

    expect(getStoredToken()).toBe("new-access-token");
    expect(getStoredRefreshToken()).toBe("new-refresh-token");
    expect(fetchMock).toHaveBeenCalledTimes(3);
    expect(fetchMock.mock.calls[0]?.[0]).toContain("/api/consent");
    expect(fetchMock.mock.calls[1]?.[0]).toContain("/api/auth/refresh");
    expect(fetchMock.mock.calls[2]?.[0]).toContain("/api/consent");
  });
});
