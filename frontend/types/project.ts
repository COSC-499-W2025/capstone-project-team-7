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
