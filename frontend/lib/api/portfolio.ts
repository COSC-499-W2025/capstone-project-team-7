import type {
  PortfolioItem,
  PortfolioItemCreate,
  PortfolioItemUpdate,
  PortfolioGenerateRequest,
  PortfolioGenerateResponse,
  PortfolioChronology,
} from "@/types/portfolio";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

function authHeaders(token: string): Record<string, string> {
  return {
    Authorization: `Bearer ${token}`,
    "Content-Type": "application/json",
  };
}

export async function listPortfolioItems(token: string): Promise<PortfolioItem[]> {
  const response = await fetch(`${API_BASE_URL}/api/portfolio/items`, {
    method: "GET",
    headers: authHeaders(token),
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail || "Failed to fetch portfolio items");
  }
  return response.json();
}

export async function getPortfolioItem(token: string, id: string): Promise<PortfolioItem> {
  const response = await fetch(`${API_BASE_URL}/api/portfolio/items/${id}`, {
    method: "GET",
    headers: authHeaders(token),
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail || "Failed to fetch portfolio item");
  }
  return response.json();
}

export async function createPortfolioItem(
  token: string,
  body: PortfolioItemCreate
): Promise<PortfolioItem> {
  const response = await fetch(`${API_BASE_URL}/api/portfolio/items`, {
    method: "POST",
    headers: authHeaders(token),
    body: JSON.stringify(body),
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail || "Failed to create portfolio item");
  }
  return response.json();
}

export async function updatePortfolioItem(
  token: string,
  id: string,
  body: PortfolioItemUpdate
): Promise<PortfolioItem> {
  const response = await fetch(`${API_BASE_URL}/api/portfolio/items/${id}`, {
    method: "PATCH",
    headers: authHeaders(token),
    body: JSON.stringify(body),
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail || "Failed to update portfolio item");
  }
  return response.json();
}

export async function deletePortfolioItem(token: string, id: string): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/api/portfolio/items/${id}`, {
    method: "DELETE",
    headers: authHeaders(token),
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail || "Failed to delete portfolio item");
  }
}

export async function generatePortfolioItem(
  token: string,
  body: PortfolioGenerateRequest
): Promise<PortfolioGenerateResponse> {
  const response = await fetch(`${API_BASE_URL}/api/portfolio/generate`, {
    method: "POST",
    headers: authHeaders(token),
    body: JSON.stringify(body),
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail || "Failed to generate portfolio item");
  }
  return response.json();
}

export async function getPortfolioChronology(token: string): Promise<PortfolioChronology> {
  const response = await fetch(`${API_BASE_URL}/api/portfolio/chronology`, {
    method: "GET",
    headers: authHeaders(token),
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail || "Failed to fetch portfolio chronology");
  }
  return response.json();
}
