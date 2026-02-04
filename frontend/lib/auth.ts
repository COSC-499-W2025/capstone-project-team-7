import type { ApiResult } from "./api.types";

const DEFAULT_API_BASE_URL = "http://localhost:8000";
const TOKEN_STORAGE_KEY = "auth_access_token";
const LEGACY_TOKEN_STORAGE_KEY = "access_token";

const getApiBaseUrl = () => {
  return process.env.NEXT_PUBLIC_API_BASE_URL || DEFAULT_API_BASE_URL;
};

// Token management functions
export const getStoredToken = (): string | null => {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(TOKEN_STORAGE_KEY) || localStorage.getItem(LEGACY_TOKEN_STORAGE_KEY);
};

export const setStoredToken = (token: string): void => {
  if (typeof window === "undefined") return;
  localStorage.setItem(TOKEN_STORAGE_KEY, token);
};

export const clearStoredToken = (): void => {
  if (typeof window === "undefined") return;
  localStorage.removeItem(TOKEN_STORAGE_KEY);
};

async function request<T>(path: string, init?: RequestInit): Promise<ApiResult<T>> {
  const baseUrl = getApiBaseUrl();
  const url = `${baseUrl}${path}`;
  
  // Automatically inject Authorization header if token exists
  const token = getStoredToken();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(init?.headers as Record<string, string> ?? {}),
  };
  
  if (token && !headers.Authorization) {
    headers.Authorization = `Bearer ${token}`;
  }

  try {
    const res = await fetch(url, {
      ...init,
      headers,
    });

    if (!res.ok) {
      const text = await res.text().catch(() => "");
      return { ok: false, status: res.status, error: text || res.statusText };
    }

    const data = (await res.json()) as T;
    return { ok: true, data };
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
