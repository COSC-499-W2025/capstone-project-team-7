import { request } from "@/lib/api";
import type {
  JobListResponse,
  ScrapeRequest,
  ScrapeResponse,
  UserJob,
  JobFilters,
  UpdateJobStatusRequest,
  AiMatchResponse,
  ScrapeRun,
} from "@/types/job";

function authHeaders(token: string): Record<string, string> {
  return { Authorization: `Bearer ${token}`, "Content-Type": "application/json" };
}

async function call<T>(path: string, init: RequestInit, fallback: string): Promise<T> {
  const result = await request<T>(path, init);
  if (!result.ok) throw new Error(result.error ?? fallback);
  return result.data;
}

/**
 * Fetch paginated jobs with optional filters
 */
export async function getJobs(
  token: string,
  filters?: JobFilters,
  page?: number,
  pageSize?: number,
): Promise<JobListResponse> {
  const params = new URLSearchParams();

  if (page != null) params.set("page", String(page));
  if (pageSize != null) params.set("page_size", String(pageSize));

  if (filters) {
    for (const [key, value] of Object.entries(filters)) {
      if (value == null) continue;
      if (Array.isArray(value)) {
        if (value.length > 0) params.set(key, value.join(","));
      } else if (typeof value === "boolean") {
        params.set(key, value ? "true" : "false");
      } else {
        params.set(key, String(value));
      }
    }
  }

  const query = params.toString();
  return call(
    `/api/jobs${query ? `?${query}` : ""}`,
    { headers: authHeaders(token) },
    "Failed to fetch jobs",
  );
}

/**
 * Fetch a single job by ID
 */
export async function getJobById(token: string, jobId: string): Promise<UserJob> {
  return call(
    `/api/jobs/${jobId}`,
    { headers: authHeaders(token) },
    "Failed to fetch job details",
  );
}

/**
 * Trigger a scrape for new jobs from a source
 */
export async function scrapeJobs(token: string, req: ScrapeRequest): Promise<ScrapeResponse> {
  return call(
    "/api/jobs/scrape",
    { method: "POST", headers: authHeaders(token), body: JSON.stringify(req) },
    "Failed to start job scrape",
  );
}

/**
 * Save a job to the user's saved list
 */
export async function saveJob(token: string, jobId: string): Promise<UserJob> {
  return call(
    `/api/jobs/${jobId}/save`,
    { method: "POST", headers: authHeaders(token) },
    "Failed to save job",
  );
}

/**
 * Remove a job from the user's saved list
 */
export async function unsaveJob(token: string, jobId: string): Promise<void> {
  const result = await request<Record<string, unknown>>(`/api/jobs/${jobId}/save`, {
    method: "DELETE",
    headers: authHeaders(token),
  });
  if (!result.ok) throw new Error(result.error ?? "Failed to unsave job");
}

/**
 * Update the application status for a saved job
 */
export async function updateJobStatus(
  token: string,
  jobId: string,
  body: UpdateJobStatusRequest,
): Promise<UserJob> {
  return call(
    `/api/jobs/${jobId}/status`,
    { method: "PATCH", headers: authHeaders(token), body: JSON.stringify(body) },
    "Failed to update job status",
  );
}

/**
 * Trigger AI match scoring for a job
 */
export async function triggerAiMatch(token: string, jobId: string): Promise<AiMatchResponse> {
  return call(
    `/api/jobs/${jobId}/ai-match`,
    { method: "POST", headers: authHeaders(token) },
    "Failed to trigger AI match",
  );
}

/**
 * Fetch the user's saved jobs, optionally filtered by status
 */
export async function getSavedJobs(token: string, status?: string): Promise<JobListResponse> {
  const query = status ? `?status=${encodeURIComponent(status)}` : "";
  return call(
    `/api/jobs/saved${query}`,
    { headers: authHeaders(token) },
    "Failed to fetch saved jobs",
  );
}

/**
 * Fetch scrape run history
 */
export async function getScrapeHistory(token: string): Promise<ScrapeRun[]> {
  return call(
    "/api/jobs/scrape-history",
    { headers: authHeaders(token) },
    "Failed to fetch scrape history",
  );
}
