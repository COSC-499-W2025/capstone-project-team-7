-- Portfolio settings for public sharing and display preferences
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

-- === PORTFOLIO SETTINGS TABLE ===
CREATE TABLE IF NOT EXISTS "public"."portfolio_settings" (
    "id" uuid DEFAULT gen_random_uuid() PRIMARY KEY,
    "user_id" uuid NOT NULL,
    "is_public" boolean NOT NULL DEFAULT false,
    "share_token" text UNIQUE,
    "display_name" text,
    "bio" text,
    "show_heatmap" boolean NOT NULL DEFAULT true,
    "show_skills_timeline" boolean NOT NULL DEFAULT true,
    "show_top_projects" boolean NOT NULL DEFAULT true,
    "show_all_skills" boolean NOT NULL DEFAULT true,
    "showcase_count" integer NOT NULL DEFAULT 3,
    "created_at" timestamptz NOT NULL DEFAULT now(),
    "updated_at" timestamptz NOT NULL DEFAULT now()
);

-- === CONSTRAINTS ===
ALTER TABLE "public"."portfolio_settings"
    ADD CONSTRAINT "portfolio_settings_user_id_fkey"
    FOREIGN KEY ("user_id") REFERENCES "public"."profiles"("id") ON DELETE CASCADE;

ALTER TABLE "public"."portfolio_settings"
    ADD CONSTRAINT "portfolio_settings_user_id_unique"
    UNIQUE ("user_id");

ALTER TABLE "public"."portfolio_settings"
    ADD CONSTRAINT "portfolio_settings_showcase_count_check"
    CHECK (showcase_count >= 1 AND showcase_count <= 10);

-- === INDEXES ===
CREATE INDEX IF NOT EXISTS "portfolio_settings_user_id_idx"
    ON "public"."portfolio_settings" USING btree ("user_id");

CREATE INDEX IF NOT EXISTS "portfolio_settings_share_token_idx"
    ON "public"."portfolio_settings" USING btree ("share_token")
    WHERE share_token IS NOT NULL;

-- === TRIGGERS ===
DROP TRIGGER IF EXISTS "update_portfolio_settings_updated_at" ON "public"."portfolio_settings";
CREATE TRIGGER "update_portfolio_settings_updated_at"
    BEFORE UPDATE ON "public"."portfolio_settings"
    FOR EACH ROW
    EXECUTE FUNCTION "public"."update_updated_at_column"();

-- === ROW LEVEL SECURITY ===
ALTER TABLE "public"."portfolio_settings" ENABLE ROW LEVEL SECURITY;

-- Owner can do everything
CREATE POLICY "select_own_portfolio_settings"
    ON "public"."portfolio_settings"
    FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "insert_own_portfolio_settings"
    ON "public"."portfolio_settings"
    FOR INSERT
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "update_own_portfolio_settings"
    ON "public"."portfolio_settings"
    FOR UPDATE
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "delete_own_portfolio_settings"
    ON "public"."portfolio_settings"
    FOR DELETE
    USING (auth.uid() = user_id);

-- Public read access for published portfolios (via share_token lookup)
CREATE POLICY "public_read_published_portfolios"
    ON "public"."portfolio_settings"
    FOR SELECT
    USING (is_public = true);

COMMENT ON TABLE "public"."portfolio_settings" IS 'User portfolio display settings and public sharing configuration';

COMMIT;
