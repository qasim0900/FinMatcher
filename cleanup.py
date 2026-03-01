#!/usr/bin/env python3
"""
FinMatcher - Complete Cleanup Script
Removes all cache, logs, temporary files, and Python cache
Cross-platform (Windows, Linux, macOS)
"""

import os
import shutil
import sys
from pathlib import Path

def print_header():
    """Print cleanup header"""
    print("=" * 60)
    print("FinMatcher - Complete Cleanup")
    print("=" * 60)
    print()

def remove_directory(path: Path, description: str) -> bool:
    """Remove directory and all contents"""
    try:
        if path.exists() and path.is_dir():
            shutil.rmtree(path)
            print(f"    ✓ {description} cleaned")
            return True
        else:
            print(f"    ℹ {description} not found")
            return False
    except Exception as e:
        print(f"    ✗ Error cleaning {description}: {e}")
        return False

def remove_files(pattern: str, description: str) -> int:
    """Remove files matching pattern"""
    try:
        count = 0
        for file_path in Path('.').rglob(pattern):
            if file_path.is_file():
                file_path.unlink()
                count += 1
        
        if count > 0:
            print(f"    ✓ {description} cleaned ({count} files)")
        else:
            print(f"    ℹ No {description} found")
        return count
    except Exception as e:
        print(f"    ✗ Error cleaning {description}: {e}")
        return 0

def clean_directory_contents(path: Path, description: str, extensions: list = None) -> int:
    """Clean contents of directory"""
    try:
        if not path.exists():
            print(f"    ℹ {description} not found")
            return 0
        
        count = 0
        for item in path.iterdir():
            if item.is_file():
                if extensions is None or item.suffix in extensions:
                    item.unlink()
                    count += 1
        
        if count > 0:
            print(f"    ✓ {description} cleaned ({count} files)")
        else:
            print(f"    ℹ {description} is empty")
        return count
    except Exception as e:
        print(f"    ✗ Error cleaning {description}: {e}")
        return 0

def main():
    """Main cleanup function"""
    print_header()
    
    # Check if running from project directory
    if not Path('finmatcher').exists():
        print("ERROR: Please run this script from the FinMatcher project root directory")
        sys.exit(1)
    
    total_cleaned = 0
    
    # 1. Clean Python cache
    print("[1/10] Cleaning Python cache files...")
    
    # Remove __pycache__ directories
    pycache_count = 0
    for pycache_dir in Path('.').rglob('__pycache__'):
        if pycache_dir.is_dir():
            shutil.rmtree(pycache_dir)
            pycache_count += 1
    
    if pycache_count > 0:
        print(f"    ✓ Removed {pycache_count} __pycache__ directories")
        total_cleaned += pycache_count
    
    # Remove .pyc and .pyo files
    pyc_count = remove_files('*.pyc', '.pyc files')
    pyo_count = remove_files('*.pyo', '.pyo files')
    total_cleaned += pyc_count + pyo_count
    
    # 2. Clean logs
    print("\n[2/10] Cleaning logs directory...")
    logs_cleaned = clean_directory_contents(Path('logs'), 'logs', ['.log'])
    total_cleaned += logs_cleaned
    
    # 3. Clean temporary attachments
    print("\n[3/10] Cleaning temporary attachments...")
    temp_cleaned = clean_directory_contents(Path('temp_attachments'), 'temporary attachments')
    total_cleaned += temp_cleaned
    
    # 4. Clean output directory
    print("\n[4/10] Cleaning output directory...")
    output_cleaned = clean_directory_contents(Path('output'), 'output files')
    total_cleaned += output_cleaned
    
    # 5. Clean reports
    print("\n[5/10] Cleaning reports directory...")
    reports_cleaned = clean_directory_contents(
        Path('reports'), 
        'reports', 
        ['.xlsx', '.xls', '.csv']
    )
    total_cleaned += reports_cleaned
    
    # 6. Clean attachments directory
    print("\n[6/10] Cleaning attachments directory...")
    attachments_cleaned = clean_directory_contents(Path('attachments'), 'attachments')
    total_cleaned += attachments_cleaned
    
    # 7. Clean .kiro cache
    print("\n[7/10] Cleaning .kiro cache...")
    kiro_cache = Path('.kiro/cache')
    if remove_directory(kiro_cache, '.kiro cache'):
        kiro_cache.mkdir(parents=True, exist_ok=True)
        total_cleaned += 1
    
    # 8. Clean pytest cache
    print("\n[8/10] Cleaning pytest cache...")
    if remove_directory(Path('.pytest_cache'), 'pytest cache'):
        total_cleaned += 1
    
    # 9. Clean coverage reports
    print("\n[9/10] Cleaning coverage reports...")
    if remove_directory(Path('htmlcov'), 'coverage HTML reports'):
        total_cleaned += 1
    
    coverage_file = Path('.coverage')
    if coverage_file.exists():
        coverage_file.unlink()
        print("    ✓ .coverage file removed")
        total_cleaned += 1
    
    # 10. Clean SQLite database (if exists)
    print("\n[10/10] Cleaning SQLite database (if exists)...")
    sqlite_db = Path('finmatcher.db')
    if sqlite_db.exists():
        sqlite_db.unlink()
        print("    ✓ SQLite database removed")
        total_cleaned += 1
    else:
        print("    ℹ No SQLite database found")
    
    # Summary
    print("\n" + "=" * 60)
    print("✓ Cleanup Complete!")
    print("=" * 60)
    print(f"\nTotal items cleaned: {total_cleaned}")
    print("\nCleaned:")
    print("  - Python cache (__pycache__, .pyc, .pyo)")
    print("  - Log files (logs/*.log)")
    print("  - Temporary attachments (temp_attachments/*)")
    print("  - Output files (output/*)")
    print("  - Excel reports (reports/*.xlsx)")
    print("  - Attachments (attachments/*)")
    print("  - Kiro cache (.kiro/cache)")
    print("  - Test cache (.pytest_cache)")
    print("  - Coverage reports (htmlcov, .coverage)")
    print("  - SQLite database (if exists)")
    print("\nNote: PostgreSQL database records and configuration files are preserved.")
    print()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nCleanup interrupted by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nUnexpected error: {e}")
        sys.exit(1)
