#!/bin/bash
# FinMatcher - Complete Setup Script
# Fixes all issues and sets up the system

set -e  # Exit on error

echo "========================================================================"
echo "  FinMatcher - Complete Setup & Fix"
echo "========================================================================"
echo

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Database credentials
DB_HOST="localhost"
DB_PORT="5432"
DB_NAME="FinMatcher"
DB_USER="postgres"
DB_PASS="Teeli@322"

export PGPASSWORD="$DB_PASS"

echo -e "${BLUE}[1/8] Checking PostgreSQL connection...${NC}"
if psql -U "$DB_USER" -h "$DB_HOST" -c "SELECT 1;" > /dev/null 2>&1; then
    echo -e "${GREEN}✅ PostgreSQL connection successful${NC}"
else
    echo -e "${RED}❌ PostgreSQL connection failed${NC}"
    echo "Please check:"
    echo "  1. PostgreSQL is running: sudo systemctl status postgresql"
    echo "  2. Password is correct: Teeli@322"
    exit 1
fi

echo
echo -e "${BLUE}[2/8] Dropping and recreating database...${NC}"
psql -U "$DB_USER" -h "$DB_HOST" -c "DROP DATABASE IF EXISTS \"$DB_NAME\";" 2>/dev/null || true
psql -U "$DB_USER" -h "$DB_HOST" -c "CREATE DATABASE \"$DB_NAME\";"
echo -e "${GREEN}✅ Database recreated${NC}"

echo
echo -e "${BLUE}[3/8] Creating tables from schema...${NC}"
if [ -f "schema/init_v3.sql" ]; then
    psql -U "$DB_USER" -d "$DB_NAME" -h "$DB_HOST" -f schema/init_v3.sql
    echo -e "${GREEN}✅ Tables created${NC}"
else
    echo -e "${RED}❌ schema/init_v3.sql not found${NC}"
    exit 1
fi

echo
echo -e "${BLUE}[4/8] Adding optimization fields...${NC}"
if [ -f "schema/add_attachment_fields.sql" ]; then
    psql -U "$DB_USER" -d "$DB_NAME" -h "$DB_HOST" -f schema/add_attachment_fields.sql
    echo -e "${GREEN}✅ Optimization fields added${NC}"
else
    echo -e "${YELLOW}⚠️  schema/add_attachment_fields.sql not found${NC}"
fi

echo
echo -e "${BLUE}[5/8] Creating performance indexes...${NC}"
psql -U "$DB_USER" -d "$DB_NAME" -h "$DB_HOST" << EOF
-- Additional performance indexes
CREATE INDEX IF NOT EXISTS idx_emails_date ON processed_emails(date);
CREATE INDEX IF NOT EXISTS idx_emails_sender ON processed_emails(sender);
CREATE INDEX IF NOT EXISTS idx_transactions_date ON transactions(date);
CREATE INDEX IF NOT EXISTS idx_receipts_date ON receipts(date);
CREATE INDEX IF NOT EXISTS idx_matches_transaction ON matches(transaction_id);
CREATE INDEX IF NOT EXISTS idx_matches_receipt ON matches(receipt_id);
EOF
echo -e "${GREEN}✅ Indexes created${NC}"

echo
echo -e "${BLUE}[6/8] Verifying database setup...${NC}"
echo "Tables in database:"
psql -U "$DB_USER" -d "$DB_NAME" -h "$DB_HOST" -c "\dt" | grep -E "processed_emails|transactions|receipts|matches"

echo
echo -e "${BLUE}[7/8] Testing database operations...${NC}"
psql -U "$DB_USER" -d "$DB_NAME" -h "$DB_HOST" << EOF > /dev/null 2>&1
-- Test insert
INSERT INTO processed_emails (message_id, subject, sender, date, has_attachment, attachment_file)
VALUES ('test_setup_001', 'Test Email', 'test@example.com', NOW(), TRUE, TRUE);

-- Test select
SELECT COUNT(*) FROM processed_emails WHERE message_id = 'test_setup_001';

-- Cleanup
DELETE FROM processed_emails WHERE message_id = 'test_setup_001';
EOF
echo -e "${GREEN}✅ Database operations working${NC}"

echo
echo -e "${BLUE}[8/8] Setting up Python environment...${NC}"
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
echo "export PYTHONPATH=\"\${PYTHONPATH}:$(pwd)\"" >> ~/.bashrc
echo -e "${GREEN}✅ Python path configured${NC}"

echo
echo "========================================================================"
echo -e "${GREEN}✅ Setup Complete!${NC}"
echo "========================================================================"
echo
echo "Database Details:"
echo "  Host: $DB_HOST"
echo "  Port: $DB_PORT"
echo "  Database: $DB_NAME"
echo "  User: $DB_USER"
echo "  Connection: postgresql://$DB_USER:***@$DB_HOST:$DB_PORT/$DB_NAME"
echo
echo "Tables Created:"
psql -U "$DB_USER" -d "$DB_NAME" -h "$DB_HOST" -c "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' ORDER BY table_name;" -t | sed 's/^/ - /'
echo
echo "Next Steps:"
echo "  1. Run tests: python configure_and_test.py"
echo "  2. If all tests pass, run: python main.py"
echo

unset PGPASSWORD
