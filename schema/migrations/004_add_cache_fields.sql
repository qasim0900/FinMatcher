-- Migration: 004_add_cache_fields.sql
-- Description: Add cache-related fields to processed_emails table
-- Created: 2026-03-01
-- Author: FinMatcher Team

-- Add md5_hash column for deduplication
ALTER TABLE processed_emails 
ADD COLUMN IF NOT EXISTS md5_hash TEXT;

-- Add account_email column
ALTER TABLE processed_emails 
ADD COLUMN IF NOT EXISTS account_email TEXT;

-- Add folder column
ALTER TABLE processed_emails 
ADD COLUMN IF NOT EXISTS folder TEXT DEFAULT 'INBOX';

-- Add is_financial column
ALTER TABLE processed_emails 
ADD COLUMN IF NOT EXISTS is_financial BOOLEAN DEFAULT FALSE;

-- Add attachment_file column
ALTER TABLE processed_emails 
ADD COLUMN IF NOT EXISTS attachment_file BOOLEAN DEFAULT FALSE;

-- Add processed_timestamp column
ALTER TABLE processed_emails 
ADD COLUMN IF NOT EXISTS processed_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP;

-- Create unique index on md5_hash
CREATE UNIQUE INDEX IF NOT EXISTS idx_md5_hash 
ON processed_emails(md5_hash);

-- Create index on account_email
CREATE INDEX IF NOT EXISTS idx_account_email 
ON processed_emails(account_email);

-- Create index on is_financial
CREATE INDEX IF NOT EXISTS idx_is_financial 
ON processed_emails(is_financial);

-- Record migration
INSERT INTO schema_migrations (version, name, description)
VALUES (4, '004_add_cache_fields', 'Add cache-related fields to processed_emails table')
ON CONFLICT (version) DO NOTHING;

-- Success message
DO $$
BEGIN
    RAISE NOTICE 'Migration 004: Cache fields added successfully';
END $$;
