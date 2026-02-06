// API client functions for Projects
import {
  ProjectListResponse,
  ProjectDetail,
  ErrorResponse,
  SkillProgressTimelineResponse,
  SkillProgressSummaryResponse,
} from "@/types/project";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

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
    const error: ErrorResponse = await response.json();
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
    const error: ErrorResponse = await response.json();
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
    const error: ErrorResponse = await response.json();
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
    const error: ErrorResponse = await response.json();
    throw new Error(error.detail || "Failed to fetch skills timeline");
  }

  return response.json();
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
    const error: ErrorResponse = await response.json();
    throw new Error(error.detail || "Failed to generate skills summary");
  }

  return response.json();
}
