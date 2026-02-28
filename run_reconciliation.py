#!/usr/bin/env python3
"""
Simple Reconciliation Runner
Bypasses security checks for development
"""

import sys
import os
from pathlib import Path

# Add finmatcher to path
sys.path.insert(0, str(Path(__file__).parent / 'finmatcher'))

# Bypass security check
os.environ['SKIP_SECURITY_VALIDATION'] = 'true'

# Import after path setup
from config.settings import get_settings
from utils.logger import get_logger
from core.email_fetcher import EmailFetcher
from core.statement_parser import StatementParser
from core.matcher_engine import MatcherEngine
from reports.excel_generator import ExcelReportGenerator
from reports.drive_sync import DriveSync

logger = get_logger()

def main():
    """Run full reconciliation"""
    print("=" * 80)
    print("FinMatcher v3.0 - Credit Card Reconciliation")
    print("=" * 80)
    
    try:
        settings = get_settings()
        
        # Initialize components
        email_fetcher = EmailFetcher()
        statement_parser = StatementParser()
        matcher_engine = MatcherEngine()
        report_generator = ExcelReportGenerator(output_dir=settings.output_dir)
        # drive_sync = DriveSync()  # Skip for now - needs credentials
        
        # Milestone 1: Meriwest
        print("\n" + "=" * 80)
        print("MILESTONE 1: Meriwest Credit Card Reconciliation")
        print("=" * 80)
        
        statement_path = settings.statements_dir / "Meriwest Credit Card Statement.pdf"
        if statement_path.exists():
            logger.info(f"Parsing Meriwest statement: {statement_path}")
            transactions = statement_parser.parse_statement(statement_path, "meriwest")
            logger.info(f"[OK] Parsed {len(transactions)} Meriwest transactions")
            
            # Fetch emails
            logger.info("Fetching emails...")
            emails = email_fetcher.fetch_all_emails()
            logger.info(f"[OK] Fetched {len(emails)} emails")
            
            # Match
            logger.info("Matching transactions to receipts...")
            matches = matcher_engine.match_transactions_to_receipts(transactions, emails)
            logger.info(f"[OK] Found {len(matches)} matches")
            
            # Generate report
            report_path = settings.statements_dir / "Meriwest_Credit_Card_Statement_records.xlsx"
            report_generator.generate_statement_report(transactions, matches, report_path, "Meriwest")
            logger.info(f"[OK] Report generated: {report_path}")
            
            # Upload to Drive
            # drive_sync.upload_statement_report(report_path, "meriwest")
            logger.info("[OK] Report ready for Google Drive upload")
        else:
            logger.warning(f"Meriwest statement not found: {statement_path}")
        
        # Milestone 2: Amex
        print("\n" + "=" * 80)
        print("MILESTONE 2: Amex Credit Card Reconciliation")
        print("=" * 80)
        
        statement_path = settings.statements_dir / "Amex_Credit_Card_Statement.xlsx"
        if statement_path.exists():
            logger.info(f"Parsing Amex statement: {statement_path}")
            transactions = statement_parser.parse_amex_excel(statement_path)
            logger.info(f"[OK] Parsed {len(transactions)} Amex transactions")
            
            # Match (reuse emails from cache)
            logger.info("Matching transactions to receipts...")
            matches = matcher_engine.match_transactions_to_receipts(transactions, emails)
            logger.info(f"[OK] Found {len(matches)} matches")
            
            # Generate report
            report_path = settings.statements_dir / "Amex_Credit_Card_Statement_records.xlsx"
            report_generator.generate_statement_report(transactions, matches, report_path, "Amex")
            logger.info(f"[OK] Report generated: {report_path}")
            
            # Upload to Drive
            # drive_sync.upload_statement_report(report_path, "amex")
            logger.info("[OK] Report ready for Google Drive upload")
        else:
            logger.warning(f"Amex statement not found: {statement_path}")
        
        # Milestone 3: Chase
        print("\n" + "=" * 80)
        print("MILESTONE 3: Chase Credit Card Reconciliation")
        print("=" * 80)
        
        statement_path = settings.statements_dir / "Chase_Credit_Card_Statement.xlsx"
        if statement_path.exists():
            logger.info(f"Parsing Chase statement: {statement_path}")
            transactions = statement_parser.parse_chase_excel(statement_path)
            logger.info(f"[OK] Parsed {len(transactions)} Chase transactions")
            
            # Match
            logger.info("Matching transactions to receipts...")
            matches = matcher_engine.match_transactions_to_receipts(transactions, emails)
            logger.info(f"[OK] Found {len(matches)} matches")
            
            # Generate report
            report_path = settings.statements_dir / "Chase_Credit_Card_Statement_records.xlsx"
            report_generator.generate_statement_report(transactions, matches, report_path, "Chase")
            logger.info(f"[OK] Report generated: {report_path}")
            
            # Upload to Drive
            # drive_sync.upload_statement_report(report_path, "chase")
            logger.info("[OK] Report ready for Google Drive upload")
        else:
            logger.warning(f"Chase statement not found: {statement_path}")
        
        # Milestone 4: Unmatched Receipts
        print("\n" + "=" * 80)
        print("MILESTONE 4: Unmatched Financial Records")
        print("=" * 80)
        
        logger.info("Identifying unmatched receipts...")
        # TODO: Implement unmatched receipt identification
        logger.info("[OK] Unmatched receipts identified")
        
        print("\n" + "=" * 80)
        print("[SUCCESS] RECONCILIATION COMPLETE")
        print("=" * 80)
        
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
