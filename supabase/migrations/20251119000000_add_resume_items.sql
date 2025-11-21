-- Resume item storage for generated resume snippets.
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

CREATE TABLE IF NOT EXISTS "public"."resume_items" (
    "id" uuid DEFAULT gen_random_uuid() PRIMARY KEY,
    "user_id" uuid NOT NULL,
    "project_name" text NOT NULL,
    "start_date" text,
    "end_date" text,
    "content" text NOT NULL,
    "bullets" jsonb NOT NULL DEFAULT '[]'::jsonb,
    "metadata" jsonb NOT NULL DEFAULT '{}'::jsonb,
    "source_path" text,
    "created_at" timestamptz NOT NULL DEFAULT now()
);

ALTER TABLE "public"."resume_items"
    ADD CONSTRAINT "resume_items_user_id_fkey"
    FOREIGN KEY ("user_id") REFERENCES "public"."profiles"("id") ON DELETE CASCADE;

CREATE INDEX IF NOT EXISTS "resume_items_user_id_idx"
    ON "public"."resume_items" USING btree ("user_id", "created_at" DESC);

ALTER TABLE "public"."resume_items" ENABLE ROW LEVEL SECURITY;

CREATE POLICY "select_own_resume_items"
    ON "public"."resume_items"
    FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "insert_own_resume_items"
    ON "public"."resume_items"
    FOR INSERT
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "delete_own_resume_items"
    ON "public"."resume_items"
    FOR DELETE
    USING (auth.uid() = user_id);

CREATE POLICY "update_own_resume_items"
    ON "public"."resume_items"
    FOR UPDATE
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

COMMIT;
