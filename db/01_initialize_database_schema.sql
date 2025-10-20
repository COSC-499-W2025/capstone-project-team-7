-- === BASE TABLES (auth-aware) ===
-- A profile row is auto-created for each new auth user
create table if not exists public.profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  email text unique,
  full_name text,
  created_at timestamptz default now()
);

create or replace function public.handle_new_user()
returns trigger language plpgsql security definer as $$
begin
  insert into public.profiles (id,email,full_name)
  values (new.id, new.email, coalesce(new.raw_user_meta_data->>'full_name',''))
  on conflict (id) do nothing;
  return new;
end$$;

drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created
  after insert on auth.users
  for each row execute function public.handle_new_user();

-- User uploads (artifacts)
create table if not exists public.uploads (
  id uuid primary key default gen_random_uuid(),
  owner uuid not null references public.profiles(id) on delete cascade,
  file_name text not null,
  storage_path text not null,         -- e.g. storage bucket path
  size_bytes bigint,
  sha256 text,
  status text default 'uploaded',     -- uploaded | processing | done | error
  created_at timestamptz default now()
);
create index if not exists idx_uploads_owner on public.uploads(owner);

-- Explicit consent records
create table if not exists public.consents (
  id uuid primary key default gen_random_uuid(),
  owner uuid not null references public.profiles(id) on delete cascade,
  upload_id uuid not null references public.uploads(id) on delete cascade,
  scope text not null,                -- e.g. 'extract_text','scan_pii'
  granted boolean not null default true,
  granted_at timestamptz default now(),
  unique(owner, upload_id, scope)
);

-- === RLS ===
alter table public.profiles enable row level security;
alter table public.uploads  enable row level security;
alter table public.consents enable row level security;

-- profiles: user can read/update only self
drop policy if exists "read own profile"   on public.profiles;
drop policy if exists "update own profile" on public.profiles;
create policy "read own profile"   on public.profiles for select using (id = auth.uid());
create policy "update own profile" on public.profiles for update using (id = auth.uid()) with check (id = auth.uid());

-- uploads: CRUD only own rows
drop policy if exists "insert own upload" on public.uploads;
drop policy if exists "select own upload" on public.uploads;
drop policy if exists "update own upload" on public.uploads;
drop policy if exists "delete own upload" on public.uploads;
create policy "insert own upload" on public.uploads for insert with check (owner = auth.uid());
create policy "select own upload" on public.uploads for select using (owner = auth.uid());
create policy "update own upload" on public.uploads for update using (owner = auth.uid());
create policy "delete own upload" on public.uploads for delete using (owner = auth.uid());

-- consents: CRUD only own rows
drop policy if exists "insert own consent" on public.consents;
drop policy if exists "select own consent" on public.consents;
drop policy if exists "update own consent" on public.consents;
drop policy if exists "delete own consent" on public.consents;
create policy "insert own consent" on public.consents for insert with check (owner = auth.uid());
create policy "select own consent" on public.consents for select using (owner = auth.uid());
create policy "update own consent" on public.consents for update using (owner = auth.uid());
create policy "delete own consent" on public.consents for delete using (owner = auth.uid());