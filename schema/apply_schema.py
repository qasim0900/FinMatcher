#!/usr/bin/env python3
"""
FinMatcher v3.0 Schema Initialization Script
Applies the v3.0 database schema to PostgreSQL
"""

import psycopg2
import os
from dotenv import load_dotenv
import sys

# Load environment variables
load_dotenv()

def get_database_url():
    """Get database URL from environment"""
    db_url = os.getenv('DATABASE_URL')
    if not db_url:
        raise ValueError("DATABASE_URL not found in environment variables")
    
    # Handle URL-encoded passwords
    return db_url.strip('"')

def apply_schema():
    """Apply the v3.0 schema to the database"""
    print("=" * 60)
    print("FinMatcher v3.0 Schema Initialization")
    print("=" * 60)
    
    # Get database connection
    db_url = get_database_url()
    print(f"\n✓ Database URL loaded from .env")
    
    try:
        # Connect to database
        print("✓ Connecting to PostgreSQL...")
        conn = psycopg2.connect(db_url)
        conn.autocommit = False
        cur = conn.cursor()
        print("✓ Connected successfully")
        
        # Read schema file
        schema_file = os.path.join(os.path.dirname(__file__), 'init_v3.sql')
        print(f"\n✓ Reading schema from: {schema_file}")
        
        with open(schema_file, 'r', encoding='utf-8') as f:
            schema_sql = f.read()
        
        print(f"✓ Schema file loaded ({len(schema_sql)} bytes)")
        
        # Execute schema
        print("\n✓ Applying schema...")
        cur.execute(schema_sql)
        conn.commit()
        print("✓ Schema applied successfully")
        
        # Verify tables created
        print("\n✓ Verifying tables...")
        cur.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_type = 'BASE TABLE'
            ORDER BY table_name
        """)
        
        tables = cur.fetchall()
        print(f"\n✓ Created {len(tables)} tables:")
        for table in tables:
            print(f"  - {table[0]}")
        
        # Verify functions created
        print("\n✓ Verifying functions...")
        cur.execute("""
            SELECT routine_name 
            FROM information_schema.routines 
            WHERE routine_schema = 'public' 
            AND routine_type = 'FUNCTION'
            ORDER BY routine_name
        """)
        
        functions = cur.fetchall()
        print(f"\n✓ Created {len(functions)} functions:")
        for func in functions:
            print(f"  - {func[0]}()")
        
        # Verify materialized views
        print("\n✓ Verifying materialized views...")
        cur.execute("""
            SELECT matviewname 
            FROM pg_matviews 
            WHERE schemaname = 'public'
            ORDER BY matviewname
        """)
        
        views = cur.fetchall()
        print(f"\n✓ Created {len(views)} materialized views:")
        for view in views:
            print(f"  - {view[0]}")
        
        # Check schema version
        cur.execute("SELECT version, description, applied_at FROM schema_version ORDER BY applied_at DESC LIMIT 1")
        version_info = cur.fetchone()
        if version_info:
            print(f"\n✓ Schema version: {version_info[0]}")
            print(f"  Description: {version_info[1]}")
            print(f"  Applied at: {version_info[2]}")
        
        cur.close()
        conn.close()
        
        print("\n" + "=" * 60)
        print("✓ Schema initialization completed successfully!")
        print("=" * 60)
        print("\nNext steps:")
        print("1. Review the created tables and functions")
        print("2. Configure database roles and permissions")
        print("3. Start implementing the service layer")
        print()
        
        return True
        
    except psycopg2.Error as e:
        print(f"\n✗ Database error: {e}")
        if conn:
            conn.rollback()
        return False
        
    except FileNotFoundError:
        print(f"\n✗ Schema file not found: {schema_file}")
        return False
        
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        if conn:
            conn.rollback()
        return False

def check_existing_schema():
    """Check if v3 schema already exists"""
    db_url = get_database_url()
    
    try:
        conn = psycopg2.connect(db_url)
        cur = conn.cursor()
        
        # Check if jobs table exists (key v3 table)
        cur.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'jobs'
            )
        """)
        
        exists = cur.fetchone()[0]
        cur.close()
        conn.close()
        
        return exists
        
    except Exception as e:
        print(f"Warning: Could not check existing schema: {e}")
        return False

if __name__ == "__main__":
    try:
        # Check if schema already exists
        if check_existing_schema():
            print("\n⚠ Warning: v3.0 schema tables already exist!")
            response = input("Do you want to continue? This will skip existing tables. (y/N): ")
            if response.lower() != 'y':
                print("Aborted.")
                sys.exit(0)
        
        # Apply schema
        success = apply_schema()
        sys.exit(0 if success else 1)
        
    except KeyboardInterrupt:
        print("\n\nAborted by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Fatal error: {e}")
        sys.exit(1)
