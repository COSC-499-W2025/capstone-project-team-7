// Typed contracts for the renderer ↔ FastAPI calls used by the desktop app.
// These are client-side shapes; backend models should mirror them.

export type PortfolioOrResume = "portfolio" | "resume";

export interface ApiSuccess<T> {
  ok: true;
  data: T;
}

export interface ApiFailure {
  ok: false;
  error: string;
  status?: number;
}

export type ApiResult<T> = ApiSuccess<T> | ApiFailure;

// ---------- Ingestion / deduplication ----------

export interface UploadZipRequest {
  // Where the ingested files should land.
  target: PortfolioOrResume;
  // Existing entity the files belong to (optional for new portfolios/resumes).
  portfolioId?: string;
  resumeId?: string;
  // Location of the uploaded archive (e.g., Supabase storage path or presigned URL).
  archiveUrl: string;
  // Original filename for auditing.
  originalFilename: string;
  // Optional checksum to help dedupe before unpacking.
  checksumSha256?: string;
}

export interface NormalizedFileSummary {
  fileId: string;
  name: string;
  sizeBytes: number;
  mimeType?: string;
  sha256: string;
  // True if this file matches an existing stored hash.
  isDuplicate: boolean;
}

export interface UploadZipResponse {
  ingestId: string;
  files: NormalizedFileSummary[];
}

export interface DedupDecision {
  ingestId: string;
  // Keep only one copy of each hash; backend removes duplicates not marked keep.
  keepFileIds: string[];
}

export interface DedupResult {
  removedFileIds: string[];
  keptFileIds: string[];
}

// ---------- Project / resume domain ----------

/** Allowed user roles for projects */
export type ProjectRoleValue = "author" | "contributor" | "lead" | "maintainer" | "reviewer";

export interface EvidenceEntry {
  id: string;
  label: string; // e.g., "Throughput +35%"
  detail?: string;
  sourceUrl?: string;
}

export interface ProjectImage {
  id: string;
  url: string;
  alt?: string;
  isThumbnail?: boolean;
}

export interface ProjectRole {
  title: ProjectRoleValue | string;
  summary?: string;
}

export interface ProjectAttributes {
  chronology?: string; // e.g., "2022-2023" or "May 2023 - Present"
  skills?: string[];
  comparisonAttributes?: Record<string, string | number | boolean>;
  highlights?: string[]; // prioritized skills/points to surface
}

export interface ProjectRepresentation {
  projectId: string;
  order: number; // for re-ranking / showcase order
  role?: ProjectRole;
  attributes?: ProjectAttributes;
  evidence?: EvidenceEntry[];
  thumbnail?: ProjectImage;
  showcase: boolean;
}

/** Project metadata returned from API */
export interface ProjectMetadata {
  id: string;
  project_name: string;
  project_path: string;
  scan_timestamp?: string;
  total_files?: number;
  total_lines?: number;
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
  role?: ProjectRoleValue | null; // User's role in the project
}

export interface ResumeItem {
  id: string;
  projectId: string;
  wording: string; // customized resume bullet/paragraph
  order: number;
  evidence?: EvidenceEntry[];
  role?: ProjectRoleValue | string; // User's role in the project
}

// ---------- Mutations ----------

export interface UpdateProjectRepresentationRequest {
  projectId: string;
  representation: ProjectRepresentation;
}

export interface UpdateResumeItemRequest {
  resumeItemId: string;
  wording: string;
  evidence?: EvidenceEntry[];
}

export interface UpdateOrderingRequest {
  target: PortfolioOrResume;
  items: Array<{
    id: string;
    order: number;
  }>;
}

export interface SetThumbnailRequest {
  projectId: string;
  imageId: string;
}

// ---------- User profile ----------

export interface UserProfile {
  user_id: string;
  display_name?: string | null;
  email?: string | null;
  education?: string | null;
  career_title?: string | null;
  avatar_url?: string | null;
  schema_url?: string | null;
  drive_url?: string | null;
  updated_at?: string | null;
}

export interface UpdateProfileRequest {
  display_name?: string;
  education?: string;
  career_title?: string;
  avatar_url?: string;
  schema_url?: string;
  drive_url?: string;
}

// ---------- Read models ----------

export interface ShowcaseProject {
  projectId: string;
  title: string;
  summary: string;
  representation: ProjectRepresentation;
  resumeItem?: ResumeItem;
}

export interface PortfolioView {
  portfolioId: string;
  name: string;
  projects: ShowcaseProject[];
}

export interface ResumeView {
  resumeId: string;
  name: string;
  items: ResumeItem[];
}

// ---------- Auth ----------

export interface AuthCredentials {
  email: string;
  password: string;
}

export interface AuthSessionResponse {
  user_id: string;
  email: string;
  access_token: string;
  refresh_token: string | null;
}

export interface ConsentRequest {
  user_id: string;
  service_name: string;
  consent_given: boolean;
}

export interface User {
  id: string;
  email: string;
}
