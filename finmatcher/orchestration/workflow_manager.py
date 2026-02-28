"""
Main workflow orchestration for FinMatcher v2.0 Enterprise Upgrade.

This module coordinates all components:
- Email fetching with financial filtering
- Statement parsing
- Multi-stage probabilistic matching
- Excel report generation
- Google Drive upload
- Checkpoint/resume capability

Validates Requirements: 8.3, 8.4, 8.5, 10.4
"""

import logging
from typing import Optional, List, Tuple
from datetime import datetime, date
from pathlib import Path
import traceback

from finmatcher.core.email_fetcher import EmailFetcher
from finmatcher.core.financial_filter import FinancialFilter
from finmatcher.core.matching_engine import MatchingEngine
from finmatcher.core.deepseek_client import DeepSeekClient
from finmatcher.storage.database_manager import DatabaseManager
from finmatcher.storage.checkpoint_manager import CheckpointManager
from finmatcher.storage.models import Transaction, Receipt, MatchResult, MatchConfidence, Attachment, AttachmentType
from finmatcher.reports.excel_generator import ExcelReportGenerator
from finmatcher.reports.drive_manager import DriveManager
from finmatcher.config.configuration_manager import ConfigurationManager
from finmatcher.utils.performance_monitor import PerformanceMonitor
from finmatcher.orchestration.parallelism_orchestrator import ParallelismOrchestrator

logger = logging.getLogger(__name__)


class WorkflowManager:
    """
    Main workflow orchestrator for FinMatcher v2.0.
    
    Coordinates:
    - Email fetching and filtering
    - Transaction parsing
    - Probabilistic matching
    - Report generation
    - Drive upload
    - Checkpoint/resume
    
    Validates Requirements: 8.3, 8.4, 8.5, 10.4
    """
    
    def __init__(self, config_path: str, credentials_path: str):
        """
        Initialize workflow manager with all components.
        
        Args:
            config_path: Path to configuration file
            credentials_path: Path to Google Drive credentials
            
        Validates Requirement: 8.3 - Check for existing checkpoint on startup
        """
        logger.info("Initializing FinMatcher v2.0 Workflow Manager...")
        
        # Load configuration
        self.config_manager = ConfigurationManager(config_path)
        self.config = self.config_manager.load_config()
        
        # Initialize database
        self.db_manager = DatabaseManager(self.config.database_path)
        self.db_manager.initialize_schema()
        
        # Initialize checkpoint manager
        self.checkpoint_manager = CheckpointManager(self.db_manager)
        
        # Check for existing checkpoint (Requirement 8.3)
        self.checkpoint = self.checkpoint_manager.load_checkpoint()
        if self.checkpoint:
            logger.info(
                f"Found checkpoint: last_transaction_id={self.checkpoint.last_transaction_id}, "
                f"last_receipt_id={self.checkpoint.last_receipt_id}, "
                f"timestamp={self.checkpoint.timestamp}"
            )
        else:
            logger.info("No checkpoint found, starting fresh processing")
        
        # Initialize DeepSeek client
        self.deepseek_client = DeepSeekClient(
            api_key=self.config.deepseek_api_key,
            timeout=self.config.deepseek_timeout
        )
        
        # Initialize matching engine
        self.matching_engine = MatchingEngine(
            config=self.config.matching_config,
            deepseek_client=self.deepseek_client
        )
        
        # Initialize email fetcher with financial filter
        self.email_fetcher = EmailFetcher(
            thread_pool_size=self.config.thread_pool_size,
            deepseek_client=self.deepseek_client
        )
        
        # Initialize report generator
        self.excel_generator = ExcelReportGenerator(
            output_dir=self.config.output_dir
        )
        
        # Initialize Drive manager
        self.drive_manager = DriveManager(
            credentials_path=credentials_path,
            root_folder_name=self.config.drive_root_folder
        )
        self.drive_manager.initialize_folder_structure()
        
        # Initialize performance monitor
        self.performance_monitor = PerformanceMonitor(
            warning_threshold=self.config.memory_warning_threshold,
            pause_threshold=self.config.memory_pause_threshold
        )
        
        # Initialize parallelism orchestrator
        self.parallelism_orchestrator = ParallelismOrchestrator(
            thread_count=self.config.thread_pool_size,
            process_count=self.config.process_pool_size
        )
        
        logger.info("Workflow manager initialized successfully")
    
    def run_full_workflow(self, statement_files: List[str], 
                         date_range: Optional[Tuple[datetime, datetime]] = None):
        """
        Run complete workflow: fetch, filter, match, report, upload.
        
        Args:
            statement_files: List of paths to statement files
            date_range: Optional date range for email fetching
            
        Validates Requirements:
        - 8.4: Resume processing from last saved record identifier
        - 8.5: Begin processing from first record if no checkpoint
        - 10.4: Log errors with stack traces and affected record IDs
        """
        logger.info("=" * 80)
        logger.info("STARTING FINMATCHER V2.0 WORKFLOW")
        logger.info("=" * 80)
        
        try:
            # Step 1: Fetch and filter emails
            logger.info("Step 1: Fetching and filtering emails...")
            emails = self.email_fetcher.fetch_all_emails(date_range=date_range)
            logger.info(f"Fetched {len(emails)} financial emails")
            
            # Step 2: Parse statement files
            logger.info("Step 2: Parsing statement files...")
            transactions = self._parse_statements(statement_files)
            logger.info(f"Parsed {len(transactions)} transactions")
            
            # Step 3: Convert emails to receipts
            logger.info("Step 3: Converting emails to receipts...")
            receipts = self._convert_emails_to_receipts(emails)
            logger.info(f"Converted {len(receipts)} receipts")
            
            # Step 4: Run matching with checkpoint support
            logger.info("Step 4: Running probabilistic matching...")
            matches = self._run_matching_with_checkpoints(transactions, receipts)
            logger.info(f"Found {len(matches)} matches")
            
            # Step 5: Generate reports
            logger.info("Step 5: Generating Excel reports...")
            self._generate_and_upload_reports(matches, transactions, receipts, statement_files)
            
            # Step 6: Upload attachments
            logger.info("Step 6: Uploading attachments...")
            self._upload_attachments(matches, receipts)
            
            # Step 7: Delete checkpoint on successful completion
            logger.info("Step 7: Cleaning up...")
            self.checkpoint_manager.delete_checkpoint()
            logger.info("Checkpoint deleted (workflow completed successfully)")
            
            # Log performance summary
            self.performance_monitor.log_performance_summary(
                emails_processed=len(emails),
                matches_found=len(matches)
            )
            
            logger.info("=" * 80)
            logger.info("WORKFLOW COMPLETED SUCCESSFULLY")
            logger.info("=" * 80)
            
        except Exception as e:
            # Log error with full context (Requirement 10.4)
            logger.error("=" * 80)
            logger.error("WORKFLOW FAILED")
            logger.error("=" * 80)
            logger.error(f"Error: {str(e)}")
            logger.error(f"Stack trace:\n{traceback.format_exc()}")
            logger.error("=" * 80)
            raise
        
        finally:
            # Shutdown parallelism orchestrator
            self.parallelism_orchestrator.shutdown(wait=True)
    
    def _parse_statements(self, statement_files: List[str]) -> List[Transaction]:
        """
        Parse statement files to extract transactions.
        
        Args:
            statement_files: List of paths to statement files
            
        Returns:
            List of Transaction objects
        """
        transactions = []
        
        for file_path in statement_files:
            try:
                # TODO: Implement statement parser
                # For now, return empty list
                logger.warning(f"Statement parsing not yet implemented for {file_path}")
            except Exception as e:
                logger.error(
                    f"Error parsing statement {file_path}: {e}",
                    extra={
                        'file_path': file_path,
                        'error_type': type(e).__name__,
                        'stack_trace': traceback.format_exc()
                    }
                )
        
        return transactions
    
    def _convert_emails_to_receipts(self, emails: List[dict]) -> List[Receipt]:
        """
        Convert email dictionaries to Receipt objects.
        
        Args:
            emails: List of email dictionaries
            
        Returns:
            List of Receipt objects
        """
        receipts = []
        
        for email_data in emails:
            try:
                # Extract attachments
                attachments = []
                for att_data in email_data.get('attachments', []):
                    attachment = Attachment(
                        id=None,
                        receipt_id=0,  # Will be set after receipt is saved
                        filename=att_data['filename'],
                        file_type=self._classify_attachment_type(att_data['filename']),
                        drive_file_id=None,
                        local_path=att_data['file_path']
                    )
                    attachments.append(attachment)
                
                # Create receipt
                receipt = Receipt(
                    id=None,
                    source='email',
                    receipt_date=email_data['received_date'].date(),
                    amount=None,  # TODO: Extract amount from email body
                    description=email_data['subject'],
                    is_financial=email_data.get('is_financial', True),
                    filter_method=email_data.get('filter_method'),
                    attachments=attachments
                )
                
                receipts.append(receipt)
                
            except Exception as e:
                logger.error(
                    f"Error converting email to receipt: {e}",
                    extra={
                        'email_id': email_data.get('email_id'),
                        'subject': email_data.get('subject'),
                        'error_type': type(e).__name__,
                        'stack_trace': traceback.format_exc()
                    }
                )
        
        return receipts
    
    def _classify_attachment_type(self, filename: str) -> AttachmentType:
        """Classify attachment type based on extension."""
        ext = Path(filename).suffix.lower()
        
        if ext in {'.pdf', '.doc', '.docx'}:
            return AttachmentType.DOCUMENT
        elif ext in {'.jpg', '.jpeg', '.png', '.gif'}:
            return AttachmentType.IMAGE
        else:
            return AttachmentType.DOCUMENT  # Default
    
    def _run_matching_with_checkpoints(self, transactions: List[Transaction], 
                                      receipts: List[Receipt]) -> List[MatchResult]:
        """
        Run matching with checkpoint support.
        
        Args:
            transactions: List of Transaction objects
            receipts: List of Receipt objects
            
        Returns:
            List of MatchResult objects
            
        Validates Requirements:
        - 8.1: Save checkpoint after processing every 1000 records
        - 8.4: Resume from last checkpoint
        """
        matches = []
        records_processed = 0
        
        # Determine starting point based on checkpoint
        start_idx = 0
        if self.checkpoint:
            # Find index of last processed transaction
            for i, txn in enumerate(transactions):
                if txn.id == self.checkpoint.last_transaction_id:
                    start_idx = i + 1
                    break
            logger.info(f"Resuming from transaction index {start_idx}")
        
        # Process transactions with memory monitoring
        for i, transaction in enumerate(transactions[start_idx:], start=start_idx):
            try:
                # Check memory before processing
                can_continue = self.performance_monitor.check_memory_and_manage()
                if not can_continue:
                    logger.warning("Memory critical, pausing briefly...")
                    import time
                    time.sleep(5)
                
                # Find matches for this transaction
                transaction_matches = self.matching_engine.find_matches(
                    transaction, receipts
                )
                matches.extend(transaction_matches)
                
                records_processed += 1
                
                # Save checkpoint every 1000 records (Requirement 8.1)
                if self.checkpoint_manager.should_checkpoint(records_processed):
                    last_receipt_id = receipts[-1].id if receipts else 0
                    self.checkpoint_manager.save_checkpoint(
                        transaction.id, last_receipt_id
                    )
                    logger.info(f"Checkpoint saved at {records_processed} records")
                
            except Exception as e:
                logger.error(
                    f"Error matching transaction: {e}",
                    extra={
                        'transaction_id': transaction.id,
                        'transaction_date': transaction.transaction_date,
                        'transaction_amount': transaction.amount,
                        'error_type': type(e).__name__,
                        'stack_trace': traceback.format_exc()
                    }
                )
        
        return matches
    
    def _generate_and_upload_reports(self, matches: List[MatchResult],
                                    transactions: List[Transaction],
                                    receipts: List[Receipt],
                                    statement_files: List[str]):
        """
        Generate Excel reports and upload to Drive.
        
        Args:
            matches: List of MatchResult objects
            transactions: List of Transaction objects
            receipts: List of Receipt objects
            statement_files: List of statement file paths
        """
        # Separate matches by confidence
        high_confidence_matches = [
            m for m in matches 
            if m.confidence in (MatchConfidence.EXACT, MatchConfidence.HIGH)
        ]
        low_confidence_receipts = [
            m.receipt for m in matches 
            if m.confidence == MatchConfidence.LOW
        ]
        
        # Separate low confidence by financial status
        financial_receipts = [r for r in low_confidence_receipts if r.is_financial]
        nonfinancial_receipts = [r for r in low_confidence_receipts if not r.is_financial]
        
        # Generate matched report for each statement
        for statement_file in statement_files:
            statement_name = Path(statement_file).stem
            statement_matches = [
                m for m in high_confidence_matches
                if m.transaction.statement_file == statement_name
            ]
            
            if statement_matches:
                report_path = self.excel_generator.generate_matched_report(
                    statement_matches, statement_name
                )
                
                # Upload to Drive
                folder_id = self.drive_manager.get_or_create_statement_folder(statement_name)
                self.drive_manager.upload_excel_report(report_path, folder_id)
                logger.info(f"Uploaded matched report for {statement_name}")
        
        # Generate unmatched financial report
        if financial_receipts:
            report_path = self.excel_generator.generate_unmatched_financial_report(
                financial_receipts
            )
            self.drive_manager.upload_excel_report(
                report_path,
                self.drive_manager.folder_structure.other_receipts_id
            )
            logger.info("Uploaded unmatched financial report")
        
        # Generate non-financial report
        if nonfinancial_receipts:
            report_path = self.excel_generator.generate_unmatched_nonfinancial_report(
                nonfinancial_receipts
            )
            self.drive_manager.upload_excel_report(
                report_path,
                self.drive_manager.folder_structure.unmatch_email_id
            )
            logger.info("Uploaded non-financial report")
    
    def _upload_attachments(self, matches: List[MatchResult], receipts: List[Receipt]):
        """
        Upload attachments to appropriate Drive folders based on match confidence.
        
        Args:
            matches: List of MatchResult objects
            receipts: List of Receipt objects
        """
        for match in matches:
            for attachment in match.receipt.attachments:
                try:
                    # Route attachment based on confidence
                    file_id = self.drive_manager.route_attachment(
                        attachment.local_path,
                        match.confidence,
                        source_prefix="email"
                    )
                    
                    # Update attachment with Drive file ID
                    attachment.drive_file_id = file_id
                    
                except Exception as e:
                    logger.error(
                        f"Error uploading attachment: {e}",
                        extra={
                            'filename': attachment.filename,
                            'receipt_id': match.receipt.id,
                            'confidence': match.confidence.value,
                            'error_type': type(e).__name__,
                            'stack_trace': traceback.format_exc()
                        }
                    )
