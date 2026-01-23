
-- Create portfolio_items table
create table if not exists public.portfolio_items (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.profiles(id) on delete cascade,
  title text not null,
  summary text,
  role text,
  evidence text,
  thumbnail text,
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

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
