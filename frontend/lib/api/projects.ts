// API client functions for Projects
import {
  ProjectListResponse,
  ProjectDetail,
  ProjectOverrides,
  SkillProgressTimelineResponse,
  SkillProgressSummaryResponse,
  AppendUploadResponse,
  AppendUploadRequest,
  SearchResponse,
  SkillsListResponse,
  RoleProfile,
  SkillGapAnalysis,
  AiAnalysisApiResponse,
} from "@/types/project";
import { request } from "@/lib/api";

function authHeaders(token: string): Record<string, string> {
  return { Authorization: `Bearer ${token}`, "Content-Type": "application/json" };
}

async function call<T>(path: string, init: RequestInit, fallback: string): Promise<T> {
  const result = await request<T>(path, init);
  if (!result.ok) throw new Error(result.error ?? fallback);
  return result.data;
}

// Legacy helpers kept to avoid breaking any callers that import them directly.
// New code should use call() / request() above.
function firstNonEmptyString(value: unknown): string | null {
  if (typeof value === "string" && value.trim()) return value;
  return null;
}

function extractErrorMessage(detail: unknown, fallback: string): string {
  const direct = firstNonEmptyString(detail);
  if (direct) return direct;

  if (Array.isArray(detail)) {
    for (const item of detail) {
      const itemString = firstNonEmptyString(item);
      if (itemString) return itemString;
      if (item && typeof item === "object") {
        const message = firstNonEmptyString(
          (item as Record<string, unknown>).message
        );
        if (message) return message;
      }
    }
  }

  if (detail && typeof detail === "object") {
    const record = detail as Record<string, unknown>;
    const message =
      firstNonEmptyString(record.message) ||
      firstNonEmptyString(record.error) ||
      firstNonEmptyString(record.detail);
    if (message) return message;

    if (Array.isArray(record.errors)) {
      for (const item of record.errors) {
        const itemString = firstNonEmptyString(item);
        if (itemString) return itemString;
        if (item && typeof item === "object") {
          const itemMessage = firstNonEmptyString(
            (item as Record<string, unknown>).message
          );
          if (itemMessage) return itemMessage;
        }
      }
    }
  }

  return fallback;
}

function extractErrorFromResponse(error: unknown, fallback: string): string {
  if (error && typeof error === "object" && "detail" in (error as Record<string, unknown>)) {
    return extractErrorMessage(
      (error as Record<string, unknown>).detail,
      fallback
    );
  }
  return fallback;
}

export interface SelectionResponse {
  user_id: string;
  project_order: string[];
  skill_order: string[];
  selected_project_ids: string[];
  selected_skill_ids: string[];
  sort_mode: "contribution" | "recency";
  created_at: string;
  updated_at: string;
}

export interface SelectionUpdateRequest {
  project_order?: string[];
  skill_order?: string[];
  selected_project_ids?: string[];
  selected_skill_ids?: string[];
  sort_mode?: "contribution" | "recency";
}

/**
 * Fetch all projects for the authenticated user
 */
export async function getProjects(token: string): Promise<ProjectListResponse> {
  return call("/api/projects", { headers: authHeaders(token) }, "Failed to fetch projects");
}

/**
 * Fetch detailed information for a specific project
 */
export async function getProjectById(token: string, projectId: string): Promise<ProjectDetail> {
  return call(`/api/projects/${projectId}`, { headers: authHeaders(token) }, "Failed to fetch project details");
}

/**
 * Delete a project
 */
export async function deleteProject(token: string, projectId: string): Promise<void> {
  const result = await request<Record<string, unknown>>(`/api/projects/${projectId}`, {
    method: "DELETE",
    headers: authHeaders(token),
  });
  if (!result.ok) throw new Error(result.error ?? "Failed to delete project");
}

/**
 * Fetch skill progression timeline for a project
 */
export async function getProjectSkillTimeline(
  token: string,
  projectId: string,
  authorEmail?: string,
): Promise<SkillProgressTimelineResponse> {
  const query = authorEmail ? `?author_email=${encodeURIComponent(authorEmail)}` : "";
  return call(
    `/api/projects/${projectId}/skills/timeline${query}`,
    { headers: authHeaders(token) },
    "Failed to fetch skills timeline"
  );
}

/**
 * Update the user's role for a project via overrides
 */
export async function updateProjectRole(
  token: string,
  projectId: string,
  role: string,
): Promise<void> {
  const result = await request<Record<string, unknown>>(`/api/projects/${projectId}/overrides`, {
    method: "PATCH",
    headers: authHeaders(token),
    body: JSON.stringify({ role }),
  });
  if (!result.ok) throw new Error(result.error ?? "Failed to update role");
}

/**
 * Update one or more project override fields (role, evidence, custom_rank, etc.)
 */
export async function updateProjectOverrides(
  token: string,
  projectId: string,
  overrides: Partial<ProjectOverrides>,
): Promise<void> {
  const result = await request<Record<string, unknown>>(`/api/projects/${projectId}/overrides`, {
    method: "PATCH",
    headers: authHeaders(token),
    body: JSON.stringify(overrides),
  });
  if (!result.ok) throw new Error(result.error ?? "Failed to update project overrides");
}

/**
 * Generate skill progression summary using the LLM
 */
export async function generateProjectSkillSummary(
  token: string,
  projectId: string,
): Promise<SkillProgressSummaryResponse> {
  return call(
    `/api/projects/${projectId}/skills/summary`,
    { method: "POST", headers: authHeaders(token) },
    "Failed to generate skills summary"
  );
}

/**
 * Append files from an upload to an existing project with deduplication
 */
export async function appendUploadToProject(
  token: string,
  projectId: string,
  uploadId: string,
  options?: AppendUploadRequest
): Promise<AppendUploadResponse> {
  return call(
    `/api/projects/${projectId}/append-upload/${uploadId}`,
    {
      method: "POST",
      headers: authHeaders(token),
      body: JSON.stringify(options ?? { skip_duplicates: true }),
    },
    "Failed to append files to project"
  );
}

/**
 * Search across projects and files
 */
export async function searchProjects(
  token: string,
  query: string,
  options?: {
    scope?: "all" | "files" | "skills";
    projectId?: string;
    limit?: number;
    offset?: number;
  }
): Promise<SearchResponse> {
  const params = new URLSearchParams();
  if (query) params.set("q", query);
  if (options?.scope) params.set("scope", options.scope);
  if (options?.projectId) params.set("project_id", options.projectId);
  if (options?.limit) params.set("limit", String(options.limit));
  if (options?.offset) params.set("offset", String(options.offset));

  return call(
    `/api/projects/search?${params}`,
    { headers: authHeaders(token) },
    "Search failed"
  );
}

/**
 * Generate and download an HTML report for a project.
 * Returns the raw HTML string.
 */
export async function exportProjectHtml(
  token: string,
  projectId: string,
): Promise<string> {
  const result = await request<string>(`/api/projects/${projectId}/export-html`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!result.ok) throw new Error(result.error ?? "Failed to generate HTML report");
  return result.data;
}

/**
 * Fetch all unique skills across user's projects
 */
export async function getSkills(
  token: string,
  category?: string,
): Promise<SkillsListResponse> {
  const params = category ? `?category=${encodeURIComponent(category)}` : "";
  return call(`/api/skills${params}`, { headers: authHeaders(token) }, "Failed to fetch skills");
}

export async function getSelection(token: string): Promise<SelectionResponse> {
  return call("/api/selection", { headers: authHeaders(token) }, "Failed to fetch selection preferences");
}

export async function saveSelection(
  token: string,
  payload: SelectionUpdateRequest,
): Promise<SelectionResponse> {
  return call(
    "/api/selection",
    { method: "POST", headers: authHeaders(token), body: JSON.stringify(payload) },
    "Failed to save selection preferences"
  );
}

/**
 * Fetch available role profiles for gap analysis
 */
export async function getAvailableRoles(token: string): Promise<RoleProfile[]> {
  return call("/api/projects/skills/roles", { headers: authHeaders(token) }, "Failed to fetch roles");
}

/**
 * Analyse skill gaps for a project against a role profile
 */
export async function getSkillGaps(
  token: string,
  projectId: string,
  role: string,
): Promise<SkillGapAnalysis> {
  const params = new URLSearchParams({ role });
  return call(
    `/api/projects/${projectId}/skills/gaps?${params}`,
    { headers: authHeaders(token) },
    "Failed to analyse skill gaps"
  );
}

/**
 * Run AI analysis for an existing project using its stored scan data.
 * Pass force=true to re-run even if a cached result exists.
 */
export async function runProjectAiAnalysis(
  token: string,
  projectId: string,
  force = false,
): Promise<AiAnalysisApiResponse> {
  const params = force ? "?force=true" : "";
  return call(
    `/api/projects/${projectId}/ai-analysis${params}`,
    { method: "POST", headers: authHeaders(token) },
    "Failed to run AI analysis"
  );
}
