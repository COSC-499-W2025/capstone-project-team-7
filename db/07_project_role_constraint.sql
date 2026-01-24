-- Migration: Add CHECK constraint for allowed role values on project_overrides.role
-- This enforces that role values are one of: author, contributor, lead, maintainer, reviewer

-- First, update any invalid existing role values to NULL
UPDATE public.project_overrides 
SET role = NULL 
WHERE role IS NOT NULL 
  AND role NOT IN ('author', 'contributor', 'lead', 'maintainer', 'reviewer');

-- Add CHECK constraint to enforce valid role values
-- Note: NULL is allowed (role is optional)
ALTER TABLE public.project_overrides
DROP CONSTRAINT IF EXISTS project_overrides_role_check;

ALTER TABLE public.project_overrides
ADD CONSTRAINT project_overrides_role_check 
CHECK (role IS NULL OR role IN ('author', 'contributor', 'lead', 'maintainer', 'reviewer'));

-- Add comment documenting the allowed values
COMMENT ON COLUMN public.project_overrides.role IS 
'User role in the project. Allowed values: author, contributor, lead, maintainer, reviewer. Auto-inferred on scan (>=80% commits = author, else contributor). Can be manually overridden.';
