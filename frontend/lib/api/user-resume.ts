/**
 * API client for user resume documents
 */

import type {
  UserResumeListResponse,
  UserResumeRecord,
  UserResumeCreateRequest,
  UserResumeUpdateRequest,
  UserResumeDuplicateRequest,
  TemplatesListResponse,
} from "@/types/user-resume";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

function authHeaders(token: string): Record<string, string> {
  return {
    Authorization: `Bearer ${token}`,
    "Content-Type": "application/json",
  };
}

/**
 * List available resume templates
 */
export async function listResumeTemplates(
  token: string
): Promise<TemplatesListResponse> {
  const response = await fetch(`${API_BASE_URL}/api/user-resumes/templates`, {
    method: "GET",
    headers: authHeaders(token),
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail?.message || "Failed to fetch templates");
  }
  return response.json();
}

/**
 * List all resumes for the authenticated user
 */
export async function listUserResumes(
  token: string,
  limit = 50,
  offset = 0
): Promise<UserResumeListResponse> {
  const response = await fetch(
    `${API_BASE_URL}/api/user-resumes?limit=${limit}&offset=${offset}`,
    { method: "GET", headers: authHeaders(token) }
  );
  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail?.message || "Failed to fetch resumes");
  }
  return response.json();
}

/**
 * Get a single resume with full content
 */
export async function getUserResume(
  token: string,
  id: string
): Promise<UserResumeRecord> {
  const response = await fetch(`${API_BASE_URL}/api/user-resumes/${id}`, {
    method: "GET",
    headers: authHeaders(token),
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail?.message || "Failed to fetch resume");
  }
  return response.json();
}

/**
 * Create a new resume
 */
export async function createUserResume(
  token: string,
  body: UserResumeCreateRequest
): Promise<UserResumeRecord> {
  const response = await fetch(`${API_BASE_URL}/api/user-resumes`, {
    method: "POST",
    headers: authHeaders(token),
    body: JSON.stringify(body),
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail?.message || "Failed to create resume");
  }
  return response.json();
}

/**
 * Update an existing resume
 */
export async function updateUserResume(
  token: string,
  id: string,
  body: UserResumeUpdateRequest
): Promise<UserResumeRecord> {
  const response = await fetch(`${API_BASE_URL}/api/user-resumes/${id}`, {
    method: "PATCH",
    headers: authHeaders(token),
    body: JSON.stringify(body),
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail?.message || "Failed to update resume");
  }
  return response.json();
}

/**
 * Delete a resume
 */
export async function deleteUserResume(
  token: string,
  id: string
): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/api/user-resumes/${id}`, {
    method: "DELETE",
    headers: authHeaders(token),
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail?.message || "Failed to delete resume");
  }
}

/**
 * Duplicate a resume
 */
export async function duplicateUserResume(
  token: string,
  id: string,
  body: UserResumeDuplicateRequest = {}
): Promise<UserResumeRecord> {
  const response = await fetch(
    `${API_BASE_URL}/api/user-resumes/${id}/duplicate`,
    {
      method: "POST",
      headers: authHeaders(token),
      body: JSON.stringify(body),
    }
  );
  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail?.message || "Failed to duplicate resume");
  }
  return response.json();
}
