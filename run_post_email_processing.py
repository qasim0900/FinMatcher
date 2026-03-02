#!/usr/bin/env python3
"""
Post-Email Processing Script - Complete workflow after emails are fetched

This script runs the complete processing pipeline after emails have been
fetched and stored in the database:
1. OCR Processing - Extract text from attachments
2. Statement Parsing - Parse credit card statements
3. Intelligent Matching - Match transactions to receipts
4. Report Generation - Create Excel reports
5. Drive Upload - Upload reports to Google Drive
"""

import sys
import time
import argparse
from pathlib import Path
from typing import List, Dict
from decimal import Decimal

from finmatcher.config.settings import get_settings
from finmatcher.database.cache_manager import get_cache_manager
from finmatcher.core.ocr_engine import OCREngine
from finmatcher.core.statement_parser import StatementParser
from finmatcher.core.matcher_engine import MatcherEngine
from finmatcher.reports.excel_generator import ExcelReportGenerator
from finmatcher.reports.drive_sync import DriveSync
from finmatcher.utils.logger import get_logger
from finmatcher.database.models import Receipt, Transaction


class PostEmailProcessor:
    """Complete post-email processing pipeline."""
    
    def __init__(self):
        """Initialize all components."""
        self.logger = get_logger()
        self.settings = get_settings()
        self.cache_manager = get_cache_manager()
        
        # Initialize components
        self.ocr_engine = OCREngine()
        self.statement_parser = StatementParser()
        self.matcher_engine = MatcherEngine()
        self.report_generator = ExcelReportGenerator(output_dir='reports')
        self.drive_sync = DriveSync()
        
        self.logger.info("Post-Email Processor initialized")
    
    def step1_ocr_processing(self) -> int:
        """Step 1: Process email attachments with OCR."""
        self.logger.info("\n" + "=" * 80)
        self.logger.info("STEP 1: OCR PROCESSING")
        self.logger.info("=" * 80)
        
        start_time = time.time()
        
        # Fetch emails with attachments from database
        emails = self._fetch_emails_with_attachments()
        
        if not emails:
            self.logger.warning("No emails with attachments found")
            return 0
        
        self.logger.info(f"Found {len(emails)} emails with attachments")
        
        receipts_created = 0
        total_attachments = 0
        
        for idx, email_data in enumerate(emails, 1):
            self.logger.info(f"\n[{idx}/{len(emails)}] Processing: {email_data.get('subject', 'No Subject')[:50]}")
            
            attachments = email_data.get('attachments', [])
            total_attachments += len(attachments)
            
            if not attachments:
                continue
            
            try:
                # Process attachments in batch
                processed = self.ocr_engine.process_attachments_batch(attachments)
                
                # Create receipts from processed attachments
                for attachment in processed:
                    receipt = self._create_receipt_from_attachment(email_data, attachment)
                    
                    if receipt and self.cache_manager.save_receipt(receipt):
                        receipts_created += 1
                        
                        confidence = attachment.get('confidence_score', 0.0)
                        amounts = attachment.get('extracted_amounts', [])
                        
                        self.logger.info(f"  ✓ {attachment['filename']} - Confidence: {confidence:.1%}")
                        if amounts:
                            self.logger.info(f"    Amount: ${amounts[0]}")
            
            except Exception as e:
                self.logger.error(f"  Error processing email: {e}")
                continue
        
        duration = time.time() - start_time
        self.logger.info(f"\n[OK] OCR Processing Complete")
        self.logger.info(f"  Receipts created: {receipts_created}")
        self.logger.info(f"  Duration: {duration:.2f}s")
        
        return receipts_created
    
    def step2_parse_statements(self) -> Dict[str, List[Transaction]]:
        """Step 2: Parse credit card statements."""
        self.logger.info("\n" + "=" * 80)
        self.logger.info("STEP 2: STATEMENT PARSING")
        self.logger.info("=" * 80)
        
        all_transactions = {}
        
        # Define statements to parse
        statements = [
            {
                'name': 'Meriwest',
                'file': 'Meriwest Credit Card Statement.pdf',
                'parser': 'meriwest'
            },
            {
                'name': 'Amex',
                'file': 'Amex_Credit_Card_Statement.xlsx',
                'parser': 'amex'
            },
            {
                'name': 'Chase',
                'file': 'Chase_Credit_Card_Statement.xlsx',
                'parser': 'chase'
            }
        ]
        
        for stmt in statements:
            statement_path = self.settings.statements_dir / stmt['file']
            
            if not statement_path.exists():
                self.logger.warning(f"Statement not found: {statement_path}")
                continue
            
            self.logger.info(f"\nParsing {stmt['name']} statement...")
            
            try:
                # Parse based on type
                if stmt['parser'] == 'meriwest':
                    transactions = self.statement_parser.parse_statement(statement_path, "meriwest")
                elif stmt['parser'] == 'amex':
                    transactions = self.statement_parser.parse_amex_excel(statement_path)
                elif stmt['parser'] == 'chase':
                    transactions = self.statement_parser.parse_chase_excel(statement_path)
                else:
                    continue
                
                self.logger.info(f"  ✓ Parsed {len(transactions)} transactions")
                all_transactions[stmt['name']] = transactions
            
            except Exception as e:
                self.logger.error(f"  Error parsing {stmt['name']}: {e}")
                continue
        
        self.logger.info(f"\n[OK] Statement Parsing Complete")
        self.logger.info(f"  Total statements parsed: {len(all_transactions)}")
        
        return all_transactions
    
    def step3_match_transactions(self, all_transactions: Dict[str, List[Transaction]]) -> Dict:
        """Step 3: Match transactions to receipts."""
        self.logger.info("\n" + "=" * 80)
        self.logger.info("STEP 3: INTELLIGENT MATCHING")
        self.logger.info("=" * 80)
        
        # Get all receipts from database
        self.logger.info("Loading receipts from database...")
        receipts = self._get_all_receipts()
        self.logger.info(f"Found {len(receipts)} receipts")
        
        matching_results = {}
        
        for statement_name, transactions in all_transactions.items():
            self.logger.info(f"\nMatching {statement_name} transactions...")
            self.logger.info(f"  Transactions: {len(transactions)}")
            
            try:
                # Run matching engine
                matches, unmatched_txns, unmatched_rcpts, stats = self.matcher_engine.match_all(
                    transactions, receipts
                )
                
                self.logger.info(f"  ✓ Matches found: {len(matches)}")
                self.logger.info(f"    - Exact matches: {stats.exact_matches}")
                self.logger.info(f"    - Fuzzy matches: {stats.fuzzy_matches}")
                self.logger.info(f"    - Semantic matches: {stats.semantic_matches}")
                self.logger.info(f"  Unmatched transactions: {len(unmatched_txns)}")
                
                matching_results[statement_name] = {
                    'transactions': transactions,
                    'matches': matches,
                    'unmatched_transactions': unmatched_txns,
                    'unmatched_receipts': unmatched_rcpts,
                    'statistics': stats
                }
            
            except Exception as e:
                self.logger.error(f"  Error matching {statement_name}: {e}")
                continue
        
        self.logger.info(f"\n[OK] Matching Complete")
        
        return matching_results
    
    def step4_generate_reports(self, matching_results: Dict) -> List[Path]:
        """Step 4: Generate Excel reports."""
        self.logger.info("\n" + "=" * 80)
        self.logger.info("STEP 4: REPORT GENERATION")
        self.logger.info("=" * 80)
        
        generated_reports = []
        
        # Generate statement reports
        for statement_name, results in matching_results.items():
            report_filename = f"{statement_name}_Credit_Card_Statement_records.xlsx"
            report_path = self.settings.statements_dir / report_filename
            
            self.logger.info(f"\nGenerating {statement_name} report...")
            
            try:
                self.report_generator.generate_statement_report(
                    results['transactions'],
                    results['matches'],
                    report_path,
                    statement_name
                )
                
                self.logger.info(f"  ✓ Report saved: {report_path}")
                generated_reports.append(report_path)
            
            except Exception as e:
                self.logger.error(f"  Error generating {statement_name} report: {e}")
                continue
        
        # Generate Other Financial Records report
        self.logger.info("\nGenerating Other Financial Records report...")
        
        try:
            unmatched_receipts = self.cache_manager.get_unmatched_receipts()
            
            if unmatched_receipts:
                other_report_path = self.settings.output_dir / "Other_Financial_records.xlsx"
                
                # Convert Receipt objects to dictionaries
                unmatched_dicts = []
                for receipt in unmatched_receipts:
                    unmatched_dicts.append({
                        'sender_name': receipt.sender_name,
                        'sender_email': receipt.sender_email,
                        'subject': receipt.subject,
                        'date': receipt.received_date,
                        'amount': receipt.amount,
                        'attachment_path': receipt.attachment_path,
                        'email_link': receipt.email_link,
                        'receiver_email': receipt.receiver_email
                    })
                
                self.report_generator.generate_other_financial_records(
                    unmatched_dicts,
                    other_report_path
                )
                
                self.logger.info(f"  ✓ Report saved: {other_report_path}")
                self.logger.info(f"  Unmatched receipts: {len(unmatched_receipts)}")
                generated_reports.append(other_report_path)
            else:
                self.logger.info("  No unmatched receipts found")
        
        except Exception as e:
            self.logger.error(f"  Error generating Other Financial Records: {e}")
        
        self.logger.info(f"\n[OK] Report Generation Complete")
        self.logger.info(f"  Total reports: {len(generated_reports)}")
        
        return generated_reports
    
    def step5_upload_to_drive(self, report_paths: List[Path]) -> int:
        """Step 5: Upload reports to Google Drive."""
        self.logger.info("\n" + "=" * 80)
        self.logger.info("STEP 5: GOOGLE DRIVE UPLOAD")
        self.logger.info("=" * 80)
        
        uploaded = 0
        
        for report_path in report_paths:
            self.logger.info(f"\nUploading {report_path.name}...")
            
            try:
                # Determine statement type from filename
                if 'Meriwest' in report_path.name:
                    success = self.drive_sync.upload_statement_report(report_path, 'meriwest')
                elif 'Amex' in report_path.name:
                    success = self.drive_sync.upload_statement_report(report_path, 'amex')
                elif 'Chase' in report_path.name:
                    success = self.drive_sync.upload_statement_report(report_path, 'chase')
                elif 'Other_Financial' in report_path.name:
                    success = self.drive_sync.upload_other_financial_records(report_path)
                else:
                    self.logger.warning(f"  Unknown report type: {report_path.name}")
                    continue
                
                if success:
                    self.logger.info(f"  ✓ Uploaded successfully")
                    uploaded += 1
                else:
                    self.logger.warning(f"  ✗ Upload failed")
            
            except Exception as e:
                self.logger.error(f"  Error uploading: {e}")
                continue
        
        self.logger.info(f"\n[OK] Drive Upload Complete")
        self.logger.info(f"  Successfully uploaded: {uploaded}/{len(report_paths)}")
        
        return uploaded
    
    def run_complete_pipeline(self):
        """Run the complete post-email processing pipeline."""
        self.logger.info("\n" + "=" * 80)
        self.logger.info("POST-EMAIL PROCESSING PIPELINE")
        self.logger.info("Complete workflow after email fetching")
        self.logger.info("=" * 80)
        
        overall_start = time.time()
        
        try:
            # Step 1: OCR Processing
            receipts_created = self.step1_ocr_processing()
            
            # Step 2: Parse Statements
            all_transactions = self.step2_parse_statements()
            
            if not all_transactions:
                self.logger.error("No statements parsed. Cannot continue.")
                return
            
            # Step 3: Match Transactions
            matching_results = self.step3_match_transactions(all_transactions)
            
            # Step 4: Generate Reports
            report_paths = self.step4_generate_reports(matching_results)
            
            # Step 5: Upload to Drive
            uploaded = self.step5_upload_to_drive(report_paths)
            
            # Final Summary
            overall_duration = time.time() - overall_start
            
            self.logger.info("\n" + "=" * 80)
            self.logger.info("PIPELINE COMPLETE - SUMMARY")
            self.logger.info("=" * 80)
            self.logger.info(f"✓ Receipts created: {receipts_created}")
            self.logger.info(f"✓ Statements parsed: {len(all_transactions)}")
            self.logger.info(f"✓ Reports generated: {len(report_paths)}")
            self.logger.info(f"✓ Reports uploaded: {uploaded}")
            self.logger.info(f"✓ Total duration: {overall_duration:.2f}s")
            
            # Show database statistics
            stats = self.cache_manager.get_statistics()
            self.logger.info("\nDatabase Statistics:")
            self.logger.info(f"  Processed emails: {stats['processed_emails']}")
            self.logger.info(f"  Total receipts: {stats['receipts']}")
            self.logger.info(f"  Total transactions: {stats['transactions']}")
            self.logger.info(f"  Total matches: {stats['matches']}")
            self.logger.info(f"  Unmatched transactions: {stats['unmatched_transactions']}")
            self.logger.info(f"  Unmatched receipts: {stats['unmatched_receipts']}")
            self.logger.info("=" * 80)
        
        except Exception as e:
            self.logger.error(f"Pipeline error: {e}", exc_info=True)
            raise
    
    def _fetch_emails_with_attachments(self) -> List[Dict]:
        """Fetch emails with attachments from database."""
        import psycopg2
        from psycopg2.extras import RealDictCursor
        
        emails_with_attachments = []
        
        try:
            with psycopg2.connect(self.cache_manager.db_url) as conn:
                cursor = conn.cursor(cursor_factory=RealDictCursor)
                
                cursor.execute("""
                    SELECT message_id, subject, sender, date, account_email, folder
                    FROM processed_emails 
                    WHERE has_attachment = TRUE
                    ORDER BY date DESC
                """)
                
                rows = cursor.fetchall()
                
                for row in rows:
                    email_data = dict(row)
                    
                    # Find attachments in temp directory
                    attachment_dir = self.settings.temp_attachments_dir / email_data['message_id'].replace('<', '').replace('>', '').replace('/', '_')
                    
                    if attachment_dir.exists():
                        attachments = []
                        for file_path in attachment_dir.glob('*'):
                            if file_path.is_file():
                                ext = file_path.suffix.lower()
                                if ext in ['.jpg', '.jpeg', '.png', '.gif', '.bmp']:
                                    content_type = 'image/jpeg'
                                elif ext == '.pdf':
                                    content_type = 'application/pdf'
                                else:
                                    content_type = 'application/octet-stream'
                                
                                attachments.append({
                                    'filename': file_path.name,
                                    'file_path': str(file_path),
                                    'content_type': content_type
                                })
                        
                        if attachments:
                            email_data['attachments'] = attachments
                            emails_with_attachments.append(email_data)
        
        except Exception as e:
            self.logger.error(f"Error fetching emails: {e}")
        
        return emails_with_attachments
    
    def _create_receipt_from_attachment(self, email_data: Dict, attachment: Dict) -> Receipt:
        """Create Receipt object from email and attachment data."""
        extracted_text = attachment.get('extracted_text', '')
        confidence = attachment.get('confidence_score', 0.0)
        amounts = attachment.get('extracted_amounts', [])
        dates = attachment.get('extracted_dates', [])
        
        return Receipt(
            receipt_id=f"{email_data['message_id']}_{attachment['filename']}",
            email_id=email_data['message_id'],
            sender_name=email_data.get('sender', ''),
            sender_email=email_data.get('sender', ''),
            subject=email_data.get('subject', ''),
            received_date=str(email_data.get('date', '')),
            amount=Decimal(str(amounts[0])) if amounts else None,
            transaction_date=dates[0] if dates else None,
            merchant_name=self.ocr_engine.extract_merchant_name(extracted_text),
            attachment_path=attachment['file_path'],
            email_link=f"https://mail.google.com/mail/u/0/#inbox/{email_data['message_id']}",
            receiver_email=email_data.get('account_email', ''),
            source='email_attachment',
            extracted_text=extracted_text[:1000],
            confidence_score=confidence,
            is_financial=self.ocr_engine.is_financial_document(extracted_text)
        )
    
    def _get_all_receipts(self) -> List[Receipt]:
        """Get all receipts from database."""
        import psycopg2
        from psycopg2.extras import RealDictCursor
        
        receipts = []
        
        try:
            with psycopg2.connect(self.cache_manager.db_url) as conn:
                cursor = conn.cursor(cursor_factory=RealDictCursor)
                cursor.execute('SELECT * FROM receipts_cache')
                
                for row in cursor.fetchall():
                    receipts.append(Receipt.from_dict(dict(row)))
        
        except Exception as e:
            self.logger.error(f"Error fetching receipts: {e}")
        
        return receipts


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Post-Email Processing - Complete workflow after email fetching"
    )
    
    args = parser.parse_args()
    
    try:
        logger = get_logger()
        logger.info("Starting post-email processing pipeline...")
        
        # Initialize processor
        processor = PostEmailProcessor()
        
        # Run complete pipeline
        processor.run_complete_pipeline()
        
        return 0
    
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
