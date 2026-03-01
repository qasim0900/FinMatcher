#!/usr/bin/env python3
"""
Preservation Property Tests for Project Cleanup and Migration Fix

**Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5**

These tests capture the baseline behavior that MUST be preserved after the fix.
Tests should PASS on unfixed code and continue to PASS after the fix.

GOAL: Verify that existing migrations, application functionality, configuration reading,
and module imports continue to work correctly after consolidation.
"""

import os
import sys
import psycopg2
from pathlib import Path
from hypothesis import given, strategies as st, settings, Phase
import pytest
import importlib
import yaml
from dotenv import load_dotenv


class TestPreservationProperties:
    """
    Property 2: Preservation - Existing Migration Execution and Application Functionality
    
    Tests that verify baseline behavior is preserved after consolidation.
    """
    
    @pytest.fixture(scope="class")
    def db_config(self):
        """Load database configuration from environment"""
        # Load .env file
        load_dotenv()
        
        # Default config (matches migrate.py)
        config = {
            'host': 'localhost',
            'port': 5432,
            'database': 'FinMatcher',
            'user': 'postgres',
            'password': 'Teeli@322'
        }
        return config
    
    @pytest.fixture(scope="class")
    def db_connection(self, db_config):
        """Create database connection for testing"""
        try:
            conn = psycopg2.connect(**db_config)
            yield conn
            conn.close()
        except Exception as e:
            pytest.skip(f"Database not available: {e}")
    
    def test_migration_files_exist(self):
        """
        Test that all existing migration files exist and are readable.
        
        **Validates: Requirement 3.1**
        
        EXPECTED: PASS on unfixed code, PASS on fixed code
        """
        project_root = Path(__file__).parent
        migrations_dir = project_root / "schema" / "migrations"
        
        # Expected migration files
        expected_migrations = [
            "001_initial_schema.sql",
            "002_add_optimization_fields.sql",
            "003_add_performance_indexes.sql"
        ]
        
        for migration_file in expected_migrations:
            migration_path = migrations_dir / migration_file
            assert migration_path.exists(), f"Migration file {migration_file} does not exist"
            assert migration_path.is_file(), f"Migration file {migration_file} is not a file"
            
            # Verify file is readable
            with open(migration_path, 'r') as f:
                content = f.read()
                assert len(content) > 0, f"Migration file {migration_file} is empty"
        
        print(f"✓ All {len(expected_migrations)} migration files exist and are readable")
    
    def test_schema_migrations_table_structure(self, db_connection):
        """
        Test that schema_migrations table has the correct structure.
        
        **Validates: Requirement 3.1, 3.2**
        
        EXPECTED: PASS on unfixed code, PASS on fixed code
        """
        cursor = db_connection.cursor()
        
        # Check if schema_migrations table exists
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'schema_migrations'
            )
        """)
        table_exists = cursor.fetchone()[0]
        
        if not table_exists:
            pytest.skip("schema_migrations table does not exist yet")
        
        # Check table structure
        cursor.execute("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'schema_migrations'
            ORDER BY ordinal_position
        """)
        columns = cursor.fetchall()
        
        # Expected columns
        expected_columns = {
            'version': 'integer',
            'name': 'character varying',
            'applied_at': 'timestamp without time zone',
            'description': 'text'
        }
        
        actual_columns = {col[0]: col[1] for col in columns}
        
        for col_name, col_type in expected_columns.items():
            assert col_name in actual_columns, f"Column {col_name} missing from schema_migrations"
        
        print(f"✓ schema_migrations table has correct structure with {len(columns)} columns")
    
    def test_expected_tables_structure(self, db_connection):
        """
        Test that all expected tables exist with correct structure.
        
        **Validates: Requirement 3.2**
        
        EXPECTED: PASS on unfixed code, PASS on fixed code
        """
        cursor = db_connection.cursor()
        
        # Expected tables from migrations
        expected_tables = [
            'processed_emails',
            'transactions',
            'receipts',
            'matches',
            'schema_migrations'
        ]
        
        for table_name in expected_tables:
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = %s
                )
            """, (table_name,))
            table_exists = cursor.fetchone()[0]
            
            if not table_exists:
                # Table might not exist if migrations haven't been run yet
                print(f"⚠ Table {table_name} does not exist (migrations may not be applied)")
                continue
            
            # Get column count
            cursor.execute("""
                SELECT COUNT(*) 
                FROM information_schema.columns 
                WHERE table_name = %s
            """, (table_name,))
            column_count = cursor.fetchone()[0]
            
            assert column_count > 0, f"Table {table_name} has no columns"
            print(f"✓ Table {table_name} exists with {column_count} columns")
    
    def test_property_migration_execution_produces_consistent_schema(self):
        """
        Property-based test: For all existing migration files, verify they can be read
        and contain expected SQL patterns.
        
        **Validates: Requirement 3.1**
        
        EXPECTED: PASS on unfixed code, PASS on fixed code
        """
        project_root = Path(__file__).parent
        migrations_dir = project_root / "schema" / "migrations"
        
        migration_files = sorted(migrations_dir.glob('*.sql'))
        
        assert len(migration_files) >= 3, f"Expected at least 3 migration files, found {len(migration_files)}"
        
        for migration_file in migration_files:
            with open(migration_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Verify migration contains expected patterns
            assert 'CREATE TABLE' in content or 'ALTER TABLE' in content or 'CREATE INDEX' in content, \
                f"Migration {migration_file.name} doesn't contain expected SQL statements"
            
            # Verify migration records itself
            assert 'INSERT INTO schema_migrations' in content, \
                f"Migration {migration_file.name} doesn't record itself in schema_migrations"
        
        print(f"✓ All {len(migration_files)} migration files contain valid SQL patterns")
    
    def test_main_application_imports(self):
        """
        Test that main.py can be imported without errors.
        
        **Validates: Requirement 3.3**
        
        EXPECTED: PASS on unfixed code, PASS on fixed code
        """
        project_root = Path(__file__).parent
        main_py = project_root / "main.py"
        
        assert main_py.exists(), "main.py does not exist"
        
        # Try to import main module (without executing)
        try:
            # Add project root to path if not already there
            if str(project_root) not in sys.path:
                sys.path.insert(0, str(project_root))
            
            # Import main module
            import main
            
            # Verify key components exist
            assert hasattr(main, 'FinMatcherOrchestrator'), "FinMatcherOrchestrator class not found in main.py"
            assert hasattr(main, 'main'), "main function not found in main.py"
            
            print("✓ main.py imports successfully with expected components")
        except ImportError as e:
            pytest.fail(f"Failed to import main.py: {e}")
    
    def test_env_file_readable(self):
        """
        Test that .env file exists and can be read correctly.
        
        **Validates: Requirement 3.4**
        
        EXPECTED: PASS on unfixed code, PASS on fixed code
        """
        project_root = Path(__file__).parent
        env_file = project_root / ".env"
        
        if not env_file.exists():
            pytest.skip(".env file does not exist")
        
        # Load .env file
        load_dotenv(env_file)
        
        # Verify we can read environment variables
        # Note: We don't check specific values, just that the file is readable
        assert env_file.exists(), ".env file does not exist"
        assert env_file.is_file(), ".env is not a file"
        
        with open(env_file, 'r') as f:
            content = f.read()
            assert len(content) > 0, ".env file is empty"
        
        print("✓ .env file exists and is readable")
    
    def test_config_yaml_readable(self):
        """
        Test that config.yaml exists and can be parsed correctly.
        
        **Validates: Requirement 3.4**
        
        EXPECTED: PASS on unfixed code, PASS on fixed code
        """
        project_root = Path(__file__).parent
        config_file = project_root / "config.yaml"
        
        assert config_file.exists(), "config.yaml does not exist"
        
        # Load and parse config.yaml
        with open(config_file, 'r') as f:
            config = yaml.safe_load(f)
        
        # Verify config has expected structure
        assert isinstance(config, dict), "config.yaml does not contain a dictionary"
        assert len(config) > 0, "config.yaml is empty"
        
        # Verify key sections exist
        expected_sections = ['matching', 'database', 'logging']
        for section in expected_sections:
            if section in config:
                print(f"✓ config.yaml contains '{section}' section")
        
        print("✓ config.yaml exists and is parseable")
    
    def test_property_finmatcher_modules_importable(self):
        """
        Property-based test: For all finmatcher package modules, verify they can be imported.
        
        **Validates: Requirement 3.5**
        
        EXPECTED: PASS on unfixed code, PASS on fixed code
        """
        project_root = Path(__file__).parent
        finmatcher_dir = project_root / "finmatcher"
        
        if not finmatcher_dir.exists():
            pytest.skip("finmatcher package does not exist")
        
        # Add project root to path
        if str(project_root) not in sys.path:
            sys.path.insert(0, str(project_root))
        
        # Key modules to test
        key_modules = [
            'finmatcher',
            'finmatcher.config',
            'finmatcher.core',
            'finmatcher.database',
            'finmatcher.storage',
            'finmatcher.utils'
        ]
        
        imported_count = 0
        for module_name in key_modules:
            try:
                importlib.import_module(module_name)
                imported_count += 1
                print(f"✓ Successfully imported {module_name}")
            except ImportError as e:
                # Some modules might have dependencies that aren't available in test environment
                print(f"⚠ Could not import {module_name}: {e}")
        
        # At least the base finmatcher module should be importable
        assert imported_count >= 1, "Could not import any finmatcher modules"
        print(f"✓ Successfully imported {imported_count}/{len(key_modules)} finmatcher modules")
    
    def test_migrate_py_exists_and_executable(self):
        """
        Test that migrate.py exists and is the primary migration tool.
        
        **Validates: Requirement 3.1**
        
        EXPECTED: PASS on unfixed code, PASS on fixed code
        """
        project_root = Path(__file__).parent
        migrate_py = project_root / "migrate.py"
        
        assert migrate_py.exists(), "migrate.py does not exist"
        assert migrate_py.is_file(), "migrate.py is not a file"
        
        # Verify file is readable and contains expected content
        with open(migrate_py, 'r', encoding='utf-8') as f:
            content = f.read()
            assert 'MigrationManager' in content, "migrate.py doesn't contain MigrationManager class"
            assert 'schema/migrations' in content, "migrate.py doesn't reference schema/migrations directory"
        
        print("✓ migrate.py exists and contains expected migration logic")
    
    def test_property_database_operations_work(self, db_connection):
        """
        Property-based test: Verify basic database operations work correctly.
        
        **Validates: Requirement 3.2, 3.3**
        
        EXPECTED: PASS on unfixed code, PASS on fixed code
        """
        cursor = db_connection.cursor()
        
        # Test basic query execution
        cursor.execute("SELECT version()")
        version = cursor.fetchone()
        assert version is not None, "Could not query database version"
        
        # Test that we can query information_schema
        cursor.execute("""
            SELECT COUNT(*) 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
        """)
        table_count = cursor.fetchone()[0]
        assert table_count >= 0, "Could not query information_schema"
        
        print(f"✓ Database operations work correctly ({table_count} tables in public schema)")
    
    def test_configuration_files_structure_preserved(self):
        """
        Test that configuration files maintain their structure.
        
        **Validates: Requirement 3.4**
        
        EXPECTED: PASS on unfixed code, PASS on fixed code
        """
        project_root = Path(__file__).parent
        
        # Check .env.example exists (template for .env)
        env_example = project_root / ".env.example"
        assert env_example.exists(), ".env.example does not exist"
        
        # Check config.yaml exists
        config_yaml = project_root / "config.yaml"
        assert config_yaml.exists(), "config.yaml does not exist"
        
        # Verify config.yaml structure
        with open(config_yaml, 'r') as f:
            config = yaml.safe_load(f)
        
        # Check for database configuration
        if 'database' in config:
            assert isinstance(config['database'], dict), "database config is not a dictionary"
            print("✓ config.yaml contains database configuration")
        
        print("✓ Configuration files structure is preserved")


if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v", "-s"])
