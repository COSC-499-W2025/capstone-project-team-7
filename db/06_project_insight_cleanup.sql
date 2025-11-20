-- Track when insights are cleared without deleting shared files/uploads.
alter table if exists public.projects
  add column if not exists insights_deleted_at timestamptz;

-- Ensure cached per-file metadata can be wiped independently of uploads.
-- (scan_files table already supports delete policies scoped by owner.)
