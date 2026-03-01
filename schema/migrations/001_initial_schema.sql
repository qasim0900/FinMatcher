-- Migration: 001_initial_schema.sql
-- Description: Initial database schema for FinMatcher
-- Created: 2026-03-01
-- Author: FinMatcher Team

-- Create migrations tracking table
CREATE TABLE IF NOT EXISTS schema_migrations (
    version INTEGER PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    description TEXT
);

-- Create processed_emails table
CREATE TABLE IF NOT EXISTS processed_emails (
    message_id VARCHAR(255) PRIMARY KEY,
    subject TEXT,
    sender VARCHAR(255),
    date TIMESTAMP,
    body TEXT,
    has_attachment BOOLEAN DEFAULT FALSE,
    processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create transactions table
CREATE TABLE IF NOT EXISTS transactions (
    id SERIAL PRIMARY KEY,
    transaction_id VARCHAR(255) UNIQUE,
    date DATE NOT NULL,
    description TEXT,
    amount DECIMAL(10, 2) NOT NULL,
    merchant VARCHAR(255),
    category VARCHAR(100),
    statement_name VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create receipts table
CREATE TABLE IF NOT EXISTS receipts (
    id SERIAL PRIMARY KEY,
    receipt_id VARCHAR(255) UNIQUE,
    email_id VARCHAR(255) REFERENCES processed_emails(message_id),
    date DATE,
    amount DECIMAL(10, 2),
    merchant VARCHAR(255),
    description TEXT,
    attachment_path TEXT,
    ocr_text TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create matches table
CREATE TABLE IF NOT EXISTS matches (
    id SERIAL PRIMARY KEY,
    transaction_id INTEGER REFERENCES transactions(id),
    receipt_id INTEGER REFERENCES receipts(id),
    match_score DECIMAL(5, 4),
    match_confidence VARCHAR(50),
    match_method VARCHAR(100),
    matched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(transaction_id, receipt_id)
);

-- Create matching_statistics table
CREATE TABLE IF NOT EXISTS matching_statistics (
    id SERIAL PRIMARY KEY,
    run_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    total_transactions INTEGER,
    total_receipts INTEGER,
    exact_matches INTEGER,
    high_confidence_matches INTEGER,
    low_confidence_matches INTEGER,
    unmatched_transactions INTEGER,
    unmatched_receipts INTEGER,
    processing_time_seconds DECIMAL(10, 2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create basic indexes
CREATE INDEX IF NOT EXISTS idx_emails_date ON processed_emails(date);
CREATE INDEX IF NOT EXISTS idx_emails_sender ON processed_emails(sender);
CREATE INDEX IF NOT EXISTS idx_transactions_date ON transactions(date);
CREATE INDEX IF NOT EXISTS idx_transactions_amount ON transactions(amount);
CREATE INDEX IF NOT EXISTS idx_receipts_date ON receipts(date);
CREATE INDEX IF NOT EXISTS idx_receipts_amount ON receipts(amount);
CREATE INDEX IF NOT EXISTS idx_matches_transaction ON matches(transaction_id);
CREATE INDEX IF NOT EXISTS idx_matches_receipt ON matches(receipt_id);

-- Record migration
INSERT INTO schema_migrations (version, name, description)
VALUES (1, '001_initial_schema', 'Initial database schema with core tables')
ON CONFLICT (version) DO NOTHING;

-- Success message
DO $$
BEGIN
    RAISE NOTICE 'Migration 001: Initial schema created successfully';
END $$;
