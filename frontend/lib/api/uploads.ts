const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

type UploadError = {
  detail?: {
    message?: string;
  } | string;
};

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

export async function uploadFromPath(token: string, sourcePath: string): Promise<UploadFromPathResponse> {
  const response = await fetch(`${API_BASE_URL}/api/uploads/from-path`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ source_path: sourcePath }),
  });

  if (!response.ok) {
    const error: UploadError = await response.json().catch(() => ({}));
    if (typeof error.detail === "string") {
      throw new Error(error.detail);
    }
    throw new Error(error.detail?.message || "Failed to upload source path");
  }

  return response.json();
}

export async function parseUpload(token: string, uploadId: string): Promise<ParseUploadResponse> {
  const response = await fetch(`${API_BASE_URL}/api/uploads/${uploadId}/parse`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({}),
  });

  if (!response.ok) {
    const error: UploadError = await response.json().catch(() => ({}));
    if (typeof error.detail === "string") {
      throw new Error(error.detail);
    }
    throw new Error(error.detail?.message || "Failed to parse uploaded source");
  }

  return response.json();
}
