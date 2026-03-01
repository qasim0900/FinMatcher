#!/bin/bash
# ============================================================================
# FinMatcher Database Setup Script
# ============================================================================
# Purpose: Automated database setup for FinMatcher project
# Usage: bash setup_database.sh
# ============================================================================

set -e  # Exit on error

echo "🚀 FinMatcher Database Setup Starting..."
echo "=========================================="

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration (from .env file)
DB_NAME="FinMatcher"
DB_USER="postgres"
DB_PASSWORD="Teeli@322"  # Update if different

echo ""
echo "📋 Configuration:"
echo "   Database: $DB_NAME"
echo "   User: $DB_USER"
echo ""

# Step 1: Check if PostgreSQL is installed
echo "🔍 Step 1: Checking PostgreSQL installation..."
if ! command -v psql &> /dev/null; then
    echo -e "${RED}❌ PostgreSQL is not installed!${NC}"
    echo "   Install with: sudo apt-get install postgresql postgresql-contrib"
    exit 1
fi
echo -e "${GREEN}✅ PostgreSQL is installed${NC}"

# Step 2: Check if PostgreSQL service is running
echo ""
echo "🔍 Step 2: Checking PostgreSQL service..."
if ! sudo systemctl is-active --quiet postgresql; then
    echo -e "${YELLOW}⚠️  PostgreSQL service is not running. Starting...${NC}"
    sudo systemctl start postgresql
    sleep 2
fi
echo -e "${GREEN}✅ PostgreSQL service is running${NC}"

# Step 3: Check if database exists
echo ""
echo "🔍 Step 3: Checking if database exists..."
DB_EXISTS=$(sudo -u postgres psql -tAc "SELECT 1 FROM pg_database WHERE datname='$DB_NAME'")

if [ "$DB_EXISTS" = "1" ]; then
    echo -e "${YELLOW}⚠️  Database '$DB_NAME' already exists${NC}"
    read -p "   Do you want to drop and recreate it? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "   Dropping existing database..."
        sudo -u postgres psql -c "DROP DATABASE \"$DB_NAME\";"
        echo -e "${GREEN}✅ Database dropped${NC}"
    else
        echo "   Keeping existing database..."
    fi
fi

# Step 4: Create database if it doesn't exist
if [ "$DB_EXISTS" != "1" ] || [[ $REPLY =~ ^[Yy]$ ]]; then
    echo ""
    echo "🔨 Step 4: Creating database..."
    sudo -u postgres psql -c "CREATE DATABASE \"$DB_NAME\";"
    echo -e "${GREEN}✅ Database '$DB_NAME' created${NC}"
fi

# Step 5: Set password for postgres user
echo ""
echo "🔐 Step 5: Setting user password..."
sudo -u postgres psql -c "ALTER USER $DB_USER WITH PASSWORD '$DB_PASSWORD';"
echo -e "${GREEN}✅ Password set for user '$DB_USER'${NC}"

# Step 6: Grant privileges
echo ""
echo "🔑 Step 6: Granting privileges..."
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE \"$DB_NAME\" TO $DB_USER;"
echo -e "${GREEN}✅ Privileges granted${NC}"

# Step 7: Run schema script
echo ""
echo "📊 Step 7: Creating database schema..."
if [ -f "schema/finmatcher_complete_schema.sql" ]; then
    PGPASSWORD=$DB_PASSWORD psql -U $DB_USER -d $DB_NAME -f schema/finmatcher_complete_schema.sql
    echo -e "${GREEN}✅ Schema created successfully${NC}"
else
    echo -e "${RED}❌ Schema file not found: schema/finmatcher_complete_schema.sql${NC}"
    exit 1
fi

# Step 8: Verify tables
echo ""
echo "🔍 Step 8: Verifying tables..."
TABLE_COUNT=$(PGPASSWORD=$DB_PASSWORD psql -U $DB_USER -d $DB_NAME -tAc "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='public';")
echo "   Tables created: $TABLE_COUNT"

if [ "$TABLE_COUNT" -ge "6" ]; then
    echo -e "${GREEN}✅ All tables created successfully${NC}"
else
    echo -e "${YELLOW}⚠️  Expected 6+ tables, found $TABLE_COUNT${NC}"
fi

# Step 9: List tables
echo ""
echo "📋 Tables in database:"
PGPASSWORD=$DB_PASSWORD psql -U $DB_USER -d $DB_NAME -c "\dt"

# Step 10: Test connection
echo ""
echo "🧪 Step 9: Testing database connection..."
python3 -c "
import psycopg2
try:
    conn = psycopg2.connect(
        dbname='$DB_NAME',
        user='$DB_USER',
        password='$DB_PASSWORD',
        host='localhost'
    )
    print('${GREEN}✅ Python connection successful${NC}')
    conn.close()
except Exception as e:
    print('${RED}❌ Python connection failed:', e, '${NC}')
    exit(1)
"

# Final summary
echo ""
echo "=========================================="
echo -e "${GREEN}🎉 Database Setup Complete!${NC}"
echo "=========================================="
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
echo "📊 Next Steps:"
echo "   1. Update .env file (already done ✅)"
echo "   2. Run: python phase1_core_integration.py"
echo "   3. Check logs: tail -f logs/finmatcher.log"
echo ""
echo "🔍 Useful Commands:"
echo "   Connect: psql -U $DB_USER -d $DB_NAME"
echo "   List tables: \dt"
echo "   List indexes: \di"
echo "   View data: SELECT * FROM processed_emails LIMIT 10;"
echo ""
echo -e "${GREEN}✅ Ready for production!${NC}"
