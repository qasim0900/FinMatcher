# FinMatcher v1.0 to v2.0 Migration Guide

This directory contains migration scripts to upgrade your FinMatcher installation from v1.0 to v2.0.

## Overview

The v2.0 upgrade introduces:
- **Semantic scoring** using DeepSeek AI for improved matching accuracy
- **Financial email filtering** with three-layer filtering (auto-reject, auto-accept, AI-verified)
- **Enhanced folder structure** with 8 specialized folders for better organization
- **New database columns** for semantic scores and filter methods

## Migration Scripts

### 1. Database Migration (`database_migration.py`)

Migrates your SQLite database from v1.0 to v2.0 schema.

**What it does:**
- Creates a timestamped backup of your existing database
- Adds `semantic_score` column to the `matches` table (default: 0.0)
- Adds `filter_method` column to the `receipts` table (default: NULL)
- Recalculates composite scores for existing matches
- Verifies data integrity after migration

**Usage:**

```bash
# Basic usage (default database path: finmatcher.db)
python -m finmatcher.migration.database_migration

# Specify custom database path
python -m finmatcher.migration.database_migration --db-path /path/to/your/database.db

# Enable debug logging
python -m finmatcher.migration.database_migration --log-level DEBUG
```

**Options:**
- `--db-path`: Path to the database file (default: `finmatcher.db`)
- `--log-level`: Logging level - DEBUG, INFO, WARNING, ERROR (default: `INFO`)

**Backup:**
The script automatically creates a backup before migration:
- Backup location: `{database_name}_v1_backup_{timestamp}.db`
- Example: `finmatcher_v1_backup_20240115_143022.db`

**Rollback:**
If migration fails, restore from the backup:
```bash
cp finmatcher_v1_backup_20240115_143022.db finmatcher.db
```

### 2. Drive Folder Migration (`drive_migration.py`)

Migrates your Google Drive folder structure from v1.0 to v2.0.

**What it does:**
- Authenticates with Google Drive API
- Creates the new 8-folder hierarchy
- Copies files from old folders to new folders based on file type
- Preserves all existing files (non-destructive)

**V1.0 Structure (Old):**
```
FinMatcher_Reports/
├── Matched_Records/
├── Unmatched_Receipts/
└── Attachments/
```

**V2.0 Structure (New):**
```
FinMatcher_Excel_Reports/
├── {Statement_File_Name}_record.xlsx/
├── Other_receipts_email.xlsx/
├── unmatch_email_records.xlsx/
├── Attach_files/
├── Attach_Image/
├── Unmatch_Email_Attach_files/
└── unmatch_attach_image/
```

**Usage:**

```bash
# Basic usage (default credentials path: auth_files/credentials.json)
python -m finmatcher.migration.drive_migration

# Specify custom credentials path
python -m finmatcher.migration.drive_migration --credentials /path/to/credentials.json

# Specify custom folder names
python -m finmatcher.migration.drive_migration \
    --old-root "MyOldFolder" \
    --new-root "MyNewFolder"

# Enable debug logging
python -m finmatcher.migration.drive_migration --log-level DEBUG
```

**Options:**
- `--credentials`: Path to credentials.json file (default: `auth_files/credentials.json`)
- `--old-root`: Name of v1.0 root folder (default: `FinMatcher_Reports`)
- `--new-root`: Name of v2.0 root folder (default: `FinMatcher_Excel_Reports`)
- `--log-level`: Logging level - DEBUG, INFO, WARNING, ERROR (default: `INFO`)

**File Mapping:**
The script automatically maps files based on type:
- **PDF, DOC, DOCX** → `Attach_files/`
- **JPG, JPEG, PNG, GIF** → `Attach_Image/`
- **XLSX, XLS** → `Other_receipts_email.xlsx/`

**Authentication:**
On first run, the script will:
1. Open a browser window for Google OAuth authentication
2. Save credentials to `token.json` for future use
3. Reuse saved credentials on subsequent runs

## Migration Workflow

Follow these steps to migrate from v1.0 to v2.0:

### Step 1: Backup Your Data

Before starting, create manual backups:

```bash
# Backup database
cp finmatcher.db finmatcher_manual_backup.db

# Backup credentials
cp -r auth_files auth_files_backup
```

### Step 2: Migrate Database

```bash
python -m finmatcher.migration.database_migration --db-path finmatcher.db
```

**Expected output:**
```
============================================================
Starting database migration from v1.0 to v2.0
============================================================
Creating backup: finmatcher_v1_backup_20240115_143022.db
Backup created successfully: finmatcher_v1_backup_20240115_143022.db (2048576 bytes)
Connected to database
Current schema version: v1.0
Adding semantic_score column to matches table
semantic_score column added successfully
Adding filter_method column to receipts table
filter_method column added successfully
Recalculating composite scores for existing matches
Found 1523 matches to recalculate
Recalculated composite scores for 1523 matches
Verifying data integrity
Record counts: 856 transactions, 1234 receipts, 1523 matches
Data integrity verification passed
============================================================
Migration completed successfully!
Backup saved at: finmatcher_v1_backup_20240115_143022.db
============================================================

✓ Migration completed successfully!
✓ Backup saved at: finmatcher_v1_backup_20240115_143022.db
```

### Step 3: Migrate Drive Folders

```bash
python -m finmatcher.migration.drive_migration --credentials auth_files/credentials.json
```

**Expected output:**
```
============================================================
Starting Drive folder migration from v1.0 to v2.0
============================================================
Google Drive authentication successful
Looking for v1.0 root folder: FinMatcher_Reports
Found v1.0 root folder (ID: 1a2b3c4d5e6f7g8h9i0j)
Creating v2.0 folder structure
Created folder: FinMatcher_Excel_Reports (ID: 9i8h7g6f5e4d3c2b1a0)
Created 6 subfolders in v2.0 structure
Migrating contents from: Matched_Records
Found 234 files to migrate
Migrated 234/234 files from Matched_Records
Migrating contents from: Unmatched_Receipts
Found 89 files to migrate
Migrated 89/89 files from Unmatched_Receipts
Migrating contents from: Attachments
Found 456 files to migrate
Migrated 456/456 files from Attachments
  Other_receipts_email.xlsx: 234 files
  unmatch_email_records.xlsx: 89 files
  Attach_files: 312 files
  Attach_Image: 144 files
============================================================
Migration completed successfully!
Total files in v2.0 structure: 779
New root folder: FinMatcher_Excel_Reports (ID: 9i8h7g6f5e4d3c2b1a0)
============================================================

✓ Migration completed successfully!
✓ New root folder: FinMatcher_Excel_Reports
```

### Step 4: Verify Migration

After migration, verify that:

1. **Database:**
   - Backup file exists
   - All tables have correct schema
   - Record counts match

2. **Drive:**
   - New folder structure exists
   - All files are present in new folders
   - File counts match

3. **Application:**
   - Run a test matching operation
   - Verify reports are generated correctly
   - Check that attachments are routed properly

### Step 5: Update Configuration

Update your `config.yaml` to use v2.0 features:

```yaml
matching:
  weights:
    amount: 0.4
    date: 0.3
    semantic: 0.3  # New in v2.0

financial_filter:
  enable_ai: true  # New in v2.0
  financial_keywords:
    - receipt
    - invoice
    - bill
    # ... more keywords
  marketing_spam_keywords:
    - unsubscribe
    - newsletter
    # ... more keywords

deepseek:
  api_key: ${DEEPSEEK_API_KEY}  # New in v2.0
  timeout: 30
  max_tokens: 512
```

## Troubleshooting

### Database Migration Issues

**Issue:** Migration fails with "duplicate column name"
```
Solution: Database is already at v2.0, no migration needed
```

**Issue:** Data integrity verification fails
```
Solution: Restore from backup and check database for corruption
```

**Issue:** Permission denied error
```
Solution: Ensure you have write permissions for the database file
```

### Drive Migration Issues

**Issue:** Authentication fails
```
Solution: 
1. Check credentials.json is valid
2. Delete token.json and re-authenticate
3. Ensure you have Drive API enabled in Google Cloud Console
```

**Issue:** Old folder not found
```
Solution: 
1. Check folder name matches exactly (case-sensitive)
2. Use --old-root flag to specify correct name
3. If no old folder exists, script will create fresh v2.0 structure
```

**Issue:** File copy fails
```
Solution:
1. Check you have sufficient Drive storage
2. Verify file permissions
3. Check network connectivity
```

## Post-Migration

After successful migration:

1. **Keep backups** for at least 30 days
2. **Monitor logs** for any issues with new features
3. **Test thoroughly** before processing production data
4. **Update documentation** with new folder locations

## Rollback Procedure

If you need to rollback to v1.0:

### Database Rollback:
```bash
# Restore from backup
cp finmatcher_v1_backup_20240115_143022.db finmatcher.db
```

### Drive Rollback:
```
Note: Drive migration is non-destructive (copies files, doesn't move them)
Your old v1.0 folders remain intact, so no rollback needed
```

## Support

For issues or questions:
1. Check logs for detailed error messages
2. Verify all prerequisites are met
3. Ensure backups are created before migration
4. Contact support with log files if issues persist

## Version Compatibility

- **Python:** 3.10+
- **SQLite:** 3.35+
- **Google Drive API:** v3
- **Dependencies:** See requirements.txt
