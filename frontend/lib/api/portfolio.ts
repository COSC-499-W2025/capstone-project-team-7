import type {
  PortfolioItem,
  PortfolioItemCreate,
  PortfolioItemUpdate,
  PortfolioGenerateRequest,
  PortfolioGenerateResponse,
  PortfolioChronology,
  PortfolioRefreshResponse,
  PortfolioSettings,
  PublicPortfolioResponse,
  ProjectEvolutionItem,
  ResourceSuggestionsResponse,
  LinkedInPostRequest,
  LinkedInPostResponse,
  LinkedInAuthUrlResponse,
  LinkedInConnectionStatus,
  LinkedInDirectPostRequest,
  LinkedInDirectPostResponse,
} from "@/types/portfolio";
import { request } from "@/lib/api";

function authHeaders(token: string): Record<string, string> {
  return {
    Authorization: `Bearer ${token}`,
    "Content-Type": "application/json",
  };
}

async function call<T>(path: string, init: RequestInit, fallback: string): Promise<T> {
  const result = await request<T>(path, init);
  if (!result.ok) throw new Error(result.error ?? fallback);
  return result.data;
}

export async function listPortfolioItems(token: string): Promise<PortfolioItem[]> {
  return call("/api/portfolio/items", { headers: authHeaders(token) }, "Failed to fetch portfolio items");
}

export async function getPortfolioItem(token: string, id: string): Promise<PortfolioItem> {
  return call(`/api/portfolio/items/${id}`, { headers: authHeaders(token) }, "Failed to fetch portfolio item");
}

export async function createPortfolioItem(
  token: string,
  body: PortfolioItemCreate
): Promise<PortfolioItem> {
  return call(
    "/api/portfolio/items",
    { method: "POST", headers: authHeaders(token), body: JSON.stringify(body) },
    "Failed to create portfolio item"
  );
}

export async function updatePortfolioItem(
  token: string,
  id: string,
  body: PortfolioItemUpdate
): Promise<PortfolioItem> {
  return call(
    `/api/portfolio/items/${id}`,
    { method: "PATCH", headers: authHeaders(token), body: JSON.stringify(body) },
    "Failed to update portfolio item"
  );
}

export async function deletePortfolioItem(token: string, id: string): Promise<void> {
  const result = await request<Record<string, unknown>>(`/api/portfolio/items/${id}`, {
    method: "DELETE",
    headers: authHeaders(token),
  });
  if (!result.ok) throw new Error(result.error ?? "Failed to delete portfolio item");
}

export async function generatePortfolioItem(
  token: string,
  body: PortfolioGenerateRequest
): Promise<PortfolioGenerateResponse> {
  return call(
    "/api/portfolio/generate",
    { method: "POST", headers: authHeaders(token), body: JSON.stringify(body) },
    "Failed to generate portfolio item"
  );
}

export async function refreshPortfolio(
  token: string,
  includeDuplicates = true
): Promise<PortfolioRefreshResponse> {
  return call(
    "/api/portfolio/refresh",
    { method: "POST", headers: authHeaders(token), body: JSON.stringify({ include_duplicates: includeDuplicates }) },
    "Failed to refresh portfolio"
  );
}

export async function getPortfolioChronology(token: string): Promise<PortfolioChronology> {
  return call("/api/portfolio/chronology", { headers: authHeaders(token) }, "Failed to fetch portfolio chronology");
}

export async function getProjectEvolution(token: string, projectIds?: string[]): Promise<ProjectEvolutionItem[]> {
  const params = projectIds?.length ? `?project_ids=${projectIds.join(",")}` : "";
  const response = await call<{ items: ProjectEvolutionItem[] }>(
    `/api/portfolio/project-evolution${params}`,
    { headers: authHeaders(token) },
    "Failed to fetch project evolution"
  );
  return response.items;
}

// ── Portfolio Settings ──────────────────────────────────────────────────

export async function getPortfolioSettings(token: string): Promise<PortfolioSettings> {
  return call("/api/portfolio/settings", { headers: authHeaders(token) }, "Failed to fetch portfolio settings");
}

export async function updatePortfolioSettings(
  token: string,
  settings: Partial<PortfolioSettings>,
): Promise<PortfolioSettings> {
  return call(
    "/api/portfolio/settings",
    { method: "PATCH", headers: authHeaders(token), body: JSON.stringify(settings) },
    "Failed to update portfolio settings"
  );
}

export async function publishPortfolio(
  token: string,
  isPublic: boolean,
): Promise<{ is_public: boolean; share_token: string | null }> {
  return call(
    "/api/portfolio/settings/publish",
    { method: "POST", headers: authHeaders(token), body: JSON.stringify({ is_public: isPublic }) },
    "Failed to publish portfolio"
  );
}

// ── Public Portfolio (no auth) ──────────────────────────────────────────

export async function getPublicPortfolio(shareToken: string): Promise<PublicPortfolioResponse> {
  // Public endpoint - no auth token, but still use request() for consistency
  const result = await request<PublicPortfolioResponse>(`/api/public/portfolio/${shareToken}`, {
    headers: { "Content-Type": "application/json" },
  });
  if (!result.ok) {
    if (result.status === 404) {
      throw new Error("Portfolio not found or not published.");
    }
    throw new Error(result.error ?? "Failed to load public portfolio");
  }
  return result.data;
}

// ── Resource Suggestions ────────────────────────────────────────────

export async function getResourceSuggestions(
  token: string,
  role?: string,
): Promise<ResourceSuggestionsResponse> {
  const params = role ? `?role=${encodeURIComponent(role)}` : "";
  return call(
    `/api/portfolio/resource-suggestions${params}`,
    { headers: authHeaders(token) },
    "Failed to fetch resource suggestions",
  );
}

// ── LinkedIn Post ───────────────────────────────────────────────────

export async function generateLinkedInPost(
  token: string,
  body: LinkedInPostRequest,
): Promise<LinkedInPostResponse> {
  return call(
    "/api/portfolio/linkedin-post",
    { method: "POST", headers: authHeaders(token), body: JSON.stringify(body) },
    "Failed to generate LinkedIn post",
  );
}

// ── LinkedIn Direct Posting ─────────────────────────────────────────

export async function getLinkedInAuthUrl(
  token: string,
): Promise<LinkedInAuthUrlResponse> {
  return call(
    "/api/linkedin/auth-url",
    { headers: authHeaders(token) },
    "Failed to get LinkedIn auth URL",
  );
}

export async function getLinkedInStatus(
  token: string,
): Promise<LinkedInConnectionStatus> {
  return call(
    "/api/linkedin/status",
    { headers: authHeaders(token) },
    "Failed to check LinkedIn status",
  );
}

export async function postToLinkedIn(
  token: string,
  body: LinkedInDirectPostRequest,
): Promise<LinkedInDirectPostResponse> {
  return call(
    "/api/linkedin/post",
    { method: "POST", headers: authHeaders(token), body: JSON.stringify(body) },
    "Failed to post to LinkedIn",
  );
}

export async function disconnectLinkedIn(token: string): Promise<void> {
  await call<Record<string, unknown>>(
    "/api/linkedin/disconnect",
    { method: "DELETE", headers: authHeaders(token) },
    "Failed to disconnect LinkedIn",
  );
}
