# 🚀 FinMatcher - Complete Deployment Guide

## 📋 Table of Contents
1. [Prerequisites Check](#prerequisites-check)
2. [Database Setup](#database-setup)
3. [Environment Configuration](#environment-configuration)
4. [Gmail API Setup](#gmail-api-setup)
5. [Dependencies Installation](#dependencies-installation)
6. [Database Migration](#database-migration)
7. [System Testing](#system-testing)
8. [Production Run](#production-run)
9. [Troubleshooting](#troubleshooting)
10. [System Cleanup](#system-cleanup)

---

## ✅ STEP 1: Prerequisites Check

### System Requirements
```bash
# Check Python version (need 3.11+)
python --version

# Check available RAM (need 16GB+)
wmic ComputerSystem get TotalPhysicalMemory

# Check CPU cores (need 8+)
wmic cpu get NumberOfCores

# Check disk space (need 50GB+)
wmic logicaldisk get size,freespace,caption
```

**Expected Output:**
- Python: 3.11 or higher ✅
- RAM: 16GB+ ✅
- CPU: 8+ cores ✅
- Disk: 50GB+ free ✅

---

## 🗄️ STEP 2: Database Setup

### Option A: PostgreSQL (Recommended for Production)

#### Install PostgreSQL
```bash
# Download from: https://www.postgresql.org/download/windows/
# Or use chocolatey:
choco install postgresql

# Verify installation
psql --version
```

#### Create Database
```bash
# Login to PostgreSQL
psql -U postgres

# Create database
CREATE DATABASE finmatcher;

# Create user
CREATE USER finmatcher_user WITH PASSWORD 'your_secure_password';

# Grant privileges
GRANT ALL PRIVILEGES ON DATABASE finmatcher TO finmatcher_user;

# Exit
\q
```

#### Test Connection
```bash
psql -U finmatcher_user -d finmatcher -h localhost
```

### Option B: SQLite (For Testing Only)
```bash
# SQLite comes with Python, no installation needed
# Database file will be created automatically
```

---

## ⚙️ STEP 3: Environment Configuration

### Create .env File
```bash
# Copy example file
copy .env.example .env

# Edit .env file
notepad .env
```

### Configure .env
```env
# Database Configuration (PostgreSQL)
DATABASE_URL=postgresql://finmatcher_user:your_secure_password@localhost:5432/finmatcher

# Or for SQLite (testing only)
# DATABASE_URL=sqlite:///finmatcher.db

# Gmail API Configuration
GMAIL_CREDENTIALS_PATH=finmatcher/auth_files/credentials.json
GMAIL_TOKEN_PATH=finmatcher/auth_files/token.json

# DeepSeek AI Configuration
DEEPSEEK_API_KEY=your_deepseek_api_key_here

# Email Accounts (comma-separated)
EMAIL_ACCOUNTS=your.email@gmail.com

# Performance Configuration
THREAD_POOL_SIZE=100
PROCESS_POOL_SIZE=16
BATCH_SIZE=10000

# Logging
LOG_LEVEL=INFO
LOG_FILE=logs/finmatcher.log
```

**Save and close the file**

---

## 📧 STEP 4: Gmail API Setup

### Enable Gmail API
1. Go to: https://console.cloud.google.com/
2. Create new project: "FinMatcher"
3. Enable Gmail API:
   - APIs & Services → Library
   - Search "Gmail API"
   - Click Enable

### Create Credentials
```bash
# 1. Go to: APIs & Services → Credentials
# 2. Create Credentials → OAuth 2.0 Client ID
# 3. Application type: Desktop app
# 4. Name: FinMatcher Desktop
# 5. Download JSON file
```

### Save Credentials
```bash
# Create auth directory
mkdir finmatcher\auth_files

# Copy downloaded file to:
copy Downloads\credentials.json finmatcher\auth_files\credentials.json
```

### Test Gmail Connection
```bash
# Run authentication test
python -c "from finmatcher.core.email_fetcher import EmailFetcher; print('Gmail API ready')"
```

**Expected:** Browser opens for Gmail authorization ✅

---

## 📦 STEP 5: Dependencies Installation

### Install Poetry (Package Manager)
```bash
# Install Poetry
pip install poetry

# Verify installation
poetry --version
```

### Install Project Dependencies
```bash
# Navigate to project directory
cd D:\UpWork\FinMatcher

# Install all dependencies
poetry install

# Verify installation
poetry show
```

**Expected:** All packages installed successfully ✅

### Alternative: pip install
```bash
# If Poetry fails, use pip
pip install -r requirements.txt

# Or install manually
pip install pandas numpy scikit-learn pybloom-live psycopg2-binary
```

---

## 🔄 STEP 6: Database Migration

### Unified Migration System

FinMatcher uses a unified migration system with two entry points:

1. **`setup_ubuntu.py`** - Complete initial setup (database creation + migrations)
2. **`migrate.py`** - Ongoing migration management

### Option A: Initial Setup (Fresh Installation)

For a fresh Ubuntu server deployment, use the unified setup script:

```bash
# Run complete setup (creates database, runs all migrations, validates)
python setup_ubuntu.py
```

**What it does:**
- ✅ Checks PostgreSQL connection
- ✅ Creates database if not exists
- ✅ Creates schema_migrations tracking table
- ✅ Runs all migrations from schema/migrations/ directory
- ✅ Validates all required tables exist
- ✅ Runs test query to verify database is functional

**Expected Output:**
```
[INFO] Checking PostgreSQL connection...
[INFO] Database 'finmatcher' created successfully
[INFO] Running migrations...
[INFO] Applied migration: 001_initial_schema.sql
[INFO] Applied migration: 002_add_optimization_fields.sql
[INFO] Applied migration: 003_add_performance_indexes.sql
[INFO] All migrations applied successfully
[INFO] Validating database setup...
[INFO] All required tables exist
[INFO] Database setup completed successfully!
```

### Option B: Ongoing Migrations (Existing Installation)

For applying new migrations to an existing database:

```bash
# Check migration status
python migrate.py status

# Apply pending migrations
python migrate.py up

# Rollback last migration (if needed)
python migrate.py down
```

### Migration Files Location

All migration files are stored in `schema/migrations/`:

```bash
schema/migrations/
├── 001_initial_schema.sql          # Creates all base tables
├── 002_add_optimization_fields.sql # Adds performance fields
└── 003_add_performance_indexes.sql # Creates indexes
```

### Verify Migration Success

```bash
# Check applied migrations
psql -U finmatcher_user -d finmatcher -c "SELECT * FROM schema_migrations ORDER BY version;"

# Verify tables created
psql -U finmatcher_user -d finmatcher -c "\dt"
```

**Expected Tables:**
- processed_emails ✅
- transactions ✅
- receipts ✅
- matches ✅
- jobs ✅
- reports ✅
- audit_log ✅
- metrics ✅
- schema_migrations ✅

### Deprecated Migration Scripts

The following scripts are **deprecated** and should not be used:

- ❌ `schema/migrate.py` (deprecated - use `migrate.py` instead)
- ❌ `complete_setup.sh` (deprecated - use `setup_ubuntu.py` instead)
- ❌ `schema/init_v3.sql` (deprecated - migrations now in schema/migrations/)
- ❌ `schema/migrate_v2_to_v3.sql` (deprecated - consolidated into migration system)

These files have been moved to `.deprecated` extensions and contain notices pointing to the new unified system.

---

## 🧪 STEP 7: System Testing

### Test 1: Database Connection
```bash
# Test database connectivity
python -c "from finmatcher.storage.database_manager import get_database_manager; db = get_database_manager(); print('Database connected:', db is not None)"
```

**Expected:** `Database connected: True` ✅

### Test 2: Configuration Loading
```bash
# Test config loading
python -c "from finmatcher.config.settings import get_settings; s = get_settings(); print('Config loaded:', s.thread_pool_size)"
```

**Expected:** `Config loaded: 100` ✅

### Test 3: Gmail API
```bash
# Test Gmail connection
python -c "from finmatcher.core.email_fetcher import EmailFetcher; ef = EmailFetcher(); print('Gmail API ready')"
```

**Expected:** `Gmail API ready` ✅

### Test 4: OCR Engine
```bash
# Test OCR functionality
python -c "from finmatcher.core.ocr_engine import OCREngine; ocr = OCREngine(); print('OCR engine ready')"
```

**Expected:** `OCR engine ready` ✅

### Test 5: Fast Processor
```bash
# Test optimized processor
python test_fast_processor.py
```

**Expected:** All tests pass ✅

---

## 🚀 STEP 8: Production Run

### Prepare Statements Folder
```bash
# Ensure statements are in place
dir statements

# Expected files:
# - Amex_Credit_Card_Statement.xlsx
# - Chase_Credit_Card_Statement.xlsx
# - Meriwest Credit Card Statement.pdf
```

### Create Output Directories
```bash
# Create necessary directories
mkdir output
mkdir reports
mkdir logs
mkdir temp_attachments
```

### Run Initial Test (Small Dataset)
```bash
# Test with 100 emails first
python main.py --test-mode --email-count=100
```

**Expected:**
- Emails fetched: 100 ✅
- Financial emails identified ✅
- Attachments processed ✅
- Matches found ✅
- Excel generated ✅

### Run Production (Full Dataset)
```bash
# Run full production pipeline
python main.py

# Or use the batch file
run.bat
```

**Monitor Progress:**
```bash
# In another terminal, watch logs
Get-Content logs\finmatcher.log -Wait -Tail 50
```

### Expected Output
```
[INFO] Starting FinMatcher v2.0
[INFO] Loading configuration...
[INFO] Connecting to database...
[INFO] Initializing Gmail API...
[INFO] Starting email processing...
[INFO] Phase 1: Gmail filtering (200,000 emails)
[INFO] Filtered to 24,088 financial emails (88% reduction)
[INFO] Phase 2: Parallel download (50 threads)
[INFO] Downloaded 24,088 emails in 2.0 minutes
[INFO] Phase 3: Database operations
[INFO] Inserted 24,088 records in 0.1 minutes
[INFO] Phase 4: OCR processing (16 parallel)
[INFO] Processed 24,088 attachments in 50.2 minutes
[INFO] Phase 5: Statement matching
[INFO] Matched 16,861 transactions (70% match rate)
[INFO] Phase 6: Excel generation
[INFO] Generated 5 Excel reports in 0.1 minutes
[INFO] Total processing time: 52.5 minutes
[INFO] FinMatcher completed successfully!
```

---

## 🔍 STEP 9: Verify Results

### Check Database Records
```bash
# Check processed emails
psql -U finmatcher_user -d finmatcher -c "SELECT COUNT(*) FROM processed_emails;"

# Check emails with attachments
psql -U finmatcher_user -d finmatcher -c "SELECT COUNT(*) FROM processed_emails WHERE attachment_file = TRUE;"

# Check matches
psql -U finmatcher_user -d finmatcher -c "SELECT COUNT(*) FROM matches;"
```

**Expected:**
- Total emails: 24,088 ✅
- With attachments: 24,088 ✅
- Matches found: ~16,000+ ✅

### Check Excel Reports
```bash
# List generated reports
dir reports

# Expected files:
# - Matched_Transactions_2026-03-01.xlsx
# - Unmatched_Transactions_2026-03-01.xlsx
# - Summary_Report_2026-03-01.xlsx
```

### Verify Excel Content
```bash
# Open Excel file
start reports\Matched_Transactions_2026-03-01.xlsx
```

**Expected Columns:**
- Email ID ✅
- Subject ✅
- Sender ✅
- Date ✅
- Amount ✅
- Attachment File ✅
- Match Confidence ✅
- Statement Reference ✅

---

## 🔧 STEP 10: Troubleshooting

### Issue 1: Database Connection Failed
```bash
# Check PostgreSQL service
sc query postgresql

# Start service if stopped
net start postgresql

# Test connection
psql -U finmatcher_user -d finmatcher -h localhost
```

### Issue 2: Gmail API Quota Exceeded
```bash
# Check quota usage
# Go to: https://console.cloud.google.com/apis/api/gmail.googleapis.com/quotas

# Solution: Wait or use multiple accounts
# Add to .env:
EMAIL_ACCOUNTS=email1@gmail.com,email2@gmail.com,email3@gmail.com
```

### Issue 3: OCR Processing Slow
```bash
# Increase parallel processes
# Edit config.yaml:
parallelism:
  process_pool_size: 32  # Increase from 16 to 32

# Or use GPU acceleration (if available)
```

### Issue 4: Memory Issues
```bash
# Reduce batch size
# Edit config.yaml:
memory:
  chunk_size: 5000  # Reduce from 10000 to 5000

# Monitor memory usage
Get-Process python | Select-Object WorkingSet
```

### Issue 5: Import Errors
```bash
# Reinstall dependencies
poetry install --no-cache

# Or clear cache and reinstall
pip cache purge
pip install -r requirements.txt --force-reinstall
```

---

## 📊 STEP 11: Performance Monitoring

### Monitor System Resources
```bash
# CPU usage
Get-Counter '\Processor(_Total)\% Processor Time'

# Memory usage
Get-Counter '\Memory\Available MBytes'

# Disk I/O
Get-Counter '\PhysicalDisk(_Total)\Disk Bytes/sec'
```

### Monitor Application Logs
```bash
# Real-time log monitoring
Get-Content logs\finmatcher.log -Wait -Tail 50

# Search for errors
Select-String -Path logs\finmatcher.log -Pattern "ERROR"

# Search for warnings
Select-String -Path logs\finmatcher.log -Pattern "WARNING"
```

### Performance Metrics
```bash
# Check processing speed
python -c "from finmatcher.utils.performance_monitor import PerformanceMonitor; pm = PerformanceMonitor(); pm.print_summary()"
```

---

## ✅ STEP 12: Production Checklist

### Pre-Deployment
- [ ] PostgreSQL installed and running
- [ ] .env file configured correctly
- [ ] Gmail API credentials configured
- [ ] All dependencies installed (`poetry install`)
- [ ] Database setup completed (`python setup_ubuntu.py`)
- [ ] Test run completed successfully

### Deployment
- [ ] Statements folder populated
- [ ] Output directories created
- [ ] Logging configured
- [ ] Monitoring in place
- [ ] Backup strategy defined

### Post-Deployment
- [ ] First production run successful
- [ ] Excel reports generated correctly
- [ ] Database records verified
- [ ] Performance metrics acceptable
- [ ] Error handling working
- [ ] Logs being captured

### Migration System Verification
- [ ] Only `migrate.py` used for migrations (not deprecated scripts)
- [ ] All migrations tracked in `schema_migrations` table
- [ ] `setup_ubuntu.py` used for initial setup
- [ ] Deprecated files (`.deprecated` extension) not referenced in code
- [ ] No references to removed scripts in documentation or code

---

## 🎯 Quick Start Commands

### Complete Setup (Run in Order)
```bash
# 1. Install dependencies
poetry install

# 2. Configure environment
cp .env.example .env
nano .env  # Edit with your credentials

# 3. Setup database (unified approach)
python setup_ubuntu.py

# 4. Test system
python test_fast_processor.py

# 5. Run production
python main.py
```

### Daily Operations
```bash
# Start processing
python main.py

# Monitor logs
tail -f logs/finmatcher.log

# Check results
ls -la reports/

# Verify database
psql -U finmatcher_user -d finmatcher -c "SELECT COUNT(*) FROM matches;"
```

### Migration Management
```bash
# Check migration status
python migrate.py status

# Apply new migrations
python migrate.py up

# Rollback if needed
python migrate.py down
```

---

## 🧹 System Cleanup

### Project Cleanup Summary

As part of the migration system consolidation, the following files have been removed or deprecated to eliminate redundancy and confusion:

#### Deprecated Migration Scripts

**Files moved to `.deprecated` extension:**

1. **`schema/migrate.py.deprecated`**
   - **Reason**: Separate v2-to-v3 migration script that didn't integrate with the main migration system
   - **Replacement**: `migrate.py` (unified migration manager)
   - **Impact**: All migrations now tracked in `schema_migrations` table

2. **`complete_setup.sh.deprecated`**
   - **Reason**: Bash-only setup script, not cross-platform, manually ran SQL files
   - **Replacement**: `setup_ubuntu.py` (Python-based, cross-platform)
   - **Impact**: Single unified entry point for complete database setup

#### Removed Redundant Setup Scripts

**Files deleted:**

3. **`setup_linux.sh`**
   - **Reason**: Redundant with `complete_setup.sh`, unclear purpose
   - **Replacement**: `setup_ubuntu.py`

4. **`reset_and_migrate.sh`**
   - **Reason**: Functionality absorbed into `migrate.py`
   - **Replacement**: `migrate.py up` command

5. **`fix_database.sh`**
   - **Reason**: Ad-hoc database fixes, not part of systematic migration
   - **Replacement**: `setup_ubuntu.py` for fresh setup, `migrate.py` for migrations

#### Removed Redundant Test Files

**Files deleted:**

6. **`comprehensive_project_test.py`**
   - **Reason**: From initial testing phase, no longer actively used
   - **Replacement**: Current test suite in `tests/` directory

7. **`comprehensive_validation_test.py`**
   - **Reason**: From validation phase, functionality covered by current tests
   - **Replacement**: Property-based tests in test suite

8. **`test_phase1_integration.py`**
   - **Reason**: Phase 1 integration complete, test no longer needed
   - **Replacement**: Integration tests in test suite

#### Removed Platform-Specific Cleanup Scripts

**Files deleted:**

9. **`cleanup.bat`**
   - **Reason**: Windows-specific, not needed for Ubuntu deployment
   - **Replacement**: `cleanup.py` (cross-platform Python script)

10. **`deep_cleanup.bat`**
    - **Reason**: Windows-specific, redundant with `cleanup.py`
    - **Replacement**: `cleanup.py` with appropriate flags

### Benefits of Consolidation

**Before Consolidation:**
- 3 separate migration systems (migrate.py, schema/migrate.py, complete_setup.sh)
- 5 overlapping setup scripts with unclear purposes
- 3 redundant test files cluttering the project
- 3 platform-specific cleanup scripts

**After Consolidation:**
- ✅ 1 unified migration system (`migrate.py` + `schema/migrations/`)
- ✅ 1 primary setup script for Ubuntu (`setup_ubuntu.py`)
- ✅ Clear test organization in `tests/` directory
- ✅ 1 cross-platform cleanup script (`cleanup.py`)

### Migration Workflow (New System)

```
┌─────────────────────────────────────────────────────────┐
│                   Fresh Installation                     │
│                                                          │
│  1. Configure .env                                       │
│  2. Run: python setup_ubuntu.py                         │
│     ├─ Creates database                                 │
│     ├─ Creates schema_migrations table                  │
│     ├─ Runs all migrations from schema/migrations/      │
│     └─ Validates setup                                  │
│                                                          │
│  Result: Database ready for use                         │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│                  Ongoing Migrations                      │
│                                                          │
│  1. Developer adds new migration to schema/migrations/   │
│     (e.g., 004_add_new_feature.sql)                     │
│                                                          │
│  2. Check status: python migrate.py status              │
│     Shows: Pending migrations: 004_add_new_feature.sql  │
│                                                          │
│  3. Apply migration: python migrate.py up               │
│     ├─ Reads schema/migrations/004_add_new_feature.sql  │
│     ├─ Executes SQL                                     │
│     └─ Records in schema_migrations table               │
│                                                          │
│  Result: Database updated with new schema               │
└─────────────────────────────────────────────────────────┘
```

### Cleanup Script (Ubuntu/Linux)

The project includes a cross-platform cleanup script for removing temporary files, cache, and logs:

```bash
# Run cleanup script
python cleanup.py
```

**What gets cleaned:**
- Python cache files (`__pycache__`, `.pyc`, `.pyo`)
- Log files (`logs/*.log`)
- Temporary attachments (`temp_attachments/*`)
- Output files (`output/*`)
- Excel reports (`reports/*.xlsx`)
- Attachments (`attachments/*`)
- Kiro cache (`.kiro/cache`)
- Test cache (`.pytest_cache`)
- Coverage reports (`htmlcov`, `.coverage`)
- SQLite database (if exists)

**Note:** PostgreSQL database records and configuration files (`.env`, `config.yaml`) are preserved.

### Manual Cleanup
```bash
# Clean Python cache only
find . -type d -name "__pycache__" -exec rm -rf {} +
find . -type f -name "*.pyc" -delete

# Clean logs only
rm -f logs/*.log

# Clean temporary files only
rm -rf temp_attachments/*
rm -rf output/*
```

---

## 📞 Support & Resources

### Documentation
- Project README: `README.md`
- API Documentation: `docs/api.md`
- Configuration Guide: `config.yaml`

### Logs Location
- Application logs: `logs/finmatcher.log`
- Error logs: `logs/errors.log`
- Performance logs: `logs/performance.log`

### Database Backup
```bash
# Backup database
pg_dump -U finmatcher_user finmatcher > backup_$(date +%Y%m%d).sql

# Restore database
psql -U finmatcher_user finmatcher < backup_20260301.sql
```

---

## 🎉 Success Indicators

Your system is working correctly if:
- ✅ Processing time < 1 hour for 200k emails
- ✅ 88%+ email reduction through filtering
- ✅ 70%+ match rate for transactions
- ✅ Excel reports generated successfully
- ✅ No errors in logs
- ✅ Memory usage stable
- ✅ Database records accurate

---

**🚀 Your FinMatcher system is now ready for production!**

For issues or questions, check the troubleshooting section or review logs.
