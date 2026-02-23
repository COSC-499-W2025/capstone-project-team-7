export interface ResumeItemSummary {
  id: string;
  project_name: string;
  start_date?: string | null;
  end_date?: string | null;
  created_at?: string | null;
  metadata: Record<string, unknown>;
}

export interface ResumeItemRecord extends ResumeItemSummary {
  content: string;
  bullets: string[];
  source_path?: string | null;
}

export interface ResumeItemListResponse {
  items: ResumeItemSummary[];
  page: { limit: number; offset: number; total: number };
}

export interface ResumeItemCreateRequest {
  project_name: string;
  start_date?: string | null;
  end_date?: string | null;
  overview?: string | null;
  content?: string | null;
  bullets?: string[];
  metadata?: Record<string, unknown>;
}

export interface ResumeItemUpdateRequest {
  project_name?: string | null;
  start_date?: string | null;
  end_date?: string | null;
  content?: string | null;
  bullets?: string[] | null;
  metadata?: Record<string, unknown> | null;
}
