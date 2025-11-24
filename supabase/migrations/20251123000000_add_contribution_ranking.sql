-- Contribution ranking metadata for saved projects
BEGIN;

ALTER TABLE IF EXISTS public.projects
    ADD COLUMN IF NOT EXISTS has_contribution_metrics boolean DEFAULT false,
    ADD COLUMN IF NOT EXISTS contribution_score numeric,
    ADD COLUMN IF NOT EXISTS user_commit_share numeric,
    ADD COLUMN IF NOT EXISTS total_commits integer,
    ADD COLUMN IF NOT EXISTS primary_contributor text,
    ADD COLUMN IF NOT EXISTS project_end_date text;

COMMIT;
