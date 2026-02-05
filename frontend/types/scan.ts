// TypeScript types for Scan API
// Based on backend/src/api/models/ scan models

export type JobState = "queued" | "running" | "succeeded" | "failed" | "canceled";

export interface ScanProgress {
  percent: number;
  message?: string;
}

export interface ScanError {
  code: string;
  message: string;
  details?: Record<string, unknown>;
}

export interface ScanResultSummary {
  total_files: number;
  bytes_processed: number;
  issues_count: number;
}

export interface ScanResult {
  summary: ScanResultSummary;
  languages: Array<{ name: string; count: number; lines: number }>;
  has_media_files: boolean;
  pdf_count: number;
  document_count: number;
  git_repos_count: number;
  files: Array<Record<string, unknown>>;
  timings: Array<[string, number]>;
}

export interface ScanStatusResponse {
  scan_id: string;
  user_id: string;
  project_id?: string;
  upload_id?: string;
  state: JobState;
  progress?: ScanProgress;
  error?: ScanError;
  result?: ScanResult;
}

export interface ScanRequest {
  source_path?: string;
  upload_id?: string;
  use_llm?: boolean;
  llm_media?: boolean;
  profile_id?: string;
  relevance_only?: boolean;
  persist_project?: boolean;
}

export interface StartScanResponse {
  scan_id: string;
}
