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

export interface ProjectEvolutionPeriod {
  period_label: string;
  commits: number;
  skill_count: number;
  languages: Record<string, number>;
  activity_types: string[];
}

export interface ProjectEvolutionItem {
  project_id: string;
  project_name: string;
  total_commits: number;
  total_lines: number;
  periods: ProjectEvolutionPeriod[];
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

export interface PortfolioSettings {
  is_public: boolean;
  share_token: string | null;
  display_name: string | null;
  bio: string | null;
  show_heatmap: boolean;
  show_skills_timeline: boolean;
  show_top_projects: boolean;
  show_all_skills: boolean;
  showcase_count: number;
}

export interface PublicPortfolioResponse {
  profile: {
    display_name?: string;
    career_title?: string;
    education?: string;
    avatar_url?: string;
    bio?: string;
  };
  settings: {
    show_heatmap: boolean;
    show_skills_timeline: boolean;
    show_top_projects: boolean;
    show_all_skills: boolean;
    showcase_count: number;
  };
  skills_timeline: SkillsTimelineItem[];
  projects_timeline: TimelineItem[];
  top_projects: {
    project_name: string;
    contribution_score?: number;
    total_commits?: number;
    user_commit_share?: number;
    primary_contributor?: string;
    languages?: string[];
  }[];
  heatmap_data: { period: string; commits: number }[];
  all_skills: string[];
}

// ── Resource Suggestions ─────────────────────────────────────────────

export interface ResourceEntry {
  title: string;
  url: string;
  type: "article" | "video" | "course" | "docs";
  level: "beginner" | "intermediate" | "advanced";
}

export interface ResourceSuggestion {
  skill_name: string;
  current_tier: string;
  target_tier: string;
  reason: string;
  importance?: string | null;
  resources: ResourceEntry[];
}

export interface ResourceSuggestionsResponse {
  suggestions: ResourceSuggestion[];
  role?: string | null;
  role_label?: string | null;
}

// ── LinkedIn Post ────────────────────────────────────────────────────

export interface LinkedInPostRequest {
  scope: "portfolio" | "project";
  project_id?: string;
}

export interface LinkedInPostResponse {
  post_text: string;
  share_url?: string | null;
}

// ── LinkedIn Direct Posting ─────────────────────────────────────────

export interface LinkedInAuthUrlResponse {
  auth_url: string;
}

export interface LinkedInConnectionStatus {
  connected: boolean;
  linkedin_name?: string | null;
  expires_at?: string | null;
}

export interface LinkedInDirectPostRequest {
  post_text: string;
}

export interface LinkedInDirectPostResponse {
  success: boolean;
  post_id?: string | null;
  error?: string | null;
}
