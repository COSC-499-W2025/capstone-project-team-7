-- Add persisted projects ranking mode preference to user selections
BEGIN;

ALTER TABLE public.user_selections
ADD COLUMN IF NOT EXISTS sort_mode text NOT NULL DEFAULT 'recency';

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'user_selections_sort_mode_check'
    ) THEN
        ALTER TABLE public.user_selections
        ADD CONSTRAINT user_selections_sort_mode_check
        CHECK (sort_mode IN ('contribution', 'recency'));
    END IF;
END
$$;

COMMENT ON COLUMN public.user_selections.sort_mode
IS 'Projects ranking mode preference: contribution or recency';

COMMIT;
