import type { ApiResult, ConsentStatus, ConsentNotice, ConsentUpdateRequest, ConfigResponse, ProfilesResponse, ProfileUpsertRequest, ConfigUpdateRequest } from "./api.types";
import { getStoredToken } from "./auth";

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

export const api = {
  health: () => request<{ status: string; message?: string }>("/health")
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
