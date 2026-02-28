#!/usr/bin/env python3
"""
FinMatcher v2 to v3 Migration Script
Migrates existing v2 schema to v3 distributed pipeline
"""

import psycopg2
import os
from dotenv import load_dotenv
import sys

load_dotenv()

def get_db_connection():
    """Get database connection"""
    db_url = os.getenv('DATABASE_URL').strip('"')
    return psycopg2.connect(db_url)

def migrate_schema():
    """Migrate v2 schema to v3"""
    print("=" * 60)
    print("FinMatcher v2 → v3 Migration")
    print("=" * 60)
    
    conn = get_db_connection()
    conn.autocommit = False
    cur = conn.cursor()
    
    try:
        # Read migration script
        migration_file = os.path.join(os.path.dirname(__file__), 'migrate_v2_to_v3.sql')
        print(f"\n✓ Reading migration script: {migration_file}")
        
        with open(migration_file, 'r', encoding='utf-8') as f:
            migration_sql = f.read()
        
        print(f"✓ Migration script loaded ({len(migration_sql)} bytes)")
        
        # Execute migration
        print("\n✓ Applying migration...")
        cur.execute(migration_sql)
        conn.commit()
        print("✓ Migration applied successfully")
        
        # Verify new tables
        print("\n✓ Verifying v3 tables...")
        v3_tables = ['jobs', 'matches', 'reports', 'audit_log', 'metrics']
        
        for table in v3_tables:
            cur.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = %s
                )
            """, (table,))
            exists = cur.fetchone()[0]
            status = "✓" if exists else "✗"
            print(f"  {status} {table}: {'exists' if exists else 'missing'}")
        
        # Verify functions
        print("\n✓ Verifying v3 functions...")
        v3_functions = ['is_valid_transition', 'update_job_status', 'get_next_jobs']
        
        for func in v3_functions:
            cur.execute("""
                SELECT EXISTS (
                    SELECT FROM pg_proc 
                    WHERE proname = %s
                )
            """, (func,))
            exists = cur.fetchone()[0]
            status = "✓" if exists else "✗"
            print(f"  {status} {func}(): {'exists' if exists else 'missing'}")
        
        # Check schema version
        cur.execute("SELECT version, description, applied_at FROM schema_version WHERE version = '3.0.0'")
        version_info = cur.fetchone()
        if version_info:
            print(f"\n✓ Schema version: {version_info[0]}")
            print(f"  Description: {version_info[1]}")
            print(f"  Applied at: {version_info[2]}")
        
        cur.close()
        conn.close()
        
        print("\n" + "=" * 60)
        print("✓ Migration completed successfully!")
        print("=" * 60)
        print("\nNext steps:")
        print("1. Run schema tests: python schema/test_schema.py")
        print("2. Start implementing v3 services")
        print()
        
        return True
        
    except Exception as e:
        print(f"\n✗ Migration error: {e}")
        conn.rollback()
        cur.close()
        conn.close()
        return False

if __name__ == "__main__":
    try:
        success = migrate_schema()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nAborted by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Fatal error: {e}")
        sys.exit(1)
