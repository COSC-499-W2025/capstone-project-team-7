// API client functions for Scans
import type { ScanRequest, ScanStatusResponse, StartScanResponse } from "@/types/scan";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

/**
 * Start a new portfolio scan
 */
export async function startScan(
  token: string,
  sourcePath: string,
  options?: Partial<ScanRequest>
): Promise<StartScanResponse> {
  const body: ScanRequest = {
    source_path: sourcePath,
    persist_project: true,
    use_llm: false,
    llm_media: false,
    relevance_only: false,
    ...options,
  };

  const response = await fetch(`${API_BASE_URL}/api/scans`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify(body),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: "Failed to start scan" }));
    throw new Error(error.detail || "Failed to start scan");
  }

  return response.json();
}

/**
 * Get the status of a scan
 */
export async function getScanStatus(
  token: string,
  scanId: string,
  signal?: AbortSignal
): Promise<ScanStatusResponse> {
  const response = await fetch(`${API_BASE_URL}/api/scans/${scanId}`, {
    method: "GET",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
    signal,
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: "Failed to get scan status" }));
    throw new Error(error.detail || "Failed to get scan status");
  }

  return response.json();
}
