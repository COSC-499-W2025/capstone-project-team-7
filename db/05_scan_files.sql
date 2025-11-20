-- Ensure projects table exists locally (Supabase already has this schema remotely)
create table if not exists public.projects (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.profiles(id) on delete cascade,
  project_name text not null,
  project_path text,
  scan_timestamp timestamptz,
  scan_data jsonb,
  total_files integer,
  total_lines integer,
  languages text[],
  has_media_analysis boolean default false,
  has_pdf_analysis boolean default false,
  has_code_analysis boolean default false,
  has_git_analysis boolean default false,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create index if not exists idx_projects_user_id on public.projects(user_id);

-- Cached scan metadata per file
create table if not exists public.scan_files (
  id uuid primary key default gen_random_uuid(),
  owner uuid not null references public.profiles(id) on delete cascade,
  project_id uuid not null references public.projects(id) on delete cascade,
  relative_path text not null,
  size_bytes bigint,
  mime_type text,
  sha256 text,
  metadata jsonb not null default '{}'::jsonb,
  last_seen_modified_at timestamptz not null,
  last_scanned_at timestamptz not null default now(),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique(project_id, relative_path)
);

create index if not exists idx_scan_files_owner on public.scan_files(owner);
create index if not exists idx_scan_files_project_path on public.scan_files(project_id, relative_path);
create index if not exists idx_scan_files_project_modified on public.scan_files(project_id, last_seen_modified_at);

-- Keep timestamps fresh on update
create trigger update_scan_files_updated_at
  before update on public.scan_files
  for each row
  execute function public.update_updated_at_column();

-- Enforce per-user isolation
alter table public.scan_files enable row level security;

drop policy if exists "scan_files_select_own" on public.scan_files;
create policy "scan_files_select_own"
  on public.scan_files
  for select
  using (owner = auth.uid());

drop policy if exists "scan_files_insert_own" on public.scan_files;
create policy "scan_files_insert_own"
  on public.scan_files
  for insert
  with check (owner = auth.uid());

drop policy if exists "scan_files_update_own" on public.scan_files;
create policy "scan_files_update_own"
  on public.scan_files
  for update
  using (owner = auth.uid())
  with check (owner = auth.uid());

drop policy if exists "scan_files_delete_own" on public.scan_files;
create policy "scan_files_delete_own"
  on public.scan_files
  for delete
  using (owner = auth.uid());

