
-- Ensure pgcrypto for gen_random_uuid
create extension if not exists "pgcrypto" with schema "extensions";

-- Create portfolio_items table
create table if not exists public.portfolio_items (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.profiles(id) on delete cascade,
  title text not null check (char_length(title) <= 255),
  summary text check (char_length(summary) <= 1000),
  role text check (char_length(role) <= 255),
  evidence text check (char_length(evidence) <= 2048),
  thumbnail text check (char_length(thumbnail) <= 1024),
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

-- Keep updated_at in sync on updates
create or replace function public.set_updated_at()
returns trigger language plpgsql as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

drop trigger if exists trg_portfolio_items_set_updated_at on public.portfolio_items;
create trigger trg_portfolio_items_set_updated_at
  before update on public.portfolio_items
  for each row execute function public.set_updated_at();

create index if not exists idx_portfolio_items_user_id on public.portfolio_items(user_id);

-- Enable Row Level Security (RLS)
alter table public.portfolio_items enable row level security;

-- RLS Policies - Allow service_role (backend) to bypass RLS, but enforce for authenticated users
drop policy if exists "insert own portfolio_item" on public.portfolio_items;
drop policy if exists "select own portfolio_item" on public.portfolio_items;
drop policy if exists "update own portfolio_item" on public.portfolio_items;
drop policy if exists "delete own portfolio_item" on public.portfolio_items;

-- Allow service role (backend operations) to bypass RLS checks
create policy "service role can do all operations" on public.portfolio_items
  for all using (auth.role() = 'service_role');

-- For authenticated users, enforce user isolation
create policy "authenticated users can insert own portfolio_item" on public.portfolio_items for insert 
  with check (auth.role() = 'authenticated' and user_id = auth.uid());
create policy "authenticated users can select own portfolio_item" on public.portfolio_items for select 
  using (auth.role() = 'authenticated' and user_id = auth.uid());
create policy "authenticated users can update own portfolio_item" on public.portfolio_items for update 
  using (auth.role() = 'authenticated' and user_id = auth.uid())
  with check (auth.role() = 'authenticated' and user_id = auth.uid());
create policy "authenticated users can delete own portfolio_item" on public.portfolio_items for delete 
  using (auth.role() = 'authenticated' and user_id = auth.uid());
