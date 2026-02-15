import type { ApiResult } from "./api.types";

const DEFAULT_API_BASE_URL = "http://localhost:8000";
const TOKEN_STORAGE_KEY = "auth_access_token";
const LEGACY_TOKEN_STORAGE_KEY = "access_token";
const REFRESH_TOKEN_STORAGE_KEY = "refresh_token";
const LEGACY_REFRESH_TOKEN_STORAGE_KEY = "refresh token";

const getApiBaseUrl = () => {
  return process.env.NEXT_PUBLIC_API_BASE_URL || DEFAULT_API_BASE_URL;
};

// Token management functions
export const getStoredToken = (): string | null => {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(TOKEN_STORAGE_KEY) || localStorage.getItem(LEGACY_TOKEN_STORAGE_KEY);
};

export const getStoredTokenCandidates = (): string[] => {
  if (typeof window === "undefined") return [];
  const primary = localStorage.getItem(TOKEN_STORAGE_KEY);
  const legacy = localStorage.getItem(LEGACY_TOKEN_STORAGE_KEY);
  return [primary, legacy].filter((value, index, arr): value is string => Boolean(value) && arr.indexOf(value) === index);
};

export const setStoredToken = (token: string): void => {
  if (typeof window === "undefined") return;
  localStorage.setItem(TOKEN_STORAGE_KEY, token);
  localStorage.setItem(LEGACY_TOKEN_STORAGE_KEY, token);
};

export const getStoredRefreshToken = (): string | null => {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(REFRESH_TOKEN_STORAGE_KEY) || localStorage.getItem(LEGACY_REFRESH_TOKEN_STORAGE_KEY);
};

export const setStoredRefreshToken = (token: string): void => {
  if (typeof window === "undefined") return;
  localStorage.setItem(REFRESH_TOKEN_STORAGE_KEY, token);
  localStorage.setItem(LEGACY_REFRESH_TOKEN_STORAGE_KEY, token);
};

export const clearStoredRefreshToken = (): void => {
  if (typeof window === "undefined") return;
  localStorage.removeItem(REFRESH_TOKEN_STORAGE_KEY);
  localStorage.removeItem(LEGACY_REFRESH_TOKEN_STORAGE_KEY);
};

export const clearStoredToken = (): void => {
  if (typeof window === "undefined") return;
  localStorage.removeItem(TOKEN_STORAGE_KEY);
  localStorage.removeItem(LEGACY_TOKEN_STORAGE_KEY);
};

export const refreshAccessToken = async (): Promise<string | null> => {
  const refreshToken = getStoredRefreshToken();
  if (!refreshToken) return null;

  const baseUrl = getApiBaseUrl();

  try {
    const res = await fetch(`${baseUrl}/api/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });

    if (!res.ok) {
      clearStoredToken();
      clearStoredRefreshToken();
      return null;
    }

    const payload = (await res.json()) as { access_token?: string; refresh_token?: string };
    if (!payload.access_token) {
      return null;
    }

    setStoredToken(payload.access_token);
    if (payload.refresh_token) {
      setStoredRefreshToken(payload.refresh_token);
    }

    return payload.access_token;
  } catch {
    return null;
  }
};

async function request<T>(path: string, init?: RequestInit): Promise<ApiResult<T>> {
  const baseUrl = getApiBaseUrl();
  const url = `${baseUrl}${path}`;
  
  // Automatically inject Authorization header if token exists
  const tokenCandidates = getStoredTokenCandidates();
  const token = tokenCandidates[0] ?? null;
  const hasExplicitAuthorization = Boolean(
    (init?.headers as Record<string, string> | undefined)?.Authorization
  );
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(init?.headers as Record<string, string> ?? {}),
  };
  
  if (token && !headers.Authorization) {
    headers.Authorization = `Bearer ${token}`;
  }

  const run = async (requestHeaders: Record<string, string>) => {
    const res = await fetch(url, {
      ...init,
      headers: requestHeaders,
    });

    if (!res.ok) {
      const text = await res.text().catch(() => "");
      return { ok: false as const, status: res.status, error: text || res.statusText };
    }

    const data = (await res.json()) as T;
    return { ok: true as const, data };
  };

  try {
    let result = await run(headers);

    const canRetryWithFallback =
      !result.ok &&
      result.status === 401 &&
      !hasExplicitAuthorization &&
      tokenCandidates.length > 1;

    if (canRetryWithFallback) {
      const fallbackToken = tokenCandidates[1];
      const fallbackHeaders = {
        ...headers,
        Authorization: `Bearer ${fallbackToken}`,
      };
      const second = await run(fallbackHeaders);
      if (second.ok) {
        setStoredToken(fallbackToken);
        return second;
      }
      result = second;
    }

    const canRetryWithRefresh =
      !result.ok &&
      result.status === 401 &&
      !hasExplicitAuthorization &&
      path !== "/api/auth/refresh";

    if (canRetryWithRefresh) {
      const refreshedToken = await refreshAccessToken();
      if (refreshedToken) {
        const refreshedHeaders = {
          ...headers,
          Authorization: `Bearer ${refreshedToken}`,
        };
        return run(refreshedHeaders);
      }
    }

    return result;
  } catch (error) {
    const message = error instanceof Error ? error.message : "Network error";
    return { ok: false, error: message };
  }
}

export interface AuthSessionInfo {
  user_id: string;
  email?: string | null;
}

export const auth = {
  getSession: (accessToken?: string): Promise<ApiResult<AuthSessionInfo>> => {
    const headers: Record<string, string> = {};
    if (accessToken) {
      headers.Authorization = `Bearer ${accessToken}`;
    }
    return request<AuthSessionInfo>("/api/auth/session", { headers });
  },
};
