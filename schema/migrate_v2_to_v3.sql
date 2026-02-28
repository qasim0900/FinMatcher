-- ===========================
-- FinMatcher v2 to v3 Migration Script
-- Adds v3 distributed pipeline tables while preserving v2 data
-- ===========================

-- Add new columns to existing emails table if they don't exist
DO $$ 
BEGIN
    -- Add received_date if it doesn't exist
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name='emails' AND column_name='received_date') THEN
        ALTER TABLE emails ADD COLUMN received_date TIMESTAMP;
    END IF;
    
    -- Add amount if it doesn't exist
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name='emails' AND column_name='amount') THEN
        ALTER TABLE emails ADD COLUMN amount DECIMAL(15, 2);
    END IF;
    
    -- Add currency if it doesn't exist
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name='emails' AND column_name='currency') THEN
        ALTER TABLE emails ADD COLUMN currency VARCHAR(10) DEFAULT 'USD';
    END IF;
    
    -- Add merchant_name if it doesn't exist
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name='emails' AND column_name='merchant_name') THEN
        ALTER TABLE emails ADD COLUMN merchant_name VARCHAR(255);
    END IF;
    
    -- Add transaction_date if it doesn't exist
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name='emails' AND column_name='transaction_date') THEN
        ALTER TABLE emails ADD COLUMN transaction_date TIMESTAMP;
    END IF;
    
    -- Add raw_email_data if it doesn't exist
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name='emails' AND column_name='raw_email_data') THEN
        ALTER TABLE emails ADD COLUMN raw_email_data JSONB;
    END IF;
    
    -- Add created_at if it doesn't exist
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name='emails' AND column_name='created_at') THEN
        ALTER TABLE emails ADD COLUMN created_at TIMESTAMP DEFAULT NOW();
    END IF;
    
    -- Add updated_at if it doesn't exist
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name='emails' AND column_name='updated_at') THEN
        ALTER TABLE emails ADD COLUMN updated_at TIMESTAMP DEFAULT NOW();
    END IF;
    
    -- Add attachment_file_path if it doesn't exist
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name='emails' AND column_name='attachment_file_path') THEN
        ALTER TABLE emails ADD COLUMN attachment_file_path TEXT;
    END IF;
    
    -- Add attachment_image_path if it doesn't exist
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name='emails' AND column_name='attachment_image_path') THEN
        ALTER TABLE emails ADD COLUMN attachment_image_path TEXT;
    END IF;
    
    -- Rename id to email_id if needed
    IF EXISTS (SELECT 1 FROM information_schema.columns 
               WHERE table_name='emails' AND column_name='id')
       AND NOT EXISTS (SELECT 1 FROM information_schema.columns 
                       WHERE table_name='emails' AND column_name='email_id') THEN
        ALTER TABLE emails RENAME COLUMN id TO email_id;
    END IF;
END $$;

-- Create indexes for new columns
CREATE INDEX IF NOT EXISTS idx_emails_received_date ON emails(received_date);
CREATE INDEX IF NOT EXISTS idx_emails_transaction_date ON emails(transaction_date);
CREATE INDEX IF NOT EXISTS idx_emails_amount ON emails(amount);
CREATE INDEX IF NOT EXISTS idx_emails_merchant ON emails(merchant_name);
CREATE INDEX IF NOT EXISTS idx_emails_created_at ON emails(created_at);

-- Create receipts table if it doesn't exist
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

CREATE INDEX IF NOT EXISTS idx_receipts_amount ON receipts(amount);
CREATE INDEX IF NOT EXISTS idx_receipts_transaction_date ON receipts(transaction_date);
CREATE INDEX IF NOT EXISTS idx_receipts_merchant ON receipts(merchant_name);

-- Create jobs table (new in v3)
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

CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);
CREATE INDEX IF NOT EXISTS idx_jobs_stage ON jobs(stage);
CREATE INDEX IF NOT EXISTS idx_jobs_email_id ON jobs(email_id);
CREATE INDEX IF NOT EXISTS idx_jobs_updated_at ON jobs(updated_at);
CREATE INDEX IF NOT EXISTS idx_jobs_worker_id ON jobs(worker_id);
CREATE INDEX IF NOT EXISTS idx_jobs_status_stage ON jobs(status, stage);

-- Create matches table (new in v3)
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

CREATE INDEX IF NOT EXISTS idx_matches_email_id ON matches(email_id);
CREATE INDEX IF NOT EXISTS idx_matches_receipt_id ON matches(receipt_id);
CREATE INDEX IF NOT EXISTS idx_matches_score ON matches(match_score DESC);
CREATE INDEX IF NOT EXISTS idx_matches_matched_at ON matches(matched_at);

-- Create reports table (new in v3)
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

CREATE INDEX IF NOT EXISTS idx_reports_status ON reports(status);
CREATE INDEX IF NOT EXISTS idx_reports_created_at ON reports(created_at);

-- Create audit_log table (new in v3)
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

CREATE INDEX IF NOT EXISTS idx_audit_log_job_id ON audit_log(job_id);
CREATE INDEX IF NOT EXISTS idx_audit_log_event_type ON audit_log(event_type);
CREATE INDEX IF NOT EXISTS idx_audit_log_created_at ON audit_log(created_at);
CREATE INDEX IF NOT EXISTS idx_audit_log_worker_id ON audit_log(worker_id);

-- Create metrics table (new in v3)
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

CREATE INDEX IF NOT EXISTS idx_metrics_service ON metrics(service_name);
CREATE INDEX IF NOT EXISTS idx_metrics_name ON metrics(metric_name);
CREATE INDEX IF NOT EXISTS idx_metrics_recorded_at ON metrics(recorded_at);
CREATE INDEX IF NOT EXISTS idx_metrics_service_name_time ON metrics(service_name, metric_name, recorded_at DESC);

-- State transition functions
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
    SELECT status, stage INTO v_old_status, v_stage
    FROM jobs
    WHERE job_id = p_job_id
    FOR UPDATE;
    
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Job % not found', p_job_id;
    END IF;
    
    IF NOT is_valid_transition(v_old_status, p_new_status) THEN
        RAISE EXCEPTION 'Invalid state transition from % to %', v_old_status, p_new_status;
    END IF;
    
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

-- Materialized views
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

-- Schema version tracking
CREATE TABLE IF NOT EXISTS schema_version (
    version VARCHAR(20) PRIMARY KEY,
    applied_at TIMESTAMP DEFAULT NOW(),
    description TEXT
);

INSERT INTO schema_version (version, description)
VALUES ('3.0.0', 'Migrated from v2 to v3 distributed pipeline')
ON CONFLICT (version) DO NOTHING;

-- Success message
DO $$
BEGIN
    RAISE NOTICE 'Migration to v3.0 completed successfully!';
END $$;
