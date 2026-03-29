export type JobSource = "linkedin" | "indeed";
export type JobType = "full-time" | "part-time" | "internship" | "contract";
export type ExperienceLevel = "entry" | "mid" | "senior";
export type ApplicationStatus = "unsaved" | "saved" | "applied" | "interviewing" | "offer" | "rejected";

export interface Job {
  id: string;
  external_id: string;
  source: JobSource;
  title: string;
  company: string;
  location: string | null;
  is_remote: boolean;
  job_type: JobType | null;
  experience_level: ExperienceLevel | null;
  salary_min: number | null;
  salary_max: number | null;
  salary_currency: string;
  description: string | null;
  url: string | null;
  company_logo_url: string | null;
  skills: string[];
  posted_at: string | null;
  scraped_at: string | null;
}

export interface UserJob {
  id: string;
  user_id: string;
  job_id: string;
  status: ApplicationStatus;
  keyword_match_score: number | null;
  ai_match_score: number | null;
  ai_match_summary: string | null;
  matched_skills: string[];
  missing_skills: string[];
  notes: string | null;
  applied_at: string | null;
  created_at: string | null;
  updated_at: string | null;
  job: Job | null;
}

export interface JobListResponse {
  count: number;
  jobs: UserJob[];
}

export interface ScrapeRequest {
  source: JobSource;
  search_query: string;
  location?: string;
  limit?: number;
}

export interface ScrapeResponse {
  run_id: string;
  source: string;
  status: string;
  jobs_found: number;
  jobs_new: number;
}

export interface JobFilters {
  source?: JobSource;
  location?: string;
  is_remote?: boolean;
  job_type?: JobType;
  experience_level?: ExperienceLevel;
  salary_min?: number;
  salary_max?: number;
  skills?: string[];
  posted_after?: string;
  search?: string;
}

export interface UpdateJobStatusRequest {
  status: ApplicationStatus;
  notes?: string;
  applied_at?: string;
}

export interface AiMatchResponse {
  job_id: string;
  ai_match_score: number;
  ai_match_summary: string;
  matched_skills: string[];
  missing_skills: string[];
}

export interface ScrapeRun {
  id: string;
  source: JobSource;
  search_query: string | null;
  location: string | null;
  status: string;
  jobs_found: number;
  jobs_new: number;
  error_message: string | null;
  started_at: string;
  completed_at: string | null;
}
