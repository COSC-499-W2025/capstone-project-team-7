-- User resumes table - stores complete resume documents (LaTeX or structured)
-- Distinct from resume_items which are per-project bullet point entries

BEGIN;

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

-- Resume templates enum
DO $$ BEGIN
    CREATE TYPE public.resume_template AS ENUM (
        'jake',           -- Jake's LaTeX template
        'classic',        -- Classic/traditional template
        'modern',         -- Modern template with sidebar
        'minimal',        -- Minimal clean template
        'custom'          -- User's fully custom LaTeX
    );
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- Main resumes table
CREATE TABLE IF NOT EXISTS "public"."user_resumes" (
    "id" uuid DEFAULT gen_random_uuid() PRIMARY KEY,
    "user_id" uuid NOT NULL,
    "name" text NOT NULL DEFAULT 'Untitled Resume',
    "template" public.resume_template NOT NULL DEFAULT 'jake',
    "latex_content" text,                                    -- Raw LaTeX source
    "structured_data" jsonb DEFAULT '{}'::jsonb,            -- Structured form data for non-LaTeX users
    "is_latex_mode" boolean NOT NULL DEFAULT true,          -- true = LaTeX editor, false = form/template mode
    "metadata" jsonb NOT NULL DEFAULT '{}'::jsonb,          -- Additional metadata (pdf_url, last_compiled, etc.)
    "created_at" timestamptz NOT NULL DEFAULT now(),
    "updated_at" timestamptz NOT NULL DEFAULT now()
);

-- Foreign key to profiles
ALTER TABLE "public"."user_resumes"
    ADD CONSTRAINT "user_resumes_user_id_fkey"
    FOREIGN KEY ("user_id") REFERENCES "public"."profiles"("id") ON DELETE CASCADE;

-- Index for efficient lookups
CREATE INDEX IF NOT EXISTS "user_resumes_user_id_idx"
    ON "public"."user_resumes" USING btree ("user_id", "updated_at" DESC);

-- Enable RLS
ALTER TABLE "public"."user_resumes" ENABLE ROW LEVEL SECURITY;

-- RLS policies - users can only access their own resumes
CREATE POLICY "select_own_user_resumes"
    ON "public"."user_resumes"
    FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "insert_own_user_resumes"
    ON "public"."user_resumes"
    FOR INSERT
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "update_own_user_resumes"
    ON "public"."user_resumes"
    FOR UPDATE
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "delete_own_user_resumes"
    ON "public"."user_resumes"
    FOR DELETE
    USING (auth.uid() = user_id);

-- Trigger to auto-update updated_at
CREATE OR REPLACE FUNCTION public.update_user_resumes_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS set_user_resumes_updated_at ON public.user_resumes;
CREATE TRIGGER set_user_resumes_updated_at
    BEFORE UPDATE ON public.user_resumes
    FOR EACH ROW
    EXECUTE FUNCTION public.update_user_resumes_updated_at();

COMMIT;
