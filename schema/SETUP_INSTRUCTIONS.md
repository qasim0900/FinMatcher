# FinMatcher Database Setup Instructions

## Quick Start (3 Steps)

### Step 1: Create Database
```bash
# Login to PostgreSQL
sudo -u postgres psql

# Create database
CREATE DATABASE "FinMatcher";

# Create user (if not exists)
CREATE USER postgres WITH PASSWORD 'your_password_here';

# Grant privileges
GRANT ALL PRIVILEGES ON DATABASE "FinMatcher" TO postgres;

# Exit
\q
```

### Step 2: Run Schema Script
```bash
# Navigate to schema directory
cd ~/FinMatcher/schema

# Run the complete schema
psql -U postgres -d FinMatcher -f finmatcher_complete_schema.sql
```

### Step 3: Verify Installation
```bash
# Login to database
psql -U postgres -d FinMatcher

# Check tables
\dt

# Expected output:
# - processed_emails
# - transactions
# - receipts
# - matches
# - matching_statistics
# - bloom_filter_cache

# Check indexes
\di

# Exit
\q
```

## Database Connection String

Update your `.env` file or code with:

```env
DATABASE_URL=postgresql://postgres:your_password_here@localhost/FinMatcher
```

Or in Python code:
```python
config = {
    'db_uri': 'postgresql://postgres:your_password_here@localhost/FinMatcher'
}
```

## Schema Overview

### Tables Created:

1. **processed_emails** - All fetched emails with attachment flags
2. **transactions** - Bank/credit card statement transactions
3. **receipts** - OCR-extracted receipt data from attachments
4. **matches** - Matching results (transactions ↔ receipts)
5. **matching_statistics** - Performance metrics per run
6. **bloom_filter_cache** - Duplicate detection cache

### Views Created:

1. **vw_matched_transactions** - Joined view of matched data
2. **vw_unmatched_transactions** - Transactions without matches
3. **vw_processing_summary** - Performance summary

### Indexes Created:

- 25+ performance indexes for fast queries
- Composite indexes for K-D Tree matching
- Partial indexes for filtered queries

## Testing Database Connection

```bash
# Test connection
python -c "import psycopg2; conn = psycopg2.connect('postgresql://postgres:your_password@localhost/FinMatcher'); print('✅ Connected'); conn.close()"
```

## Troubleshooting

### Issue 1: Database doesn't exist
```bash
sudo -u postgres createdb FinMatcher
```

### Issue 2: Permission denied
```bash
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE \"FinMatcher\" TO postgres;"
```

### Issue 3: Password authentication failed
```bash
# Reset password
sudo -u postgres psql -c "ALTER USER postgres PASSWORD 'newpassword';"
```

## Next Steps

After database setup:
1. Update `.env` file with correct DATABASE_URL
2. Run `python phase1_core_integration.py` to test
3. Check data: `psql -U postgres -d FinMatcher -c "SELECT COUNT(*) FROM processed_emails;"`

## Schema Maintenance

### Backup Database
```bash
pg_dump -U postgres FinMatcher > backup_$(date +%Y%m%d).sql
```

### Restore Database
```bash
psql -U postgres FinMatcher < backup_20260301.sql
```

### Clear All Data (Testing Only)
```bash
psql -U postgres -d FinMatcher -c "TRUNCATE processed_emails, transactions, receipts, matches, matching_statistics, bloom_filter_cache CASCADE;"
```

---

**✅ Schema Ready for Production!**
