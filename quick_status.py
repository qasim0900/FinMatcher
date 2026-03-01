#!/usr/bin/env python3
"""Quick status check for FinMatcher"""

import psycopg2
from datetime import datetime

conn = psycopg2.connect('postgresql://postgres:Teeli%40322@localhost/FinMatcher')
cur = conn.cursor()

print("\n" + "=" * 60)
print("📊 FinMatcher - Quick Status")
print("=" * 60)
print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

# Email stats
cur.execute("SELECT COUNT(*) FROM processed_emails")
total = cur.fetchone()[0]

cur.execute("SELECT COUNT(*) FROM processed_emails WHERE has_attachment = TRUE")
attachments = cur.fetchone()[0]

cur.execute("SELECT COUNT(*) FROM processed_emails WHERE is_financial = TRUE")
financial = cur.fetchone()[0]

cur.execute("SELECT COUNT(DISTINCT account_email) FROM processed_emails")
accounts = cur.fetchone()[0]

print(f"📧 Total Emails: {total:,}")
print(f"📎 With Attachments: {attachments}")
print(f"💰 Financial: {financial}")
print(f"👤 Accounts: {accounts}")

if total > 0:
    print(f"\n📊 Rates:")
    print(f"   Attachment Rate: {attachments/total*100:.1f}%")
    print(f"   Financial Rate: {financial/total*100:.1f}%")

# Transaction stats
cur.execute("SELECT COUNT(*) FROM transactions")
transactions = cur.fetchone()[0]

cur.execute("SELECT COUNT(*) FROM receipts")
receipts = cur.fetchone()[0]

cur.execute("SELECT COUNT(*) FROM matches")
matches = cur.fetchone()[0]

print(f"\n💳 Transactions: {transactions}")
print(f"🧾 Receipts: {receipts}")
print(f"🔗 Matches: {matches}")

print("\n" + "=" * 60)

conn.close()
