#!/usr/bin/env python3
"""
Real-time progress monitor for FinMatcher
"""

import psycopg2
import time
from datetime import datetime

def monitor_progress():
    """Monitor processing progress in real-time"""
    
    conn_string = 'postgresql://postgres:Teeli%40322@localhost/FinMatcher'
    
    print("🔍 FinMatcher - Real-time Progress Monitor")
    print("=" * 60)
    print("Press Ctrl+C to stop monitoring\n")
    
    last_count = 0
    start_time = time.time()
    
    try:
        while True:
            try:
                conn = psycopg2.connect(conn_string)
                cur = conn.cursor()
                
                # Get current counts
                cur.execute("SELECT COUNT(*) FROM processed_emails")
                total_emails = cur.fetchone()[0]
                
                cur.execute("SELECT COUNT(*) FROM processed_emails WHERE has_attachment = TRUE")
                with_attachments = cur.fetchone()[0]
                
                cur.execute("SELECT COUNT(*) FROM processed_emails WHERE is_financial = TRUE")
                financial = cur.fetchone()[0]
                
                # Calculate rate
                elapsed = time.time() - start_time
                if elapsed > 0:
                    rate = (total_emails - last_count) / 10  # emails per second
                else:
                    rate = 0
                
                # Display progress
                timestamp = datetime.now().strftime('%H:%M:%S')
                print(f"\r[{timestamp}] 📧 Emails: {total_emails:,} | "
                      f"📎 Attachments: {with_attachments} | "
                      f"💰 Financial: {financial} | "
                      f"⚡ Rate: {rate:.1f}/s", end='', flush=True)
                
                last_count = total_emails
                conn.close()
                
                time.sleep(10)
                
            except psycopg2.OperationalError as e:
                print(f"\n❌ Database connection error: {e}")
                time.sleep(10)
                
    except KeyboardInterrupt:
        print("\n\n✅ Monitoring stopped")
        print("=" * 60)
        
        # Final summary
        try:
            conn = psycopg2.connect(conn_string)
            cur = conn.cursor()
            
            cur.execute("SELECT COUNT(*) FROM processed_emails")
            total = cur.fetchone()[0]
            
            cur.execute("SELECT COUNT(*) FROM processed_emails WHERE has_attachment = TRUE")
            attachments = cur.fetchone()[0]
            
            cur.execute("SELECT COUNT(*) FROM processed_emails WHERE is_financial = TRUE")
            financial = cur.fetchone()[0]
            
            print(f"\n📊 Final Statistics:")
            print(f"   Total Emails: {total:,}")
            print(f"   With Attachments: {attachments}")
            print(f"   Financial: {financial}")
            
            if total > 0:
                print(f"   Attachment Rate: {attachments/total*100:.1f}%")
                print(f"   Financial Rate: {financial/total*100:.1f}%")
            
            conn.close()
            
        except Exception as e:
            print(f"Error getting final stats: {e}")

if __name__ == "__main__":
    monitor_progress()
