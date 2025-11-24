-- Cleanup unused legacy tables
BEGIN;

-- Drop legacy consents table (app uses consents_v1 instead)
DROP TABLE IF EXISTS public.consents;

-- Drop unused uploads table (not referenced by application code)
DROP TABLE IF EXISTS public.uploads;

COMMIT;
