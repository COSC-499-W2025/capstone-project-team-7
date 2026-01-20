-- Project overrides for chronology corrections, comparison attributes, highlighted skills, role, evidence, and thumbnail
-- Allows users to customize project display and metadata beyond computed/scanned values
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

-- === PROJECT OVERRIDES TABLE ===
-- Stores user-defined overrides for project display and metadata
CREATE TABLE IF NOT EXISTS "public"."project_overrides" (
    "id" uuid DEFAULT gen_random_uuid() PRIMARY KEY,
    "project_id" uuid NOT NULL,
    "user_id" uuid NOT NULL,
    
    -- Chronology corrections (override computed dates)
    "start_date_override" date,
    "end_date_override" date,
    
    -- Role and evidence (user-written, encrypted at application layer)
    "role" text,
    "evidence" text[] DEFAULT '{}'::text[],
    
    -- Display customization
    "thumbnail_url" text,
    "highlighted_skills" text[] DEFAULT '{}'::text[],
    
    -- Comparison attributes (flexible key-value pairs for portfolio comparisons)
    "comparison_attributes" jsonb DEFAULT '{}'::jsonb,
    
    -- Custom ranking (override computed contribution score)
    "custom_rank" numeric,
    
    "created_at" timestamptz NOT NULL DEFAULT now(),
    "updated_at" timestamptz NOT NULL DEFAULT now()
);

-- === CONSTRAINTS ===
-- Foreign key to projects with cascade delete
ALTER TABLE "public"."project_overrides"
    ADD CONSTRAINT "project_overrides_project_id_fkey"
    FOREIGN KEY ("project_id") REFERENCES "public"."projects"("id") ON DELETE CASCADE;

-- Foreign key to profiles with cascade delete
ALTER TABLE "public"."project_overrides"
    ADD CONSTRAINT "project_overrides_user_id_fkey"
    FOREIGN KEY ("user_id") REFERENCES "public"."profiles"("id") ON DELETE CASCADE;

-- Ensure one override record per project
ALTER TABLE "public"."project_overrides"
    ADD CONSTRAINT "project_overrides_project_id_unique"
    UNIQUE ("project_id");

-- === INDEXES ===
-- Index for efficient project lookups
CREATE INDEX IF NOT EXISTS "project_overrides_project_id_idx"
    ON "public"."project_overrides" USING btree ("project_id");

-- Index for efficient user lookups
CREATE INDEX IF NOT EXISTS "project_overrides_user_id_idx"
    ON "public"."project_overrides" USING btree ("user_id");

-- === TRIGGERS ===
-- Automatically update the updated_at timestamp
-- Note: update_updated_at_column function already exists from user_configs migration
DROP TRIGGER IF EXISTS "update_project_overrides_updated_at" ON "public"."project_overrides";
CREATE TRIGGER "update_project_overrides_updated_at"
    BEFORE UPDATE ON "public"."project_overrides"
    FOR EACH ROW
    EXECUTE FUNCTION "public"."update_updated_at_column"();

-- === ROW LEVEL SECURITY ===
ALTER TABLE "public"."project_overrides" ENABLE ROW LEVEL SECURITY;

-- Users can read only their own overrides
CREATE POLICY "select_own_overrides"
    ON "public"."project_overrides"
    FOR SELECT
    USING (auth.uid() = user_id);

-- Users can insert their own overrides
CREATE POLICY "insert_own_overrides"
    ON "public"."project_overrides"
    FOR INSERT
    WITH CHECK (auth.uid() = user_id);

-- Users can update their own overrides
CREATE POLICY "update_own_overrides"
    ON "public"."project_overrides"
    FOR UPDATE
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

-- Users can delete their own overrides
CREATE POLICY "delete_own_overrides"
    ON "public"."project_overrides"
    FOR DELETE
    USING (auth.uid() = user_id);

-- === COMMENTS ===
COMMENT ON TABLE "public"."project_overrides" IS 'User-defined overrides for project display, chronology, and metadata';
COMMENT ON COLUMN "public"."project_overrides"."start_date_override" IS 'Override for project start date (chronology correction)';
COMMENT ON COLUMN "public"."project_overrides"."end_date_override" IS 'Override for project end date (chronology correction)';
COMMENT ON COLUMN "public"."project_overrides"."role" IS 'User role/title for this project (encrypted at app layer)';
COMMENT ON COLUMN "public"."project_overrides"."evidence" IS 'User-written evidence/accomplishments (encrypted at app layer)';
COMMENT ON COLUMN "public"."project_overrides"."thumbnail_url" IS 'Custom thumbnail URL (overrides project-level thumbnail)';
COMMENT ON COLUMN "public"."project_overrides"."highlighted_skills" IS 'Skills to highlight for this project';
COMMENT ON COLUMN "public"."project_overrides"."comparison_attributes" IS 'Custom key-value pairs for portfolio comparisons';
COMMENT ON COLUMN "public"."project_overrides"."custom_rank" IS 'Manual ranking override (0-100 scale)';

COMMIT;
