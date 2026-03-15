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

import { request } from "@/lib/api";

function authHeaders(token: string): Record<string, string> {
  return { Authorization: `Bearer ${token}`, "Content-Type": "application/json" };
}

async function call<T>(path: string, init: RequestInit, fallback: string): Promise<T> {
  const result = await request<T>(path, init);
  if (!result.ok) throw new Error(result.error ?? fallback);
  return result.data;
}

/**
 * List available resume templates
 */
export async function listResumeTemplates(token: string): Promise<TemplatesListResponse> {
  return call("/api/user-resumes/templates", { headers: authHeaders(token) }, "Failed to fetch templates");
}

export async function listUserResumes(token: string, limit = 50, offset = 0): Promise<UserResumeListResponse> {
  return call(`/api/user-resumes?limit=${limit}&offset=${offset}`, { headers: authHeaders(token) }, "Failed to fetch resumes");
}

export async function getUserResume(token: string, id: string): Promise<UserResumeRecord> {
  return call(`/api/user-resumes/${id}`, { headers: authHeaders(token) }, "Failed to fetch resume");
}

export async function createUserResume(token: string, body: UserResumeCreateRequest): Promise<UserResumeRecord> {
  return call("/api/user-resumes", { method: "POST", headers: authHeaders(token), body: JSON.stringify(body) }, "Failed to create resume");
}

export async function updateUserResume(token: string, id: string, body: UserResumeUpdateRequest): Promise<UserResumeRecord> {
  return call(`/api/user-resumes/${id}`, { method: "PATCH", headers: authHeaders(token), body: JSON.stringify(body) }, "Failed to update resume");
}

export async function deleteUserResume(token: string, id: string): Promise<void> {
  const result = await request<Record<string, unknown>>(`/api/user-resumes/${id}`, { method: "DELETE", headers: authHeaders(token) });
  if (!result.ok) throw new Error(result.error ?? "Failed to delete resume");
}

export async function duplicateUserResume(token: string, id: string, body: UserResumeDuplicateRequest = {}): Promise<UserResumeRecord> {
  return call(`/api/user-resumes/${id}/duplicate`, { method: "POST", headers: authHeaders(token), body: JSON.stringify(body) }, "Failed to duplicate resume");
}
