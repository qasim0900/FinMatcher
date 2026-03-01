-- ============================================================================
-- FinMatcher - Complete Database Schema
-- ============================================================================
-- Purpose: Production-ready schema for 200k+ email processing
-- Optimizations: Indexes, constraints, and performance tuning included
-- ============================================================================

-- Drop existing tables if needed (use with caution in production)
-- DROP TABLE IF EXISTS matches CASCADE;
-- DROP TABLE IF EXISTS receipts CASCADE;
-- DROP TABLE IF EXISTS transactions CASCADE;
-- DROP TABLE IF EXISTS processed_emails CASCADE;
-- DROP TABLE IF EXISTS matching_statistics CASCADE;

-- ============================================================================
-- TABLE 1: PROCESSED_EMAILS
-- ============================================================================
-- Purpose: Store all processed emails with attachment flags
-- Optimization: Indexes on attachment_file, date, and financial_score

CREATE TABLE IF NOT EXISTS processed_emails (
    id SERIAL PRIMARY KEY,
    message_id VARCHAR(255) UNIQUE NOT NULL,
    subject TEXT,
    sender VARCHAR(500),
    date TIMESTAMP WITH TIME ZONE,
    body_text TEXT,
    
    -- Attachment tracking
    has_attachment BOOLEAN DEFAULT FALSE,
    attachment_file BOOLEAN DEFAULT FALSE,  -- TRUE if file downloaded
    attachment_filename TEXT,
    attachment_count INTEGER DEFAULT 0,
    
    -- Processing metadata
    processing_status VARCHAR(50) DEFAULT 'pending',
    financial_score FLOAT DEFAULT 0.0,
    
    -- Derived fields (vectorized processing)
    date_processed DATE,
    sender_domain VARCHAR(255),
    subject_length INTEGER,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Performance Indexes for processed_emails
CREATE INDEX IF NOT EXISTS idx_processed_emails_attachment 
    ON processed_emails(has_attachment) 
    WHERE has_attachment = TRUE;

CREATE INDEX IF NOT EXISTS idx_processed_emails_attachment_file 
    ON processed_emails(attachment_file) 
    WHERE attachment_file = TRUE;

CREATE INDEX IF NOT EXISTS idx_processed_emails_date 
    ON processed_emails(date_processed);

CREATE INDEX IF NOT EXISTS idx_processed_emails_date_time 
    ON processed_emails(date);

CREATE INDEX IF NOT EXISTS idx_processed_emails_financial_score 
    ON processed_emails(financial_score DESC);

CREATE INDEX IF NOT EXISTS idx_processed_emails_status 
    ON processed_emails(processing_status);

CREATE INDEX IF NOT EXISTS idx_processed_emails_sender_domain 
    ON processed_emails(sender_domain);

-- Composite index for K-D Tree matching
CREATE INDEX IF NOT EXISTS idx_processed_emails_date_amount 
    ON processed_emails(date_processed, financial_score);

-- ============================================================================
-- TABLE 2: TRANSACTIONS
-- ============================================================================
-- Purpose: Store bank/credit card statement transactions
-- Source: Excel/PDF statements uploaded by user

CREATE TABLE IF NOT EXISTS transactions (
    id SERIAL PRIMARY KEY,
    
    -- Transaction details
    statement_source VARCHAR(100),  -- e.g., "Amex", "Chase", "Meriwest"
    transaction_date DATE NOT NULL,
    description TEXT,
    amount DECIMAL(15, 2) NOT NULL,
    currency VARCHAR(10) DEFAULT 'USD',
    
    -- Categorization
    category VARCHAR(100),
    merchant_name VARCHAR(255),
    
    -- Matching status
    is_matched BOOLEAN DEFAULT FALSE,
    match_confidence DECIMAL(5, 2),
    
    -- Metadata
    raw_text TEXT,  -- Original text from statement
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Performance Indexes for transactions
CREATE INDEX IF NOT EXISTS idx_transactions_date 
    ON transactions(transaction_date);

CREATE INDEX IF NOT EXISTS idx_transactions_amount 
    ON transactions(amount);

CREATE INDEX IF NOT EXISTS idx_transactions_source 
    ON transactions(statement_source);

CREATE INDEX IF NOT EXISTS idx_transactions_matched 
    ON transactions(is_matched);

-- Composite index for K-D Tree spatial matching
CREATE INDEX IF NOT EXISTS idx_transactions_date_amount 
    ON transactions(transaction_date, amount);

CREATE INDEX IF NOT EXISTS idx_transactions_merchant 
    ON transactions(merchant_name);

-- ============================================================================
-- TABLE 3: RECEIPTS
-- ============================================================================
-- Purpose: Store extracted receipt data from email attachments
-- Source: OCR processing of PDF/image attachments

CREATE TABLE IF NOT EXISTS receipts (
    id SERIAL PRIMARY KEY,
    
    -- Link to email
    email_id VARCHAR(255) REFERENCES processed_emails(message_id) ON DELETE CASCADE,
    
    -- Receipt details (extracted via OCR)
    vendor_name TEXT,
    transaction_date DATE,
    amount DECIMAL(15, 2),
    currency VARCHAR(10) DEFAULT 'USD',
    
    -- Additional extracted fields
    invoice_number VARCHAR(100),
    order_number VARCHAR(100),
    category VARCHAR(100),
    
    -- OCR metadata
    raw_text TEXT,  -- Full OCR extracted text
    ocr_confidence FLOAT,  -- OCR accuracy score
    extraction_method VARCHAR(50),  -- 'tesseract', 'google_vision', 'deepseek'
    
    -- Matching status
    is_matched BOOLEAN DEFAULT FALSE,
    match_confidence DECIMAL(5, 2),
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Performance Indexes for receipts
CREATE INDEX IF NOT EXISTS idx_receipts_email_id 
    ON receipts(email_id);

CREATE INDEX IF NOT EXISTS idx_receipts_date 
    ON receipts(transaction_date);

CREATE INDEX IF NOT EXISTS idx_receipts_amount 
    ON receipts(amount);

CREATE INDEX IF NOT EXISTS idx_receipts_vendor 
    ON receipts(vendor_name);

CREATE INDEX IF NOT EXISTS idx_receipts_matched 
    ON receipts(is_matched);

-- Composite index for K-D Tree matching
CREATE INDEX IF NOT EXISTS idx_receipts_date_amount 
    ON receipts(transaction_date, amount);

-- ============================================================================
-- TABLE 4: MATCHES
-- ============================================================================
-- Purpose: Store matching results between transactions and receipts
-- Algorithm: K-D Tree spatial matching + fuzzy string matching

CREATE TABLE IF NOT EXISTS matches (
    id SERIAL PRIMARY KEY,
    
    -- Foreign keys
    transaction_id INTEGER REFERENCES transactions(id) ON DELETE CASCADE,
    receipt_id INTEGER REFERENCES receipts(id) ON DELETE CASCADE,
    
    -- Matching scores
    confidence_score DECIMAL(5, 2) NOT NULL,  -- 0.00 to 100.00
    date_similarity DECIMAL(5, 2),  -- Date match score
    amount_similarity DECIMAL(5, 2),  -- Amount match score
    vendor_similarity DECIMAL(5, 2),  -- Vendor name match score
    
    -- Match metadata
    match_type VARCHAR(50),  -- 'exact', 'fuzzy', 'manual'
    match_algorithm VARCHAR(50),  -- 'kd_tree', 'bloom_filter', 'manual'
    
    -- Status
    is_verified BOOLEAN DEFAULT FALSE,  -- User verification
    verification_notes TEXT,
    
    -- Timestamps
    match_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    verified_date TIMESTAMP,
    
    -- Ensure unique matches
    UNIQUE(transaction_id, receipt_id)
);

-- Performance Indexes for matches
CREATE INDEX IF NOT EXISTS idx_matches_transaction 
    ON matches(transaction_id);

CREATE INDEX IF NOT EXISTS idx_matches_receipt 
    ON matches(receipt_id);

CREATE INDEX IF NOT EXISTS idx_matches_confidence 
    ON matches(confidence_score DESC);

CREATE INDEX IF NOT EXISTS idx_matches_verified 
    ON matches(is_verified);

CREATE INDEX IF NOT EXISTS idx_matches_type 
    ON matches(match_type);

-- ============================================================================
-- TABLE 5: MATCHING_STATISTICS
-- ============================================================================
-- Purpose: Track performance metrics for each processing run
-- Use: Performance monitoring and optimization analysis

CREATE TABLE IF NOT EXISTS matching_statistics (
    id SERIAL PRIMARY KEY,
    
    -- Run metadata
    run_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    run_type VARCHAR(50),  -- 'full', 'incremental', 'test'
    
    -- Email processing stats
    total_emails_fetched INTEGER DEFAULT 0,
    total_emails_processed INTEGER DEFAULT 0,
    total_emails_with_attachments INTEGER DEFAULT 0,
    
    -- Transaction stats
    total_transactions INTEGER DEFAULT 0,
    total_receipts INTEGER DEFAULT 0,
    
    -- Matching stats
    total_matches INTEGER DEFAULT 0,
    exact_matches INTEGER DEFAULT 0,
    fuzzy_matches INTEGER DEFAULT 0,
    unmatched_transactions INTEGER DEFAULT 0,
    unmatched_receipts INTEGER DEFAULT 0,
    
    -- Performance metrics
    processing_time_seconds INTEGER,
    gmail_filtering_time_seconds INTEGER,
    download_time_seconds INTEGER,
    ocr_time_seconds INTEGER,
    matching_time_seconds INTEGER,
    excel_generation_time_seconds INTEGER,
    
    -- Efficiency metrics
    match_rate DECIMAL(5, 2),  -- Percentage of successful matches
    average_confidence DECIMAL(5, 2),
    
    -- Resource usage
    peak_memory_mb INTEGER,
    cpu_usage_percent DECIMAL(5, 2),
    
    -- Notes
    notes TEXT
);

-- Performance Indexes for matching_statistics
CREATE INDEX IF NOT EXISTS idx_statistics_run_date 
    ON matching_statistics(run_date DESC);

CREATE INDEX IF NOT EXISTS idx_statistics_run_type 
    ON matching_statistics(run_type);

-- ============================================================================
-- TABLE 6: BLOOM_FILTER_CACHE (Optional - For Deduplication)
-- ============================================================================
-- Purpose: Store Bloom filter state for duplicate detection
-- Note: Can be implemented in-memory, but persistent storage helps

CREATE TABLE IF NOT EXISTS bloom_filter_cache (
    id SERIAL PRIMARY KEY,
    email_hash VARCHAR(64) UNIQUE NOT NULL,  -- SHA-256 hash of email content
    message_id VARCHAR(255),
    processed_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Index for fast hash lookup
CREATE INDEX IF NOT EXISTS idx_bloom_filter_hash 
    ON bloom_filter_cache(email_hash);

-- ============================================================================
-- VIEWS FOR REPORTING
-- ============================================================================

-- View 1: Matched Transactions with Receipt Details
CREATE OR REPLACE VIEW vw_matched_transactions AS
SELECT 
    t.id AS transaction_id,
    t.transaction_date,
    t.description AS transaction_description,
    t.amount AS transaction_amount,
    t.statement_source,
    r.vendor_name,
    r.invoice_number,
    r.order_number,
    pe.subject AS email_subject,
    pe.sender AS email_sender,
    pe.attachment_filename,
    m.confidence_score,
    m.match_type,
    m.is_verified
FROM transactions t
INNER JOIN matches m ON t.id = m.transaction_id
INNER JOIN receipts r ON m.receipt_id = r.id
INNER JOIN processed_emails pe ON r.email_id = pe.message_id
ORDER BY t.transaction_date DESC;

-- View 2: Unmatched Transactions
CREATE OR REPLACE VIEW vw_unmatched_transactions AS
SELECT 
    t.id,
    t.transaction_date,
    t.description,
    t.amount,
    t.statement_source,
    t.merchant_name
FROM transactions t
WHERE t.is_matched = FALSE
ORDER BY t.transaction_date DESC;

-- View 3: Processing Summary
CREATE OR REPLACE VIEW vw_processing_summary AS
SELECT 
    run_date,
    total_emails_processed,
    total_matches,
    match_rate,
    processing_time_seconds,
    ROUND(processing_time_seconds / 60.0, 2) AS processing_time_minutes
FROM matching_statistics
ORDER BY run_date DESC;

-- ============================================================================
-- FUNCTIONS FOR AUTOMATION
-- ============================================================================

-- Function 1: Update timestamp on record modification
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply trigger to tables
CREATE TRIGGER update_processed_emails_updated_at
    BEFORE UPDATE ON processed_emails
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_transactions_updated_at
    BEFORE UPDATE ON transactions
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_receipts_updated_at
    BEFORE UPDATE ON receipts
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- INITIAL DATA VALIDATION
-- ============================================================================

-- Check if tables were created successfully
DO $$
DECLARE
    table_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO table_count
    FROM information_schema.tables
    WHERE table_schema = 'public'
    AND table_name IN (
        'processed_emails',
        'transactions',
        'receipts',
        'matches',
        'matching_statistics',
        'bloom_filter_cache'
    );
    
    RAISE NOTICE 'Tables created: %', table_count;
    
    IF table_count = 6 THEN
        RAISE NOTICE '✅ All tables created successfully!';
    ELSE
        RAISE WARNING '⚠️ Some tables may be missing. Expected 6, found %', table_count;
    END IF;
END $$;

-- ============================================================================
-- SCHEMA COMPLETE
-- ============================================================================
-- Next Steps:
-- 1. Run this script: psql -U postgres -d FinMatcher -f finmatcher_complete_schema.sql
-- 2. Verify tables: \dt
-- 3. Verify indexes: \di
-- 4. Test connection in Python code
-- ============================================================================
