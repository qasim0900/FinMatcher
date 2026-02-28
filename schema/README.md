# FinMatcher v3.0 Database Schema

## Overview

This directory contains the PostgreSQL database schema for FinMatcher v3.0 distributed pipeline architecture. The schema supports independent services for email ingestion, matching, reporting, and upload with state-based orchestration.

## Files

- `init_v3.sql` - Complete v3.0 schema (for fresh installations)
- `migrate_v2_to_v3.sql` - Migration script from v2 to v3 (preserves existing data)
- `apply_schema.py` - Python script to apply fresh v3 schema
- `migrate.py` - Python script to migrate from v2 to v3
- `test_schema.py` - Test suite for schema functions

## Quick Start

### For Existing v2 Installations (Recommended)

```bash
# Migrate from v2 to v3 (preserves existing data)
python schema/migrate.py
```

### For Fresh Installations

```bash
# Apply v3 schema from scratch
python schema/apply_schema.py
```

### Test the Schema

```bash
# Run schema tests
python schema/test_schema.py
```

## Database Tables

### Core Tables

#### `emails`
Stores all ingested email transactions with extracted metadata.

**Key Columns:**
- `email_id` - Primary key
- `message_id` - Unique email identifier
- `account_email` - Source Gmail account
- `amount`, `merchant_name`, `transaction_date` - Extracted transaction data
- `created_at`, `updated_at` - Timestamps

**Indexes:** message_id, account_email, received_date, transaction_date, amount, merchant_name

#### `receipts`
Stores receipt data for matching (v2 compatibility).

**Key Columns:**
- `receipt_id` - Primary key
- `amount`, `merchant_name`, `transaction_date` - Receipt details
- `category`, `payment_method` - Classification

**Indexes:** amount, transaction_date, merchant_name

#### `jobs`
Central job management table for pipeline orchestration.

**Key Columns:**
- `job_id` - Primary key
- `email_id` - Foreign key to emails
- `status` - Current job status (pending, downloaded, matched, report_generated, uploaded, failed, dead_letter)
- `stage` - Pipeline stage (ingestion, matching, reporting, upload)
- `worker_id` - Worker processing this job
- `retry_count`, `max_retries` - Retry management
- `error_message` - Error details

**Indexes:** status, stage, email_id, worker_id, status+stage composite

**State Machine:**
```
pending → downloaded → matched → report_generated → uploaded
   ↓          ↓           ↓              ↓
failed → dead_letter (after max retries)
   ↓
pending (retry)
```

#### `matches`
Stores matching results between emails and receipts.

**Key Columns:**
- `match_id` - Primary key
- `email_id`, `receipt_id` - Foreign keys
- `match_score` - Confidence score (0-1)
- `match_type` - exact, fuzzy, partial, manual
- `confidence_level` - high, medium, low
- `amount_diff`, `date_diff_days`, `merchant_similarity` - Match metrics

**Indexes:** email_id, receipt_id, match_score, matched_at

#### `reports`
Tracks generated reports.

**Key Columns:**
- `report_id` - Primary key
- `report_name`, `report_type` - Report metadata
- `file_path`, `file_size_bytes` - File details
- `record_count`, `generation_time_ms` - Performance metrics
- `status` - pending, generated, uploaded, failed

**Indexes:** status, created_at

#### `audit_log`