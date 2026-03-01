#!/usr/bin/env python3
"""
Verify milestone data in the database
Enhanced version with detailed statistics
"""

import os
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

def print_section(title):
    """Print a formatted section header"""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)

def print_subsection(title):
    """Print a formatted subsection header"""
    print(f"\n📊 {title}")
    print("-" * 80)

def verify_milestones():
    """Verify all milestone data with detailed statistics"""
    db_url = os.getenv('DATABASE_URL')
    if not db_url:
        print("❌ ERROR: DATABASE_URL not found in .env")
        return
    
    try:
        conn = psycopg2.connect(db_url)
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        print_section("FINMATCHER MILESTONE VERIFICATION")
        print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # ===========================
        # Milestone 1: Meriwest
        # ===========================
        print_subsection("MILESTONE 1: Meriwest Credit Card Transactions")
        cursor.execute("""
            SELECT 
                COUNT(*) as total_transactions,
                SUM(amount) as total_amount,
                AVG(amount) as avg_amount,
                MIN(transaction_date) as earliest_date,
                MAX(transaction_date) as latest_date
            FROM receipts
            WHERE payment_method = 'Meriwest'
        """)
        result = cursor.fetchone()
        print(f"  Total Transactions: {result['total_transactions']}")
        print(f"  Total Amount: ${result['total_amount'] or 0:,.2f}")
        print(f"  Average Amount: ${result['avg_amount'] or 0:,.2f}")
        print(f"  Date Range: {result['earliest_date']} to {result['latest_date']}")
        
        # Sample transactions
        cursor.execute("""
            SELECT merchant_name, amount, transaction_date
            FROM receipts
            WHERE payment_method = 'Meriwest'
            ORDER BY transaction_date DESC
            LIMIT 5
        """)
        print("\n  Recent Transactions:")
        for row in cursor.fetchall():
            print(f"    • {row['transaction_date']} | {row['merchant_name'][:40]:40} | ${row['amount']:>10,.2f}")
        
        # ===========================
        # Milestone 2: Amex
        # ===========================
        print_subsection("MILESTONE 2: Amex Credit Card Transactions")
        cursor.execute("""
            SELECT 
                COUNT(*) as total_transactions,
                SUM(amount) as total_amount,
                AVG(amount) as avg_amount,
                MIN(transaction_date) as earliest_date,
                MAX(transaction_date) as latest_date
            FROM receipts
            WHERE payment_method = 'Amex'
        """)
        result = cursor.fetchone()
        print(f"  Total Transactions: {result['total_transactions']}")
        print(f"  Total Amount: ${result['total_amount'] or 0:,.2f}")
        print(f"  Average Amount: ${result['avg_amount'] or 0:,.2f}")
        print(f"  Date Range: {result['earliest_date']} to {result['latest_date']}")
        
        # Sample transactions
        cursor.execute("""
            SELECT merchant_name, amount, transaction_date
            FROM receipts
            WHERE payment_method = 'Amex'
            ORDER BY transaction_date DESC
            LIMIT 5
        """)
        print("\n  Recent Transactions:")
        for row in cursor.fetchall():
            print(f"    • {row['transaction_date']} | {row['merchant_name'][:40]:40} | ${row['amount']:>10,.2f}")
        
        # ===========================
        # Milestone 3: Chase
        # ===========================
        print_subsection("MILESTONE 3: Chase Credit Card Transactions")
        cursor.execute("""
            SELECT 
                COUNT(*) as total_transactions,
                SUM(amount) as total_amount,
                AVG(amount) as avg_amount,
                MIN(transaction_date) as earliest_date,
                MAX(transaction_date) as latest_date
            FROM receipts
            WHERE payment_method = 'Chase'
        """)
        result = cursor.fetchone()
        print(f"  Total Transactions: {result['total_transactions']}")
        print(f"  Total Amount: ${result['total_amount'] or 0:,.2f}")
        print(f"  Average Amount: ${result['avg_amount'] or 0:,.2f}")
        print(f"  Date Range: {result['earliest_date']} to {result['latest_date']}")
        
        # Sample transactions
        cursor.execute("""
            SELECT merchant_name, amount, transaction_date
            FROM receipts
            WHERE payment_method = 'Chase'
            ORDER BY transaction_date DESC
            LIMIT 5
        """)
        print("\n  Recent Transactions:")
        for row in cursor.fetchall():
            print(f"    • {row['transaction_date']} | {row['merchant_name'][:40]:40} | ${row['amount']:>10,.2f}")
        
        # ===========================
        # Milestone 4: Unified Reconciliation
        # ===========================
        print_subsection("MILESTONE 4: Unified Reconciliation")
        
        # All cards summary
        cursor.execute("""
            SELECT 
                payment_method,
                COUNT(*) as transaction_count,
                SUM(amount) as total_amount,
                AVG(amount) as avg_amount
            FROM receipts
            GROUP BY payment_method
            ORDER BY transaction_count DESC
        """)
        print("\n  Transactions by Card:")
        total_txns = 0
        total_amt = 0
        for row in cursor.fetchall():
            print(f"    {row['payment_method']:15} | {row['transaction_count']:5} txns | ${row['total_amount'] or 0:>12,.2f} | Avg: ${row['avg_amount'] or 0:>8,.2f}")
            total_txns += row['transaction_count']
            total_amt += (row['total_amount'] or 0)
        print(f"    {'TOTAL':15} | {total_txns:5} txns | ${total_amt:>12,.2f}")
        
        # Email receipts
        cursor.execute("""
            SELECT 
                COUNT(*) as total_emails,
                COUNT(CASE WHEN amount IS NOT NULL THEN 1 END) as emails_with_amount,
                COUNT(CASE WHEN attachment_file_path IS NOT NULL OR attachment_image_path IS NOT NULL THEN 1 END) as emails_with_attachments,
                SUM(amount) as total_email_amount
            FROM emails
        """)
        result = cursor.fetchone()
        print(f"\n  Email Receipts:")
        print(f"    Total Emails: {result['total_emails']}")
        print(f"    Emails with Amount: {result['emails_with_amount']}")
        print(f"    Emails with Attachments: {result['emails_with_attachments']}")
        print(f"    Total Email Amount: ${result['total_email_amount'] or 0:,.2f}")
        
        # Matching statistics
        cursor.execute("""
            SELECT 
                confidence_level,
                COUNT(*) as match_count,
                AVG(match_score) as avg_score
            FROM matches
            GROUP BY confidence_level
            ORDER BY match_count DESC
        """)
        print(f"\n  Matching Statistics:")
        total_matches = 0
        for row in cursor.fetchall():
            print(f"    {row['confidence_level']:10} | {row['match_count']:5} matches | Avg Score: {row['avg_score']:.4f}")
            total_matches += row['match_count']
        
        # Overall status
        cursor.execute("""
            SELECT 
                (SELECT COUNT(*) FROM receipts) as total_transactions,
                (SELECT COUNT(*) FROM emails WHERE amount IS NOT NULL) as total_email_receipts,
                (SELECT COUNT(*) FROM matches) as total_matches
        """)
        result = cursor.fetchone()
        match_rate = (result['total_matches'] / result['total_transactions'] * 100) if result['total_transactions'] > 0 else 0
        
        print(f"\n  Overall Reconciliation Status:")
        print(f"    Total Credit Card Transactions: {result['total_transactions']}")
        print(f"    Total Email Receipts: {result['total_email_receipts']}")
        print(f"    Total Matches: {result['total_matches']}")
        print(f"    Match Rate: {match_rate:.2f}%")
        
        # Unmatched transactions
        cursor.execute("""
            SELECT 
                payment_method,
                COUNT(*) as unmatched_count,
                SUM(amount) as unmatched_amount
            FROM receipts r
            WHERE NOT EXISTS (
                SELECT 1 FROM matches m WHERE m.receipt_id = r.receipt_id
            )
            GROUP BY payment_method
        """)
        print(f"\n  Unmatched Transactions:")
        for row in cursor.fetchall():
            print(f"    {row['payment_method']:15} | {row['unmatched_count']:5} unmatched | ${row['unmatched_amount'] or 0:>12,.2f}")
        
        # ===========================
        # Additional Statistics
        # ===========================
        print_subsection("ADDITIONAL STATISTICS")
        
        # Top merchants
        cursor.execute("""
            SELECT 
                merchant_name,
                COUNT(*) as transaction_count,
                SUM(amount) as total_spent
            FROM receipts
            GROUP BY merchant_name
            ORDER BY transaction_count DESC
            LIMIT 10
        """)
        print("\n  Top 10 Merchants by Transaction Count:")
        for row in cursor.fetchall():
            print(f"    {row['merchant_name'][:40]:40} | {row['transaction_count']:3} txns | ${row['total_spent'] or 0:>10,.2f}")
        
        # Monthly breakdown
        cursor.execute("""
            SELECT 
                TO_CHAR(transaction_date, 'YYYY-MM') as month,
                COUNT(*) as transaction_count,
                SUM(amount) as total_amount
            FROM receipts
            GROUP BY TO_CHAR(transaction_date, 'YYYY-MM')
            ORDER BY month DESC
            LIMIT 6
        """)
        print(f"\n  Monthly Transaction Summary (Last 6 Months):")
        for row in cursor.fetchall():
            print(f"    {row['month']} | {row['transaction_count']:5} txns | ${row['total_amount'] or 0:>12,.2f}")
        
        print_section("VERIFICATION COMPLETE")
        
        # Status indicators
        if result['total_transactions'] == 0:
            print("\n⚠️  WARNING: No credit card transactions found!")
            print("   Run: python reconcile_all.py")
        elif result['total_matches'] == 0:
            print("\n⚠️  WARNING: No matches found!")
            print("   Run: python reconcile_all.py")
        elif match_rate < 50:
            print(f"\n⚠️  WARNING: Low match rate ({match_rate:.2f}%)")
            print("   Consider reviewing matching parameters")
        else:
            print(f"\n✅ SUCCESS: {match_rate:.2f}% of transactions matched!")
            print("   Ready to upload to Google Drive")
        
        print("\n" + "=" * 80 + "\n")
        
        cursor.close()
        conn.close()
        
    except psycopg2.Error as e:
        print(f"\n❌ Database Error: {e}")
        print("\nTroubleshooting:")
        print("  1. Check if PostgreSQL is running: sudo systemctl status postgresql")
        print("  2. Verify DATABASE_URL in .env file")
        print("  3. Check database exists: psql -U postgres -l")
    except Exception as e:
        print(f"\n❌ Error: {e}")

if __name__ == "__main__":
    verify_milestones()