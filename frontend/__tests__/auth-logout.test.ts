import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  logout,
  getStoredToken,
  getStoredRefreshToken,
  setStoredToken,
  setStoredRefreshToken,
  refreshAccessToken,
} from "@/lib/auth";

describe("logout functionality", () => {
  beforeEach(() => {
    localStorage.clear();
    sessionStorage.clear();
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
    localStorage.clear();
    sessionStorage.clear();
  });

  it("calls backend logout endpoint with access token", async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      json: vi.fn().mockResolvedValue({ ok: true }),
    });
    vi.stubGlobal("fetch", mockFetch);

    setStoredToken("test-access-token");
    logout();

    // Give async fetch time to execute
    await new Promise((resolve) => setTimeout(resolve, 10));

    expect(mockFetch).toHaveBeenCalledWith(
      "http://localhost:8000/api/auth/logout",
      expect.objectContaining({
        method: "POST",
        headers: { Authorization: "Bearer test-access-token" },
      })
    );
  });

  it("does not clear localStorage tokens directly (handled by useAuth hook)", () => {
    setStoredToken("test-access-token");
    setStoredRefreshToken("test-refresh-token");

    // Mock fetch to avoid actual network calls
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({
      ok: true,
      json: vi.fn().mockResolvedValue({ ok: true }),
    }));

    expect(getStoredToken()).toBe("test-access-token");
    expect(getStoredRefreshToken()).toBe("test-refresh-token");

    logout();

    expect(getStoredToken()).toBe("test-access-token");
    expect(getStoredRefreshToken()).toBe("test-refresh-token");
  });

  it("does not set logout flag directly (handled by useAuth hook)", () => {
    setStoredToken("test-access-token");

    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({
      ok: true,
      json: vi.fn().mockResolvedValue({ ok: true }),
    }));

    expect(sessionStorage.getItem("auth_logged_out")).toBeNull();

    logout();

    expect(sessionStorage.getItem("auth_logged_out")).toBeNull();
  });

  it("completes logout even if backend call fails", async () => {
    const mockFetch = vi.fn().mockRejectedValue(new Error("Network error"));
    vi.stubGlobal("fetch", mockFetch);

    setStoredToken("test-access-token");

    // Should not throw - uses fire-and-forget pattern
    expect(() => {
      logout();
    }).not.toThrow();

    // Give async fetch time to execute and fail
    await new Promise((resolve) => setTimeout(resolve, 10));

    expect(mockFetch).toHaveBeenCalled();
  });

  it("returns null from refreshAccessToken when logout flag is set", async () => {
    setStoredToken("test-access-token");
    setStoredRefreshToken("test-refresh-token");

    // Set logout flag as the hook would
    sessionStorage.setItem("auth_logged_out", "1");

    const token = await refreshAccessToken();

    expect(token).toBeNull();
  });

  it("does not call backend if no access token is stored", async () => {
    const mockFetch = vi.fn();
    vi.stubGlobal("fetch", mockFetch);

    logout();

    // Give async code time to run
    await new Promise((resolve) => setTimeout(resolve, 10));

    // Should not call fetch if no token
    expect(mockFetch).not.toHaveBeenCalled();
  });

  it("ignores backend errors when invalidating refresh token", async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 500,
      statusText: "Internal Server Error",
    });
    vi.stubGlobal("fetch", mockFetch);

    setStoredToken("test-access-token");

    // Should not throw even with backend 500 error
    expect(() => {
      logout();
    }).not.toThrow();

    await new Promise((resolve) => setTimeout(resolve, 10));

    expect(mockFetch).toHaveBeenCalled();
  });
});
