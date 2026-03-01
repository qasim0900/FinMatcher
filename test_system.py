#!/usr/bin/env python3
"""
FinMatcher System Test
Quick test to verify all components are working
"""

import sys
from pathlib import Path

def test_imports():
    """Test if all required modules can be imported"""
    print("🔍 Testing imports...")
    try:
        from finmatcher.config.settings import get_settings
        from finmatcher.utils.logger import get_logger
        from finmatcher.core.email_fetcher import EmailFetcher
        from finmatcher.core.statement_parser import StatementParser
        from finmatcher.core.ocr_engine import OCREngine
        from finmatcher.core.matcher_engine import MatcherEngine
        from finmatcher.reports.excel_generator import ExcelReportGenerator
        print("✅ All imports successful")
        return True
    except Exception as e:
        print(f"❌ Import failed: {e}")
        return False

def test_database():
    """Test database connection"""
    print("\n🔍 Testing database connection...")
    try:
        import psycopg2
        conn = psycopg2.connect(
            dbname='FinMatcher',
            user='postgres',
            password='Teeli@322',
            host='localhost'
        )
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='public';")
        count = cursor.fetchone()[0]
        print(f"✅ Database connected! Tables: {count}")
        conn.close()
        return True
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False

def test_config():
    """Test configuration loading"""
    print("\n🔍 Testing configuration...")
    try:
        from finmatcher.config.settings import get_settings
        settings = get_settings()
        print(f"✅ Configuration loaded")
        print(f"   - Statements dir: {settings.statements_dir}")
        print(f"   - Thread pool size: {settings.thread_pool_size}")
        return True
    except Exception as e:
        print(f"❌ Configuration failed: {e}")
        return False

def test_directories():
    """Test required directories exist"""
    print("\n🔍 Testing directories...")
    required_dirs = [
        'statements',
        'logs',
        'reports',
        'temp_attachments',
        'output',
        'finmatcher/auth_files'
    ]
    
    all_exist = True
    for dir_path in required_dirs:
        path = Path(dir_path)
        if path.exists():
            print(f"   ✅ {dir_path}")
        else:
            print(f"   ❌ {dir_path} (missing)")
            all_exist = False
    
    return all_exist

def test_statement_files():
    """Test statement files exist"""
    print("\n🔍 Testing statement files...")
    statement_files = [
        'statements/Meriwest Credit Card Statement.pdf',
        'statements/Amex_Credit_Card_Statement.xlsx',
        'statements/Chase_Credit_Card_Statement.xlsx'
    ]
    
    found = 0
    for file_path in statement_files:
        path = Path(file_path)
        if path.exists():
            print(f"   ✅ {file_path}")
            found += 1
        else:
            print(f"   ⚠️  {file_path} (missing)")
    
    print(f"\n   Found {found}/{len(statement_files)} statement files")
    return found > 0

def test_gmail_credentials():
    """Test Gmail credentials exist"""
    print("\n🔍 Testing Gmail credentials...")
    creds_path = Path('finmatcher/auth_files/credentials.json')
    if creds_path.exists():
        print("   ✅ credentials.json found")
        return True
    else:
        print("   ❌ credentials.json missing")
        return False

def main():
    """Run all tests"""
    print("=" * 60)
    print("🚀 FinMatcher System Test")
    print("=" * 60)
    
    tests = [
        ("Imports", test_imports),
        ("Database", test_database),
        ("Configuration", test_config),
        ("Directories", test_directories),
        ("Statement Files", test_statement_files),
        ("Gmail Credentials", test_gmail_credentials)
    ]
    
    results = {}
    for test_name, test_func in tests:
        try:
            results[test_name] = test_func()
        except Exception as e:
            print(f"\n❌ {test_name} test crashed: {e}")
            results[test_name] = False
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 Test Summary")
    print("=" * 60)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {test_name}")
    
    print("\n" + "=" * 60)
    print(f"Results: {passed}/{total} tests passed")
    print("=" * 60)
    
    if passed == total:
        print("\n🎉 All tests passed! System is ready.")
        print("\nRun the system with:")
        print("   python main.py --mode full_reconciliation")
        return 0
    else:
        print("\n⚠️  Some tests failed. Fix issues before running.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
