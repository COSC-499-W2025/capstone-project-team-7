// API client functions for Projects
import {
  ProjectListResponse,
  ProjectDetail,
  ProjectOverrides,
  ErrorResponse,
  SkillProgressTimelineResponse,
  SkillProgressSummaryResponse,
  AppendUploadResponse,
  AppendUploadRequest,
  SearchResponse,
  SkillsListResponse,
  RoleProfile,
  SkillGapAnalysis,
  AiAnalysisApiResponse,
  AiBatchApiResponse,
  AiBatchStatusApiResponse,
} from "@/types/project";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

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
  const response = await fetch(`${API_BASE_URL}/api/projects`, {
    method: "GET",
    headers: {
      "Authorization": `Bearer ${token}`,
      "Content-Type": "application/json",
    },
  });

  if (!response.ok) {
    const error: ErrorResponse = await response.json().catch(() => ({}) as ErrorResponse);
    throw new Error(extractErrorFromResponse(error, "Failed to fetch projects"));
  }

  return response.json();
}

/**
 * Fetch detailed information for a specific project
 */
export async function getProjectById(token: string, projectId: string): Promise<ProjectDetail> {
  const response = await fetch(`${API_BASE_URL}/api/projects/${projectId}`, {
    method: "GET",
    headers: {
      "Authorization": `Bearer ${token}`,
      "Content-Type": "application/json",
    },
  });

  if (!response.ok) {
    const error: ErrorResponse = await response.json().catch(() => ({}) as ErrorResponse);
    throw new Error(
      extractErrorFromResponse(error, "Failed to fetch project details")
    );
  }

  return response.json();
}

/**
 * Delete a project
 */
export async function deleteProject(token: string, projectId: string): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/api/projects/${projectId}`, {
    method: "DELETE",
    headers: {
      "Authorization": `Bearer ${token}`,
      "Content-Type": "application/json",
    },
  });

  if (!response.ok) {
    const error: ErrorResponse = await response.json().catch(() => ({}) as ErrorResponse);
    throw new Error(extractErrorFromResponse(error, "Failed to delete project"));
  }
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
  const response = await fetch(
    `${API_BASE_URL}/api/projects/${projectId}/skills/timeline${query}`,
    {
      method: "GET",
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
      },
    }
  );

  if (!response.ok) {
    const error: ErrorResponse = await response.json().catch(() => ({}) as ErrorResponse);
    throw new Error(
      extractErrorFromResponse(error, "Failed to fetch skills timeline")
    );
  }

  return response.json();
}

/**
 * Update the user's role for a project via overrides
 */
export async function updateProjectRole(
  token: string,
  projectId: string,
  role: string,
): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/api/projects/${projectId}/overrides`, {
    method: "PATCH",
    headers: {
      "Authorization": `Bearer ${token}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ role }),
  });

  if (!response.ok) {
    const error: ErrorResponse = await response.json().catch(() => ({}) as ErrorResponse);
    throw new Error(extractErrorFromResponse(error, "Failed to update role"));
  }
}

/**
 * Update one or more project override fields (role, evidence, custom_rank, etc.)
 */
export async function updateProjectOverrides(
  token: string,
  projectId: string,
  overrides: Partial<ProjectOverrides>,
): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/api/projects/${projectId}/overrides`, {
    method: "PATCH",
    headers: {
      "Authorization": `Bearer ${token}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify(overrides),
  });

  if (!response.ok) {
    const error: ErrorResponse = await response.json().catch(() => ({}) as ErrorResponse);
    throw new Error(
      extractErrorFromResponse(error, "Failed to update project overrides")
    );
  }
}

/**
 * Generate skill progression summary using the LLM
 */
export async function generateProjectSkillSummary(
  token: string,
  projectId: string,
): Promise<SkillProgressSummaryResponse> {
  const response = await fetch(`${API_BASE_URL}/api/projects/${projectId}/skills/summary`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
  });

  if (!response.ok) {
    const error: ErrorResponse = await response.json().catch(() => ({}) as ErrorResponse);
    throw new Error(
      extractErrorFromResponse(error, "Failed to generate skills summary")
    );
  }

  return response.json();
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
  const response = await fetch(
    `${API_BASE_URL}/api/projects/${projectId}/append-upload/${uploadId}`,
    {
      method: "POST",
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify(options ?? { skip_duplicates: true }),
    }
  );

  if (!response.ok) {
    const error: ErrorResponse = await response.json().catch(() => ({}) as ErrorResponse);
    throw new Error(
      extractErrorFromResponse(error, "Failed to append files to project")
    );
  }

  return response.json();
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

  const response = await fetch(`${API_BASE_URL}/api/projects/search?${params}`, {
    method: "GET",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
  });

  if (!response.ok) {
    const error: ErrorResponse = await response.json().catch(() => ({}) as ErrorResponse);
    throw new Error(extractErrorFromResponse(error, "Search failed"));
  }

  return response.json();
}

/**
 * Generate and download an HTML report for a project.
 * Returns the raw HTML string.
 */
export async function exportProjectHtml(
  token: string,
  projectId: string,
): Promise<string> {
  const response = await fetch(
    `${API_BASE_URL}/api/projects/${projectId}/export-html`,
    {
      method: "POST",
      headers: {
        Authorization: `Bearer ${token}`,
      },
    },
  );

  if (!response.ok) {
    let detail = "Failed to generate HTML report";
    try {
      const err = await response.json();
      detail = err.detail || detail;
    } catch {
      // response wasn't JSON
    }
    throw new Error(detail);
  }

  return response.text();
}

/**
 * Fetch all unique skills across user's projects
 */
export async function getSkills(
  token: string,
  category?: string,
): Promise<SkillsListResponse> {
  const params = category ? `?category=${encodeURIComponent(category)}` : "";
  const response = await fetch(`${API_BASE_URL}/api/skills${params}`, {
    method: "GET",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
  });

  if (!response.ok) {
    const error: ErrorResponse = await response.json().catch(() => ({}) as ErrorResponse);
    throw new Error(error.detail || "Failed to fetch skills");
  }

  return response.json();
}

export async function getSelection(token: string): Promise<SelectionResponse> {
  const response = await fetch(`${API_BASE_URL}/api/selection`, {
    method: "GET",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
  });

  if (!response.ok) {
    const error: ErrorResponse = await response.json().catch(() => ({}) as ErrorResponse);
    throw new Error(error.detail || "Failed to fetch selection preferences");
  }

  return response.json();
}

export async function saveSelection(
  token: string,
  payload: SelectionUpdateRequest,
): Promise<SelectionResponse> {
  const response = await fetch(`${API_BASE_URL}/api/selection`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    const error: ErrorResponse = await response.json().catch(() => ({}) as ErrorResponse);
    throw new Error(error.detail || "Failed to save selection preferences");
  }

  return response.json();
}

/**
 * Fetch available role profiles for gap analysis
 */
export async function getAvailableRoles(token: string): Promise<RoleProfile[]> {
  const response = await fetch(`${API_BASE_URL}/api/projects/skills/roles`, {
    method: "GET",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
  });

  if (!response.ok) {
    const error: ErrorResponse = await response.json().catch(() => ({}) as ErrorResponse);
    throw new Error(extractErrorFromResponse(error, "Failed to fetch roles"));
  }

  return response.json();
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
  const response = await fetch(
    `${API_BASE_URL}/api/projects/${projectId}/skills/gaps?${params}`,
    {
      method: "GET",
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
      },
    },
  );

  if (!response.ok) {
    const error: ErrorResponse = await response.json().catch(() => ({}) as ErrorResponse);
    throw new Error(extractErrorFromResponse(error, "Failed to analyse skill gaps"));
  }

  return response.json();
}

/**
 * Run AI analysis for an existing project using its stored scan data.
 * pass force=true to re-run even if a cached result exists.
 */
export async function runProjectAiAnalysis(
  token: string,
  projectId: string,
  force = false,
): Promise<AiAnalysisApiResponse> {
  const params = force ? "?force=true" : "";
  const response = await fetch(
    `${API_BASE_URL}/api/projects/${projectId}/ai-analysis${params}`,
    {
      method: "POST",
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
      },
    },
  );

  if (!response.ok) {
    const error: ErrorResponse = await response.json().catch(() => ({}) as ErrorResponse);
    throw new Error(extractErrorFromResponse(error, "Failed to run AI analysis"));
  }

  return response.json();
}

/**
 * Run or reuse project-scoped batch AI processing.
 */
export async function runProjectAiBatch(
  token: string,
  projectId: string,
  force = false,
): Promise<AiBatchApiResponse> {
  const params = force ? "?force=true" : "";
  const response = await fetch(
    `${API_BASE_URL}/api/projects/${projectId}/ai-batch${params}`,
    {
      method: "POST",
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
      },
    },
  );

  if (!response.ok) {
    const error: ErrorResponse = await response.json().catch(() => ({}) as ErrorResponse);
    throw new Error(extractErrorFromResponse(error, "Failed to run AI batch analysis"));
  }

  return response.json();
}

/**
 * Fetch cached batch AI processing result for a project.
 */
export async function getProjectAiBatch(
  token: string,
  projectId: string,
): Promise<AiBatchApiResponse> {
  const response = await fetch(
    `${API_BASE_URL}/api/projects/${projectId}/ai-batch`,
    {
      method: "GET",
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
      },
    },
  );

  if (!response.ok) {
    const error: ErrorResponse = await response.json().catch(() => ({}) as ErrorResponse);
    throw new Error(extractErrorFromResponse(error, "Failed to fetch AI batch analysis"));
  }

  return response.json();
}

/**
 * Fetch in-progress batch status messages for real-time polling.
 */
export async function getProjectAiBatchStatus(
  token: string,
  projectId: string,
): Promise<AiBatchStatusApiResponse> {
  const response = await fetch(
    `${API_BASE_URL}/api/projects/${projectId}/ai-batch/status`,
    {
      method: "GET",
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
      },
    },
  );

  if (!response.ok) {
    const error: ErrorResponse = await response.json().catch(() => ({}) as ErrorResponse);
    throw new Error(extractErrorFromResponse(error, "Failed to fetch AI batch status"));
  }

  return response.json();
}
