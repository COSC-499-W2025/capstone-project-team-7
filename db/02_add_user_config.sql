-- === USER CONFIGS TABLE ===
-- Stores user configuration for file scanning preferences

create table if not exists public.user_configs (
  id uuid primary key default gen_random_uuid(),
  owner uuid not null references public.profiles(id) on delete cascade,
  
  -- Scan profiles (all available profiles for this user)
  scan_profiles jsonb not null default '{
    "all": {
      "description": "Scan all supported file types",
      "extensions": [".py", ".js", ".html", ".css", ".txt", ".md", ".json"],
      "exclude_dirs": ["__pycache__", "node_modules", ".git", "venv"]
    },
    "code_only": {
      "description": "Scan only code files",
      "extensions": [".py", ".js", ".java", ".cpp", ".c", ".go", ".rs"],
      "exclude_dirs": ["__pycache__", "node_modules", ".git", "venv"]
    },
    "python_only": {
      "description": "Scan only Python files",
      "extensions": [".py"],
      "exclude_dirs": ["__pycache__", "venv", ".git"]
    },
    "web_only": {
      "description": "Scan only web files",
      "extensions": [".html", ".css", ".js", ".jsx", ".tsx", ".vue"],
      "exclude_dirs": ["node_modules", ".git"]
    },
    "documents_only": {
      "description": "Scan only document files",
      "extensions": [".txt", ".md", ".doc", ".docx", ".pdf"],
      "exclude_dirs": [".git"]
    }
  }'::jsonb,
  
  -- Currently active profile
  current_profile text not null default 'all',
  
  -- Additional settings
  max_file_size_mb integer not null default 10,
  follow_symlinks boolean not null default false,
  
  created_at timestamptz default now(),
  updated_at timestamptz default now(),
  
  -- Ensure one config per user
  unique(owner)
);

-- Index for faster lookups
create index if not exists idx_user_configs_owner on public.user_configs(owner);

-- === AUTO-CREATE CONFIG FUNCTION ===
-- Creates default config when a new profile is created
create or replace function public.handle_new_user_config()
returns trigger
language plpgsql
security definer
as $$
begin
  insert into public.user_configs (owner)
  values (new.id)
  on conflict (owner) do nothing;
  return new;
end$$;

-- Trigger to auto-create config after profile creation
drop trigger if exists on_profile_created on public.profiles;
create trigger on_profile_created
  after insert on public.profiles
  for each row execute function public.handle_new_user_config();

-- === UPDATE TIMESTAMP FUNCTION ===
-- Automatically update the updated_at timestamp
create or replace function public.update_updated_at_column()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end$$;

-- Trigger to update updated_at on config changes
drop trigger if exists update_user_configs_updated_at on public.user_configs;
create trigger update_user_configs_updated_at
  before update on public.user_configs
  for each row execute function public.update_updated_at_column();

-- === RLS POLICIES ===
alter table public.user_configs enable row level security;

-- Users can read only their own config
drop policy if exists "read own config" on public.user_configs;
create policy "read own config"
  on public.user_configs for select
  using (owner = auth.uid());

-- Users can update only their own config
drop policy if exists "update own config" on public.user_configs;
create policy "update own config"
  on public.user_configs for update
  using (owner = auth.uid())
  with check (owner = auth.uid());

-- Users can insert their own config (though trigger usually handles this)
drop policy if exists "insert own config" on public.user_configs;
create policy "insert own config"
  on public.user_configs for insert
  with check (owner = auth.uid());

-- Users can delete their own config
drop policy if exists "delete own config" on public.user_configs;
create policy "delete own config"
  on public.user_configs for delete
  using (owner = auth.uid());

-- === COMMENTS ===
comment on table public.user_configs is 'User configuration for file scanning preferences';
comment on column public.user_configs.scan_profiles is 'JSON object containing all available scan profiles for the user';
comment on column public.user_configs.current_profile is 'Name of the currently active scan profile (must exist in scan_profiles)';
comment on column public.user_configs.max_file_size_mb is 'Maximum file size in MB to scan';
comment on column public.user_configs.follow_symlinks is 'Whether to follow symbolic links during scanning';