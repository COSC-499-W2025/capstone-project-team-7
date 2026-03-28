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

export interface ProjectScanLanguageEntry {
  language?: string;
  name?: string;
  files?: number;
  count?: number;
  lines?: number;
  bytes?: number;
  percentage?: number;
}

export interface ProjectScanSummary extends Record<string, unknown> {
  total_files?: number;
  total_lines?: number;
  bytes_processed?: number;
  total_size_bytes?: number;
  total_bytes?: number;
  issues_found?: number;
  issue_count?: number;
  scan_duration_seconds?: number;
  scan_duration?: number;
  languages?: ProjectScanLanguageEntry[];
}

export type SkillTier = "beginner" | "intermediate" | "advanced";

export interface TierBreakdown {
  beginner: number;
  intermediate: number;
  advanced: number;
}

export interface ProjectSkillCategoryItem extends Record<string, unknown> {
  name?: string;
  proficiency?: string | number;
  description?: string;
  proficiency_score?: number;
  category_label?: string;
  highest_tier?: SkillTier;
  tier_breakdown?: TierBreakdown;
}

export type ProjectSkillCategoryEntry = string | ProjectSkillCategoryItem;
export type ProjectSkillsByCategory = Record<string, ProjectSkillCategoryEntry[]>;

export interface ProjectSkillsAnalysis extends Record<string, unknown> {
  success?: boolean;
  total_skills?: number;
  skills_by_category?: ProjectSkillsByCategory;
  category_labels?: Record<string, string>;
  skills?: Array<{
    name?: string;
    category?: string;
    description?: string;
    proficiency_score?: number;
    highest_tier?: SkillTier;
    tier_breakdown?: TierBreakdown;
    evidence_count?: number;
    evidence?: SkillEvidenceItem[];
  }>;
  skill_adoption_timeline?: SkillAdoptionEntry[];
  skill_progression?: SkillProgressionMap;
}

export interface ProjectScanFile extends Record<string, unknown> {
  path?: string;
  file_path?: string;
  size_bytes?: number;
  mime_type?: string;
  created_at?: string | null;
  modified_at?: string | null;
  file_hash?: string | null;
}

export interface ProjectContributionContributor extends Record<string, unknown> {
  name?: string;
  commits?: number;
  commit_percentage?: number;
  first_commit_date?: string;
  last_commit_date?: string;
  active_days?: number;
}

export interface ProjectContributionMetrics extends Record<string, unknown> {
  project_type?: string;
  total_commits?: number;
  total_contributors?: number;
  user_commit_share?: number;
  project_start_date?: string;
  project_end_date?: string;
  contributors?: ProjectContributionContributor[];
}

export interface ProjectDuplicateGroup extends Record<string, unknown> {
  hash?: string;
  files?: string[];
  wasted_bytes?: number;
  count?: number;
}

export interface ProjectDuplicateReport extends Record<string, unknown> {
  duplicate_groups?: ProjectDuplicateGroup[];
  total_duplicates?: number;
  total_wasted_bytes?: number;
  total_wasted_mb?: number;
}

export interface ProjectCategoryInfo {
  category: string;
  label: string;
  confidence: number;
}

export interface ProjectScanData extends Record<string, unknown> {
  summary?: ProjectScanSummary;
  skills_analysis?: ProjectSkillsAnalysis;
  code_analysis?: Record<string, unknown>;
  git_analysis?: unknown;
  contribution_metrics?: ProjectContributionMetrics;
  media_analysis?: unknown;
  llm_media?: unknown;
  pdf_analysis?: unknown;
  document_analysis?: unknown;
  duplicate_report?: ProjectDuplicateReport;
  files?: ProjectScanFile[];
  languages?: string[] | ProjectScanLanguageEntry[] | Record<string, unknown>;
  project_category?: ProjectCategoryInfo;
  ai_analysis?: ProjectAiAnalysis | null;
}

export interface ProjectAiAnalysisCategory {
  category: string;
  label: string;
  summary?: string | null;
  insights?: string[] | null;
}

export interface ProjectAiKeyFile {
  file_path?: string | null;
  summary?: string | null;
}

export interface ProjectAiAnalysis {
  overall_summary?: string | null;
  categories?: ProjectAiAnalysisCategory[] | null;
  render_mode?: "cards" | "markdown_report" | null;
  markdown_report?: string | null;
  key_files?: ProjectAiKeyFile[] | null;
  // Legacy fields kept for backward compat with already-cached results
  portfolio_overview?: string | null;
  project_insights?: string[] | null;
  key_achievements?: string[] | null;
  recommendations?: string[] | null;
}

export interface AiAnalysisApiResponse {
  project_id: string;
  result: ProjectAiAnalysis;
  llm_status: string;
  cached: boolean;
  status_messages?: string[] | null;
}

export interface AiBatchApiResponse {
  project_id: string;
  status: string;
  cached: boolean;
  result?: Record<string, unknown> | null;
  detail?: string | null;
  status_messages?: string[] | null;
}

export interface AiBatchStatusApiResponse {
  project_id: string;
  status: string;
  detail?: string | null;
  status_messages: string[];
  updated_at?: string | null;
}

export interface ProjectDetail extends ProjectMetadata {
  scan_data?: ProjectScanData | null;
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
  scan_data?: ProjectScanData;
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

export interface AppendUploadResponse {
  project_id: string;
  upload_id: string;
  status: string;
  files_added: number;
  files_updated: number;
  files_skipped_duplicate: number;
  total_files_in_upload: number;
}

export interface AppendUploadRequest {
  skip_duplicates?: boolean;
}

// Search API types
export interface SearchResultItem {
  type: "file" | "skill";
  project_id: string;
  project_name: string;
  // File fields
  path?: string;
  name?: string;
  size_bytes?: number;
  mime_type?: string;
  // Skill fields
  category?: string;
  skill?: string;
  proficiency?: string;
}

export interface SearchResponse {
  items: SearchResultItem[];
  page: {
    limit: number;
    offset: number;
    total: number;
  };
}

export interface SkillsListResponse {
  skills: string[];
}

export interface SkillEvidenceItem {
  type?: string;
  description?: string;
  file?: string;
  line?: number | null;
  confidence?: number;
  timestamp?: string | null;
  tier?: SkillTier;
}

export interface SkillAdoptionEntry {
  skill_name?: string;
  category?: string;
  first_used_period?: string;
  file?: string;
  current_proficiency?: number;
  total_usage?: number;
}

export interface SkillProgressionPoint {
  period: string;
  proficiency: number;
  evidence_count: number;
  file?: string;
  description?: string;
}

export type SkillProgressionMap = Record<string, SkillProgressionPoint[]>;

export interface RoleProfile {
  key: string;
  label: string;
  description: string;
}

export type SkillImportance = "critical" | "recommended" | "nice_to_have";

export interface WeightedSkillEntry {
  name: string;
  importance: SkillImportance;
}

export interface SkillGapAnalysis {
  role: string;
  role_label: string;
  matched: WeightedSkillEntry[];
  missing: WeightedSkillEntry[];
  extra: string[];
  coverage_percent: number;
  weighted_coverage_percent: number;
}
