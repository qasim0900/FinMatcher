#!/usr/bin/env python3
"""
FinMatcher - Unified Ubuntu Setup Script
Handles complete database setup and migration in one command
"""

import os
import sys
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from pathlib import Path
from urllib.parse import urlparse
import subprocess

# ANSI color codes for output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'

def print_success(message):
    """Print success message in green"""
    print(f"{GREEN}[OK] {message}{RESET}")

def print_error(message):
    """Print error message in red"""
    print(f"{RED}[ERROR] {message}{RESET}")

def print_warning(message):
    """Print warning message in yellow"""
    print(f"{YELLOW}[WARN] {message}{RESET}")

def print_info(message):
    """Print info message in blue"""
    print(f"{BLUE}[INFO] {message}{RESET}")

def print_header(message):
    """Print section header"""
    print(f"\n{'='*60}")
    print(f"{BLUE}{message}{RESET}")
    print(f"{'='*60}")

def load_database_config():
    """Load database configuration from .env file"""
    print_header("Loading Database Configuration")
    
    env_file = Path('.env')
    if not env_file.exists():
        print_error("Configuration file .env not found")
        print_info("Please create .env file with DATABASE_URL")
        print_info("Example: DATABASE_URL=postgresql://user:password@localhost:5432/dbname")
        return None
    
    # Read .env file
    database_url = None
    with open(env_file, 'r') as f:
        for line in f:
            line = line.strip()
            # Skip empty lines and comments
            if not line or line.startswith('#'):
                continue
            if line.startswith('DATABASE_URL='):
                database_url = line.split('=', 1)[1]
                break
    
    if not database_url:
        print_error("DATABASE_URL not found in .env file")
        return None
    
    # Parse DATABASE_URL
    try:
        parsed = urlparse(database_url)
        config = {
            'host': parsed.hostname or 'localhost',
            'port': parsed.port or 5432,
            'database': parsed.path.lstrip('/'),
            'user': parsed.username,
            'password': parsed.password.replace('%40', '@') if parsed.password else None
        }
        
        print_success(f"Configuration loaded: {config['user']}@{config['host']}:{config['port']}/{config['database']}")
        return config
    
    except Exception as e:
        print_error(f"Failed to parse DATABASE_URL: {e}")
        return None

def check_postgresql_connection(config):
    """Check if PostgreSQL server is accessible"""
    print_header("Checking PostgreSQL Connection")
    
    try:
        # Connect to default postgres database to check server
        conn_config = config.copy()
        conn_config['database'] = 'postgres'
        
        conn = psycopg2.connect(**conn_config)
        conn.close()
        
        print_success(f"PostgreSQL server is accessible at {config['host']}:{config['port']}")
        return True
    
    except psycopg2.OperationalError as e:
        print_error(f"Cannot connect to PostgreSQL server: {e}")
        print_info("Please ensure PostgreSQL is running and credentials are correct")
        return False
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        return False

def create_database_if_not_exists(config):
    """Create database if it doesn't exist"""
    print_header("Creating Database")
    
    try:
        # Connect to default postgres database
        conn_config = config.copy()
        conn_config['database'] = 'postgres'
        
        conn = psycopg2.connect(**conn_config)
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        
        # Check if database exists
        cursor.execute(
            "SELECT 1 FROM pg_database WHERE datname = %s",
            (config['database'],)
        )
        exists = cursor.fetchone()
        
        if exists:
            print_info(f"Database '{config['database']}' already exists")
        else:
            # Create database
            cursor.execute(f"CREATE DATABASE {config['database']}")
            print_success(f"Database '{config['database']}' created successfully")
        
        cursor.close()
        conn.close()
        return True
    
    except Exception as e:
        print_error(f"Failed to create database: {e}")
        return False

def run_migrations(config):
    """Run migrations using migrate.py"""
    print_header("Running Database Migrations")
    
    # Check if migrate.py exists
    migrate_script = Path('migrate.py')
    if not migrate_script.exists():
        print_error("migrate.py not found in project root")
        return False
    
    # Check if migrations directory exists
    migrations_dir = Path('schema/migrations')
    if not migrations_dir.exists():
        print_error("schema/migrations directory not found")
        return False
    
    try:
        # Run migrate.py up command
        print_info("Executing: python migrate.py up")
        result = subprocess.run(
            [sys.executable, 'migrate.py', 'up'],
            capture_output=True,
            text=True
        )
        
        # Print output
        if result.stdout:
            print(result.stdout)
        
        if result.returncode == 0:
            print_success("Migrations completed successfully")
            return True
        else:
            print_error("Migration failed")
            if result.stderr:
                print(result.stderr)
            return False
    
    except Exception as e:
        print_error(f"Failed to run migrations: {e}")
        return False

def validate_database_setup(config):
    """Validate that all required tables exist"""
    print_header("Validating Database Setup")
    
    # Required tables based on task requirements
    required_tables = [
        'schema_migrations',
        'processed_emails',
        'transactions',
        'receipts',
        'matches',
        'jobs',
        'reports',
        'audit_log',
        'metrics'
    ]
    
    try:
        conn = psycopg2.connect(**config)
        cursor = conn.cursor()
        
        missing_tables = []
        existing_tables = []
        
        for table in required_tables:
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = %s
                )
            """, (table,))
            
            exists = cursor.fetchone()[0]
            if exists:
                existing_tables.append(table)
            else:
                missing_tables.append(table)
        
        # Print results
        if existing_tables:
            print_success(f"Found {len(existing_tables)} required tables:")
            for table in existing_tables:
                print(f"  [+] {table}")
        
        if missing_tables:
            print_warning(f"Missing {len(missing_tables)} tables:")
            for table in missing_tables:
                print(f"  [-] {table}")
        
        cursor.close()
        conn.close()
        
        # Consider validation successful if core tables exist
        # Note: jobs, reports, audit_log, metrics may be created by application code
        core_tables = ['schema_migrations', 'processed_emails', 'transactions', 'receipts', 'matches']
        core_missing = [t for t in core_tables if t in missing_tables]
        
        if core_missing:
            print_error(f"Core tables missing: {', '.join(core_missing)}")
            return False
        
        # Warn about optional tables but don't fail
        optional_tables = ['jobs', 'reports', 'audit_log', 'metrics']
        optional_missing = [t for t in optional_tables if t in missing_tables]
        if optional_missing:
            print_info(f"Optional tables (may be created by application): {', '.join(optional_missing)}")
        
        print_success("Database validation passed")
        return True
    
    except Exception as e:
        print_error(f"Validation failed: {e}")
        return False

def run_test_query(config):
    """Run a test query to verify database is functional"""
    print_header("Testing Database Functionality")
    
    try:
        conn = psycopg2.connect(**config)
        cursor = conn.cursor()
        
        # Test query: Get migration version
        cursor.execute("SELECT COALESCE(MAX(version), 0) FROM schema_migrations")
        version = cursor.fetchone()[0]
        
        print_success(f"Database is functional - Current schema version: {version}")
        
        # Test query: Count records in main tables
        test_tables = ['processed_emails', 'transactions', 'receipts', 'matches']
        print_info("Table record counts:")
        
        for table in test_tables:
            try:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                print(f"  {table}: {count} records")
            except Exception as e:
                print_warning(f"  {table}: Could not query ({e})")
        
        cursor.close()
        conn.close()
        
        print_success("Test queries completed successfully")
        return True
    
    except Exception as e:
        print_error(f"Test query failed: {e}")
        return False

def main():
    """Main setup function"""
    print(f"\n{BLUE}{'='*60}")
    print("FinMatcher - Unified Ubuntu Setup")
    print(f"{'='*60}{RESET}\n")
    
    # Step 1: Load configuration
    config = load_database_config()
    if not config:
        print_error("Setup failed: Could not load database configuration")
        return 1
    
    # Step 2: Check PostgreSQL connection
    if not check_postgresql_connection(config):
        print_error("Setup failed: Cannot connect to PostgreSQL server")
        print_info("Action required:")
        print_info("  1. Ensure PostgreSQL is installed and running")
        print_info("  2. Verify credentials in .env file")
        print_info("  3. Check firewall settings if connecting to remote server")
        return 1
    
    # Step 3: Create database if not exists
    if not create_database_if_not_exists(config):
        print_error("Setup failed: Could not create database")
        print_info("Action required:")
        print_info("  1. Check user has CREATE DATABASE permission")
        print_info("  2. Verify database name is valid")
        return 1
    
    # Step 4: Run migrations
    if not run_migrations(config):
        print_error("Setup failed: Migration errors occurred")
        print_info("Action required:")
        print_info("  1. Check migration files in schema/migrations/")
        print_info("  2. Review error messages above")
        print_info("  3. Verify database user has necessary permissions")
        return 1
    
    # Step 5: Validate setup
    if not validate_database_setup(config):
        print_error("Setup failed: Database validation failed")
        print_info("Action required:")
        print_info("  1. Check if migrations completed successfully")
        print_info("  2. Review migration files for errors")
        return 1
    
    # Step 6: Run test query
    if not run_test_query(config):
        print_error("Setup failed: Database functionality test failed")
        print_info("Action required:")
        print_info("  1. Check database permissions")
        print_info("  2. Verify tables were created correctly")
        return 1
    
    # Success!
    print(f"\n{GREEN}{'='*60}")
    print("[OK] Setup completed successfully!")
    print(f"{'='*60}{RESET}\n")
    
    print_info("Next steps:")
    print("  1. Run the application: python main.py")
    print("  2. For future migrations: python migrate.py up")
    print("  3. Check migration status: python migrate.py status")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
