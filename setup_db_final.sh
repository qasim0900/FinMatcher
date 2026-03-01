#!/bin/bash
# ============================================================================
# FinMatcher Database Setup - Final Working Version
# ============================================================================

set -e

echo "🚀 FinMatcher Database Setup"
echo "=============================="

DB_NAME="FinMatcher"
DB_USER="postgres"
DB_PASSWORD="Teeli@322"

# Get absolute path to schema file
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCHEMA_FILE="$SCRIPT_DIR/schema/finmatcher_complete_schema.sql"

echo ""
echo "📁 Working directory: $SCRIPT_DIR"
echo "📄 Schema file: $SCHEMA_FILE"

# Check if schema file exists
if [ ! -f "$SCHEMA_FILE" ]; then
    echo "❌ Schema file not found: $SCHEMA_FILE"
    exit 1
fi

echo "✅ Schema file found"

# Step 1: Create Database
echo ""
echo "📊 Step 1: Creating database..."
PGPASSWORD="$DB_PASSWORD" psql -U postgres -h localhost <<EOF
DROP DATABASE IF EXISTS "$DB_NAME";
CREATE DATABASE "$DB_NAME";
EOF

echo "✅ Database created"

# Step 2: Run Schema
echo ""
echo "📋 Step 2: Creating schema..."
PGPASSWORD="$DB_PASSWORD" psql -U postgres -h localhost -d "$DB_NAME" -f "$SCHEMA_FILE"

echo "✅ Schema created"

# Step 3: Verify Tables
echo ""
echo "🔍 Step 3: Verifying tables..."
TABLE_COUNT=$(PGPASSWORD="$DB_PASSWORD" psql -U postgres -h localhost -d "$DB_NAME" -tAc "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='public';")

echo "   Tables created: $TABLE_COUNT"

if [ "$TABLE_COUNT" -ge "6" ]; then
    echo "✅ All tables verified"
else
    echo "⚠️  Expected 6+ tables, found $TABLE_COUNT"
fi

# Step 4: List Tables
echo ""
echo "📋 Tables in database:"
PGPASSWORD="$DB_PASSWORD" psql -U postgres -h localhost -d "$DB_NAME" -c "\dt"

# Step 5: Test Python Connection
echo ""
echo "🧪 Step 4: Testing Python connection..."
python3 << PYTHON_EOF
import psycopg2
try:
    conn = psycopg2.connect(
        dbname='$DB_NAME',
        user='$DB_USER',
        password='$DB_PASSWORD',
        host='localhost'
    )
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='public';")
    count = cursor.fetchone()[0]
    print(f"✅ Python connection successful! Tables: {count}")
    conn.close()
except Exception as e:
    print(f"❌ Python connection failed: {e}")
    exit(1)
PYTHON_EOF

# Final Summary
echo ""
echo "=============================="
echo "✅ Setup Complete!"
echo "=============================="
echo ""
echo "📝 Connection Details:"
echo "   Database: $DB_NAME"
echo "   User: $DB_USER"
echo "   Host: localhost"
echo "   Port: 5432"
echo ""
echo "🔗 Connection String:"
echo "   postgresql://$DB_USER:$DB_PASSWORD@localhost:5432/$DB_NAME"
echo ""
echo "🚀 Next Steps:"
echo "   1. Run: python phase1_core_integration.py"
echo "   2. Or connect: psql -U postgres -h localhost -d $DB_NAME"
echo ""
