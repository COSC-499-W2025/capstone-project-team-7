-- Enforce portfolio_items length constraints and keep updated_at current
create extension if not exists "pgcrypto" with schema "extensions";

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

-- Add length constraints idempotently
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'portfolio_items_title_length') THEN
    ALTER TABLE public.portfolio_items ADD CONSTRAINT portfolio_items_title_length CHECK (char_length(title) <= 255);
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'portfolio_items_summary_length') THEN
    ALTER TABLE public.portfolio_items ADD CONSTRAINT portfolio_items_summary_length CHECK (char_length(summary) <= 1000);
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'portfolio_items_role_length') THEN
    ALTER TABLE public.portfolio_items ADD CONSTRAINT portfolio_items_role_length CHECK (char_length(role) <= 255);
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'portfolio_items_evidence_length') THEN
    ALTER TABLE public.portfolio_items ADD CONSTRAINT portfolio_items_evidence_length CHECK (char_length(evidence) <= 2048);
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'portfolio_items_thumbnail_length') THEN
    ALTER TABLE public.portfolio_items ADD CONSTRAINT portfolio_items_thumbnail_length CHECK (char_length(thumbnail) <= 1024);
  END IF;
END$$;
