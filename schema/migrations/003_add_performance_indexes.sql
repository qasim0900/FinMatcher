-- Migration: 003_add_performance_indexes.sql
-- Description: Add additional performance indexes for K-D Tree and spatial matching
-- Created: 2026-03-01
-- Author: FinMatcher Team

-- Create composite indexes for date-amount matching (K-D Tree optimization)
CREATE INDEX IF NOT EXISTS idx_transactions_date_amount 
ON transactions(date, amount);

CREATE INDEX IF NOT EXISTS idx_receipts_date_amount 
ON receipts(date, amount);

CREATE INDEX IF NOT EXISTS idx_emails_date_amount 
ON processed_emails(date, amount_numeric) 
WHERE amount_numeric IS NOT NULL;

-- Create indexes for text search
CREATE INDEX IF NOT EXISTS idx_transactions_description 
ON transactions USING gin(to_tsvector('english', description));

CREATE INDEX IF NOT EXISTS idx_receipts_description 
ON receipts USING gin(to_tsvector('english', description));

CREATE INDEX IF NOT EXISTS idx_emails_subject 
ON processed_emails USING gin(to_tsvector('english', subject));

-- Create indexes for merchant matching
CREATE INDEX IF NOT EXISTS idx_transactions_merchant 
ON transactions(merchant) 
WHERE merchant IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_receipts_merchant 
ON receipts(merchant) 
WHERE merchant IS NOT NULL;

-- Create index for match confidence filtering
CREATE INDEX IF NOT EXISTS idx_matches_confidence 
ON matches(match_confidence);

CREATE INDEX IF NOT EXISTS idx_matches_score 
ON matches(match_score DESC);

-- Add statement_name index for filtering
CREATE INDEX IF NOT EXISTS idx_transactions_statement 
ON transactions(statement_name) 
WHERE statement_name IS NOT NULL;

-- Record migration
INSERT INTO schema_migrations (version, name, description)
VALUES (3, '003_add_performance_indexes', 'Add performance indexes for spatial matching and text search')
ON CONFLICT (version) DO NOTHING;

-- Success message
DO $$
BEGIN
    RAISE NOTICE 'Migration 003: Performance indexes added successfully';
END $$;
