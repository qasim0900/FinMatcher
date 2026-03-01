#!/bin/bash
# ============================================================================
# FinMatcher - Production Run Script
# ============================================================================

set -e

echo "🚀 FinMatcher - Starting Production Run"
echo "========================================"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Step 1: Check Python environment
echo ""
echo "🔍 Step 1: Checking Python environment..."
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Python3 not found${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Python3 found: $(python3 --version)${NC}"

# Step 2: Check database connection
echo ""
echo "🔍 Step 2: Testing database connection..."
python3 << PYTHON_EOF
import psycopg2
try:
    conn = psycopg2.connect(
        dbname='FinMatcher',
        user='postgres',
        password='Teeli@322',
        host='localhost'
    )
    print('${GREEN}✅ Database connection successful${NC}')
    conn.close()
except Exception as e:
    print('${RED}❌ Database connection failed:', e, '${NC}')
    exit(1)
PYTHON_EOF

# Step 3: Check required directories
echo ""
echo "🔍 Step 3: Checking required directories..."
REQUIRED_DIRS=("statements" "logs" "reports" "temp_attachments" "output")
for dir in "${REQUIRED_DIRS[@]}"; do
    if [ ! -d "$dir" ]; then
        echo "   Creating directory: $dir"
        mkdir -p "$dir"
    fi
done
echo -e "${GREEN}✅ All directories ready${NC}"

# Step 4: Check statement files
echo ""
echo "🔍 Step 4: Checking statement files..."
STATEMENT_FILES=(
    "statements/Meriwest Credit Card Statement.pdf"
    "statements/Amex_Credit_Card_Statement.xlsx"
    "statements/Chase_Credit_Card_Statement.xlsx"
)
MISSING_FILES=0
for file in "${STATEMENT_FILES[@]}"; do
    if [ -f "$file" ]; then
        echo -e "   ${GREEN}✅${NC} $file"
    else
        echo -e "   ${RED}❌${NC} $file (missing)"
        MISSING_FILES=$((MISSING_FILES + 1))
    fi
done

if [ $MISSING_FILES -gt 0 ]; then
    echo -e "${YELLOW}⚠️  $MISSING_FILES statement file(s) missing${NC}"
    echo "   Some milestones may fail"
fi

# Step 5: Check Gmail credentials
echo ""
echo "🔍 Step 5: Checking Gmail credentials..."
if [ -f "finmatcher/auth_files/credentials.json" ]; then
    echo -e "${GREEN}✅ Gmail credentials found${NC}"
else
    echo -e "${RED}❌ Gmail credentials missing${NC}"
    echo "   Place credentials.json in finmatcher/auth_files/"
    exit 1
fi

# Step 6: Show execution options
echo ""
echo "========================================"
echo "✅ Pre-flight checks complete!"
echo "========================================"
echo ""
echo "📋 Available execution modes:"
echo ""
echo "1. Full Reconciliation (All Milestones)"
echo "   python main.py --mode full_reconciliation"
echo ""
echo "2. Milestone 1 (Meriwest)"
echo "   python main.py --mode milestone_1"
echo ""
echo "3. Milestone 2 (Amex)"
echo "   python main.py --mode milestone_2"
echo ""
echo "4. Milestone 3 (Chase)"
echo "   python main.py --mode milestone_3"
echo ""
echo "5. Milestone 4 (Unmatched Records)"
echo "   python main.py --mode milestone_4"
echo ""
echo "========================================"
echo ""

# Ask user which mode to run
read -p "Enter mode number (1-5) or 'q' to quit: " MODE_CHOICE

case $MODE_CHOICE in
    1)
        echo ""
        echo "🚀 Running Full Reconciliation..."
        python3 main.py --mode full_reconciliation
        ;;
    2)
        echo ""
        echo "🚀 Running Milestone 1 (Meriwest)..."
        python3 main.py --mode milestone_1
        ;;
    3)
        echo ""
        echo "🚀 Running Milestone 2 (Amex)..."
        python3 main.py --mode milestone_2
        ;;
    4)
        echo ""
        echo "🚀 Running Milestone 3 (Chase)..."
        python3 main.py --mode milestone_3
        ;;
    5)
        echo ""
        echo "🚀 Running Milestone 4 (Unmatched)..."
        python3 main.py --mode milestone_4
        ;;
    q|Q)
        echo "Exiting..."
        exit 0
        ;;
    *)
        echo -e "${RED}Invalid choice${NC}"
        exit 1
        ;;
esac

# Show results
echo ""
echo "========================================"
echo "✅ Execution Complete!"
echo "========================================"
echo ""
echo "📊 Check results:"
echo "   - Logs: logs/finmatcher.log"
echo "   - Reports: reports/"
echo "   - Database: psql -U postgres -h localhost -d FinMatcher"
echo ""
