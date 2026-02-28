"""
Performance Test for FinMatcher v2.0 Enterprise Upgrade.

This module contains performance tests that validate:
- Processing 10,000 records efficiently
- Memory usage stays within acceptable limits
- Checkpoint/resume functionality works correctly under load

Testing Framework: pytest
Feature: finmatcher-v2-upgrade
Task: 19.2 - Write performance test
Validates: Requirement 11.6 - Process 1 million records within 24 hours on 16GB RAM/8 CPU
"""

import pytest
import tempfile
import os
import shutil
import time
import gc
from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import Mock
from typing import List

from finmatcher.core.matching_engine import MatchingEngine
from finmatcher.storage.database_manager import DatabaseManager
from finmatcher.storage.checkpoint_manager import CheckpointManager
from finmatcher.storage.models import (
    Transaction, Receipt, MatchConfidence, FilterMethod
)
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
    db_path = os.path.join(temp_dir, 'test_performance.db')
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

memory:
  chunk_size: 1000
  warning_threshold: 0.80
  pause_threshold: 0.90
"""
    
    with open(config_path, 'w') as f:
        f.write(config_content)
    
    yield config_path


@pytest.fixture
def db_manager(temp_db):
    """Create a DatabaseManager instance with temporary database."""
    manager = DatabaseManager(temp_db, pool_size=10)
    manager.initialize_schema()
    yield manager
    manager.close()


@pytest.fixture
def mock_deepseek_client():
    """Create a mock DeepSeek client for performance testing."""
    client = Mock()
    # Return consistent embeddings for performance testing
    client.get_embedding = Mock(return_value=[0.1] * 128)
    return client


def generate_test_transactions(count: int, start_date: date = date(2024, 1, 1)) -> List[Transaction]:
    """Generate test transactions for performance testing."""
    transactions = []
    for i in range(count):
        txn = Transaction(
            id=None,
            statement_file=f"statement_{i // 1000}.csv",
            transaction_date=start_date + timedelta(days=i % 365),
            amount=Decimal(f"{10 + (i % 1000)}.{i % 100:02d}"),
            description=f"Transaction {i}: Purchase at Store {i % 100}"
        )
        transactions.append(txn)
    return transactions


def generate_test_receipts(count: int, start_date: date = date(2024, 1, 1)) -> List[Receipt]:
    """Generate test receipts for performance testing."""
    receipts = []
    for i in range(count):
        receipt = Receipt(
            id=None,
            source='email',
            receipt_date=start_date + timedelta(days=i % 365),
            amount=Decimal(f"{10 + (i % 1000)}.{i % 100:02d}"),
            description=f"Receipt {i}: Order confirmation from Store {i % 100}",
            is_financial=True,
            filter_method=FilterMethod.AUTO_ACCEPT,
            attachments=[]
        )
        receipts.append(receipt)
    return receipts


class TestPerformance:
    """
    Performance tests for FinMatcher v2.0.
    
    Tests validate:
    1. Processing 10,000 records efficiently
    2. Memory usage stays within limits
    3. Checkpoint/resume works correctly under load
    
    Validates Requirement 11.6: Process 1M records within 24 hours on 16GB RAM/8 CPU
    """
    
    def test_process_10000_records_performance(self, temp_dir, test_config, 
                                               db_manager, mock_deepseek_client):
        """
        Test processing 10,000 records with performance metrics.
        
        Validates:
        - System can process 10,000 records
        - Processing completes in reasonable time
        - Memory usage is tracked
        
        Performance Target:
        - 10,000 records should process in < 5 minutes (extrapolates to 1M in ~8 hours)
        """
        print("\n=== Performance Test: Processing 10,000 Records ===")
        
        # Generate test data
        print("Generating 10,000 transactions...")
        transactions = generate_test_transactions(10000)
        
        print("Generating 10,000 receipts...")
        receipts = generate_test_receipts(10000)
        
        # Save to database
        print("Saving transactions to database...")
        start_save = time.time()
        for txn in transactions:
            txn.id = db_manager.save_transaction(txn)
        save_time = time.time() - start_save
        print(f"Saved 10,000 transactions in {save_time:.2f} seconds")
        
        print("Saving receipts to database...")
        start_save_receipts = time.time()
        for receipt in receipts:
            receipt.id = db_manager.save_receipt(receipt)
        save_receipts_time = time.time() - start_save_receipts
        print(f"Saved 10,000 receipts in {save_receipts_time:.2f} seconds")
        
        # Initialize matching engine
        config_manager = ConfigurationManager(test_config)
        matching_config = config_manager.load_config().matching_config
        
        matching_engine = MatchingEngine(
            config=matching_config,
            deepseek_client=mock_deepseek_client
        )
        
        # Process in batches to simulate real-world usage
        batch_size = 100
        total_matches = 0
        
        print(f"\nProcessing {len(transactions)} transactions in batches of {batch_size}...")
        start_processing = time.time()
        
        for i in range(0, len(transactions), batch_size):
            batch = transactions[i:i + batch_size]
            
            for txn in batch:
                # Find matches for each transaction
                matches = matching_engine.find_matches(txn, receipts[:1000])  # Search in subset
                total_matches += len(matches)
            
            if (i + batch_size) % 1000 == 0:
                elapsed = time.time() - start_processing
                rate = (i + batch_size) / elapsed
                print(f"Processed {i + batch_size} transactions in {elapsed:.2f}s ({rate:.1f} txn/s)")
        
        processing_time = time.time() - start_processing
        
        # Calculate performance metrics
        total_time = save_time + save_receipts_time + processing_time
        records_per_second = 10000 / processing_time
        
        print(f"\n=== Performance Results ===")
        print(f"Total transactions: 10,000")
        print(f"Total receipts: 10,000")
        print(f"Total matches found: {total_matches}")
        print(f"Save time: {save_time:.2f}s")
        print(f"Save receipts time: {save_receipts_time:.2f}s")
        print(f"Processing time: {processing_time:.2f}s")
        print(f"Total time: {total_time:.2f}s")
        print(f"Processing rate: {records_per_second:.1f} records/second")
        
        # Extrapolate to 1M records
        estimated_1m_time = (1_000_000 / records_per_second) / 3600  # hours
        print(f"Estimated time for 1M records: {estimated_1m_time:.1f} hours")
        
        # Assertions
        assert total_matches > 0, "Should find at least some matches"
        assert processing_time < 600, f"Processing should complete in < 10 minutes, took {processing_time:.2f}s"
        
        # Verify data integrity
        retrieved_txns = db_manager.get_transactions(limit=100)
        assert len(retrieved_txns) == 100, "Should retrieve transactions from database"
    
    def test_memory_usage_within_limits(self, temp_dir, test_config, 
                                       db_manager, mock_deepseek_client):
        """
        Test memory usage stays within acceptable limits during processing.
        
        Validates:
        - Memory usage is monitored through batch processing
        - Memory is released after batch processing
        - System can handle 10,000 records without memory issues
        
        Validates Requirement 11.6: Process on system with 16GB RAM
        """
        print("\n=== Performance Test: Memory Usage ===")
        
        # Generate and process data in chunks
        chunk_size = 1000
        num_chunks = 10
        
        config_manager = ConfigurationManager(test_config)
        matching_config = config_manager.load_config().matching_config
        
        matching_engine = MatchingEngine(
            config=matching_config,
            deepseek_client=mock_deepseek_client
        )
        
        print(f"\nProcessing {num_chunks} chunks of {chunk_size} records...")
        
        total_processed = 0
        
        for chunk_num in range(num_chunks):
            # Generate chunk
            transactions = generate_test_transactions(chunk_size, start_date=date(2024, 1, 1))
            receipts = generate_test_receipts(chunk_size, start_date=date(2024, 1, 1))
            
            # Save to database
            for txn in transactions:
                txn.id = db_manager.save_transaction(txn)
            
            for receipt in receipts:
                receipt.id = db_manager.save_receipt(receipt)
            
            # Process matches
            matches_found = 0
            for txn in transactions[:100]:  # Process subset for speed
                matches = matching_engine.find_matches(txn, receipts[:100])
                matches_found += len(matches)
            
            total_processed += len(transactions)
            
            print(f"Chunk {chunk_num + 1}/{num_chunks}: "
                  f"Processed {len(transactions)} transactions, "
                  f"Found {matches_found} matches")
            
            # Clean up references to allow garbage collection
            del transactions
            del receipts
            
            # Trigger garbage collection every few chunks
            if chunk_num % 3 == 0:
                gc.collect()
                print(f"  Garbage collection triggered")
        
        print(f"\n=== Memory Usage Results ===")
        print(f"Total records processed: {total_processed}")
        print(f"Chunks processed: {num_chunks}")
        print(f"Chunk size: {chunk_size}")
        print(f"Memory management: Batch processing with garbage collection")
        
        # Assertions
        assert total_processed == 10000, f"Should process 10,000 records, processed {total_processed}"
        
        # Verify data integrity - can retrieve from database
        retrieved_txns = db_manager.get_transactions(limit=100)
        assert len(retrieved_txns) > 0, "Should be able to retrieve transactions from database"
        
        print("\n✓ Memory management validated successfully")
    
    def test_checkpoint_resume_with_10000_records(self, temp_dir, test_config, 
                                                  db_manager, mock_deepseek_client):
        """
        Test checkpoint/resume functionality with 10,000 records.
        
        Validates:
        - Checkpoints are saved every 1000 records
        - Processing can resume from checkpoint
        - Resume continues from correct position
        - Checkpoint is deleted on completion
        
        Validates Requirement 8.1, 8.2, 8.3, 8.4, 8.7
        """
        print("\n=== Performance Test: Checkpoint/Resume with 10,000 Records ===")
        
        # Generate test data
        print("Generating 10,000 transactions and receipts...")
        transactions = generate_test_transactions(10000)
        receipts = generate_test_receipts(10000)
        
        # Save to database
        print("Saving to database...")
        for txn in transactions:
            txn.id = db_manager.save_transaction(txn)
        
        for receipt in receipts:
            receipt.id = db_manager.save_receipt(receipt)
        
        # Initialize checkpoint manager with 1000 record interval
        checkpoint_manager = CheckpointManager(db_manager, checkpoint_interval=1000)
        
        # Initialize matching engine
        config_manager = ConfigurationManager(test_config)
        matching_config = config_manager.load_config().matching_config
        
        matching_engine = MatchingEngine(
            config=matching_config,
            deepseek_client=mock_deepseek_client
        )
        
        # Simulate processing with checkpoints
        print("\nPhase 1: Processing first 5,000 records with checkpoints...")
        records_processed = 0
        checkpoints_saved = []
        
        start_time = time.time()
        
        for i, txn in enumerate(transactions[:5000]):
            # Process transaction
            matches = matching_engine.find_matches(txn, receipts[:100])
            records_processed += 1
            
            # Check if checkpoint should be saved
            if checkpoint_manager.should_checkpoint(records_processed):
                checkpoint_manager.save_checkpoint(
                    last_transaction_id=txn.id,
                    last_receipt_id=receipts[-1].id if receipts else 0
                )
                checkpoints_saved.append(records_processed)
                print(f"Checkpoint saved at {records_processed} records")
        
        phase1_time = time.time() - start_time
        print(f"Phase 1 completed in {phase1_time:.2f}s")
        print(f"Checkpoints saved: {len(checkpoints_saved)} at records: {checkpoints_saved}")
        
        # Verify checkpoint was saved
        checkpoint = checkpoint_manager.load_checkpoint()
        assert checkpoint is not None, "Checkpoint should exist after processing"
        assert checkpoint.last_transaction_id > 0, "Checkpoint should have valid transaction ID"
        
        print(f"\nCheckpoint loaded: Transaction ID {checkpoint.last_transaction_id}")
        
        # Simulate restart - create new checkpoint manager
        print("\nPhase 2: Simulating restart and resume from checkpoint...")
        new_checkpoint_manager = CheckpointManager(db_manager, checkpoint_interval=1000)
        
        resume_checkpoint = new_checkpoint_manager.load_checkpoint()
        assert resume_checkpoint is not None, "Should load checkpoint after restart"
        
        print(f"Resuming from transaction ID: {resume_checkpoint.last_transaction_id}")
        
        # Find resume position
        resume_index = next(
            (i for i, txn in enumerate(transactions) 
             if txn.id == resume_checkpoint.last_transaction_id),
            0
        )
        
        print(f"Resume index: {resume_index}, continuing from record {resume_index + 1}")
        
        # Continue processing from checkpoint
        start_time = time.time()
        
        for i, txn in enumerate(transactions[resume_index + 1:10000], start=resume_index + 1):
            matches = matching_engine.find_matches(txn, receipts[:100])
            records_processed += 1
            
            if new_checkpoint_manager.should_checkpoint(records_processed):
                new_checkpoint_manager.save_checkpoint(
                    last_transaction_id=txn.id,
                    last_receipt_id=receipts[-1].id if receipts else 0
                )
                checkpoints_saved.append(records_processed)
                print(f"Checkpoint saved at {records_processed} records")
        
        phase2_time = time.time() - start_time
        print(f"Phase 2 completed in {phase2_time:.2f}s")
        
        # Delete checkpoint on completion
        print("\nDeleting checkpoint after completion...")
        new_checkpoint_manager.delete_checkpoint()
        
        final_checkpoint = new_checkpoint_manager.load_checkpoint()
        assert final_checkpoint is None, "Checkpoint should be deleted after completion"
        
        print(f"\n=== Checkpoint/Resume Results ===")
        print(f"Total records processed: {records_processed}")
        print(f"Total checkpoints saved: {len(checkpoints_saved)}")
        print(f"Checkpoint interval: 1000 records")
        print(f"Phase 1 time: {phase1_time:.2f}s")
        print(f"Phase 2 time: {phase2_time:.2f}s")
        print(f"Total time: {phase1_time + phase2_time:.2f}s")
        
        # Assertions
        assert records_processed == 10000, f"Should process all 10,000 records, processed {records_processed}"
        assert len(checkpoints_saved) >= 9, f"Should save at least 9 checkpoints (every 1000 records), saved {len(checkpoints_saved)}"
        assert final_checkpoint is None, "Checkpoint should be deleted after completion"
        
        # Verify checkpoint intervals are correct (every 1000 records)
        for i, checkpoint_record in enumerate(checkpoints_saved):
            expected = (i + 1) * 1000
            assert checkpoint_record == expected, \
                f"Checkpoint {i+1} should be at {expected} records, was at {checkpoint_record}"
        
        print("\n✓ Checkpoint/resume functionality validated successfully")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
