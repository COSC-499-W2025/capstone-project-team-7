-- Add profile fields for the Profile page (education, career, avatar, links).

ALTER TABLE public.profiles
  ADD COLUMN IF NOT EXISTS education    text,
  ADD COLUMN IF NOT EXISTS career_title text,
  ADD COLUMN IF NOT EXISTS avatar_url   text,
  ADD COLUMN IF NOT EXISTS schema_url   text,
  ADD COLUMN IF NOT EXISTS drive_url    text,
  ADD COLUMN IF NOT EXISTS updated_at   timestamptz DEFAULT now();
