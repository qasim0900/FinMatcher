-- Migration: 005_fix_column_names.sql
-- Description: Fix column name mismatches between schema and cache_manager
-- Created: 2026-03-01
-- Author: FinMatcher Team

-- Add has_attachments column (cache_manager expects this name)
ALTER TABLE processed_emails 
ADD COLUMN IF NOT EXISTS has_attachments BOOLEAN DEFAULT FALSE;

-- Copy data from has_attachment to has_attachments if has_attachment exists
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.columns 
               WHERE table_name='processed_emails' AND column_name='has_attachment') THEN
        UPDATE processed_emails SET has_attachments = has_attachment WHERE has_attachment IS NOT NULL;
    END IF;
END $$;

-- Copy data from attachment_file to has_attachments if attachment_file exists
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.columns 
               WHERE table_name='processed_emails' AND column_name='attachment_file') THEN
        UPDATE processed_emails SET has_attachments = attachment_file WHERE attachment_file IS NOT NULL;
    END IF;
END $$;

-- Create index on has_attachments
CREATE INDEX IF NOT EXISTS idx_has_attachments 
ON processed_emails(has_attachments);

-- Record migration
INSERT INTO schema_migrations (version, name, description)
VALUES (5, '005_fix_column_names', 'Fix column name mismatches for cache_manager compatibility')
ON CONFLICT (version) DO NOTHING;

-- Success message
DO $$
BEGIN
    RAISE NOTICE 'Migration 005: Column names fixed successfully';
END $$;
