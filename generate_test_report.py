#!/usr/bin/env python3
"""
Generate comprehensive test report for FinMatcher
"""

import psycopg2
from datetime import datetime
from pathlib import Path

def generate_report():
    """Generate comprehensive test report"""
    
    print("=" * 80)
    print("🎯 FINMATCHER - COMPREHENSIVE TEST REPORT")
    print("=" * 80)
    print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Database Connection Test
    print("1️⃣ DATABASE CONNECTION TEST")
    print("-" * 80)
    try:
        conn = psycopg2.connect('postgresql://postgres:Teeli%40322@localhost/FinMatcher')
        cur = conn.cursor()
        print("   ✅ Database connection successful")
        
        # Check tables
        cur.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema='public' 
            ORDER BY table_name
        """)
        tables = cur.fetchall()
        print(f"   ✅ Tables found: {len(tables)}")
        for table in tables:
            print(f"      - {table[0]}")
        
    except Exception as e:
        print(f"   ❌ Database connection failed: {e}")
        return
    
    print()
    
    # Email Processing Stats
    print("2️⃣ EMAIL PROCESSING STATISTICS")
    print("-" * 80)
    
    cur.execute("SELECT COUNT(*) FROM processed_emails")
    total_emails = cur.fetchone()[0]
    
    cur.execute("SELECT COUNT(*) FROM processed_emails WHERE has_attachment = TRUE")
    emails_with_attachments = cur.fetchone()[0]
    
    cur.execute("SELECT COUNT(*) FROM processed_emails WHERE is_financial = TRUE")
    financial_emails = cur.fetchone()[0]
    
    cur.execute("SELECT COUNT(DISTINCT account_email) FROM processed_emails")
    unique_accounts = cur.fetchone()[0]
    
    cur.execute("SELECT COUNT(DISTINCT folder) FROM processed_emails")
    unique_folders = cur.fetchone()[0]
    
    print(f"   📧 Total Emails Processed: {total_emails}")
    print(f"   📎 Emails with Attachments: {emails_with_attachments}")
    print(f"   💰 Financial Emails: {financial_emails}")
    print(f"   👤 Unique Email Accounts: {unique_accounts}")
    print(f"   📁 Unique Folders: {unique_folders}")
    
    if total_emails > 0:
        print(f"   📊 Attachment Rate: {emails_with_attachments/total_emails*100:.1f}%")
        print(f"   📊 Financial Rate: {financial_emails/total_emails*100:.1f}%")
    
    print()
    
    # Transaction Stats
    print("3️⃣ TRANSACTION STATISTICS")
    print("-" * 80)
    
    cur.execute("SELECT COUNT(*) FROM transactions")
    total_transactions = cur.fetchone()[0]
    
    cur.execute("SELECT COUNT(DISTINCT statement_name) FROM transactions")
    unique_sources = cur.fetchone()[0]
    
    print(f"   💳 Total Transactions: {total_transactions}")
    print(f"   🏦 Unique Statement Sources: {unique_sources}")
    
    print()
    
    # Receipt Stats
    print("4️⃣ RECEIPT STATISTICS")
    print("-" * 80)
    
    cur.execute("SELECT COUNT(*) FROM receipts")
    total_receipts = cur.fetchone()[0]
    
    cur.execute("SELECT COUNT(*) FROM receipts WHERE amount IS NOT NULL")
    receipts_with_amount = cur.fetchone()[0]
    
    print(f"   🧾 Total Receipts: {total_receipts}")
    print(f"   💵 Receipts with Amount: {receipts_with_amount}")
    
    print()
    
    # Match Stats
    print("5️⃣ MATCHING STATISTICS")
    print("-" * 80)
    
    cur.execute("SELECT COUNT(*) FROM matches")
    total_matches = cur.fetchone()[0]
    
    print(f"   🔗 Total Matches: {total_matches}")
    
    print()
    
    # File System Check
    print("6️⃣ FILE SYSTEM CHECK")
    print("-" * 80)
    
    directories = {
        'statements': Path('statements'),
        'logs': Path('logs'),
        'reports': Path('reports'),
        'temp_attachments': Path('temp_attachments'),
        'output': Path('output')
    }
    
    for name, path in directories.items():
        if path.exists():
            files = list(path.glob('*'))
            print(f"   ✅ {name}: {len(files)} files")
        else:
            print(f"   ❌ {name}: Directory not found")
    
    print()
    
    # Performance Metrics
    print("7️⃣ PERFORMANCE METRICS")
    print("-" * 80)
    
    cur.execute("SELECT COUNT(*) FROM matching_statistics")
    stats_count = cur.fetchone()[0]
    
    if stats_count > 0:
        print(f"   📊 Processing runs recorded: {stats_count}")
    else:
        print("   ⚠️  No processing statistics available yet")
    
    print()
    
    # System Health Check
    print("8️⃣ SYSTEM HEALTH CHECK")
    print("-" * 80)
    
    health_checks = []
    
    # Check 1: Database connectivity
    health_checks.append(("Database Connection", True))
    
    # Check 2: Tables exist
    health_checks.append(("Database Tables", len(tables) >= 6))
    
    # Check 3: Email processing working
    health_checks.append(("Email Processing", total_emails > 0))
    
    # Check 4: Logs directory
    health_checks.append(("Logs Directory", Path('logs').exists()))
    
    # Check 5: Statements directory
    health_checks.append(("Statements Directory", Path('statements').exists()))
    
    for check_name, status in health_checks:
        status_icon = "✅" if status else "❌"
        print(f"   {status_icon} {check_name}")
    
    passed = sum(1 for _, status in health_checks if status)
    total = len(health_checks)
    
    print()
    print(f"   Health Score: {passed}/{total} ({passed/total*100:.0f}%)")
    
    print()
    
    # Final Summary
    print("=" * 80)
    print("📊 SUMMARY")
    print("=" * 80)
    
    if passed == total:
        print("   🎉 ALL SYSTEMS OPERATIONAL")
        print("   ✅ Database: Connected and populated")
        print("   ✅ Email Processing: Active")
        print("   ✅ File System: Ready")
        print("   ✅ System Health: 100%")
    else:
        print("   ⚠️  SOME ISSUES DETECTED")
        print(f"   System Health: {passed/total*100:.0f}%")
    
    print()
    print("=" * 80)
    
    conn.close()

if __name__ == "__main__":
    generate_report()
