#!/usr/bin/env python3
"""
Test script to check if receipts are being extracted properly
"""

import sys
import os
from pathlib import Path

# Add finmatcher to path
sys.path.insert(0, str(Path(__file__).parent / 'finmatcher'))

# Bypass security check
os.environ['SKIP_SECURITY_VALIDATION'] = 'true'

from database.cache_manager import get_cache_manager
from utils.logger import get_logger

logger = get_logger()

def main():
    """Check receipts in database"""
    print("=" * 80)
    print("Checking Receipts in Database")
    print("=" * 80)
    
    try:
        cache_manager = get_cache_manager()
        
        # Get statistics
        stats = cache_manager.get_statistics()
        
        print("\nDatabase Statistics:")
        print(f"  Processed Emails: {stats['processed_emails']}")
        print(f"  Receipts: {stats['receipts']}")
        print(f"  Transactions: {stats['transactions']}")
        print(f"  Matches: {stats['matches']}")
        print(f"  Matched Receipts: {stats['matched_receipts']}")
        print(f"  Unmatched Receipts: {stats['unmatched_receipts']}")
        
        # Get all receipts
        receipts = cache_manager.get_all_receipts()
        
        print(f"\nTotal Receipts Retrieved: {len(receipts)}")
        
        if receipts:
            print("\nSample Receipts (first 5):")
            for i, receipt in enumerate(receipts[:5], 1):
                print(f"\n  Receipt {i}:")
                print(f"    Sender: {receipt.get('sender_name')} <{receipt.get('sender_email')}>")
                print(f"    Subject: {receipt.get('subject')}")
                print(f"    Date: {receipt.get('date')}")
                print(f"    Amount: ${receipt.get('amount')}")
                print(f"    Attachment: {receipt.get('attachment_path')}")
        else:
            print("\n[WARNING] No receipts found in database!")
            print("\nPossible reasons:")
            print("  1. Email fetching not completed")
            print("  2. No attachments in emails")
            print("  3. OCR processing failed")
            print("  4. Receipts not saved to database")
            
            print("\nChecking processed emails...")
            if stats['processed_emails'] > 0:
                print(f"  ✓ {stats['processed_emails']} emails were processed")
                print("  Issue: Attachments might not have been processed with OCR")
            else:
                print("  ✗ No emails processed yet")
                print("  Run: python run_reconciliation.py")
        
        print("\n" + "=" * 80)
        
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
