-- User secrets: encrypted API keys and other user-scoped credentials
-- Allows users to persist secrets (e.g. OpenAI API key) encrypted at rest
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

-- === USER SECRETS TABLE ===
CREATE TABLE IF NOT EXISTS "public"."user_secrets" (
    "id" uuid DEFAULT gen_random_uuid() PRIMARY KEY,
    "user_id" uuid NOT NULL,
    "secret_key" text NOT NULL,
    "encrypted_value" jsonb NOT NULL,
    "provider" text,
    "metadata" jsonb DEFAULT '{}'::jsonb,
    "created_at" timestamptz NOT NULL DEFAULT now(),
    "updated_at" timestamptz NOT NULL DEFAULT now()
);

-- === CONSTRAINTS ===
ALTER TABLE "public"."user_secrets"
    ADD CONSTRAINT "user_secrets_user_id_fkey"
    FOREIGN KEY ("user_id") REFERENCES "public"."profiles"("id") ON DELETE CASCADE;

ALTER TABLE "public"."user_secrets"
    ADD CONSTRAINT "user_secrets_user_id_secret_key_unique"
    UNIQUE ("user_id", "secret_key");

-- === INDEXES ===
CREATE INDEX IF NOT EXISTS "user_secrets_user_id_idx"
    ON "public"."user_secrets" USING btree ("user_id");

-- === TRIGGERS ===
-- Reuse existing update_updated_at_column function
DROP TRIGGER IF EXISTS "update_user_secrets_updated_at" ON "public"."user_secrets";
CREATE TRIGGER "update_user_secrets_updated_at"
    BEFORE UPDATE ON "public"."user_secrets"
    FOR EACH ROW
    EXECUTE FUNCTION "public"."update_updated_at_column"();

-- === ROW LEVEL SECURITY ===
ALTER TABLE "public"."user_secrets" ENABLE ROW LEVEL SECURITY;

CREATE POLICY "select_own_secrets"
    ON "public"."user_secrets"
    FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "insert_own_secrets"
    ON "public"."user_secrets"
    FOR INSERT
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "update_own_secrets"
    ON "public"."user_secrets"
    FOR UPDATE
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "delete_own_secrets"
    ON "public"."user_secrets"
    FOR DELETE
    USING (auth.uid() = user_id);

COMMENT ON TABLE "public"."user_secrets" IS 'Encrypted user secrets (API keys, credentials) stored at rest';
COMMENT ON COLUMN "public"."user_secrets"."secret_key" IS 'Identifier for the secret, e.g. openai_api_key';
COMMENT ON COLUMN "public"."user_secrets"."encrypted_value" IS 'AES-GCM encrypted envelope {v, iv, ct}';
COMMENT ON COLUMN "public"."user_secrets"."provider" IS 'Service provider, e.g. openai';

COMMIT;
