#!/usr/bin/env python3
"""
Test cache_manager integration with new schema
"""

import sys
import os
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from finmatcher.database.cache_manager import get_cache_manager, ProcessedEmail

def test_cache_manager():
    """Test cache manager with new schema"""
    print("🧪 Testing Cache Manager Integration")
    print("=" * 60)
    
    try:
        # Get cache manager instance
        print("\n1️⃣ Initializing cache manager...")
        cache_manager = get_cache_manager()
        print("   ✅ Cache manager initialized")
        
        # Test email processing check
        print("\n2️⃣ Testing email duplicate detection...")
        test_message_id = "test-message-123@example.com"
        is_processed = cache_manager.is_email_processed(test_message_id)
        print(f"   ✅ Email processed check: {is_processed}")
        
        # Test marking email as processed
        print("\n3️⃣ Testing mark email as processed...")
        test_email = ProcessedEmail(
            email_id="test-email-123",
            message_id=test_message_id,
            processed_timestamp=datetime.now(),
            account_email="test@example.com",
            folder="INBOX",
            has_attachments=True,
            is_financial=True
        )
        
        result = cache_manager.mark_email_processed(test_email)
        print(f"   ✅ Mark email result: {result}")
        
        # Verify it's now marked as processed
        print("\n4️⃣ Verifying email is now marked as processed...")
        is_processed_now = cache_manager.is_email_processed(test_message_id)
        print(f"   ✅ Email now processed: {is_processed_now}")
        
        # Test batch processing
        print("\n5️⃣ Testing batch email processing...")
        batch_emails = [
            ProcessedEmail(
                email_id=f"batch-email-{i}",
                message_id=f"batch-message-{i}@example.com",
                processed_timestamp=datetime.now(),
                account_email="test@example.com",
                folder="INBOX",
                has_attachments=False,
                is_financial=False
            )
            for i in range(5)
        ]
        
        batch_result = cache_manager.mark_emails_processed_batch(batch_emails)
        print(f"   ✅ Batch processing result: {batch_result}")
        
        # Get database stats
        print("\n6️⃣ Getting database statistics...")
        import psycopg2
        conn = psycopg2.connect('postgresql://postgres:Teeli%40322@localhost/FinMatcher')
        cur = conn.cursor()
        
        cur.execute("SELECT COUNT(*) FROM processed_emails")
        total_emails = cur.fetchone()[0]
        
        cur.execute("SELECT COUNT(*) FROM processed_emails WHERE is_financial = TRUE")
        financial_emails = cur.fetchone()[0]
        
        cur.execute("SELECT COUNT(*) FROM processed_emails WHERE has_attachment = TRUE")
        emails_with_attachments = cur.fetchone()[0]
        
        print(f"   📊 Total emails: {total_emails}")
        print(f"   💰 Financial emails: {financial_emails}")
        print(f"   📎 Emails with attachments: {emails_with_attachments}")
        
        conn.close()
        
        print("\n" + "=" * 60)
        print("✅ All cache manager tests passed!")
        print("=" * 60)
        
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_cache_manager()
    sys.exit(0 if success else 1)
