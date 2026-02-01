import type { ApiResult } from "./api.types";

const DEFAULT_API_BASE_URL = "http://localhost:8000";

const getApiBaseUrl = () => {
  return process.env.NEXT_PUBLIC_API_BASE_URL || DEFAULT_API_BASE_URL;
};

async function request<T>(path: string, init?: RequestInit): Promise<ApiResult<T>> {
  const baseUrl = getApiBaseUrl();
  const url = `${baseUrl}${path}`;

  try {
    const res = await fetch(url, {
      ...init,
      headers: {
        "Content-Type": "application/json",
        ...(init?.headers ?? {}),
      },
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
  getSession: (accessToken?: string): Promise<ApiResult<AuthSessionInfo>> =>
    request<AuthSessionInfo>("/api/auth/session", {
      headers: accessToken ? { Authorization: `Bearer ${accessToken}` } : {},
    }),
};
