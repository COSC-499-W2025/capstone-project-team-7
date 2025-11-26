-- Support efficient ordering by contribution score within a user's projects
BEGIN;

CREATE INDEX IF NOT EXISTS projects_user_contribution_score_idx
    ON public.projects (user_id, contribution_score);

COMMIT;
