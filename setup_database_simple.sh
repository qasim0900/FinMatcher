#!/bin/bash
# ============================================================================
# FinMatcher Database Setup - Simple Version (Using sudo)
# ============================================================================

set -e

echo "🚀 FinMatcher Database Setup (Simple Mode)"
echo "=========================================="

DB_NAME="FinMatcher"
DB_USER="postgres"
DB_PASSWORD="Teeli@322"

# Step 1: Create/Recreate Database
echo ""
echo "📊 Creating database..."
sudo -u postgres psql <<EOF
DROP DATABASE IF EXISTS "$DB_NAME";
CREATE DATABASE "$DB_NAME";
ALTER USER $DB_USER WITH PASSWORD '$DB_PASSWORD';
GRANT ALL PRIVILEGES ON DATABASE "$DB_NAME" TO $DB_USER;
EOF

echo "✅ Database created"

# Step 2: Run Schema (using sudo -u postgres)
echo ""
echo "📋 Creating schema..."
sudo -u postgres psql -d "$DB_NAME" -f schema/finmatcher_complete_schema.sql

echo ""
echo "✅ Schema created"

# Step 3: Verify
echo ""
echo "🔍 Verifying tables..."
sudo -u postgres psql -d "$DB_NAME" -c "\dt"

echo ""
echo "=========================================="
echo "✅ Setup Complete!"
echo "=========================================="
echo ""
echo "Connection String:"
echo "postgresql://$DB_USER:$DB_PASSWORD@localhost:5432/$DB_NAME"
echo ""
echo "Test connection:"
echo "sudo -u postgres psql -d $DB_NAME"
