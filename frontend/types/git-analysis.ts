// TypeScript types for Git Analysis
// Aligned with backend/src/local_analysis/git_repo.py analyze_git_repo()

/**
 * A single contributor (after merge-by-identity).
 */
export interface GitContributor {
  name: string;
  email: string | null;
  commits: number;
  percent: number;
  first_commit_date?: string | null;
  last_commit_date?: string | null;
  active_days?: number;
  aliases?: string[];
  all_emails?: string[];
}

/**
 * One month of activity in the timeline.
 */
export interface GitTimelineEntry {
  month: string;
  commits: number;
  messages: string[];
  top_files: string[];
  languages: Record<string, number>;
  contributors: number;
}

/**
 * First and last commit dates for the repo.
 */
export interface GitDateRange {
  start: string | null;
  end: string | null;
}

/**
 * Full analysis result for a single git repo.
 * Returned by analyze_git_repo().
 */
export interface GitRepoAnalysis {
  path: string;
  error?: string;
  commit_count: number;
  contributors: GitContributor[];
  project_type: string;
  date_range: GitDateRange | null;
  branches: string[];
  timeline: GitTimelineEntry[];
}
