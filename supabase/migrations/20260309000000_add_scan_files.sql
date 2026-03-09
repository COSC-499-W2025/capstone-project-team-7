BEGIN;

CREATE TABLE IF NOT EXISTS public.scan_files (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    owner uuid NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    project_id uuid NOT NULL REFERENCES public.projects(id) ON DELETE CASCADE,
    relative_path text NOT NULL,
    size_bytes bigint,
    mime_type text,
    sha256 text,
    metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
    last_seen_modified_at timestamptz NOT NULL,
    last_scanned_at timestamptz NOT NULL DEFAULT now(),
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (project_id, relative_path)
);

CREATE INDEX IF NOT EXISTS idx_scan_files_owner ON public.scan_files(owner);
CREATE INDEX IF NOT EXISTS idx_scan_files_project_path ON public.scan_files(project_id, relative_path);
CREATE INDEX IF NOT EXISTS idx_scan_files_project_modified ON public.scan_files(project_id, last_seen_modified_at);

DROP TRIGGER IF EXISTS update_scan_files_updated_at ON public.scan_files;
CREATE TRIGGER update_scan_files_updated_at
    BEFORE UPDATE ON public.scan_files
    FOR EACH ROW
    EXECUTE FUNCTION public.update_updated_at_column();

ALTER TABLE public.scan_files ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS scan_files_select_own ON public.scan_files;
CREATE POLICY scan_files_select_own
    ON public.scan_files
    FOR SELECT
    USING (owner = auth.uid());

DROP POLICY IF EXISTS scan_files_insert_own ON public.scan_files;
CREATE POLICY scan_files_insert_own
    ON public.scan_files
    FOR INSERT
    WITH CHECK (owner = auth.uid());

DROP POLICY IF EXISTS scan_files_update_own ON public.scan_files;
CREATE POLICY scan_files_update_own
    ON public.scan_files
    FOR UPDATE
    USING (owner = auth.uid())
    WITH CHECK (owner = auth.uid());

DROP POLICY IF EXISTS scan_files_delete_own ON public.scan_files;
CREATE POLICY scan_files_delete_own
    ON public.scan_files
    FOR DELETE
    USING (owner = auth.uid());

COMMIT;
