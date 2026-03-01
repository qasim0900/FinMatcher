#!/bin/bash
# FinMatcher - Reset Database and Run Migrations
# Complete fresh start with migrations

set -e

echo "========================================================================"
echo "  FinMatcher - Reset Database & Run Migrations"
echo "========================================================================"
echo

# Database credentials
DB_HOST="localhost"
DB_PORT="5432"
DB_NAME="FinMatcher"
DB_USER="postgres"
DB_PASS="Teeli@322"

export PGPASSWORD="$DB_PASS"

echo "[1/5] Dropping existing database..."
psql -U "$DB_USER" -h "$DB_HOST" -c "DROP DATABASE IF EXISTS \"$DB_NAME\";" 2>/dev/null || true
echo "✅ Database dropped"

echo
echo "[2/5] Creating fresh database..."
psql -U "$DB_USER" -h "$DB_HOST" -c "CREATE DATABASE \"$DB_NAME\";"
echo "✅ Database created"

echo
echo "[3/5] Running migrations..."
python migrate.py up

echo
echo "[4/5] Verifying database structure..."
echo "Tables created:"
psql -U "$DB_USER" -d "$DB_NAME" -h "$DB_HOST" -c "\dt"

echo
echo "[5/5] Checking migration history..."
psql -U "$DB_USER" -d "$DB_NAME" -h "$DB_HOST" -c "SELECT * FROM schema_migrations ORDER BY version;"

echo
echo "========================================================================"
echo "✅ Database Reset & Migration Complete!"
echo "========================================================================"
echo
echo "Next steps:"
echo "  1. Run tests: python configure_and_test.py"
echo "  2. Run application: python main.py"
echo

unset PGPASSWORD
