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
} from "@/types/project";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

export interface SelectionResponse {
  user_id: string;
  project_order: string[];
  skill_order: string[];
  selected_project_ids: string[];
  selected_skill_ids: string[];
  created_at: string;
  updated_at: string;
}

export interface SelectionUpdateRequest {
  project_order?: string[];
  skill_order?: string[];
  selected_project_ids?: string[];
  selected_skill_ids?: string[];
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
    throw new Error(error.detail || "Failed to fetch projects");
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
    throw new Error(error.detail || "Failed to fetch project details");
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
    throw new Error(error.detail || "Failed to delete project");
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
    throw new Error(error.detail || "Failed to fetch skills timeline");
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
    throw new Error(error.detail || "Failed to update role");
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
    throw new Error(error.detail || "Failed to update project overrides");
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
    throw new Error(error.detail || "Failed to generate skills summary");
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
    throw new Error(error.detail || "Failed to append files to project");
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
    throw new Error(error.detail || "Search failed");
  }

  return response.json();
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
