import type {
  ApiResult,
  AuthCredentials,
  AuthSessionResponse,
  ConfigResponse,
  ConfigUpdateRequest,
  ConsentNotice,
  ConsentStatus,
  ConsentUpdateRequest,
  ConsentRequest,
  ProfilesResponse,
  ProfileUpsertRequest,
  SaveSecretRequest,
  SaveSecretResponse,
  SecretStatusResponse,
  UpdateProfileRequest,
  UserProfile,
  EncryptionStatus,
  VerifyStoredKeyResponse,
} from "./api.types";
import {
  clearStoredRefreshToken,
  clearStoredToken,
  getStoredTokenCandidates,
  refreshAccessToken,
  setStoredToken,
} from "./auth";
import { getContributionHeaders } from "./settings";

const DEFAULT_API_BASE_URL = "http://localhost:8000";

type ResponseParser<T> = (response: Response) => Promise<T>;

const getApiBaseUrl = () => {
  return process.env.NEXT_PUBLIC_API_BASE_URL || DEFAULT_API_BASE_URL;
};

async function parseJsonResponse<T>(response: Response): Promise<T> {
  const text = await response.text();
  return (text ? JSON.parse(text) : {}) as T;
}

export async function request<T>(
  path: string,
  init?: RequestInit,
  parseResponse?: ResponseParser<T>,
): Promise<ApiResult<T>> {
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
    ...getContributionHeaders(),
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

    const data = parseResponse
      ? await parseResponse(res)
      : await parseJsonResponse<T>(res);
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
      path !== "/api/auth/refresh";

    if (canRetryWithRefresh) {
      const refreshedToken = await refreshAccessToken();
      if (refreshedToken) {
        const refreshedHeaders = {
          ...headers,
          Authorization: `Bearer ${refreshedToken}`,
        };
        result = await run(refreshedHeaders);
      }
    }

    if (!result.ok && (result.status === 401 || result.status === 403)) {
      clearStoredToken();
      clearStoredRefreshToken();
      localStorage.removeItem("user");
      window.dispatchEvent(new CustomEvent("auth:signout", { detail: { expired: true } }));
      return { ok: false as const, status: result.status, error: "Session expired" };
    }

    return result;
  } catch (error) {
    const message = error instanceof Error ? error.message : "Network error";
    return { ok: false as const, error: message };
  }
}

function authHeaders(token: string): Record<string, string> {
  return { Authorization: `Bearer ${token}` };
}

export const api = {
  health: () => request<{ status: string; message?: string }>("/health"),

  profile: {
    get: (token?: string) =>
      request<UserProfile>(
        "/api/profile",
        token
          ? {
              headers: authHeaders(token),
            }
          : undefined
      ),

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
    requestPasswordReset: (email: string, redirectTo?: string) =>
      request<{ ok: boolean; message?: string }>("/api/auth/request-reset", {
        method: "POST",
        body: JSON.stringify({ email, redirect_to: redirectTo })
      }),
    resetPassword: (token: string, newPassword: string) =>
      request<{ ok: boolean; message?: string }>("/api/auth/reset-password", {
        method: "POST",
        body: JSON.stringify({ token, new_password: newPassword })
      }),
    saveConsent: (userId: string, serviceName: string, consentGiven: boolean, accessToken: string) =>
      request<{ success: boolean }>("/api/auth/consent", {
        method: "POST",
        body: JSON.stringify({ user_id: userId, service_name: serviceName, consent_given: consentGiven }),
        headers: {
          Authorization: `Bearer ${accessToken}`
        }
      })
  },
  projects: {
    uploadThumbnail: async (token: string, projectId: string, file: File): Promise<ApiResult<{ thumbnail_url: string }>> => {
      const baseUrl = getApiBaseUrl();
      const form = new FormData();
      form.append("file", file);
      try {
        const res = await fetch(`${baseUrl}/api/projects/${projectId}/thumbnail`, {
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

    deleteThumbnail: async (
      token: string,
      projectId: string
    ): Promise<ApiResult<{ ok: boolean; message: string }>> => {
      const baseUrl = getApiBaseUrl();
      try {
        const res = await fetch(`${baseUrl}/api/projects/${projectId}/thumbnail`, {
          method: "DELETE",
          headers: { Authorization: `Bearer ${token}` },
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
  },
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

export const encryption = {
  status: (): Promise<ApiResult<EncryptionStatus>> =>
    request<EncryptionStatus>("/api/encryption/status", { cache: "no-store" }),
};

export const secrets = {
  getStatus: (): Promise<ApiResult<SecretStatusResponse>> =>
    request<SecretStatusResponse>("/api/settings/secrets"),
  save: (payload: SaveSecretRequest): Promise<ApiResult<SaveSecretResponse>> =>
    request<SaveSecretResponse>("/api/settings/secrets", {
      method: "PUT",
      body: JSON.stringify(payload),
    }),
  remove: (secretKey: string): Promise<ApiResult<{ ok: boolean; message: string }>> =>
    request<{ ok: boolean; message: string }>("/api/settings/secrets", {
      method: "DELETE",
      body: JSON.stringify({ secret_key: secretKey }),
    }),
  verify: (): Promise<ApiResult<VerifyStoredKeyResponse>> =>
    request<VerifyStoredKeyResponse>("/api/settings/secrets/verify", {
      method: "POST",
    }),
};
