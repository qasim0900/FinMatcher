-- Migration: 002_add_optimization_fields.sql
-- Description: Add optimization fields for performance improvements
-- Created: 2026-03-01
-- Author: FinMatcher Team

-- Add attachment_file column to processed_emails
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name='processed_emails' AND column_name='attachment_file'
    ) THEN
        ALTER TABLE processed_emails ADD COLUMN attachment_file BOOLEAN DEFAULT FALSE;
        RAISE NOTICE 'Added attachment_file column';
    ELSE
        RAISE NOTICE 'attachment_file column already exists';
    END IF;
END $$;

-- Add attachment_file_path column
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name='processed_emails' AND column_name='attachment_file_path'
    ) THEN
        ALTER TABLE processed_emails ADD COLUMN attachment_file_path TEXT;
        RAISE NOTICE 'Added attachment_file_path column';
    ELSE
        RAISE NOTICE 'attachment_file_path column already exists';
    END IF;
END $$;

-- Add attachment_image_path column
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name='processed_emails' AND column_name='attachment_image_path'
    ) THEN
        ALTER TABLE processed_emails ADD COLUMN attachment_image_path TEXT;
        RAISE NOTICE 'Added attachment_image_path column';
    ELSE
        RAISE NOTICE 'attachment_image_path column already exists';
    END IF;
END $$;

-- Create optimization indexes
CREATE INDEX IF NOT EXISTS idx_emails_attachment_file 
ON processed_emails(attachment_file) 
WHERE attachment_file = TRUE;

CREATE INDEX IF NOT EXISTS idx_emails_attachment_file_path 
ON processed_emails(attachment_file_path) 
WHERE attachment_file_path IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_emails_attachment_image 
ON processed_emails(attachment_image_path) 
WHERE attachment_image_path IS NOT NULL;

-- Add amount_numeric column to processed_emails for faster matching
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name='processed_emails' AND column_name='amount_numeric'
    ) THEN
        ALTER TABLE processed_emails ADD COLUMN amount_numeric DECIMAL(10, 2);
        RAISE NOTICE 'Added amount_numeric column';
    ELSE
        RAISE NOTICE 'amount_numeric column already exists';
    END IF;
END $$;

-- Create index for amount-based matching
CREATE INDEX IF NOT EXISTS idx_emails_amount_numeric 
ON processed_emails(amount_numeric) 
WHERE amount_numeric IS NOT NULL;

-- Record migration
INSERT INTO schema_migrations (version, name, description)
VALUES (2, '002_add_optimization_fields', 'Add optimization fields for performance improvements')
ON CONFLICT (version) DO NOTHING;

-- Success message
DO $$
BEGIN
    RAISE NOTICE 'Migration 002: Optimization fields added successfully';
END $$;
