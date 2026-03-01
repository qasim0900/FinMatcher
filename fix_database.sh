#!/bin/bash
# FinMatcher - Database Fix Script
# Automatically creates database and tables

set -e  # Exit on error

echo "========================================"
echo "FinMatcher - Database Fix"
echo "========================================"
echo

# Database credentials
DB_HOST="localhost"
DB_PORT="5432"
DB_NAME="FinMatcher"
DB_USER="postgres"
DB_PASS="Teeli@322"

export PGPASSWORD="$DB_PASS"

echo "Step 1: Checking PostgreSQL connection..."
if psql -U "$DB_USER" -h "$DB_HOST" -c "SELECT 1;" > /dev/null 2>&1; then
    echo "✅ PostgreSQL connection successful"
else
    echo "❌ PostgreSQL connection failed"
    echo "Please check:"
    echo "  1. PostgreSQL is running: sudo systemctl status postgresql"
    echo "  2. Password is correct: Teeli@322"
    echo "  3. User 'postgres' exists"
    exit 1
fi

echo
echo "Step 2: Checking if database exists..."
if psql -U "$DB_USER" -h "$DB_HOST" -lqt | cut -d \| -f 1 | grep -qw "$DB_NAME"; then
    echo "✅ Database '$DB_NAME' exists"
else
    echo "⚠️  Database '$DB_NAME' does not exist. Creating..."
    psql -U "$DB_USER" -h "$DB_HOST" -c "CREATE DATABASE \"$DB_NAME\";"
    echo "✅ Database created"
fi

echo
echo "Step 3: Dropping existing tables (if any)..."
psql -U "$DB_USER" -d "$DB_NAME" -h "$DB_HOST" << EOF
DROP TABLE IF EXISTS matches CASCADE;
DROP TABLE IF EXISTS matching_statistics CASCADE;
DROP TABLE IF EXISTS receipts CASCADE;
DROP TABLE IF EXISTS transactions CASCADE;
DROP TABLE IF EXISTS processed_emails CASCADE;
EOF
echo "✅ Old tables dropped"

echo
echo "Step 4: Creating tables from schema..."
if [ -f "schema/init_v3.sql" ]; then
    psql -U "$DB_USER" -d "$DB_NAME" -h "$DB_HOST" -f schema/init_v3.sql
    echo "✅ Tables created from init_v3.sql"
else
    echo "❌ schema/init_v3.sql not found"
    exit 1
fi

echo
echo "Step 5: Adding optimization fields..."
if [ -f "schema/add_attachment_fields.sql" ]; then
    psql -U "$DB_USER" -d "$DB_NAME" -h "$DB_HOST" -f schema/add_attachment_fields.sql 2>/dev/null || true
    echo "✅ Optimization fields added"
else
    echo "⚠️  schema/add_attachment_fields.sql not found (optional)"
fi

echo
echo "Step 6: Creating indexes..."
psql -U "$DB_USER" -d "$DB_NAME" -h "$DB_HOST" << EOF
-- Create performance indexes
CREATE INDEX IF NOT EXISTS idx_emails_attachment_file 
ON processed_emails(attachment_file) 
WHERE attachment_file = TRUE;

CREATE INDEX IF NOT EXISTS idx_emails_date 
ON processed_emails(date);

CREATE INDEX IF NOT EXISTS idx_transactions_date 
ON transactions(date);

CREATE INDEX IF NOT EXISTS idx_receipts_date 
ON receipts(date);

CREATE INDEX IF NOT EXISTS idx_matches_transaction 
ON matches(transaction_id);

CREATE INDEX IF NOT EXISTS idx_matches_receipt 
ON matches(receipt_id);
EOF
echo "✅ Indexes created"

echo
echo "Step 7: Verifying tables..."
echo "Tables in database:"
psql -U "$DB_USER" -d "$DB_NAME" -h "$DB_HOST" -c "\dt"

echo
echo "Step 8: Checking processed_emails structure..."
psql -U "$DB_USER" -d "$DB_NAME" -h "$DB_HOST" -c "\d processed_emails"

echo
echo "Step 9: Testing insert..."
psql -U "$DB_USER" -d "$DB_NAME" -h "$DB_HOST" << EOF
INSERT INTO processed_emails (message_id, subject, sender, date, has_attachment, attachment_file)
VALUES ('test_fix_001', 'Test Email', 'test@example.com', NOW(), TRUE, TRUE);

SELECT * FROM processed_emails WHERE message_id = 'test_fix_001';

DELETE FROM processed_emails WHERE message_id = 'test_fix_001';
EOF
echo "✅ Insert test successful"

echo
echo "========================================"
echo "✅ Database Fix Complete!"
echo "========================================"
echo
echo "Database Details:"
echo "  Host: $DB_HOST"
echo "  Port: $DB_PORT"
echo "  Database: $DB_NAME"
echo "  User: $DB_USER"
echo "  Connection: postgresql://$DB_USER:***@$DB_HOST:$DB_PORT/$DB_NAME"
echo
echo "Next steps:"
echo "  1. Run tests: python configure_and_test.py"
echo "  2. Run application: python main.py"
echo

unset PGPASSWORD
