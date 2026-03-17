// API client functions for Scans
import type { ScanRequest, ScanStatusResponse, StartScanResponse } from "@/types/scan";
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

  return call(
    "/api/scans",
    { method: "POST", headers: authHeaders(token), body: JSON.stringify(body) },
    "Failed to start scan"
  );
}

/**
 * Get the status of a scan
 */
export async function getScanStatus(
  token: string,
  scanId: string,
  signal?: AbortSignal
): Promise<ScanStatusResponse> {
  return call(
    `/api/scans/${scanId}`,
    { headers: authHeaders(token), signal },
    "Failed to get scan status"
  );
}
