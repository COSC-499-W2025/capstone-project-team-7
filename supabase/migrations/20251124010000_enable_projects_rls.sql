-- Enable row-level security on projects and enforce owner-only access
BEGIN;

ALTER TABLE public.projects ENABLE ROW LEVEL SECURITY;

-- Select own projects
CREATE POLICY "select_own_projects" ON public.projects
    FOR SELECT
    USING (user_id = auth.uid());

-- Insert own projects
CREATE POLICY "insert_own_projects" ON public.projects
    FOR INSERT
    WITH CHECK (user_id = auth.uid());

-- Update own projects
CREATE POLICY "update_own_projects" ON public.projects
    FOR UPDATE
    USING (user_id = auth.uid());

-- Delete own projects
CREATE POLICY "delete_own_projects" ON public.projects
    FOR DELETE
    USING (user_id = auth.uid());

COMMIT;
