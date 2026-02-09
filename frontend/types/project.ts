// TypeScript types for Project API
// Based on backend/src/api/project_routes.py models

export interface ProjectMetadata {
  id: string;
  user_id?: string;
  project_name: string;
  project_path: string;
  scan_timestamp?: string;
  total_files: number;
  total_lines: number;
  languages?: string[];
  has_media_analysis?: boolean;
  has_pdf_analysis?: boolean;
  has_code_analysis?: boolean;
  has_git_analysis?: boolean;
  has_contribution_metrics?: boolean;
  has_skills_analysis?: boolean;
  has_document_analysis?: boolean;
  has_skills_progress?: boolean;
  contribution_score?: number;
  user_commit_share?: number;
  total_commits?: number;
  primary_contributor?: string;
  project_end_date?: string;
  thumbnail_url?: string;
  created_at?: string;
  role?: string; // User's role in the project
}

export interface ProjectOverrides {
  role?: string;
  evidence?: string[];
  thumbnail_url?: string;
  custom_rank?: number; // 0-100
  start_date_override?: string;
  end_date_override?: string;
  comparison_attributes?: Record<string, string>;
  highlighted_skills?: string[];
}

export interface ProjectDetail extends ProjectMetadata {
  scan_data?: Record<string, any>;
  user_overrides?: ProjectOverrides;
}

export interface ProjectListResponse {
  count: number;
  projects: ProjectMetadata[];
}

export interface SkillProgressPeriod {
  period_label: string;
  commits: number;
  tests_changed: number;
  skill_count: number;
  evidence_count: number;
  top_skills: string[];
  languages: Record<string, number>;
  contributors: number;
  commit_messages: string[];
  top_files: string[];
  activity_types: string[];
  period_languages: Record<string, number>;
}

export interface SkillProgressSummary {
  overview: string;
  timeline: string[];
  skills_focus: string[];
  suggested_next_steps: string[];
  validation_warning?: string | null;
}

export interface SkillProgressTimelineResponse {
  project_id: string;
  timeline: SkillProgressPeriod[];
  note?: string | null;
  summary?: SkillProgressSummary | null;
}

export interface SkillProgressSummaryResponse {
  project_id: string;
  summary?: SkillProgressSummary | null;
  note?: string | null;
  llm_status?: string | null;
}

export interface CreateProjectRequest {
  project_name: string;
  project_path: string;
  scan_data?: Record<string, any>;
}

export interface CreateProjectResponse {
  id: string;
  project_name: string;
  scan_timestamp: string;
  message: string;
}

export interface ErrorResponse {
  detail: string;
  error_code?: string;
}
