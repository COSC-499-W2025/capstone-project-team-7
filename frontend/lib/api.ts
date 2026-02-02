import type { ApiResult, ConsentStatus, ConsentNotice, ConsentUpdateRequest, ConfigResponse, ProfilesResponse, ProfileUpsertRequest, ConfigUpdateRequest } from "./api.types";
import { getStoredToken } from "./auth";
import type { ApiResult, UserProfile, UpdateProfileRequest } from "./api.types";
import type { ApiResult, AuthCredentials, AuthSessionResponse, ConsentRequest } from "./api.types";

const DEFAULT_API_BASE_URL = "http://localhost:8000";

const getApiBaseUrl = () => {
  return process.env.NEXT_PUBLIC_API_BASE_URL || DEFAULT_API_BASE_URL;
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
  auth: {
    login: (email: string, password: string) =>
      request<AuthSessionResponse>("/api/auth/login", {
        method: "POST",
        body: JSON.stringify({ email, password })
      }),
    signup: (email: string, password: string) =>
      request<AuthSessionResponse>("/api/auth/signup", {
        method: "POST",
        body: JSON.stringify({ email, password })
      }),
    refresh: (refreshToken: string) =>
      request<AuthSessionResponse>("/api/auth/refresh", {
        method: "POST",
        body: JSON.stringify({ refresh_token: refreshToken })
      }),
    saveConsent: (userId: string, serviceName: string, consentGiven: boolean, accessToken: string) =>
      request<{ success: boolean }>("/api/auth/consent", {
        method: "POST",
        body: JSON.stringify({ user_id: userId, service_name: serviceName, consent_given: consentGiven }),
        headers: {
          Authorization: `Bearer ${accessToken}`
        }
      })
  }
};

export const consent = {
  get: (): Promise<ApiResult<ConsentStatus>> => request<ConsentStatus>("/api/consent"),
  set: (payload: ConsentUpdateRequest): Promise<ApiResult<ConsentStatus>> =>
    request<ConsentStatus>("/api/consent", { method: "POST", body: JSON.stringify(payload) }),
  notice: (service: string): Promise<ApiResult<ConsentNotice>> =>
    request<ConsentNotice>(`/api/consent/notice?service=${encodeURIComponent(service)}`),
};

export const config = {
  get: (): Promise<ApiResult<ConfigResponse>> => request<ConfigResponse>("/api/config"),
  update: (payload: ConfigUpdateRequest): Promise<ApiResult<ConfigResponse>> =>
    request<ConfigResponse>("/api/config", { method: "PUT", body: JSON.stringify(payload) }),
  listProfiles: (): Promise<ApiResult<ProfilesResponse>> => request<ProfilesResponse>("/api/config/profiles"),
  saveProfile: (payload: ProfileUpsertRequest): Promise<ApiResult<any>> =>
    request<any>("/api/config/profiles", { method: "POST", body: JSON.stringify(payload) }),
};
