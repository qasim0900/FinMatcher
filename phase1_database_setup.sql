-- Phase 1: Database Schema Setup for FastEmailProcessor
-- PostgreSQL optimization script for FinMatcher Core Integration

-- =====================================================
-- STEP 1: Create optimized table structure
-- =====================================================

-- Drop existing table if needed (CAUTION: Only for fresh setup)
-- DROP TABLE IF EXISTS processed_emails CASCADE;

-- Create main processed_emails table with optimized schema
CREATE TABLE IF NOT EXISTS processed_emails (
    id SERIAL PRIMARY KEY,
    message_id VARCHAR(255) UNIQUE NOT NULL,
    subject TEXT,
    sender VARCHAR(500),
    date TIMESTAMP WITH TIME ZONE,
    has_attachment BOOLEAN DEFAULT FALSE,
    attachment_count INTEGER DEFAULT 0,
    attachment_filenames TEXT[], -- Array to store multiple attachment names
    processing_status VARCHAR(50) DEFAULT 'pending',
    financial_score FLOAT DEFAULT 0.0,
    date_processed DATE,
    sender_domain VARCHAR(255),
    subject_length INTEGER,
    email_size_bytes INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- =====================================================
-- STEP 2: Create performance-optimized indexes
-- =====================================================

-- Primary performance indexes
CREATE INDEX IF NOT EXISTS idx_processed_emails_attachment 
ON processed_emails(has_attachment) 
WHERE has_attachment = TRUE;

CREATE INDEX IF NOT EXISTS idx_processed_emails_date 
ON processed_emails(date_processed DESC);

CREATE INDEX IF NOT EXISTS idx_processed_emails_financial_score 
ON processed_emails(financial_score DESC) 
WHERE financial_score > 0.5;

CREATE INDEX IF NOT EXISTS idx_processed_emails_status 
ON processed_emails(processing_status);

-- Composite indexes for complex queries
CREATE INDEX IF NOT EXISTS idx_processed_emails_attachment_date 
ON processed_emails(has_attachment, date_processed DESC) 
WHERE has_attachment = TRUE;

CREATE INDEX IF NOT EXISTS idx_processed_emails_sender_domain 
ON processed_emails(sender_domain) 
WHERE sender_domain IS NOT NULL;

-- Full-text search index for subject
CREATE INDEX IF NOT EXISTS idx_processed_emails_subject_fts 
ON processed_emails USING gin(to_tsvector('english', subject));

-- =====================================================
-- STEP 3: Create supporting tables
-- =====================================================

-- Table for tracking email attachments
CREATE TABLE IF NOT EXISTS email_attachments (
    id SERIAL PRIMARY KEY,
    email_id INTEGER REFERENCES processed_emails(id) ON DELETE CASCADE,
    filename VARCHAR(500) NOT NULL,
    file_size INTEGER DEFAULT 0,
    mime_type VARCHAR(100),
    attachment_id VARCHAR(255), -- Gmail attachment ID
    downloaded BOOLEAN DEFAULT FALSE,
    ocr_processed BOOLEAN DEFAULT FALSE,
    ocr_text TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Index for attachment queries
CREATE INDEX IF NOT EXISTS idx_email_attachments_email_id 
ON email_attachments(email_id);

CREATE INDEX IF NOT EXISTS idx_email_attachments_downloaded 
ON email_attachments(downloaded);

CREATE INDEX IF NOT EXISTS idx_email_attachments_ocr_processed 
ON email_attachments(ocr_processed);

-- Table for processing statistics
CREATE TABLE IF NOT EXISTS processing_stats (
    id SERIAL PRIMARY KEY,
    processing_date DATE DEFAULT CURRENT_DATE,
    phase VARCHAR(50) NOT NULL,
    emails_processed INTEGER DEFAULT 0,
    processing_time_seconds FLOAT DEFAULT 0.0,
    success_rate FLOAT DEFAULT 0.0,
    errors_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- =====================================================
-- STEP 4: Create utility functions
-- =====================================================

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Trigger to automatically update updated_at
DROP TRIGGER IF EXISTS update_processed_emails_updated_at ON processed_emails;
CREATE TRIGGER update_processed_emails_updated_at
    BEFORE UPDATE ON processed_emails
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Function to calculate financial score
CREATE OR REPLACE FUNCTION calculate_financial_score(subject_text TEXT, sender_text TEXT)
RETURNS FLOAT AS $$
DECLARE
    score FLOAT := 0.0;
    combined_text TEXT;
BEGIN
    combined_text := LOWER(COALESCE(subject_text, '') || ' ' || COALESCE(sender_text, ''));
    
    -- Check for financial keywords
    IF combined_text ~ '(invoice|receipt|bill|statement|payment|order|confirmation|transaction|purchase)' THEN
        score := score + 0.5;
    END IF;
    
    -- Check for financial domains
    IF sender_text ~ '@(billing|invoices|receipts|accounting|noreply|orders|payments)' THEN
        score := score + 0.3;
    END IF;
    
    -- Check for amount patterns
    IF combined_text ~ '\$[0-9]+\.?[0-9]*' THEN
        score := score + 0.2;
    END IF;
    
    RETURN LEAST(score, 1.0); -- Cap at 1.0
END;
$$ LANGUAGE plpgsql;

-- =====================================================
-- STEP 5: Create views for common queries
-- =====================================================

-- View for emails with attachments (most commonly used)
CREATE OR REPLACE VIEW emails_with_attachments AS
SELECT 
    id,
    message_id,
    subject,
    sender,
    date,
    attachment_count,
    financial_score,
    processing_status,
    created_at
FROM processed_emails 
WHERE has_attachment = TRUE
ORDER BY financial_score DESC, date DESC;

-- View for high-priority financial emails
CREATE OR REPLACE VIEW high_priority_financial_emails AS
SELECT 
    id,
    message_id,
    subject,
    sender,
    date,
    attachment_count,
    financial_score,
    processing_status
FROM processed_emails 
WHERE has_attachment = TRUE 
  AND financial_score >= 0.7
  AND processing_status = 'pending'
ORDER BY financial_score DESC, date DESC;

-- View for processing statistics
CREATE OR REPLACE VIEW processing_summary AS
SELECT 
    processing_date,
    phase,
    SUM(emails_processed) as total_emails,
    AVG(processing_time_seconds) as avg_processing_time,
    AVG(success_rate) as avg_success_rate,
    SUM(errors_count) as total_errors
FROM processing_stats 
GROUP BY processing_date, phase
ORDER BY processing_date DESC, phase;

-- =====================================================
-- STEP 6: Insert initial configuration data
-- =====================================================

-- Insert processing phases for tracking
INSERT INTO processing_stats (phase, emails_processed, processing_time_seconds, success_rate) 
VALUES 
    ('Phase 1: Core Integration', 0, 0.0, 0.0),
    ('Phase 2: Statement Matching', 0, 0.0, 0.0),
    ('Phase 3: OCR Processing', 0, 0.0, 0.0),
    ('Phase 4: Excel Generation', 0, 0.0, 0.0)
ON CONFLICT DO NOTHING;

-- =====================================================
-- STEP 7: Performance optimization settings
-- =====================================================

-- Optimize PostgreSQL settings for bulk operations
-- (These should be set in postgresql.conf for production)

-- Increase work_mem for sorting and hashing
-- SET work_mem = '256MB';

-- Increase maintenance_work_mem for index creation
-- SET maintenance_work_mem = '1GB';

-- Optimize for bulk inserts
-- SET synchronous_commit = off; -- Only for bulk loading, turn back on for production

-- =====================================================
-- STEP 8: Verification queries
-- =====================================================

-- Verify table creation
SELECT 
    table_name, 
    column_name, 
    data_type, 
    is_nullable
FROM information_schema.columns 
WHERE table_name = 'processed_emails' 
ORDER BY ordinal_position;

-- Verify indexes
SELECT 
    indexname, 
    indexdef 
FROM pg_indexes 
WHERE tablename = 'processed_emails';

-- Check table size and statistics
SELECT 
    schemaname,
    tablename,
    attname,
    n_distinct,
    correlation
FROM pg_stats 
WHERE tablename = 'processed_emails';

-- =====================================================
-- STEP 9: Cleanup and maintenance procedures
-- =====================================================

-- Procedure to clean up old processed emails (optional)
CREATE OR REPLACE FUNCTION cleanup_old_emails(days_old INTEGER DEFAULT 365)
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM processed_emails 
    WHERE created_at < CURRENT_DATE - INTERVAL '1 day' * days_old
      AND processing_status = 'completed';
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    
    -- Update statistics
    INSERT INTO processing_stats (phase, emails_processed, processing_time_seconds, success_rate)
    VALUES ('Cleanup', -deleted_count, 0, 1.0);
    
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- Procedure to update table statistics
CREATE OR REPLACE FUNCTION update_table_statistics()
RETURNS VOID AS $$
BEGIN
    ANALYZE processed_emails;
    ANALYZE email_attachments;
    ANALYZE processing_stats;
END;
$$ LANGUAGE plpgsql;

-- =====================================================
-- STEP 10: Grant permissions (adjust as needed)
-- =====================================================

-- Create application user if not exists
-- CREATE USER finmatcher_app WITH PASSWORD 'secure_password_here';

-- Grant necessary permissions
-- GRANT SELECT, INSERT, UPDATE, DELETE ON processed_emails TO finmatcher_app;
-- GRANT SELECT, INSERT, UPDATE, DELETE ON email_attachments TO finmatcher_app;
-- GRANT SELECT, INSERT, UPDATE, DELETE ON processing_stats TO finmatcher_app;
-- GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO finmatcher_app;

-- =====================================================
-- COMPLETION MESSAGE
-- =====================================================

DO $$
BEGIN
    RAISE NOTICE '✅ Phase 1 Database Setup Complete!';
    RAISE NOTICE '📊 Tables created: processed_emails, email_attachments, processing_stats';
    RAISE NOTICE '🚀 Indexes optimized for high-performance queries';
    RAISE NOTICE '🔧 Utility functions and views ready';
    RAISE NOTICE '📈 Ready for FastEmailProcessor integration';
END $$;