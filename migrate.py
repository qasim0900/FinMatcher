#!/usr/bin/env python3
"""
FinMatcher - Database Migration Tool
Manages database schema versions and migrations
"""

import os
import sys
import psycopg2
from pathlib import Path
from datetime import datetime
import argparse
from urllib.parse import urlparse
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Database configuration from environment
def get_db_config():
    """Load database configuration from DATABASE_URL environment variable"""
    database_url = os.getenv('DATABASE_URL')
    
    if database_url:
        # Parse DATABASE_URL
        parsed = urlparse(database_url)
        return {
            'host': parsed.hostname or 'localhost',
            'port': parsed.port or 5432,
            'database': parsed.path.lstrip('/'),
            'user': parsed.username,
            'password': parsed.password.replace('%40', '@') if parsed.password else None
        }
    else:
        # Fallback to hardcoded config for backward compatibility
        return {
            'host': 'localhost',
            'port': 5432,
            'database': 'FinMatcher',
            'user': 'postgres',
            'password': 'Teeli@322'
        }

DB_CONFIG = get_db_config()

MIGRATIONS_DIR = Path('schema/migrations')

class MigrationManager:
    """Manages database migrations"""
    
    def __init__(self, config):
        self.config = config
        self.conn = None
        self.cursor = None
    
    def connect(self):
        """Connect to database"""
        try:
            self.conn = psycopg2.connect(**self.config)
            self.cursor = self.conn.cursor()
            print(f"[OK] Connected to database: {self.config['database']}")
            return True
        except Exception as e:
            print(f"[ERROR] Database connection failed: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from database"""
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()
    
    def create_migrations_table(self):
        """Create migrations tracking table if not exists"""
        try:
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    version INTEGER PRIMARY KEY,
                    name VARCHAR(255) NOT NULL,
                    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    description TEXT
                )
            """)
            self.conn.commit()
            print("[OK] Migrations tracking table ready")
            return True
        except Exception as e:
            print(f"[ERROR] Failed to create migrations table: {e}")
            self.conn.rollback()
            return False
    
    def get_current_version(self):
        """Get current database version"""
        try:
            self.cursor.execute("""
                SELECT COALESCE(MAX(version), 0) FROM schema_migrations
            """)
            version = self.cursor.fetchone()[0]
            return version
        except Exception as e:
            print(f"[WARN] Could not get current version: {e}")
            return 0
    
    def get_applied_migrations(self):
        """Get list of applied migrations"""
        try:
            self.cursor.execute("""
                SELECT version, name, applied_at, description 
                FROM schema_migrations 
                ORDER BY version
            """)
            return self.cursor.fetchall()
        except Exception as e:
            print(f"[WARN] Could not get applied migrations: {e}")
            return []
    
    def get_pending_migrations(self):
        """Get list of pending migrations"""
        current_version = self.get_current_version()
        
        # Get all migration files
        migration_files = sorted(MIGRATIONS_DIR.glob('*.sql'))
        
        pending = []
        for migration_file in migration_files:
            # Extract version from filename (e.g., 001_initial_schema.sql -> 1)
            try:
                version = int(migration_file.stem.split('_')[0])
                if version > current_version:
                    pending.append((version, migration_file))
            except ValueError:
                print(f"[WARN] Invalid migration filename: {migration_file.name}")
        
        return pending
    
    def apply_migration(self, version, migration_file):
        """Apply a single migration"""
        print(f"\n{'='*60}")
        print(f"Applying migration {version}: {migration_file.name}")
        print(f"{'='*60}")
        
        try:
            # Read migration file
            with open(migration_file, 'r') as f:
                sql = f.read()
            
            # Execute migration
            self.cursor.execute(sql)
            self.conn.commit()
            
            print(f"[OK] Migration {version} applied successfully")
            return True
            
        except Exception as e:
            print(f"[ERROR] Migration {version} failed: {e}")
            self.conn.rollback()
            return False
    
    def migrate_up(self, target_version=None):
        """Run pending migrations up to target version"""
        print("\n" + "="*60)
        print("Database Migration - Migrate Up")
        print("="*60)
        
        current_version = self.get_current_version()
        print(f"Current database version: {current_version}")
        
        pending = self.get_pending_migrations()
        
        if not pending:
            print("[OK] Database is up to date. No pending migrations.")
            return True
        
        print(f"Found {len(pending)} pending migration(s)")
        
        # Filter by target version if specified
        if target_version:
            pending = [(v, f) for v, f in pending if v <= target_version]
        
        # Apply migrations
        for version, migration_file in pending:
            if not self.apply_migration(version, migration_file):
                print(f"\n[ERROR] Migration stopped at version {version}")
                return False
        
        new_version = self.get_current_version()
        print(f"\n{'='*60}")
        print(f"[OK] Migration complete!")
        print(f"Database version: {current_version} -> {new_version}")
        print(f"{'='*60}")
        return True
    
    def migrate_down(self, target_version):
        """Rollback to target version (not implemented - requires down migrations)"""
        print("[WARN] Rollback not implemented. Please restore from backup.")
        return False
    
    def status(self):
        """Show migration status"""
        print("\n" + "="*60)
        print("Database Migration Status")
        print("="*60)
        
        current_version = self.get_current_version()
        print(f"\nCurrent version: {current_version}")
        
        # Show applied migrations
        applied = self.get_applied_migrations()
        if applied:
            print(f"\nApplied migrations ({len(applied)}):")
            print("-" * 60)
            for version, name, applied_at, description in applied:
                print(f"  [{version}] {name}")
                print(f"      Applied: {applied_at}")
                if description:
                    print(f"      Description: {description}")
        
        # Show pending migrations
        pending = self.get_pending_migrations()
        if pending:
            print(f"\nPending migrations ({len(pending)}):")
            print("-" * 60)
            for version, migration_file in pending:
                print(f"  [{version}] {migration_file.name}")
        else:
            print("\n[OK] No pending migrations")
        
        print("\n" + "="*60)
    
    def create_migration(self, name, description=""):
        """Create a new migration file"""
        # Get next version number
        current_version = self.get_current_version()
        
        # Check existing migration files
        migration_files = list(MIGRATIONS_DIR.glob('*.sql'))
        if migration_files:
            max_file_version = max([
                int(f.stem.split('_')[0]) 
                for f in migration_files 
                if f.stem.split('_')[0].isdigit()
            ])
            next_version = max(current_version, max_file_version) + 1
        else:
            next_version = current_version + 1
        
        # Create migration filename
        filename = f"{next_version:03d}_{name}.sql"
        filepath = MIGRATIONS_DIR / filename
        
        # Create migration template
        template = f"""-- Migration: {filename}
-- Description: {description or name.replace('_', ' ').title()}
-- Created: {datetime.now().strftime('%Y-%m-%d')}
-- Author: FinMatcher Team

-- Add your migration SQL here

-- Example: Add a new column
-- ALTER TABLE processed_emails ADD COLUMN new_field TEXT;

-- Example: Create an index
-- CREATE INDEX IF NOT EXISTS idx_new_field ON processed_emails(new_field);

-- Record migration
INSERT INTO schema_migrations (version, name, description)
VALUES ({next_version}, '{filename}', '{description or name.replace('_', ' ').title()}')
ON CONFLICT (version) DO NOTHING;

-- Success message
DO $$
BEGIN
    RAISE NOTICE 'Migration {next_version}: {name} completed successfully';
END $$;
"""
        
        # Write migration file
        with open(filepath, 'w') as f:
            f.write(template)
        
        print(f"[OK] Created migration: {filepath}")
        print(f"   Version: {next_version}")
        print(f"   Edit the file to add your migration SQL")
        
        return filepath

def main():
    """Main migration command"""
    parser = argparse.ArgumentParser(description='FinMatcher Database Migration Tool')
    parser.add_argument('command', choices=['up', 'down', 'status', 'create'], 
                       help='Migration command')
    parser.add_argument('--version', type=int, help='Target version for migration')
    parser.add_argument('--name', type=str, help='Name for new migration (for create command)')
    parser.add_argument('--description', type=str, help='Description for new migration')
    
    args = parser.parse_args()
    
    # Create migrations directory if not exists
    MIGRATIONS_DIR.mkdir(parents=True, exist_ok=True)
    
    # Initialize migration manager
    manager = MigrationManager(DB_CONFIG)
    
    # Handle create command (doesn't need database connection)
    if args.command == 'create':
        if not args.name:
            print("[ERROR] --name is required for create command")
            return 1
        manager.create_migration(args.name, args.description or "")
        return 0
    
    # Connect to database
    if not manager.connect():
        return 1
    
    try:
        # Create migrations table
        manager.create_migrations_table()
        
        # Execute command
        if args.command == 'up':
            success = manager.migrate_up(args.version)
        elif args.command == 'down':
            if not args.version:
                print("[ERROR] --version is required for down command")
                return 1
            success = manager.migrate_down(args.version)
        elif args.command == 'status':
            manager.status()
            success = True
        else:
            print(f"[ERROR] Unknown command: {args.command}")
            success = False
        
        return 0 if success else 1
        
    finally:
        manager.disconnect()

if __name__ == "__main__":
    sys.exit(main())
