import { request } from "@/lib/api";

export interface UploadFromPathResponse {
  upload_id: string;
  status: string;
  filename: string;
  size_bytes: number;
}

export interface ParseUploadResponse {
  upload_id: string;
  status: string;
}

function authHeaders(token: string): Record<string, string> {
  return { Authorization: `Bearer ${token}`, "Content-Type": "application/json" };
}

async function call<T>(path: string, init: RequestInit, fallback: string): Promise<T> {
  const result = await request<T>(path, init);
  if (!result.ok) throw new Error(result.error ?? fallback);
  return result.data;
}

export async function uploadFromPath(token: string, sourcePath: string): Promise<UploadFromPathResponse> {
  return call(
    "/api/uploads/from-path",
    { method: "POST", headers: authHeaders(token), body: JSON.stringify({ source_path: sourcePath }) },
    "Failed to upload source path"
  );
}

export async function parseUpload(token: string, uploadId: string): Promise<ParseUploadResponse> {
  return call(
    `/api/uploads/${uploadId}/parse`,
    { method: "POST", headers: authHeaders(token), body: JSON.stringify({}) },
    "Failed to parse uploaded source"
  );
}
