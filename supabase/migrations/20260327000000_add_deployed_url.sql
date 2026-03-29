-- Add deployed_url column to portfolio_settings for tracking Vercel deployments
ALTER TABLE "public"."portfolio_settings"
    ADD COLUMN IF NOT EXISTS "deployed_url" text;
