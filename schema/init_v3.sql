-- ===========================
-- FinMatcher v3.0 Database Schema
-- Distributed Pipeline Architecture
-- ===========================

-- Drop existing tables if recreating (use with caution)
-- DROP TABLE IF EXISTS metrics CASCADE;
-- DROP TABLE IF EXISTS audit_log CASCADE;
-- DROP TABLE IF EXISTS reports CASCADE;
-- DROP TABLE IF EXISTS matches CASCADE;
-- DROP TABLE IF EXISTS jobs CASCADE;
-- DROP TABLE IF EXISTS emails CASCADE;
-- DROP TABLE IF EXISTS receipts CASCADE;

-- ===========================
-- Core Tables
-- ===========================

-- Table: emails
-- Stores all ingested email transactions
CREATE TABLE IF NOT EXISTS emails (
    email_id BIGSERIAL PRIMARY KEY,
    message_id TEXT UNIQUE NOT NULL,
    account_email VARCHAR(255) NOT NULL,
    folder TEXT,
    uid INTEGER,
    subject TEXT,
    sender VARCHAR(255),
    to_email TEXT,
    cc_email TEXT,
    reply_to TEXT,
    received_date TIMESTAMP,
    date_sent TIMESTAMP,
    body_text TEXT,
    body_html TEXT,
    raw_headers TEXT,
    amount DECIMAL(15, 2),
    currency VARCHAR(10) DEFAULT 'USD',
    merchant_name VARCHAR(255),
    transaction_date TIMESTAMP,
    raw_email_data JSONB,
    attachment_file_path TEXT,
    attachment_image_path TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Indexes for emails table
CREATE INDEX IF NOT EXISTS idx_emails_message_id ON emails(message_id);
CREATE INDEX IF NOT EXISTS idx_emails_account ON emails(account_email);
CREATE INDEX IF NOT EXISTS idx_emails_received_date ON emails(received_date);
CREATE INDEX IF NOT EXISTS idx_emails_transaction_date ON emails(transaction_date);
CREATE INDEX IF NOT EXISTS idx_emails_amount ON emails(amount);
CREATE INDEX IF NOT EXISTS idx_emails_merchant ON emails(merchant_name);
CREATE INDEX IF NOT EXISTS idx_emails_created_at ON emails(created_at);

-- Table: receipts
-- Stores receipt data for matching (v2 compatibility)
CREATE TABLE IF NOT EXISTS receipts (
    receipt_id BIGSERIAL PRIMARY KEY,
    receipt_number VARCHAR(100) UNIQUE,
    amount DECIMAL(15, 2) NOT NULL,
    currency VARCHAR(10) DEFAULT 'USD',
    merchant_name VARCHAR(255),
    transaction_date TIMESTAMP NOT NULL,
    category VARCHAR(100),
    payment_method VARCHAR(50),
    description TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Indexes for receipts table
CREATE INDEX IF NOT EXISTS idx_receipts_amount ON receipts(amount);
CREATE INDEX IF NOT EXISTS idx_receipts_transaction_date ON receipts(transaction_date);
CREATE INDEX IF NOT EXISTS idx_receipts_merchant ON receipts(merchant_name);
CREATE INDEX IF NOT EXISTS idx_receipts_created_at ON receipts(created_at);

-- Table: jobs
-- Central job management table for pipeline orchestration
CREATE TABLE IF NOT EXISTS jobs (
    job_id BIGSERIAL PRIMARY KEY,
    email_id BIGINT REFERENCES emails(email_id) ON DELETE CASCADE,
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    stage VARCHAR(50) NOT NULL,
    worker_id VARCHAR(100),
    retry_count INT DEFAULT 0,
    max_retries INT DEFAULT 3,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    
    CONSTRAINT valid_status CHECK (
        status IN ('pending', 'downloaded', 'matched', 'report_generated', 'uploaded', 'failed', 'dead_letter')
    ),
    CONSTRAINT valid_stage CHECK (
        stage IN ('ingestion', 'matching', 'reporting', 'upload')
    )
);

-- Indexes for jobs table
CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);
CREATE INDEX IF NOT EXISTS idx_jobs_stage ON jobs(stage);
CREATE INDEX IF NOT EXISTS idx_jobs_email_id ON jobs(email_id);
CREATE INDEX IF NOT EXISTS idx_jobs_updated_at ON jobs(updated_at);
CREATE INDEX IF NOT EXISTS idx_jobs_worker_id ON jobs(worker_id);
CREATE INDEX IF NOT EXISTS idx_jobs_status_stage ON jobs(status, stage);
CREATE INDEX IF NOT EXISTS idx_jobs_created_at ON jobs(created_at);

-- Table: matches
-- Stores matching results between emails and receipts
CREATE TABLE IF NOT EXISTS matches (
    match_id BIGSERIAL PRIMARY KEY,
    email_id BIGINT REFERENCES emails(email_id) ON DELETE CASCADE,
    receipt_id BIGINT REFERENCES receipts(receipt_id) ON DELETE CASCADE,
    match_score DECIMAL(5, 4) NOT NULL,
    match_type VARCHAR(50) NOT NULL,
    amount_diff DECIMAL(15, 2),
    date_diff_days INT,
    merchant_similarity DECIMAL(5, 4),
    confidence_level VARCHAR(20),
    matched_at TIMESTAMP DEFAULT NOW(),
    metadata JSONB,
    
    CONSTRAINT valid_match_type CHECK (
        match_type IN ('exact', 'fuzzy', 'partial', 'manual')
    ),
    CONSTRAINT valid_confidence CHECK (
        confidence_level IN ('high', 'medium', 'low')
    )
);

-- Indexes for matches table
CREATE INDEX IF NOT EXISTS idx_matches_email_id ON matches(email_id);
CREATE INDEX IF NOT EXISTS idx_matches_receipt_id ON matches(receipt_id);
CREATE INDEX IF NOT EXISTS idx_matches_score ON matches(match_score DESC);
CREATE INDEX IF NOT EXISTS idx_matches_matched_at ON matches(matched_at);
CREATE INDEX IF NOT EXISTS idx_matches_confidence ON matches(confidence_level);

-- Table: reports
-- Tracks generated reports
CREATE TABLE IF NOT EXISTS reports (
    report_id BIGSERIAL PRIMARY KEY,
    report_name VARCHAR(255) NOT NULL,
    report_type VARCHAR(50) NOT NULL,
    file_path TEXT,
    file_size_bytes BIGINT,
    record_count INT,
    generation_time_ms INT,
    status VARCHAR(50) DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT NOW(),
    uploaded_at TIMESTAMP,
    metadata JSONB,
    
    CONSTRAINT valid_report_type CHECK (
        report_type IN ('excel', 'csv', 'json')
    ),
    CONSTRAINT valid_report_status CHECK (
        status IN ('pending', 'generated', 'uploaded', 'failed')
    )
);

-- Indexes for reports table
CREATE INDEX IF NOT EXISTS idx_reports_status ON reports(status);
CREATE INDEX IF NOT EXISTS idx_reports_created_at ON reports(created_at);
CREATE INDEX IF NOT EXISTS idx_reports_report_type ON reports(report_type);

-- Table: audit_log
-- Comprehensive audit trail for all state transitions
CREATE TABLE IF NOT EXISTS audit_log (
    log_id BIGSERIAL PRIMARY KEY,
    job_id BIGINT REFERENCES jobs(job_id) ON DELETE CASCADE,
    event_type VARCHAR(50) NOT NULL,
    old_status VARCHAR(50),
    new_status VARCHAR(50),
    worker_id VARCHAR(100),
    stage VARCHAR(50),
    metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    
    CONSTRAINT valid_event_type CHECK (
        event_type IN ('status_change', 'retry', 'error', 'completion', 'dead_letter')
    )
);

-- Indexes for audit_log table
CREATE INDEX IF NOT EXISTS idx_audit_log_job_id ON audit_log(job_id);
CREATE INDEX IF NOT EXISTS idx_audit_log_event_type ON audit_log(event_type);
CREATE INDEX IF NOT EXISTS idx_audit_log_created_at ON audit_log(created_at);
CREATE INDEX IF NOT EXISTS idx_audit_log_worker_id ON audit_log(worker_id);

-- Table: metrics
-- Performance and observability metrics
CREATE TABLE IF NOT EXISTS metrics (
    metric_id BIGSERIAL PRIMARY KEY,
    service_name VARCHAR(100) NOT NULL,
    metric_name VARCHAR(100) NOT NULL,
    metric_value DECIMAL(15, 4),
    metric_unit VARCHAR(50),
    worker_id VARCHAR(100),
    recorded_at TIMESTAMP DEFAULT NOW(),
    metadata JSONB
);

-- Indexes for metrics table
CREATE INDEX IF NOT EXISTS idx_metrics_service ON metrics(service_name);
CREATE INDEX IF NOT EXISTS idx_metrics_name ON metrics(metric_name);
CREATE INDEX IF NOT EXISTS idx_metrics_recorded_at ON metrics(recorded_at);
CREATE INDEX IF NOT EXISTS idx_metrics_service_name_time ON metrics(service_name, metric_name, recorded_at DESC);

-- Table: sync_state (v2 compatibility)
-- Tracks IMAP sync state for incremental fetching
CREATE TABLE IF NOT EXISTS sync_state (
    account_email TEXT,
    folder TEXT,
    last_uid INTEGER,
    last_sync TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY(account_email, folder)
);

-- Table: attachments (v2 compatibility)
-- Stores email attachment metadata
CREATE TABLE IF NOT EXISTS attachments (
    id SERIAL PRIMARY KEY,
    message_id TEXT,
    filename TEXT,
    file_path TEXT,
    file_size INTEGER,
    file_hash TEXT UNIQUE,
    content_id TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_attachments_message_id ON attachments(message_id);
CREATE INDEX IF NOT EXISTS idx_attachments_file_hash ON attachments(file_hash);

-- ===========================
-- State Transition Functions
-- ===========================

-- Function: is_valid_transition
-- Validates state machine transitions
CREATE OR REPLACE FUNCTION is_valid_transition(
    p_old_status VARCHAR(50),
    p_new_status VARCHAR(50)
)
RETURNS BOOLEAN AS $$
BEGIN
    RETURN CASE
        WHEN p_old_status = 'pending' AND p_new_status IN ('downloaded', 'failed') THEN TRUE
        WHEN p_old_status = 'downloaded' AND p_new_status IN ('matched', 'failed') THEN TRUE
        WHEN p_old_status = 'matched' AND p_new_status IN ('report_generated', 'failed') THEN TRUE
        WHEN p_old_status = 'report_generated' AND p_new_status IN ('uploaded', 'failed') THEN TRUE
        WHEN p_old_status = 'failed' AND p_new_status IN ('pending', 'dead_letter') THEN TRUE
        ELSE FALSE
    END;
END;
$$ LANGUAGE plpgsql;

-- Function: update_job_status
-- Atomic state transition with audit logging
CREATE OR REPLACE FUNCTION update_job_status(
    p_job_id BIGINT,
    p_new_status VARCHAR(50),
    p_worker_id VARCHAR(100),
    p_error_message TEXT DEFAULT NULL
)
RETURNS BOOLEAN AS $$
DECLARE
    v_old_status VARCHAR(50);
    v_stage VARCHAR(50);
BEGIN
    -- Get current status
    SELECT status, stage INTO v_old_status, v_stage
    FROM jobs
    WHERE job_id = p_job_id
    FOR UPDATE;
    
    -- Check if job exists
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Job % not found', p_job_id;
    END IF;
    
    -- Validate state transition
    IF NOT is_valid_transition(v_old_status, p_new_status) THEN
        RAISE EXCEPTION 'Invalid state transition from % to %', v_old_status, p_new_status;
    END IF;
    
    -- Update job status
    UPDATE jobs
    SET status = p_new_status,
        worker_id = p_worker_id,
        updated_at = NOW(),
        error_message = p_error_message,
        completed_at = CASE 
            WHEN p_new_status IN ('uploaded', 'failed', 'dead_letter') THEN NOW() 
            ELSE completed_at 
        END
    WHERE job_id = p_job_id;
    
    -- Insert audit log
    INSERT INTO audit_log (job_id, event_type, old_status, new_status, worker_id, stage, metadata)
    VALUES (
        p_job_id,
        'status_change',
        v_old_status,
        p_new_status,
        p_worker_id,
        v_stage,
        jsonb_build_object('error_message', p_error_message, 'timestamp', NOW())
    );
    
    RETURN TRUE;
END;
$$ LANGUAGE plpgsql;

-- Function: get_next_jobs
-- Atomic job polling for workers with SKIP LOCKED
CREATE OR REPLACE FUNCTION get_next_jobs(
    p_stage VARCHAR(50),
    p_required_status VARCHAR(50),
    p_worker_id VARCHAR(100),
    p_batch_size INT DEFAULT 100
)
RETURNS TABLE(job_id BIGINT, email_id BIGINT) AS $$
BEGIN
    RETURN QUERY
    UPDATE jobs
    SET worker_id = p_worker_id,
        started_at = CASE WHEN started_at IS NULL THEN NOW() ELSE started_at END,
        updated_at = NOW()
    WHERE jobs.job_id IN (
        SELECT j.job_id
        FROM jobs j
        WHERE j.stage = p_stage
          AND j.status = p_required_status
          AND (j.worker_id IS NULL OR j.worker_id = p_worker_id)
          AND j.retry_count < j.max_retries
        ORDER BY j.created_at
        LIMIT p_batch_size
        FOR UPDATE SKIP LOCKED
    )
    RETURNING jobs.job_id, jobs.email_id;
END;
$$ LANGUAGE plpgsql;

-- Function: increment_retry_count
-- Increments retry count and logs retry event
CREATE OR REPLACE FUNCTION increment_retry_count(
    p_job_id BIGINT,
    p_worker_id VARCHAR(100),
    p_error_message TEXT
)
RETURNS BOOLEAN AS $$
DECLARE
    v_retry_count INT;
    v_max_retries INT;
    v_stage VARCHAR(50);
BEGIN
    -- Get current retry count
    SELECT retry_count, max_retries, stage 
    INTO v_retry_count, v_max_retries, v_stage
    FROM jobs
    WHERE job_id = p_job_id
    FOR UPDATE;
    
    -- Increment retry count
    UPDATE jobs
    SET retry_count = retry_count + 1,
        error_message = p_error_message,
        updated_at = NOW(),
        status = CASE 
            WHEN retry_count + 1 >= max_retries THEN 'dead_letter'
            ELSE 'failed'
        END
    WHERE job_id = p_job_id;
    
    -- Insert audit log
    INSERT INTO audit_log (job_id, event_type, old_status, new_status, worker_id, stage, metadata)
    VALUES (
        p_job_id,
        'retry',
        'failed',
        CASE WHEN v_retry_count + 1 >= v_max_retries THEN 'dead_letter' ELSE 'failed' END,
        p_worker_id,
        v_stage,
        jsonb_build_object(
            'error_message', p_error_message, 
            'retry_count', v_retry_count + 1,
            'max_retries', v_max_retries,
            'timestamp', NOW()
        )
    );
    
    RETURN TRUE;
END;
$$ LANGUAGE plpgsql;

-- ===========================
-- Materialized Views
-- ===========================

-- View: pipeline_status_summary
-- Aggregated pipeline status for monitoring
CREATE MATERIALIZED VIEW IF NOT EXISTS pipeline_status_summary AS
SELECT
    status,
    stage,
    COUNT(*) as job_count,
    AVG(EXTRACT(EPOCH FROM (completed_at - started_at))) as avg_duration_seconds,
    MIN(created_at) as oldest_job,
    MAX(updated_at) as last_updated
FROM jobs
GROUP BY status, stage;

CREATE INDEX IF NOT EXISTS idx_pipeline_summary_status ON pipeline_status_summary(status);
CREATE INDEX IF NOT EXISTS idx_pipeline_summary_stage ON pipeline_status_summary(stage);

-- View: service_metrics_summary
-- Aggregated metrics per service
CREATE MATERIALIZED VIEW IF NOT EXISTS service_metrics_summary AS
SELECT
    service_name,
    metric_name,
    AVG(metric_value) as avg_value,
    MIN(metric_value) as min_value,
    MAX(metric_value) as max_value,
    COUNT(*) as sample_count,
    MAX(recorded_at) as last_recorded
FROM metrics
WHERE recorded_at > NOW() - INTERVAL '1 hour'
GROUP BY service_name, metric_name;

CREATE INDEX IF NOT EXISTS idx_service_metrics_service ON service_metrics_summary(service_name);

-- ===========================
-- Helper Functions
-- ===========================

-- Function: refresh_materialized_views
-- Refreshes all materialized views
CREATE OR REPLACE FUNCTION refresh_materialized_views()
RETURNS VOID AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY pipeline_status_summary;
    REFRESH MATERIALIZED VIEW CONCURRENTLY service_metrics_summary;
END;
$$ LANGUAGE plpgsql;

-- Function: cleanup_old_metrics
-- Removes metrics older than specified days
CREATE OR REPLACE FUNCTION cleanup_old_metrics(p_days INT DEFAULT 30)
RETURNS INT AS $$
DECLARE
    v_deleted_count INT;
BEGIN
    DELETE FROM metrics
    WHERE recorded_at < NOW() - (p_days || ' days')::INTERVAL;
    
    GET DIAGNOSTICS v_deleted_count = ROW_COUNT;
    RETURN v_deleted_count;
END;
$$ LANGUAGE plpgsql;

-- Function: cleanup_old_audit_logs
-- Removes audit logs older than specified days
CREATE OR REPLACE FUNCTION cleanup_old_audit_logs(p_days INT DEFAULT 90)
RETURNS INT AS $$
DECLARE
    v_deleted_count INT;
BEGIN
    DELETE FROM audit_log
    WHERE created_at < NOW() - (p_days || ' days')::INTERVAL;
    
    GET DIAGNOSTICS v_deleted_count = ROW_COUNT;
    RETURN v_deleted_count;
END;
$$ LANGUAGE plpgsql;

-- ===========================
-- Initial Data / Seed
-- ===========================

-- Insert sample configuration if needed
-- (Add any initial data here)

-- ===========================
-- Grants and Permissions
-- ===========================

-- Note: Run these commands separately with appropriate credentials
-- CREATE ROLE finmatcher_app WITH LOGIN PASSWORD 'your_secure_password';
-- GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA public TO finmatcher_app;
-- GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO finmatcher_app;
-- GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO finmatcher_app;

-- CREATE ROLE finmatcher_readonly WITH LOGIN PASSWORD 'your_readonly_password';
-- GRANT SELECT ON ALL TABLES IN SCHEMA public TO finmatcher_readonly;

-- ===========================
-- Schema Version Tracking
-- ===========================

CREATE TABLE IF NOT EXISTS schema_version (
    version VARCHAR(20) PRIMARY KEY,
    applied_at TIMESTAMP DEFAULT NOW(),
    description TEXT
);

INSERT INTO schema_version (version, description)
VALUES ('3.0.0', 'Initial v3.0 distributed pipeline schema')
ON CONFLICT (version) DO NOTHING;

-- ===========================
-- End of Schema
-- ===========================
