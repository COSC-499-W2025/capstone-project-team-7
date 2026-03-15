import type {
  ResumeItemListResponse,
  ResumeItemRecord,
  ResumeItemCreateRequest,
  ResumeItemUpdateRequest,
} from "@/types/resume";
import { request } from "@/lib/api";

function authHeaders(token: string): Record<string, string> {
  return { Authorization: `Bearer ${token}`, "Content-Type": "application/json" };
}

async function call<T>(path: string, init: RequestInit, fallback: string): Promise<T> {
  const result = await request<T>(path, init);
  if (!result.ok) throw new Error(result.error ?? fallback);
  return result.data;
}

export async function listResumeItems(token: string, limit = 50, offset = 0): Promise<ResumeItemListResponse> {
  return call(`/api/resume/items?limit=${limit}&offset=${offset}`, { headers: authHeaders(token) }, "Failed to fetch resume items");
}

export async function getResumeItem(token: string, id: string): Promise<ResumeItemRecord> {
  return call(`/api/resume/items/${id}`, { headers: authHeaders(token) }, "Failed to fetch resume item");
}

export async function createResumeItem(token: string, body: ResumeItemCreateRequest): Promise<ResumeItemRecord> {
  return call("/api/resume/items", { method: "POST", headers: authHeaders(token), body: JSON.stringify(body) }, "Failed to create resume item");
}

export async function updateResumeItem(token: string, id: string, body: ResumeItemUpdateRequest): Promise<ResumeItemRecord> {
  return call(`/api/resume/items/${id}`, { method: "PATCH", headers: authHeaders(token), body: JSON.stringify(body) }, "Failed to update resume item");
}

export async function deleteResumeItem(token: string, id: string): Promise<void> {
  const result = await request<Record<string, unknown>>(`/api/resume/items/${id}`, { method: "DELETE", headers: authHeaders(token) });
  if (!result.ok) throw new Error(result.error ?? "Failed to delete resume item");
}
