import type { ApiResult, UserProfile, UpdateProfileRequest } from "./api.types";

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
        ...(init?.headers ?? {})
      }
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

function authHeaders(token: string): Record<string, string> {
  return { Authorization: `Bearer ${token}` };
}

export const api = {
  health: () => request<{ status: string; message?: string }>("/health"),

  profile: {
    get: (token: string) =>
      request<UserProfile>("/api/profile", {
        headers: authHeaders(token),
      }),

    update: (token: string, data: UpdateProfileRequest) =>
      request<UserProfile>("/api/profile", {
        method: "PATCH",
        headers: authHeaders(token),
        body: JSON.stringify(data),
      }),

    uploadAvatar: async (token: string, file: File): Promise<ApiResult<{ avatar_url: string }>> => {
      const baseUrl = getApiBaseUrl();
      const form = new FormData();
      form.append("file", file);
      try {
        const res = await fetch(`${baseUrl}/api/profile/avatar`, {
          method: "POST",
          headers: { Authorization: `Bearer ${token}` },
          body: form,
        });
        if (!res.ok) {
          const text = await res.text().catch(() => "");
          return { ok: false, status: res.status, error: text || res.statusText };
        }
        const data = await res.json();
        return { ok: true, data };
      } catch (error) {
        const message = error instanceof Error ? error.message : "Network error";
        return { ok: false, error: message };
      }
    },

    deleteAvatar: (token: string) =>
      request<{ ok: boolean; message: string }>("/api/profile/avatar", {
        method: "DELETE",
        headers: authHeaders(token),
      }),

    changePassword: (token: string, currentPassword: string, newPassword: string) =>
      request<{ ok: boolean; message: string }>("/api/profile/password", {
        method: "POST",
        headers: authHeaders(token),
        body: JSON.stringify({ current_password: currentPassword, new_password: newPassword }),
      }),
  },
};
