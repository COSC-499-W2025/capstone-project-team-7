-- Job Board feature: jobs cache, user job tracking, scrape audit trail
BEGIN;

-- === JOBS TABLE (shared cache, deduplicated by external_id + source) ===
CREATE TABLE IF NOT EXISTS "public"."jobs" (
    "id" uuid DEFAULT gen_random_uuid() PRIMARY KEY,
    "external_id" text NOT NULL,
    "source" text NOT NULL CHECK ("source" IN ('linkedin', 'indeed')),
    "title" text NOT NULL,
    "company" text NOT NULL,
    "location" text,
    "is_remote" boolean DEFAULT false,
    "job_type" text CHECK ("job_type" IS NULL OR "job_type" IN ('full-time', 'part-time', 'internship', 'contract')),
    "experience_level" text CHECK ("experience_level" IS NULL OR "experience_level" IN ('entry', 'mid', 'senior')),
    "salary_min" integer,
    "salary_max" integer,
    "salary_currency" text DEFAULT 'USD',
    "description" text,
    "url" text,
    "company_logo_url" text,
    "skills" text[] DEFAULT '{}',
    "posted_at" timestamptz,
    "scraped_at" timestamptz NOT NULL DEFAULT now(),
    "raw_data" jsonb DEFAULT '{}'::jsonb,
    "created_at" timestamptz NOT NULL DEFAULT now(),
    "updated_at" timestamptz NOT NULL DEFAULT now(),

    CONSTRAINT "jobs_external_id_source_unique" UNIQUE ("external_id", "source")
);

CREATE INDEX IF NOT EXISTS "jobs_source_idx" ON "public"."jobs" USING btree ("source");
CREATE INDEX IF NOT EXISTS "jobs_posted_at_idx" ON "public"."jobs" USING btree ("posted_at" DESC NULLS LAST);
CREATE INDEX IF NOT EXISTS "jobs_skills_idx" ON "public"."jobs" USING gin ("skills");
CREATE INDEX IF NOT EXISTS "jobs_company_idx" ON "public"."jobs" USING btree ("company");
CREATE INDEX IF NOT EXISTS "jobs_location_idx" ON "public"."jobs" USING btree ("location");

-- === USER_JOBS TABLE (per-user bookmarks + application tracking) ===
CREATE TABLE IF NOT EXISTS "public"."user_jobs" (
    "id" uuid DEFAULT gen_random_uuid() PRIMARY KEY,
    "user_id" uuid NOT NULL,
    "job_id" uuid NOT NULL REFERENCES "public"."jobs"("id") ON DELETE CASCADE,
    "status" text NOT NULL DEFAULT 'saved' CHECK ("status" IN ('saved', 'applied', 'interviewing', 'offer', 'rejected')),
    "keyword_match_score" real,
    "ai_match_score" real,
    "ai_match_summary" text,
    "matched_skills" text[] DEFAULT '{}',
    "missing_skills" text[] DEFAULT '{}',
    "notes" text,
    "applied_at" timestamptz,
    "created_at" timestamptz NOT NULL DEFAULT now(),
    "updated_at" timestamptz NOT NULL DEFAULT now(),

    CONSTRAINT "user_jobs_user_job_unique" UNIQUE ("user_id", "job_id")
);

ALTER TABLE "public"."user_jobs"
    ADD CONSTRAINT "user_jobs_user_id_fkey"
    FOREIGN KEY ("user_id") REFERENCES "public"."profiles"("id") ON DELETE CASCADE;

CREATE INDEX IF NOT EXISTS "user_jobs_user_id_idx" ON "public"."user_jobs" USING btree ("user_id");
CREATE INDEX IF NOT EXISTS "user_jobs_status_idx" ON "public"."user_jobs" USING btree ("user_id", "status");
CREATE INDEX IF NOT EXISTS "user_jobs_keyword_score_idx" ON "public"."user_jobs" USING btree ("user_id", "keyword_match_score" DESC NULLS LAST);

-- === JOB_SCRAPE_RUNS TABLE (audit trail for Apify scrape operations) ===
CREATE TABLE IF NOT EXISTS "public"."job_scrape_runs" (
    "id" uuid DEFAULT gen_random_uuid() PRIMARY KEY,
    "user_id" uuid NOT NULL REFERENCES "public"."profiles"("id") ON DELETE CASCADE,
    "source" text NOT NULL CHECK ("source" IN ('linkedin', 'indeed')),
    "actor_id" text NOT NULL,
    "run_id" text,
    "status" text NOT NULL DEFAULT 'pending' CHECK ("status" IN ('pending', 'running', 'completed', 'failed')),
    "search_query" text,
    "location" text,
    "jobs_found" integer DEFAULT 0,
    "jobs_new" integer DEFAULT 0,
    "error_message" text,
    "started_at" timestamptz NOT NULL DEFAULT now(),
    "completed_at" timestamptz,
    "created_at" timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS "job_scrape_runs_user_idx" ON "public"."job_scrape_runs" USING btree ("user_id");

-- === TRIGGERS (reuse existing update_updated_at_column function) ===
DROP TRIGGER IF EXISTS "update_jobs_updated_at" ON "public"."jobs";
CREATE TRIGGER "update_jobs_updated_at"
    BEFORE UPDATE ON "public"."jobs"
    FOR EACH ROW
    EXECUTE FUNCTION "public"."update_updated_at_column"();

DROP TRIGGER IF EXISTS "update_user_jobs_updated_at" ON "public"."user_jobs";
CREATE TRIGGER "update_user_jobs_updated_at"
    BEFORE UPDATE ON "public"."user_jobs"
    FOR EACH ROW
    EXECUTE FUNCTION "public"."update_updated_at_column"();

-- === ROW LEVEL SECURITY ===

-- jobs: All authenticated users can read (shared cache). Authenticated users can insert/update (backend inserts on behalf).
ALTER TABLE "public"."jobs" ENABLE ROW LEVEL SECURITY;

CREATE POLICY "select_jobs_authenticated"
    ON "public"."jobs" FOR SELECT
    USING (auth.role() = 'authenticated');

CREATE POLICY "insert_jobs_authenticated"
    ON "public"."jobs" FOR INSERT
    WITH CHECK (auth.role() = 'authenticated');

CREATE POLICY "update_jobs_authenticated"
    ON "public"."jobs" FOR UPDATE
    USING (auth.role() = 'authenticated');

-- user_jobs: Users can CRUD only their own rows
ALTER TABLE "public"."user_jobs" ENABLE ROW LEVEL SECURITY;

CREATE POLICY "select_own_user_jobs"
    ON "public"."user_jobs" FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "insert_own_user_jobs"
    ON "public"."user_jobs" FOR INSERT
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "update_own_user_jobs"
    ON "public"."user_jobs" FOR UPDATE
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "delete_own_user_jobs"
    ON "public"."user_jobs" FOR DELETE
    USING (auth.uid() = user_id);

-- job_scrape_runs: Users can read/insert/update only their own rows
ALTER TABLE "public"."job_scrape_runs" ENABLE ROW LEVEL SECURITY;

CREATE POLICY "select_own_scrape_runs"
    ON "public"."job_scrape_runs" FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "insert_own_scrape_runs"
    ON "public"."job_scrape_runs" FOR INSERT
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "update_own_scrape_runs"
    ON "public"."job_scrape_runs" FOR UPDATE
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

COMMIT;
