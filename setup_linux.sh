#!/bin/bash
# FinMatcher - Linux Setup Script

set -e  # Exit on error

echo "========================================"
echo "FinMatcher - Linux Setup"
echo "========================================"
echo

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if running from correct directory
if [ ! -d "finmatcher" ]; then
    echo -e "${RED}ERROR: Please run this script from the FinMatcher project root directory${NC}"
    exit 1
fi

echo "Step 1: Configuring PostgreSQL..."
echo "=================================="

# Check if PostgreSQL is installed
if ! command -v psql &> /dev/null; then
    echo -e "${RED}PostgreSQL is not installed. Installing...${NC}"
    sudo apt-get update
    sudo apt-get install -y postgresql postgresql-contrib
fi

# Check if PostgreSQL is running
if ! sudo systemctl is-active --quiet postgresql; then
    echo "Starting PostgreSQL..."
    sudo systemctl start postgresql
fi

# Configure pg_hba.conf for password authentication
PG_VERSION=$(psql --version | grep -oP '\d+' | head -1)
PG_HBA_FILE="/etc/postgresql/${PG_VERSION}/main/pg_hba.conf"

echo "Configuring PostgreSQL authentication..."
sudo sed -i 's/local\s*all\s*postgres\s*peer/local   all             postgres                                md5/' "$PG_HBA_FILE"
sudo sed -i 's/local\s*all\s*all\s*peer/local   all             all                                     md5/' "$PG_HBA_FILE"

# Restart PostgreSQL
echo "Restarting PostgreSQL..."
sudo systemctl restart postgresql

echo -e "${GREEN}✓ PostgreSQL configured${NC}"
echo

echo "Step 2: Setting up database..."
echo "=================================="

# Set password for postgres user
echo "Setting PostgreSQL password..."
sudo -u postgres psql -c "ALTER USER postgres WITH PASSWORD 'Teeli@322';" 2>/dev/null || true

# Create database
echo "Creating FinMatcher database..."
PGPASSWORD='Teeli@322' psql -U postgres -h localhost -c "DROP DATABASE IF EXISTS \"FinMatcher\";" 2>/dev/null || true
PGPASSWORD='Teeli@322' psql -U postgres -h localhost -c "CREATE DATABASE \"FinMatcher\";"

# Run migrations
echo "Running database migrations..."
PGPASSWORD='Teeli@322' psql -U postgres -d FinMatcher -h localhost -f schema/init_v3.sql

# Add optimization fields
if [ -f "schema/add_attachment_fields.sql" ]; then
    echo "Adding optimization fields..."
    PGPASSWORD='Teeli@322' psql -U postgres -d FinMatcher -h localhost -f schema/add_attachment_fields.sql
fi

echo -e "${GREEN}✓ Database setup complete${NC}"
echo

echo "Step 3: Setting up Python environment..."
echo "=================================="

# Add project to PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
echo "export PYTHONPATH=\"\${PYTHONPATH}:$(pwd)\"" >> ~/.bashrc

# Check if virtual environment exists
if [ ! -d ".venv" ] && [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
    source venv/bin/activate
else
    if [ -d ".venv" ]; then
        source .venv/bin/activate
    else
        source venv/bin/activate
    fi
fi

# Install dependencies
echo "Installing Python dependencies..."
if [ -f "pyproject.toml" ]; then
    pip install poetry
    poetry install
else
    pip install -r requirements.txt 2>/dev/null || pip install pandas numpy scikit-learn pybloom-live psycopg2-binary python-dotenv pyyaml
fi

echo -e "${GREEN}✓ Python environment setup complete${NC}"
echo

echo "Step 4: Creating necessary directories..."
echo "=================================="

mkdir -p logs
mkdir -p output
mkdir -p reports
mkdir -p temp_attachments
mkdir -p attachments
mkdir -p finmatcher/auth_files

echo -e "${GREEN}✓ Directories created${NC}"
echo

echo "Step 5: Verifying setup..."
echo "=================================="

# Test database connection
echo -n "Testing database connection... "
if PGPASSWORD='Teeli@322' psql -U postgres -d FinMatcher -h localhost -c "SELECT 1;" > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC}"
else
    echo -e "${RED}✗${NC}"
    exit 1
fi

# Test Python imports
echo -n "Testing Python imports... "
if python -c "from finmatcher.config.settings import get_settings" 2>/dev/null; then
    echo -e "${GREEN}✓${NC}"
else
    echo -e "${RED}✗${NC}"
    echo -e "${YELLOW}Note: Some imports may fail until all dependencies are installed${NC}"
fi

echo
echo "========================================"
echo -e "${GREEN}✓ Setup Complete!${NC}"
echo "========================================"
echo
echo "Next steps:"
echo "  1. Configure .env file:"
echo "     nano .env"
echo
echo "  2. Add Gmail credentials:"
echo "     Place credentials.json in finmatcher/auth_files/"
echo
echo "  3. Run the application:"
echo "     python main.py"
echo
echo "Database connection string:"
echo "  postgresql://postgres:Teeli%40322@localhost:5432/FinMatcher"
echo
