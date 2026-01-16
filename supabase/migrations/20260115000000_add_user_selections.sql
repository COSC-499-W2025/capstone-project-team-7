-- User selections for project/skill ordering and showcase preferences
-- Stores custom ordering and selection state for portfolio display
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

-- === USER SELECTIONS TABLE ===
-- Stores user preferences for project/skill ordering and showcase selection
CREATE TABLE IF NOT EXISTS "public"."user_selections" (
    "id" uuid DEFAULT gen_random_uuid() PRIMARY KEY,
    "user_id" uuid NOT NULL,
    "project_order" text[] DEFAULT '{}'::text[],
    "skill_order" text[] DEFAULT '{}'::text[],
    "selected_project_ids" text[] DEFAULT '{}'::text[],
    "selected_skill_ids" text[] DEFAULT '{}'::text[],
    "created_at" timestamptz NOT NULL DEFAULT now(),
    "updated_at" timestamptz NOT NULL DEFAULT now()
);

-- === CONSTRAINTS ===
-- Foreign key to profiles with cascade delete
ALTER TABLE "public"."user_selections"
    ADD CONSTRAINT "user_selections_user_id_fkey"
    FOREIGN KEY ("user_id") REFERENCES "public"."profiles"("id") ON DELETE CASCADE;

-- Ensure one selection record per user
ALTER TABLE "public"."user_selections"
    ADD CONSTRAINT "user_selections_user_id_unique"
    UNIQUE ("user_id");

-- === INDEXES ===
-- Index for efficient user lookups
CREATE INDEX IF NOT EXISTS "user_selections_user_id_idx"
    ON "public"."user_selections" USING btree ("user_id");

-- === TRIGGERS ===
-- Automatically update the updated_at timestamp
-- Note: update_updated_at_column function already exists from user_configs migration
DROP TRIGGER IF EXISTS "update_user_selections_updated_at" ON "public"."user_selections";
CREATE TRIGGER "update_user_selections_updated_at"
    BEFORE UPDATE ON "public"."user_selections"
    FOR EACH ROW
    EXECUTE FUNCTION "public"."update_updated_at_column"();

-- === ROW LEVEL SECURITY ===
ALTER TABLE "public"."user_selections" ENABLE ROW LEVEL SECURITY;

-- Users can read only their own selections
CREATE POLICY "select_own_selections"
    ON "public"."user_selections"
    FOR SELECT
    USING (auth.uid() = user_id);

-- Users can insert their own selections
CREATE POLICY "insert_own_selections"
    ON "public"."user_selections"
    FOR INSERT
    WITH CHECK (auth.uid() = user_id);

-- Users can update their own selections
CREATE POLICY "update_own_selections"
    ON "public"."user_selections"
    FOR UPDATE
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

-- Users can delete their own selections
CREATE POLICY "delete_own_selections"
    ON "public"."user_selections"
    FOR DELETE
    USING (auth.uid() = user_id);

-- === COMMENTS ===
COMMENT ON TABLE "public"."user_selections" IS 'User preferences for project/skill ordering and showcase selection';
COMMENT ON COLUMN "public"."user_selections"."project_order" IS 'Ordered array of project IDs for display';
COMMENT ON COLUMN "public"."user_selections"."skill_order" IS 'Ordered array of skill names for display';
COMMENT ON COLUMN "public"."user_selections"."selected_project_ids" IS 'Array of project IDs selected for showcase';
COMMENT ON COLUMN "public"."user_selections"."selected_skill_ids" IS 'Array of skill names selected for showcase';

COMMIT;
