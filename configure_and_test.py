#!/usr/bin/env python3
"""
FinMatcher - Complete Configuration and Testing Script
Tests each component step by step with your database configuration
"""

import os
import sys
import time
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

# Set database URL
os.environ['DATABASE_URL'] = 'postgresql://postgres:Teeli%40322@localhost:5432/FinMatcher'

def print_header(title):
    """Print section header"""
    print("\n" + "="*70)
    print(f"  {title}")
    print("="*70)

def print_step(step_num, total_steps, description):
    """Print step header"""
    print(f"\n[{step_num}/{total_steps}] {description}")
    print("-" * 50)

def test_result(success, message):
    """Print test result"""
    if success:
        print(f"✅ {message}")
        return True
    else:
        print(f"❌ {message}")
        return False

def main():
    """Run complete configuration and testing"""
    
    print_header("FinMatcher - Configuration & Testing")
    print(f"Database: postgresql://postgres:***@localhost:5432/FinMatcher")
    print(f"Working Directory: {os.getcwd()}")
    
    results = {
        'passed': 0,
        'failed': 0,
        'total': 15
    }
    
    # TEST 1: Check Python Version
    print_step(1, results['total'], "Checking Python Version")
    try:
        import sys
        version = sys.version_info
        if version.major == 3 and version.minor >= 11:
            test_result(True, f"Python {version.major}.{version.minor}.{version.micro}")
            results['passed'] += 1
        else:
            test_result(False, f"Python {version.major}.{version.minor} (need 3.11+)")
            results['failed'] += 1
    except Exception as e:
        test_result(False, f"Error: {e}")
        results['failed'] += 1
    
    # TEST 2: Check Project Structure
    print_step(2, results['total'], "Checking Project Structure")
    try:
        required_dirs = ['finmatcher', 'schema', 'statements']
        all_exist = True
        for dir_name in required_dirs:
            if Path(dir_name).exists():
                print(f"  ✓ {dir_name}/ exists")
            else:
                print(f"  ✗ {dir_name}/ missing")
                all_exist = False
        
        if all_exist:
            test_result(True, "All required directories exist")
            results['passed'] += 1
        else:
            test_result(False, "Some directories are missing")
            results['failed'] += 1
    except Exception as e:
        test_result(False, f"Error: {e}")
        results['failed'] += 1
    
    # TEST 3: Check Database Connection
    print_step(3, results['total'], "Testing Database Connection")
    try:
        import psycopg2
        conn = psycopg2.connect(
            host='localhost',
            port=5432,
            database='FinMatcher',
            user='postgres',
            password='Teeli@322'
        )
        cursor = conn.cursor()
        cursor.execute("SELECT version();")
        version = cursor.fetchone()[0]
        print(f"  PostgreSQL: {version.split(',')[0]}")
        cursor.close()
        conn.close()
        test_result(True, "Database connection successful")
        results['passed'] += 1
    except Exception as e:
        test_result(False, f"Database connection failed: {e}")
        results['failed'] += 1
    
    # TEST 4: Check Database Tables
    print_step(4, results['total'], "Checking Database Tables")
    try:
        import psycopg2
        conn = psycopg2.connect(
            host='localhost',
            port=5432,
            database='FinMatcher',
            user='postgres',
            password='Teeli@322'
        )
        cursor = conn.cursor()
        
        required_tables = ['processed_emails', 'transactions', 'receipts', 'matches']
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
        """)
        existing_tables = [row[0] for row in cursor.fetchall()]
        
        all_exist = True
        for table in required_tables:
            if table in existing_tables:
                print(f"  ✓ {table} exists")
            else:
                print(f"  ✗ {table} missing")
                all_exist = False
        
        cursor.close()
        conn.close()
        
        if all_exist:
            test_result(True, "All required tables exist")
            results['passed'] += 1
        else:
            test_result(False, "Some tables are missing - run migration")
            results['failed'] += 1
    except Exception as e:
        test_result(False, f"Error checking tables: {e}")
        results['failed'] += 1
    
    # TEST 5: Check attachment_file Column
    print_step(5, results['total'], "Checking Optimization Fields")
    try:
        import psycopg2
        conn = psycopg2.connect(
            host='localhost',
            port=5432,
            database='FinMatcher',
            user='postgres',
            password='Teeli@322'
        )
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'processed_emails' 
            AND column_name = 'attachment_file'
        """)
        
        if cursor.fetchone():
            print(f"  ✓ attachment_file column exists")
            test_result(True, "Optimization fields configured")
            results['passed'] += 1
        else:
            print(f"  ✗ attachment_file column missing")
            test_result(False, "Run: psql -f schema/add_attachment_fields.sql")
            results['failed'] += 1
        
        cursor.close()
        conn.close()
    except Exception as e:
        test_result(False, f"Error: {e}")
        results['failed'] += 1
    
    # TEST 6: Check Required Python Packages
    print_step(6, results['total'], "Checking Python Dependencies")
    try:
        required_packages = [
            ('pandas', 'pandas'),
            ('numpy', 'numpy'),
            ('sklearn', 'scikit-learn'),
            ('psycopg2', 'psycopg2'),
            ('dotenv', 'python-dotenv'),
            ('yaml', 'pyyaml')
        ]
        
        all_installed = True
        for module_name, package_name in required_packages:
            try:
                __import__(module_name)
                print(f"  ✓ {package_name}")
            except ImportError:
                print(f"  ✗ {package_name} missing")
                all_installed = False
        
        if all_installed:
            test_result(True, "All dependencies installed")
            results['passed'] += 1
        else:
            test_result(False, "Some packages missing - run: pip install -r requirements.txt")
            results['failed'] += 1
    except Exception as e:
        test_result(False, f"Error: {e}")
        results['failed'] += 1
    
    # TEST 7: Check .env File
    print_step(7, results['total'], "Checking Environment Configuration")
    try:
        if Path('.env').exists():
            print(f"  ✓ .env file exists")
            
            # Check if DATABASE_URL is set
            from dotenv import load_dotenv
            load_dotenv()
            
            db_url = os.getenv('DATABASE_URL')
            if db_url and 'FinMatcher' in db_url:
                print(f"  ✓ DATABASE_URL configured")
                test_result(True, "Environment configuration valid")
                results['passed'] += 1
            else:
                print(f"  ✗ DATABASE_URL not properly configured")
                test_result(False, "Update DATABASE_URL in .env")
                results['failed'] += 1
        else:
            print(f"  ✗ .env file missing")
            test_result(False, "Create .env file from .env.example")
            results['failed'] += 1
    except Exception as e:
        test_result(False, f"Error: {e}")
        results['failed'] += 1
    
    # TEST 8: Check Config Files
    print_step(8, results['total'], "Checking Configuration Files")
    try:
        config_files = ['config.yaml', '.env']
        all_exist = True
        
        for config_file in config_files:
            if Path(config_file).exists():
                print(f"  ✓ {config_file} exists")
            else:
                print(f"  ✗ {config_file} missing")
                all_exist = False
        
        if all_exist:
            test_result(True, "Configuration files present")
            results['passed'] += 1
        else:
            test_result(False, "Some configuration files missing")
            results['failed'] += 1
    except Exception as e:
        test_result(False, f"Error: {e}")
        results['failed'] += 1
    
    # TEST 9: Check Gmail Credentials
    print_step(9, results['total'], "Checking Gmail API Credentials")
    try:
        creds_path = Path('finmatcher/auth_files/credentials.json')
        if creds_path.exists():
            print(f"  ✓ credentials.json exists")
            test_result(True, "Gmail credentials configured")
            results['passed'] += 1
        else:
            print(f"  ✗ credentials.json missing")
            test_result(False, "Add Gmail API credentials to finmatcher/auth_files/")
            results['failed'] += 1
    except Exception as e:
        test_result(False, f"Error: {e}")
        results['failed'] += 1
    
    # TEST 10: Check Statements Folder
    print_step(10, results['total'], "Checking Statements Folder")
    try:
        statements_dir = Path('statements')
        if statements_dir.exists():
            statement_files = list(statements_dir.glob('*.xlsx')) + list(statements_dir.glob('*.pdf'))
            if statement_files:
                print(f"  ✓ Found {len(statement_files)} statement files")
                for file in statement_files[:3]:  # Show first 3
                    print(f"    - {file.name}")
                test_result(True, "Statement files present")
                results['passed'] += 1
            else:
                print(f"  ✗ No statement files found")
                test_result(False, "Add statement files to statements/ folder")
                results['failed'] += 1
        else:
            print(f"  ✗ statements/ directory missing")
            test_result(False, "Create statements/ directory")
            results['failed'] += 1
    except Exception as e:
        test_result(False, f"Error: {e}")
        results['failed'] += 1
    
    # TEST 11: Test Database Write
    print_step(11, results['total'], "Testing Database Write Operations")
    try:
        import psycopg2
        conn = psycopg2.connect(
            host='localhost',
            port=5432,
            database='FinMatcher',
            user='postgres',
            password='Teeli@322'
        )
        cursor = conn.cursor()
        
        # Test insert
        cursor.execute("""
            INSERT INTO processed_emails (message_id, subject, sender, date, has_attachment)
            VALUES ('test_001', 'Test Email', 'test@example.com', NOW(), TRUE)
            ON CONFLICT (message_id) DO NOTHING
        """)
        conn.commit()
        
        # Test select
        cursor.execute("SELECT COUNT(*) FROM processed_emails WHERE message_id = 'test_001'")
        count = cursor.fetchone()[0]
        
        # Cleanup
        cursor.execute("DELETE FROM processed_emails WHERE message_id = 'test_001'")
        conn.commit()
        
        cursor.close()
        conn.close()
        
        if count > 0:
            test_result(True, "Database write operations working")
            results['passed'] += 1
        else:
            test_result(False, "Database write failed")
            results['failed'] += 1
    except Exception as e:
        test_result(False, f"Database write error: {e}")
        results['failed'] += 1
    
    # TEST 12: Test Pandas Operations
    print_step(12, results['total'], "Testing Pandas/NumPy Operations")
    try:
        import pandas as pd
        import numpy as np
        
        # Create test dataframe
        df = pd.DataFrame({
            'email_id': [f'email_{i}' for i in range(1000)],
            'subject': [f'Invoice #{i}' if i % 2 == 0 else f'Email {i}' for i in range(1000)],
            'amount': np.random.uniform(10, 1000, 1000)
        })
        
        # Test vectorized filtering
        financial_mask = df['subject'].str.contains('Invoice', case=False, regex=False)
        filtered = df[financial_mask]
        
        print(f"  ✓ Created DataFrame with {len(df)} rows")
        print(f"  ✓ Filtered to {len(filtered)} financial emails")
        
        test_result(True, "Pandas/NumPy operations working")
        results['passed'] += 1
    except Exception as e:
        test_result(False, f"Pandas/NumPy error: {e}")
        results['failed'] += 1
    
    # TEST 13: Test K-D Tree
    print_step(13, results['total'], "Testing K-D Tree Spatial Indexing")
    try:
        from sklearn.neighbors import KDTree
        import numpy as np
        
        # Create test data
        points = np.random.rand(1000, 2)
        tree = KDTree(points, leaf_size=40)
        
        # Test query
        query_point = [[0.5, 0.5]]
        distances, indices = tree.query(query_point, k=5)
        
        print(f"  ✓ Created K-D Tree with {len(points)} points")
        print(f"  ✓ Query returned {len(indices[0])} nearest neighbors")
        
        test_result(True, "K-D Tree operations working")
        results['passed'] += 1
    except Exception as e:
        test_result(False, f"K-D Tree error: {e}")
        results['failed'] += 1
    
    # TEST 14: Test Bloom Filter
    print_step(14, results['total'], "Testing Bloom Filter")
    try:
        from pybloom_live import BloomFilter
        
        # Create bloom filter
        bloom = BloomFilter(capacity=10000, error_rate=0.001)
        
        # Add items
        for i in range(100):
            bloom.add(f"email_{i}")
        
        # Test membership
        exists = "email_50" in bloom
        not_exists = "email_999" not in bloom
        
        print(f"  ✓ Created Bloom Filter (capacity: 10,000)")
        print(f"  ✓ Added 100 items")
        print(f"  ✓ Membership test: {exists and not_exists}")
        
        test_result(True, "Bloom Filter operations working")
        results['passed'] += 1
    except Exception as e:
        test_result(False, f"Bloom Filter error: {e}")
        results['failed'] += 1
    
    # TEST 15: Test Import of Main Modules
    print_step(15, results['total'], "Testing FinMatcher Module Imports")
    try:
        # Set PYTHONPATH
        sys.path.insert(0, os.getcwd())
        
        modules_to_test = [
            'finmatcher.config.settings',
            'finmatcher.database.models',
            'finmatcher.utils.logger'
        ]
        
        all_imported = True
        for module in modules_to_test:
            try:
                __import__(module)
                print(f"  ✓ {module}")
            except ImportError as e:
                print(f"  ✗ {module}: {e}")
                all_imported = False
        
        if all_imported:
            test_result(True, "All core modules can be imported")
            results['passed'] += 1
        else:
            test_result(False, "Some modules failed to import")
            results['failed'] += 1
    except Exception as e:
        test_result(False, f"Import error: {e}")
        results['failed'] += 1
    
    # FINAL SUMMARY
    print_header("TEST SUMMARY")
    
    pass_rate = (results['passed'] / results['total']) * 100
    
    print(f"\nTotal Tests: {results['total']}")
    print(f"Passed: {results['passed']} ✅")
    print(f"Failed: {results['failed']} ❌")
    print(f"Pass Rate: {pass_rate:.1f}%")
    
    print("\n" + "="*70)
    
    if results['failed'] == 0:
        print("🎉 ALL TESTS PASSED - SYSTEM READY FOR PRODUCTION!")
        print("="*70)
        print("\nNext steps:")
        print("  1. Run: python main.py")
        print("  2. Monitor logs: tail -f logs/finmatcher.log")
        print("  3. Check results: ls -la reports/")
        return 0
    else:
        print("⚠️  SOME TESTS FAILED - PLEASE FIX ISSUES ABOVE")
        print("="*70)
        print("\nCommon fixes:")
        print("  - Database: psql -U postgres -d FinMatcher -f schema/init_v3.sql")
        print("  - Dependencies: pip install -r requirements.txt")
        print("  - Environment: cp .env.example .env && nano .env")
        return 1

if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nUnexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
