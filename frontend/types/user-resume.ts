/**
 * Types for user resume documents (full resume, not just items)
 */

export type ResumeTemplate = "jake" | "classic" | "modern" | "minimal" | "custom";

export interface ResumeTemplateMeta {
  id: ResumeTemplate;
  name: string;
  description: string;
  preview_url?: string | null;
}

export interface UserResumeSummary {
  id: string;
  name: string;
  template: ResumeTemplate;
  is_latex_mode: boolean;
  metadata: Record<string, unknown>;
  created_at?: string | null;
  updated_at?: string | null;
}

export interface UserResumeRecord extends UserResumeSummary {
  latex_content?: string | null;
  structured_data: ResumeStructuredData;
}

export interface UserResumeListResponse {
  items: UserResumeSummary[];
  page: { limit: number; offset: number; total: number };
}

export interface UserResumeCreateRequest {
  name?: string;
  template?: ResumeTemplate;
  latex_content?: string | null;
  structured_data?: ResumeStructuredData | null;
  is_latex_mode?: boolean;
  metadata?: Record<string, unknown> | null;
}

export interface UserResumeUpdateRequest {
  name?: string | null;
  template?: ResumeTemplate | null;
  latex_content?: string | null;
  structured_data?: ResumeStructuredData | null;
  is_latex_mode?: boolean | null;
  metadata?: Record<string, unknown> | null;
}

export interface UserResumeDuplicateRequest {
  new_name?: string | null;
}

export interface UserResumeAddItemsRequest {
  item_ids: string[];
}

export interface TemplatesListResponse {
  templates: ResumeTemplateMeta[];
}

// ============================================================================
// Structured data for non-LaTeX mode
// ============================================================================

export interface ResumeContactInfo {
  full_name: string;
  email?: string;
  phone?: string;
  linkedin_url?: string;
  github_url?: string;
  portfolio_url?: string;
  location?: string;
}

export interface ResumeEducationEntry {
  id: string;
  institution: string;
  degree: string;
  field_of_study?: string;
  location?: string;
  start_date?: string;
  end_date?: string;
  gpa?: string;
  highlights?: string[];
}

export interface ResumeExperienceEntry {
  id: string;
  company: string;
  position: string;
  location?: string;
  start_date?: string;
  end_date?: string;
  bullets: string[];
}

export interface ResumeProjectEntry {
  id: string;
  name: string;
  role?: string;
  company?: string;
  technologies?: string;
  url?: string;
  start_date?: string;
  end_date?: string;
  bullets: string[];
  // Link to resume_item for auto-population
  resume_item_id?: string;
}

export interface ResumeSkillsSection {
  languages?: string[];
  frameworks?: string[];
  developer_tools?: string[];
  libraries?: string[];
  // Allow custom categories
  custom?: Record<string, string[]>;
}

export interface ResumeAwardEntry {
  id: string;
  title: string;
  issuer?: string;
  date?: string;
  description?: string;
}

export interface ResumeStructuredData {
  contact?: ResumeContactInfo;
  education?: ResumeEducationEntry[];
  experience?: ResumeExperienceEntry[];
  projects?: ResumeProjectEntry[];
  skills?: ResumeSkillsSection;
  awards?: ResumeAwardEntry[];
  // Section ordering
  section_order?: string[];
}
