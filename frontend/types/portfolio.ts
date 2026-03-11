export interface PortfolioItem {
  id: string;
  user_id: string;
  created_at: string;
  updated_at: string;
  title: string;
  summary: string | null;
  role: string | null;
  evidence: string | null;
  thumbnail: string | null;
}

export interface PortfolioItemCreate {
  title: string;
  summary?: string | null;
  role?: string | null;
  evidence?: string | null;
  thumbnail?: string | null;
}

export interface PortfolioItemUpdate {
  title?: string | null;
  summary?: string | null;
  role?: string | null;
  evidence?: string | null;
  thumbnail?: string | null;
}

export interface PortfolioGenerateRequest {
  project_id?: string | null;
  upload_id?: string | null;
  persist: boolean;
}

export interface PortfolioGenerateResponse {
  id?: string | null;
  title: string;
  summary?: string | null;
  role?: string | null;
  evidence?: string | null;
  persisted: boolean;
}

export interface TimelineItem {
  project_id: string;
  name: string;
  start_date?: string | null;
  end_date?: string | null;
  duration_days?: number | null;
  role?: string | null;
  evidence: string[];
}

export interface SkillsTimelineItem {
  period_label: string;
  skills: string[];
  commits: number;
  projects: string[];
}

export interface PortfolioChronology {
  projects: TimelineItem[];
  skills: SkillsTimelineItem[];
}

export interface DuplicateFileInfo {
  path: string;
  project_id: string;
  project_name: string;
}

export interface DuplicateGroup {
  sha256: string;
  file_count: number;
  wasted_bytes: number;
  files: DuplicateFileInfo[];
}

export interface DedupSummary {
  duplicate_groups_count: number;
  total_wasted_bytes: number;
}

export interface DedupReport {
  summary: DedupSummary;
  duplicate_groups: DuplicateGroup[];
}

export interface PortfolioRefreshResponse {
  status: string;
  projects_scanned: number;
  total_files: number;
  total_size_bytes: number;
  dedup_report?: DedupReport | null;
}
