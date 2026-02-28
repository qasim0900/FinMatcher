"""
Unit tests for CheckpointManager resume logic.

This module contains unit tests to verify checkpoint and resume capability:
- Resume from checkpoint
- Fresh start when no checkpoint exists
- Checkpoint deletion on completion

Testing Framework: pytest
Feature: finmatcher-v2-upgrade
Validates: Requirements 8.3, 8.4, 8.5, 8.7
"""

import pytest
import tempfile
import os
from datetime import date, datetime
from decimal import Decimal

from finmatcher.storage.database_manager import DatabaseManager
from finmatcher.storage.checkpoint_manager import CheckpointManager
from finmatcher.storage.models import Transaction, Receipt, FilterMethod


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    fd, path = tempfile.mkstemp(suffix='.db')
    os.close(fd)
    yield path
    # Cleanup
    if os.path.exists(path):
        os.unlink(path)


@pytest.fixture
def db_manager(temp_db):
    """Create a DatabaseManager instance with temporary database."""
    manager = DatabaseManager(temp_db, pool_size=5)
    manager.initialize_schema()
    yield manager
    manager.close()


@pytest.fixture
def checkpoint_manager(db_manager):
    """Create a CheckpointManager instance."""
    return CheckpointManager(db_manager, checkpoint_interval=1000)


class TestResumeFromCheckpoint:
    """
    Test resume from checkpoint functionality.
    
    Validates: Requirements 8.3, 8.4 - Check for existing checkpoint and resume from last saved state
    """
    
    def test_resume_from_existing_checkpoint(self, db_manager, checkpoint_manager):
        """
        Test that system resumes processing from last checkpoint.
        
        Validates:
        - Requirement 8.3: Check for existing checkpoint data on startup
        - Requirement 8.4: Resume processing from last saved record identifier if checkpoint exists
        """
        # Insert some test data
        for i in range(1, 11):
            txn = Transaction(
                id=None,
                statement_file=f"statement_{i}.csv",
                transaction_date=date(2024, 1, 1),
                amount=Decimal(f"{i * 10}.00"),
                description=f"Transaction {i}"
            )
            db_manager.save_transaction(txn)
            
            receipt = Receipt(
                id=None,
                source="email",
                receipt_date=date(2024, 1, 1),
                amount=Decimal(f"{i * 10}.00"),
                description=f"Receipt {i}",
                is_financial=True,
                filter_method=FilterMethod.AUTO_ACCEPT
            )
            db_manager.save_receipt(receipt)
        
        # Save checkpoint at transaction 5, receipt 5
        checkpoint_manager.save_checkpoint(
            last_transaction_id=5,
            last_receipt_id=5
        )
        
        # Load checkpoint
        checkpoint = checkpoint_manager.load_checkpoint()
        
        # Verify checkpoint was loaded correctly
        assert checkpoint is not None, "Checkpoint should exist"
        assert checkpoint.last_transaction_id == 5, "Should resume from transaction 5"
        assert checkpoint.last_receipt_id == 5, "Should resume from receipt 5"
        assert isinstance(checkpoint.timestamp, date), "Timestamp should be a date object"
        
        # Simulate resuming processing from checkpoint
        remaining_transactions = db_manager.get_transactions(limit=100, offset=checkpoint.last_transaction_id)
        remaining_receipts = db_manager.get_receipts(limit=100, offset=checkpoint.last_receipt_id)
        
        # Verify we get the remaining records (6-10)
        assert len(remaining_transactions) == 5, "Should have 5 remaining transactions"
        assert len(remaining_receipts) == 5, "Should have 5 remaining receipts"
        assert remaining_transactions[0].id == 6, "First remaining transaction should be ID 6"
        assert remaining_receipts[0].id == 6, "First remaining receipt should be ID 6"
    
    def test_checkpoint_contains_timestamp(self, db_manager, checkpoint_manager):
        """
        Test that checkpoint contains timestamp.
        
        Validates: Requirement 8.2 - Checkpoint contains last processed record identifier and timestamp
        """
        # Save checkpoint
        checkpoint_manager.save_checkpoint(
            last_transaction_id=100,
            last_receipt_id=50
        )
        
        # Load checkpoint
        checkpoint = checkpoint_manager.load_checkpoint()
        
        # Verify checkpoint has all required fields
        assert checkpoint is not None, "Checkpoint should exist"
        assert checkpoint.last_transaction_id == 100
        assert checkpoint.last_receipt_id == 50
        assert checkpoint.timestamp is not None, "Checkpoint should have timestamp"
        assert isinstance(checkpoint.timestamp, date), "Timestamp should be a date object"
        
        # Verify timestamp is recent (within last minute)
        now = datetime.now().date()
        assert checkpoint.timestamp == now, "Timestamp should be today's date"
    
    def test_resume_with_multiple_checkpoints(self, db_manager, checkpoint_manager):
        """
        Test that only the latest checkpoint is used when multiple saves occur.
        
        Validates: Requirement 8.4 - Resume from last saved record identifier
        """
        # Save first checkpoint
        checkpoint_manager.save_checkpoint(
            last_transaction_id=10,
            last_receipt_id=10
        )
        
        # Save second checkpoint (should replace first)
        checkpoint_manager.save_checkpoint(
            last_transaction_id=20,
            last_receipt_id=20
        )
        
        # Save third checkpoint (should replace second)
        checkpoint_manager.save_checkpoint(
            last_transaction_id=30,
            last_receipt_id=30
        )
        
        # Load checkpoint
        checkpoint = checkpoint_manager.load_checkpoint()
        
        # Verify only the latest checkpoint is loaded
        assert checkpoint is not None, "Checkpoint should exist"
        assert checkpoint.last_transaction_id == 30, "Should load latest checkpoint (30)"
        assert checkpoint.last_receipt_id == 30, "Should load latest checkpoint (30)"
        
        # Verify only one checkpoint exists in database
        with db_manager.read_pool.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) as count FROM checkpoints")
            result = cursor.fetchone()
            assert result['count'] == 1, "Should have exactly one checkpoint"
    
    def test_resume_after_crash_simulation(self, db_manager, checkpoint_manager):
        """
        Test resume capability after simulated crash.
        
        Validates: Requirement 8.4 - Resume processing from last saved record identifier
        """
        # Simulate processing 2500 records with checkpoints every 1000
        for i in range(1, 2501):
            txn = Transaction(
                id=None,
                statement_file=f"statement_{i}.csv",
                transaction_date=date(2024, 1, 1),
                amount=Decimal(f"{i}.00"),
                description=f"Transaction {i}"
            )
            db_manager.save_transaction(txn)
            
            # Save checkpoint every 1000 records
            if i % 1000 == 0:
                checkpoint_manager.save_checkpoint(
                    last_transaction_id=i,
                    last_receipt_id=i
                )
        
        # Simulate crash - create new checkpoint manager instance
        new_checkpoint_manager = CheckpointManager(db_manager, checkpoint_interval=1000)
        
        # Load checkpoint (simulating restart after crash)
        checkpoint = new_checkpoint_manager.load_checkpoint()
        
        # Verify we can resume from last checkpoint (2000)
        assert checkpoint is not None, "Checkpoint should exist after crash"
        assert checkpoint.last_transaction_id == 2000, "Should resume from last checkpoint at 2000"
        assert checkpoint.last_receipt_id == 2000, "Should resume from last checkpoint at 2000"
        
        # Verify we can continue processing from checkpoint
        remaining = db_manager.get_transactions(limit=1000, offset=checkpoint.last_transaction_id)
        assert len(remaining) == 500, "Should have 500 remaining transactions (2001-2500)"


class TestFreshStart:
    """
    Test fresh start when no checkpoint exists.
    
    Validates: Requirement 8.5 - Begin processing from first record if no checkpoint exists
    """
    
    def test_no_checkpoint_returns_none(self, db_manager, checkpoint_manager):
        """
        Test that load_checkpoint returns None when no checkpoint exists.
        
        Validates: Requirement 8.5 - Begin processing from first record if no checkpoint exists
        """
        # Try to load checkpoint when none exists
        checkpoint = checkpoint_manager.load_checkpoint()
        
        # Verify None is returned
        assert checkpoint is None, "Should return None when no checkpoint exists"
    
    def test_fresh_start_processing(self, db_manager, checkpoint_manager):
        """
        Test that processing starts from beginning when no checkpoint exists.
        
        Validates: Requirement 8.5 - Begin processing from first record if no checkpoint exists
        """
        # Insert test data
        for i in range(1, 51):
            txn = Transaction(
                id=None,
                statement_file=f"statement_{i}.csv",
                transaction_date=date(2024, 1, 1),
                amount=Decimal(f"{i}.00"),
                description=f"Transaction {i}"
            )
            db_manager.save_transaction(txn)
        
        # Load checkpoint (should be None)
        checkpoint = checkpoint_manager.load_checkpoint()
        assert checkpoint is None, "No checkpoint should exist"
        
        # Start processing from beginning (offset 0)
        start_offset = checkpoint.last_transaction_id if checkpoint else 0
        transactions = db_manager.get_transactions(limit=50, offset=start_offset)
        
        # Verify we start from the first record
        assert len(transactions) == 50, "Should get all 50 transactions"
        assert transactions[0].id == 1, "Should start from first transaction (ID 1)"
        assert transactions[0].description == "Transaction 1"
    
    def test_fresh_start_after_checkpoint_deletion(self, db_manager, checkpoint_manager):
        """
        Test fresh start after checkpoint has been deleted.
        
        Validates: Requirement 8.5 - Begin processing from first record if no checkpoint exists
        """
        # Save a checkpoint
        checkpoint_manager.save_checkpoint(
            last_transaction_id=100,
            last_receipt_id=100
        )
        
        # Verify checkpoint exists
        checkpoint = checkpoint_manager.load_checkpoint()
        assert checkpoint is not None, "Checkpoint should exist"
        
        # Delete checkpoint
        checkpoint_manager.delete_checkpoint()
        
        # Try to load checkpoint again
        checkpoint = checkpoint_manager.load_checkpoint()
        assert checkpoint is None, "Checkpoint should not exist after deletion"
        
        # Verify we would start from beginning
        start_offset = checkpoint.last_transaction_id if checkpoint else 0
        assert start_offset == 0, "Should start from offset 0"
    
    def test_empty_database_fresh_start(self, db_manager, checkpoint_manager):
        """
        Test fresh start with empty database.
        
        Validates: Requirement 8.5 - Begin processing from first record if no checkpoint exists
        """
        # Load checkpoint from empty database
        checkpoint = checkpoint_manager.load_checkpoint()
        assert checkpoint is None, "No checkpoint should exist in empty database"
        
        # Get transactions from empty database
        transactions = db_manager.get_transactions(limit=100, offset=0)
        assert len(transactions) == 0, "Should return empty list for empty database"


class TestCheckpointDeletion:
    """
    Test checkpoint deletion on completion.
    
    Validates: Requirement 8.7 - Delete checkpoint after successful completion
    """
    
    def test_delete_checkpoint_on_completion(self, db_manager, checkpoint_manager):
        """
        Test that checkpoint is deleted after successful completion.
        
        Validates: Requirement 8.7 - Delete checkpoint after successful completion of all processing
        """
        # Save a checkpoint
        checkpoint_manager.save_checkpoint(
            last_transaction_id=1000,
            last_receipt_id=1000
        )
        
        # Verify checkpoint exists
        checkpoint = checkpoint_manager.load_checkpoint()
        assert checkpoint is not None, "Checkpoint should exist before deletion"
        assert checkpoint.last_transaction_id == 1000
        
        # Delete checkpoint (simulating successful completion)
        checkpoint_manager.delete_checkpoint()
        
        # Verify checkpoint no longer exists
        checkpoint = checkpoint_manager.load_checkpoint()
        assert checkpoint is None, "Checkpoint should not exist after deletion"
        
        # Verify checkpoint table is empty
        with db_manager.read_pool.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) as count FROM checkpoints")
            result = cursor.fetchone()
            assert result['count'] == 0, "Checkpoints table should be empty"
    
    def test_delete_nonexistent_checkpoint(self, db_manager, checkpoint_manager):
        """
        Test that deleting a nonexistent checkpoint doesn't raise an error.
        
        Validates: Requirement 8.7 - Delete checkpoint after successful completion
        """
        # Verify no checkpoint exists
        checkpoint = checkpoint_manager.load_checkpoint()
        assert checkpoint is None, "No checkpoint should exist"
        
        # Delete checkpoint (should not raise error)
        try:
            checkpoint_manager.delete_checkpoint()
        except Exception as e:
            pytest.fail(f"Deleting nonexistent checkpoint should not raise error: {e}")
        
        # Verify still no checkpoint
        checkpoint = checkpoint_manager.load_checkpoint()
        assert checkpoint is None, "Still no checkpoint should exist"
    
    def test_delete_checkpoint_multiple_times(self, db_manager, checkpoint_manager):
        """
        Test that checkpoint can be deleted multiple times without error.
        
        Validates: Requirement 8.7 - Delete checkpoint after successful completion
        """
        # Save a checkpoint
        checkpoint_manager.save_checkpoint(
            last_transaction_id=500,
            last_receipt_id=500
        )
        
        # Delete checkpoint first time
        checkpoint_manager.delete_checkpoint()
        checkpoint = checkpoint_manager.load_checkpoint()
        assert checkpoint is None, "Checkpoint should be deleted"
        
        # Delete checkpoint second time (should not raise error)
        try:
            checkpoint_manager.delete_checkpoint()
        except Exception as e:
            pytest.fail(f"Deleting checkpoint twice should not raise error: {e}")
        
        # Verify still no checkpoint
        checkpoint = checkpoint_manager.load_checkpoint()
        assert checkpoint is None, "Still no checkpoint should exist"
    
    def test_checkpoint_lifecycle(self, db_manager, checkpoint_manager):
        """
        Test complete checkpoint lifecycle: save -> load -> resume -> delete.
        
        Validates: Requirements 8.3, 8.4, 8.7
        """
        # Insert test data
        for i in range(1, 101):
            txn = Transaction(
                id=None,
                statement_file=f"statement_{i}.csv",
                transaction_date=date(2024, 1, 1),
                amount=Decimal(f"{i}.00"),
                description=f"Transaction {i}"
            )
            db_manager.save_transaction(txn)
        
        # Phase 1: Save checkpoint at 50
        checkpoint_manager.save_checkpoint(
            last_transaction_id=50,
            last_receipt_id=50
        )
        
        # Phase 2: Load checkpoint and verify
        checkpoint = checkpoint_manager.load_checkpoint()
        assert checkpoint is not None, "Checkpoint should exist"
        assert checkpoint.last_transaction_id == 50
        
        # Phase 3: Resume processing from checkpoint
        remaining = db_manager.get_transactions(limit=100, offset=checkpoint.last_transaction_id)
        assert len(remaining) == 50, "Should have 50 remaining transactions"
        assert remaining[0].id == 51, "Should resume from transaction 51"
        
        # Phase 4: Complete processing and delete checkpoint
        checkpoint_manager.delete_checkpoint()
        
        # Phase 5: Verify checkpoint is gone
        checkpoint = checkpoint_manager.load_checkpoint()
        assert checkpoint is None, "Checkpoint should be deleted after completion"


class TestCheckpointErrorHandling:
    """Test error handling in checkpoint operations."""
    
    def test_save_checkpoint_rollback_on_error(self, temp_db):
        """Test that save_checkpoint rolls back on error."""
        import sqlite3
        
        # Create a fresh database manager
        db_manager = DatabaseManager(temp_db, pool_size=5)
        db_manager.initialize_schema()
        checkpoint_manager = CheckpointManager(db_manager, checkpoint_interval=1000)
        
        # Close the write connection to simulate error
        db_manager.write_conn.close()
        
        # Try to save checkpoint (should raise error)
        with pytest.raises(Exception):
            checkpoint_manager.save_checkpoint(
                last_transaction_id=100,
                last_receipt_id=100
            )
        
        # Reconnect for cleanup
        db_manager.write_conn = sqlite3.connect(temp_db, check_same_thread=False)
        db_manager.write_conn.row_factory = sqlite3.Row
        
        # Verify no checkpoint was saved
        checkpoint = checkpoint_manager.load_checkpoint()
        assert checkpoint is None, "No checkpoint should be saved after error"
        
        # Cleanup
        db_manager.close()
    
    def test_delete_checkpoint_rollback_on_error(self, temp_db):
        """Test that delete_checkpoint rolls back on error."""
        import sqlite3
        
        # Create a fresh database manager
        db_manager = DatabaseManager(temp_db, pool_size=5)
        db_manager.initialize_schema()
        checkpoint_manager = CheckpointManager(db_manager, checkpoint_interval=1000)
        
        # Save a checkpoint first
        checkpoint_manager.save_checkpoint(
            last_transaction_id=100,
            last_receipt_id=100
        )
        
        # Verify checkpoint exists
        checkpoint = checkpoint_manager.load_checkpoint()
        assert checkpoint is not None, "Checkpoint should exist"
        
        # Close the write connection to simulate error
        db_manager.write_conn.close()
        
        # Try to delete checkpoint (should raise error)
        with pytest.raises(Exception):
            checkpoint_manager.delete_checkpoint()
        
        # Reconnect for verification
        db_manager.write_conn = sqlite3.connect(temp_db, check_same_thread=False)
        db_manager.write_conn.row_factory = sqlite3.Row
        
        # Verify checkpoint still exists (rollback occurred)
        checkpoint = checkpoint_manager.load_checkpoint()
        assert checkpoint is not None, "Checkpoint should still exist after failed deletion"
        
        # Cleanup
        db_manager.close()
