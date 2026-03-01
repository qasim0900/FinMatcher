#!/usr/bin/env python3
"""
Fix all import statements in the project
Changes relative imports to absolute imports with finmatcher prefix
"""

import os
import re
from pathlib import Path

def fix_imports_in_file(filepath):
    """Fix imports in a single file"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # Fix imports - add finmatcher prefix
        patterns = [
            (r'^from config\.', 'from finmatcher.config.'),
            (r'^from database\.', 'from finmatcher.database.'),
            (r'^from utils\.', 'from finmatcher.utils.'),
            (r'^from core\.', 'from finmatcher.core.'),
            (r'^from reports\.', 'from finmatcher.reports.'),
            (r'^from storage\.', 'from finmatcher.storage.'),
            (r'^from orchestration\.', 'from finmatcher.orchestration.'),
            (r'^from optimization\.', 'from finmatcher.optimization.'),
        ]
        
        for pattern, replacement in patterns:
            content = re.sub(pattern, replacement, content, flags=re.MULTILINE)
        
        # Only write if content changed
        if content != original_content:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        
        return False
        
    except Exception as e:
        print(f"Error processing {filepath}: {e}")
        return False

def main():
    """Fix imports in all Python files"""
    print("="*60)
    print("Fixing Import Statements")
    print("="*60)
    print()
    
    # Find all Python files
    python_files = []
    
    # Search in finmatcher directory
    if Path('finmatcher').exists():
        python_files.extend(Path('finmatcher').rglob('*.py'))
    
    # Search in root directory (excluding venv)
    for py_file in Path('.').glob('*.py'):
        if 'venv' not in str(py_file) and '.venv' not in str(py_file):
            python_files.append(py_file)
    
    print(f"Found {len(python_files)} Python files")
    print()
    
    fixed_count = 0
    
    for filepath in python_files:
        if fix_imports_in_file(filepath):
            print(f"✅ Fixed: {filepath}")
            fixed_count += 1
    
    print()
    print("="*60)
    print(f"✅ Fixed {fixed_count} files")
    print("="*60)

if __name__ == "__main__":
    main()
