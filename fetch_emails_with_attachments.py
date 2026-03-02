#!/usr/bin/env python3
"""
Fetch Emails with Attachments

This script fetches financial emails with attachments and saves them to database.
"""

import sys
import time
from datetime import datetime, timedelta

from finmatcher.config.settings import get_settings
from finmatcher.database.cache_manager import get_cache_manager
from finmatcher.core.email_fetcher import EmailFetcher
from finmatcher.utils.logger import get_logger


def fetch_emails_with_attachments():
    """Fetch emails with attachments from all accounts."""
    
    logger = get_logger()
    settings = get_settings()
    cache_manager = get_cache_manager()
    
    logger.info("=" * 80)
    logger.info("FETCHING EMAILS WITH ATTACHMENTS")
    logger.info("=" * 80)
    
    # Show current stats
    stats = cache_manager.get_statistics()
    logger.info(f"\nCurrent Database Stats:")
    logger.info(f"  Processed emails: {stats['processed_emails']}")
    logger.info(f"  Receipts: {stats['receipts']}")
    logger.info(f"  Transactions: {stats['transactions']}")
    logger.info(f"  Matches: {stats['matches']}")
    
    # Initialize email fetcher
    logger.info("\nInitializing email fetcher...")
    email_fetcher = EmailFetcher()
    
    # Fetch emails (no date range = fetch all)
    logger.info("\nFetching emails from all accounts...")
    logger.info("This will:")
    logger.info("  1. Connect to all configured Gmail accounts")
    logger.info("  2. Search for financial emails")
    logger.info("  3. Download attachments (PDFs, images)")
    logger.info("  4. Save to database")
    logger.info("")
    
    start_time = time.time()
    
    try:
        # Fetch all emails with attachments
        emails = email_fetcher.fetch_all_emails(date_range=None)
        
        duration = time.time() - start_time
        
        logger.info("\n" + "=" * 80)
        logger.info("FETCH COMPLETE")
        logger.info("=" * 80)
        logger.info(f"Total emails fetched: {len(emails)}")
        logger.info(f"Duration: {duration:.2f} seconds")
        
        # Count emails with attachments
        emails_with_attachments = [e for e in emails if e.get('attachments')]
        logger.info(f"Emails with attachments: {len(emails_with_attachments)}")
        
        # Show attachment statistics
        total_attachments = sum(len(e.get('attachments', [])) for e in emails)
        logger.info(f"Total attachments: {total_attachments}")
        
        # Show updated stats
        stats = cache_manager.get_statistics()
        logger.info(f"\nUpdated Database Stats:")
        logger.info(f"  Processed emails: {stats['processed_emails']}")
        logger.info(f"  Receipts: {stats['receipts']}")
        
        # Show attachment directory
        logger.info(f"\nAttachments saved to: {settings.temp_attachments_dir}")
        
        # Count files in attachment directory
        if settings.temp_attachments_dir.exists():
            attachment_files = list(settings.temp_attachments_dir.rglob('*'))
            attachment_files = [f for f in attachment_files if f.is_file()]
            logger.info(f"Total attachment files on disk: {len(attachment_files)}")
        
        logger.info("=" * 80)
        
        if emails_with_attachments:
            logger.info("\n✅ SUCCESS: Emails with attachments fetched!")
            logger.info("You can now run: python run_post_email_processing.py")
        else:
            logger.warning("\n⚠ WARNING: No emails with attachments found")
            logger.info("This could mean:")
            logger.info("  - No financial emails have attachments")
            logger.info("  - Emails were already processed")
            logger.info("  - Date range is too narrow")
        
        return len(emails_with_attachments)
    
    except Exception as e:
        logger.error(f"\n❌ ERROR: {e}", exc_info=True)
        return 0


def main():
    """Main entry point."""
    
    try:
        logger = get_logger()
        logger.info("Starting email fetch with attachments...")
        
        count = fetch_emails_with_attachments()
        
        if count > 0:
            return 0
        else:
            return 1
    
    except KeyboardInterrupt:
        print("\n\nProcess interrupted by user")
        return 130
    
    except Exception as e:
        print(f"\n\nFatal error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
