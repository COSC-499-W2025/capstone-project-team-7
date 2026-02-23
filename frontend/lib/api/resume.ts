import type {
  ResumeItemListResponse,
  ResumeItemRecord,
  ResumeItemCreateRequest,
  ResumeItemUpdateRequest,
} from "@/types/resume";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

function authHeaders(token: string): Record<string, string> {
  return {
    Authorization: `Bearer ${token}`,
    "Content-Type": "application/json",
  };
}

export async function listResumeItems(
  token: string,
  limit = 50,
  offset = 0
): Promise<ResumeItemListResponse> {
  const response = await fetch(
    `${API_BASE_URL}/api/resume/items?limit=${limit}&offset=${offset}`,
    { method: "GET", headers: authHeaders(token) }
  );
  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail || "Failed to fetch resume items");
  }
  return response.json();
}

export async function getResumeItem(
  token: string,
  id: string
): Promise<ResumeItemRecord> {
  const response = await fetch(`${API_BASE_URL}/api/resume/items/${id}`, {
    method: "GET",
    headers: authHeaders(token),
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail || "Failed to fetch resume item");
  }
  return response.json();
}

export async function createResumeItem(
  token: string,
  body: ResumeItemCreateRequest
): Promise<ResumeItemRecord> {
  const response = await fetch(`${API_BASE_URL}/api/resume/items`, {
    method: "POST",
    headers: authHeaders(token),
    body: JSON.stringify(body),
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail || "Failed to create resume item");
  }
  return response.json();
}

export async function updateResumeItem(
  token: string,
  id: string,
  body: ResumeItemUpdateRequest
): Promise<ResumeItemRecord> {
  const response = await fetch(`${API_BASE_URL}/api/resume/items/${id}`, {
    method: "PATCH",
    headers: authHeaders(token),
    body: JSON.stringify(body),
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail || "Failed to update resume item");
  }
  return response.json();
}

export async function deleteResumeItem(
  token: string,
  id: string
): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/api/resume/items/${id}`, {
    method: "DELETE",
    headers: authHeaders(token),
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail || "Failed to delete resume item");
  }
}
