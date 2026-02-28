"""
End-to-End Integration Test for FinMatcher v2.0 Enterprise Upgrade.

This module contains integration tests that validate the complete workflow:
- Email filtering with financial filter
- Transaction and receipt creation
- Multi-stage probabilistic matching
- Excel report generation
- Checkpoint and resume capability

Testing Framework: pytest
Feature: finmatcher-v2-upgrade
Task: 19.1 - Write end-to-end integration test
"""

import pytest
import tempfile
import os
import shutil
from pathlib import Path
from datetime import date
from decimal import Decimal
from unittest.mock import Mock

from finmatcher.core.financial_filter import FinancialFilter, FilterMethod
from finmatcher.core.matching_engine import MatchingEngine
from finmatcher.core.deepseek_client import DeepSeekClient
from finmatcher.storage.database_manager import DatabaseManager
from finmatcher.storage.checkpoint_manager import CheckpointManager
from finmatcher.storage.models import (
    Transaction, Receipt, MatchConfidence, AttachmentType
)
from finmatcher.reports.excel_generator import ExcelReportGenerator
from finmatcher.config.configuration_manager import ConfigurationManager


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    temp_path = tempfile.mkdtemp()
    yield temp_path
    shutil.rmtree(temp_path, ignore_errors=True)


@pytest.fixture
def temp_db(temp_dir):
    """Create a temporary database for testing."""
    db_path = os.path.join(temp_dir, 'test_finmatcher.db')
    yield db_path


@pytest.fixture
def test_config(temp_dir, temp_db):
    """Create test configuration."""
    config_path = os.path.join(temp_dir, 'test_config.yaml')
    
    config_content = f"""
matching:
  weights:
    amount: 0.4
    date: 0.3
    semantic: 0.3
  thresholds:
    amount_tolerance: 1.00
    date_variance: 3
    exact_match: 0.98
    high_confidence: 0.85
  algorithm:
    lambda_decay: 2.0

deepseek:
  api_key: test_api_key
  timeout: 30
  max_tokens: 512

database:
  path: "{temp_db}"
  wal_mode: true

checkpoints:
  interval: 1000
"""
    
    with open(config_path, 'w') as f:
        f.write(config_content)
    
    yield config_path


@pytest.fixture
def db_manager(temp_db):
    """Create a DatabaseManager instance with temporary database."""
    manager = DatabaseManager(temp_db, pool_size=5)
    manager.initialize_schema()
    yield manager
    manager.close()


@pytest.fixture
def mock_deepseek_client():
    """Create a mock DeepSeek client."""
    client = Mock(spec=DeepSeekClient)
    client.get_embedding = Mock(return_value=[0.1] * 128)
    client.verify_financial_email = Mock(return_value=True)
    return client


class TestEndToEndIntegration:
    """
    End-to-end integration tests for complete FinMatcher workflow.
    
    Tests the complete pipeline:
    1. Email filtering
    2. Transaction/receipt creation
    3. Multi-stage probabilistic matching
    4. Excel report generation
    5. Checkpoint and resume
    """
    
    def test_complete_workflow_with_exact_matches(self, temp_dir, test_config, 
                                                   db_manager, mock_deepseek_client):
        """
        Test complete workflow: filter → match → report.
        
        Validates:
        - Email filtering accepts financial emails
        - Matching engine finds exact matches
        - Reports are generated correctly
        """
        # Step 1: Create test transactions
        transactions = [
            Transaction(
                id=None,
                statement_file="test_statement",
                transaction_date=date(2024, 1, 15),
                amount=Decimal("99.99"),
                description="Amazon purchase"
            ),
            Transaction(
                id=None,
                statement_file="test_statement",
                transaction_date=date(2024, 1, 16),
                amount=Decimal("45.50"),
                description="Grocery store"
            )
        ]
        
        for txn in transactions:
            txn.id = db_manager.save_transaction(txn)
        
        # Step 2: Create test receipts
        receipts = [
            Receipt(
                id=None,
                source='email',
                receipt_date=date(2024, 1, 15),
                amount=Decimal("99.99"),
                description="Amazon order receipt",
                is_financial=True,
                filter_method=FilterMethod.AUTO_ACCEPT,
                attachments=[]
            ),
            Receipt(
                id=None,
                source='email',
                receipt_date=date(2024, 1, 16),
                amount=Decimal("45.50"),
                description="Grocery payment confirmation",
                is_financial=True,
                filter_method=FilterMethod.AUTO_ACCEPT,
                attachments=[]
            )
        ]
        
        for receipt in receipts:
            receipt.id = db_manager.save_receipt(receipt)
        
        # Step 3: Run matching engine
        config_manager = ConfigurationManager(test_config)
        matching_config = config_manager.load_config().matching_config
        
        matching_engine = MatchingEngine(
            config=matching_config,
            deepseek_client=mock_deepseek_client
        )
        
        all_matches = []
        for transaction in transactions:
            matches = matching_engine.find_matches(transaction, receipts)
            all_matches.extend(matches)
        
        # Verify matches were found
        assert len(all_matches) >= 2, "Should find at least 2 matches"
        
        # Verify match quality
        high_quality_matches = [
            m for m in all_matches 
            if m.confidence in (MatchConfidence.EXACT, MatchConfidence.HIGH)
        ]
        assert len(high_quality_matches) >= 2, "Should have at least 2 high-quality matches"
        
        # Step 4: Generate Excel reports
        output_dir = os.path.join(temp_dir, 'reports')
        os.makedirs(output_dir, exist_ok=True)
        
        excel_generator = ExcelReportGenerator(output_dir=output_dir)
        
        if high_quality_matches:
            report_path = excel_generator.generate_matched_report(
                high_quality_matches,
                "test_statement"
            )
            
            # Verify report was created
            assert os.path.exists(report_path), "Matched report should be created"
            assert report_path.endswith('.xlsx'), "Report should be Excel file"
            
            # Verify report contains data
            import openpyxl
            wb = openpyxl.load_workbook(report_path)
            ws = wb.active
            assert ws.max_row >= 3, "Report should have header + data rows"
    
    def test_workflow_with_financial_filtering(self, mock_deepseek_client):
        """
        Test financial email filtering.
        
        Validates:
        - Financial emails are accepted
        - Non-financial emails are rejected
        """
        financial_filter = FinancialFilter(deepseek_client=mock_deepseek_client)
        
        test_emails = [
            {'subject': 'Your invoice #12345', 'sender': 'billing@company.com', 'body': 'Invoice'},
            {'subject': 'Unsubscribe', 'sender': 'marketing@spam.com', 'body': 'Click here'},
            {'subject': 'Payment confirmation', 'sender': 'receipts@store.com', 'body': 'Payment'}
        ]
        
        filtered_emails = []
        for email_data in test_emails:
            result = financial_filter.filter_email(email_data)
            if result:
                filtered_emails.append(result)
        
        assert len(filtered_emails) == 2, "Should accept 2 financial emails"
        
        for email in filtered_emails:
            assert email.get('is_financial') == True
            assert email.get('filter_method') in [
                FilterMethod.AUTO_ACCEPT.value,
                FilterMethod.AI_VERIFIED.value
            ]
    
    def test_workflow_with_checkpoint_resume(self, temp_dir, test_config, db_manager, 
                                            mock_deepseek_client):
        """
        Test checkpoint and resume capability.
        
        Validates:
        - Checkpoints are saved during processing
        - Processing can resume from checkpoint
        - Checkpoint is deleted on completion
        """
        # Create transactions
        transactions = []
        for i in range(1, 26):
            txn = Transaction(
                id=None,
                statement_file="test_statement",
                transaction_date=date(2024, 1, 15),
                amount=Decimal(f"{i}.00"),
                description=f"Transaction {i}"
            )
            txn.id = db_manager.save_transaction(txn)
            transactions.append(txn)
        
        # Create receipts
        receipts = []
        for i in range(1, 26):
            receipt = Receipt(
                id=None,
                source='email',
                receipt_date=date(2024, 1, 15),
                amount=Decimal(f"{i}.00"),
                description=f"Receipt {i}",
                is_financial=True,
                filter_method=FilterMethod.AUTO_ACCEPT,
                attachments=[]
            )
            receipt.id = db_manager.save_receipt(receipt)
            receipts.append(receipt)
        
        # Initialize checkpoint manager
        checkpoint_manager = CheckpointManager(db_manager, checkpoint_interval=10)
        
        # Simulate processing with checkpoints
        config_manager = ConfigurationManager(test_config)
        matching_config = config_manager.load_config().matching_config
        
        matching_engine = MatchingEngine(
            config=matching_config,
            deepseek_client=mock_deepseek_client
        )
        
        records_processed = 0
        
        # Process first 15 transactions
        for transaction in transactions[:15]:
            matches = matching_engine.find_matches(transaction, receipts)
            records_processed += 1
            
            if checkpoint_manager.should_checkpoint(records_processed):
                checkpoint_manager.save_checkpoint(
                    transaction.id,
                    receipts[-1].id if receipts else 0
                )
        
        # Verify checkpoint was saved
        checkpoint = checkpoint_manager.load_checkpoint()
        assert checkpoint is not None, "Checkpoint should exist"
        assert checkpoint.last_transaction_id > 0
        
        # Simulate resume
        new_checkpoint_manager = CheckpointManager(db_manager, checkpoint_interval=10)
        resume_checkpoint = new_checkpoint_manager.load_checkpoint()
        assert resume_checkpoint is not None, "Should load checkpoint after restart"
        
        # Delete checkpoint
        new_checkpoint_manager.delete_checkpoint()
        final_checkpoint = new_checkpoint_manager.load_checkpoint()
        assert final_checkpoint is None, "Checkpoint should be deleted"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
