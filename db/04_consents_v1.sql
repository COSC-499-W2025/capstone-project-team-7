-- Create table + enable RLS
create table if not exists public.consents_v1(
  user_id uuid primary key references auth.users(id) on delete cascade,
  accepted boolean not null default false,
  accepted_at timestamptz,
  version text not null default 'v1',
  metadata jsonb not null default '{}'
);
alter table public.consents_v1 enable row level security;

-- Re-create policies idempotently
drop policy if exists "consent_v1_read_own"   on public.consents_v1;
drop policy if exists "consent_v1_insert_own" on public.consents_v1;
drop policy if exists "consent_v1_update_own" on public.consents_v1;

create policy "consent_v1_read_own"
  on public.consents_v1 for select using (auth.uid() = user_id);

create policy "consent_v1_insert_own"
  on public.consents_v1 for insert with check (auth.uid() = user_id);

create policy "consent_v1_update_own"
  on public.consents_v1 for update using (auth.uid() = user_id)
  with check (auth.uid() = user_id);

  drop policy if exists "consent_v1_delete_own" on public.consents_v1;

create policy "consent_v1_delete_own"
  on public.consents_v1 for delete using (auth.uid() = user_id);