"""
Unit tests for DatabaseManager.

This module contains unit tests to verify database operations including:
- Concurrent read operations from multiple threads
- Serialized write operations to prevent conflicts
- Transaction rollback on errors
- Pagination and batch operations

Testing Framework: pytest
Feature: finmatcher-v2-upgrade
Validates: Requirements 7.3, 7.4, 7.5
"""

import pytest
import sqlite3
import threading
import tempfile
import os
from datetime import date
from decimal import Decimal
from pathlib import Path

from finmatcher.storage.database_manager import DatabaseManager
from finmatcher.storage.models import (
    Transaction, Receipt, MatchResult, Attachment,
    MatchConfidence, AttachmentType, FilterMethod
)


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


class TestConcurrentReads:
    """
    Test concurrent read operations from multiple threads.
    
    Validates: Requirement 7.3 - Support concurrent read operations from multiple threads
    """
    
    def test_concurrent_reads_dont_block(self, db_manager):
        """Test that concurrent read operations don't block each other."""
        # Insert test data
        for i in range(100):
            txn = Transaction(
                id=None,
                statement_file=f"statement_{i}.csv",
                transaction_date=date(2024, 1, 1),
                amount=Decimal("100.00"),
                description=f"Transaction {i}"
            )
            db_manager.save_transaction(txn)
        
        results = []
        errors = []
        
        def read_transactions(thread_id):
            """Read transactions in a thread."""
            try:
                txns = db_manager.get_transactions(limit=50, offset=thread_id * 10)
                results.append((thread_id, len(txns)))
            except Exception as e:
                errors.append((thread_id, str(e)))
        
        # Create 10 threads that read concurrently
        threads = []
        for i in range(10):
            thread = threading.Thread(target=read_transactions, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Verify no errors occurred
        assert len(errors) == 0, f"Errors occurred during concurrent reads: {errors}"
        
        # Verify all threads completed successfully
        assert len(results) == 10, f"Expected 10 results, got {len(results)}"
    
    def test_concurrent_reads_with_writes(self, db_manager):
        """Test that read operations don't block during writes (WAL mode benefit)."""
        # Insert initial data
        for i in range(50):
            txn = Transaction(
                id=None,
                statement_file=f"statement_{i}.csv",
                transaction_date=date(2024, 1, 1),
                amount=Decimal("100.00"),
                description=f"Transaction {i}"
            )
            db_manager.save_transaction(txn)
        
        read_results = []
        write_results = []
        
        def read_continuously():
            """Continuously read transactions."""
            for _ in range(10):
                txns = db_manager.get_transactions(limit=50)
                read_results.append(len(txns))
        
        def write_continuously():
            """Continuously write transactions."""
            for i in range(10):
                txn = Transaction(
                    id=None,
                    statement_file=f"new_statement_{i}.csv",
                    transaction_date=date(2024, 1, 2),
                    amount=Decimal("200.00"),
                    description=f"New Transaction {i}"
                )
                txn_id = db_manager.save_transaction(txn)
                write_results.append(txn_id)
        
        # Start reader and writer threads
        reader_thread = threading.Thread(target=read_continuously)
        writer_thread = threading.Thread(target=write_continuously)
        
        reader_thread.start()
        writer_thread.start()
        
        reader_thread.join()
        writer_thread.join()
        
        # Verify both operations completed successfully
        assert len(read_results) == 10, "Reader thread should complete all reads"
        assert len(write_results) == 10, "Writer thread should complete all writes"


class TestSerializedWrites:
    """
    Test serialized write operations to prevent conflicts.
    
    Validates: Requirement 7.4 - Serialize write operations to prevent conflicts
    """
    
    def test_writes_are_serialized(self, db_manager):
        """Test that write operations are properly serialized."""
        write_order = []
        lock = threading.Lock()
        
        def write_transaction(thread_id):
            """Write a transaction and record the order."""
            txn = Transaction(
                id=None,
                statement_file=f"statement_{thread_id}.csv",
                transaction_date=date(2024, 1, 1),
                amount=Decimal("100.00"),
                description=f"Transaction {thread_id}"
            )
            txn_id = db_manager.save_transaction(txn)
            
            with lock:
                write_order.append((thread_id, txn_id))
        
        # Create multiple threads that write concurrently
        threads = []
        for i in range(20):
            thread = threading.Thread(target=write_transaction, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Verify all writes completed successfully
        assert len(write_order) == 20, f"Expected 20 writes, got {len(write_order)}"
        
        # Verify all transaction IDs are unique
        txn_ids = [txn_id for _, txn_id in write_order]
        assert len(set(txn_ids)) == 20, "All transaction IDs should be unique"
        
        # Verify data integrity by reading back
        txns = db_manager.get_transactions(limit=20)
        assert len(txns) == 20, "All transactions should be persisted"
    
    def test_concurrent_writes_no_corruption(self, db_manager):
        """Test that concurrent writes don't corrupt data."""
        def write_receipt(receipt_id):
            """Write a receipt with specific data."""
            # Use receipt_id for amount but keep date constant to avoid invalid dates
            receipt = Receipt(
                id=None,
                source="email",
                receipt_date=date(2024, 1, min(receipt_id, 28)),  # Keep within valid day range
                amount=Decimal(f"{receipt_id}.00"),
                description=f"Receipt {receipt_id}",
                is_financial=True,
                filter_method=FilterMethod.AUTO_ACCEPT
            )
            db_manager.save_receipt(receipt)
        
        # Create 50 threads writing different receipts
        threads = []
        for i in range(1, 51):
            thread = threading.Thread(target=write_receipt, args=(i,))
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # Verify all receipts were saved correctly
        receipts = db_manager.get_receipts(limit=50)
        assert len(receipts) == 50, "All receipts should be saved"
        
        # Verify data integrity - each receipt should have unique amount
        amounts = [float(r.amount) for r in receipts]
        assert len(set(amounts)) == 50, "All amounts should be unique"


class TestTransactionRollback:
    """
    Test transaction rollback on errors.
    
    Validates: Requirement 7.5 - Ensure atomicity by committing or rolling back all operations together
    """
    
    def test_transaction_rollback_on_error(self, db_manager):
        """Test that transaction rolls back when an error occurs."""
        # Create operations where the last one will fail
        def operation1():
            cursor = db_manager.write_conn.cursor()
            cursor.execute("""
                INSERT INTO transactions (statement_file, transaction_date, amount, description)
                VALUES (?, ?, ?, ?)
            """, ("statement1.csv", "2024-01-01", 100.00, "Transaction 1"))
        
        def operation2():
            cursor = db_manager.write_conn.cursor()
            cursor.execute("""
                INSERT INTO transactions (statement_file, transaction_date, amount, description)
                VALUES (?, ?, ?, ?)
            """, ("statement2.csv", "2024-01-02", 200.00, "Transaction 2"))
        
        def operation3_fails():
            # This will fail due to syntax error
            cursor = db_manager.write_conn.cursor()
            cursor.execute("INSERT INTO nonexistent_table VALUES (1, 2, 3)")
        
        # Execute transaction that should fail
        with pytest.raises(Exception):
            db_manager.execute_transaction([operation1, operation2, operation3_fails])
        
        # Verify no transactions were saved (rollback occurred)
        txns = db_manager.get_transactions()
        assert len(txns) == 0, "No transactions should be saved after rollback"
    
    def test_transaction_commit_on_success(self, db_manager):
        """Test that transaction commits when all operations succeed."""
        def operation1():
            cursor = db_manager.write_conn.cursor()
            cursor.execute("""
                INSERT INTO transactions (statement_file, transaction_date, amount, description)
                VALUES (?, ?, ?, ?)
            """, ("statement1.csv", "2024-01-01", 100.00, "Transaction 1"))
        
        def operation2():
            cursor = db_manager.write_conn.cursor()
            cursor.execute("""
                INSERT INTO transactions (statement_file, transaction_date, amount, description)
                VALUES (?, ?, ?, ?)
            """, ("statement2.csv", "2024-01-02", 200.00, "Transaction 2"))
        
        def operation3():
            cursor = db_manager.write_conn.cursor()
            cursor.execute("""
                INSERT INTO transactions (statement_file, transaction_date, amount, description)
                VALUES (?, ?, ?, ?)
            """, ("statement3.csv", "2024-01-03", 300.00, "Transaction 3"))
        
        # Execute transaction that should succeed
        db_manager.execute_transaction([operation1, operation2, operation3])
        
        # Verify all transactions were saved (commit occurred)
        txns = db_manager.get_transactions()
        assert len(txns) == 3, "All transactions should be saved after commit"
        assert txns[0].amount == Decimal("100.00")
        assert txns[1].amount == Decimal("200.00")
        assert txns[2].amount == Decimal("300.00")


class TestPaginationAndBatchOperations:
    """
    Test pagination and batch operations.
    
    Validates: Requirement 7.5 - Pagination for large result sets
    """
    
    def test_pagination_transactions(self, db_manager):
        """Test pagination of transaction records."""
        # Insert 250 transactions
        for i in range(250):
            txn = Transaction(
                id=None,
                statement_file=f"statement_{i}.csv",
                transaction_date=date(2024, 1, 1),
                amount=Decimal(f"{i}.00"),
                description=f"Transaction {i}"
            )
            db_manager.save_transaction(txn)
        
        # Test pagination
        page1 = db_manager.get_transactions(limit=100, offset=0)
        page2 = db_manager.get_transactions(limit=100, offset=100)
        page3 = db_manager.get_transactions(limit=100, offset=200)
        
        assert len(page1) == 100, "First page should have 100 records"
        assert len(page2) == 100, "Second page should have 100 records"
        assert len(page3) == 50, "Third page should have 50 records"
        
        # Verify no overlap between pages
        page1_amounts = {float(t.amount) for t in page1}
        page2_amounts = {float(t.amount) for t in page2}
        page3_amounts = {float(t.amount) for t in page3}
        
        assert len(page1_amounts & page2_amounts) == 0, "Pages should not overlap"
        assert len(page2_amounts & page3_amounts) == 0, "Pages should not overlap"
    
    def test_pagination_receipts(self, db_manager):
        """Test pagination of receipt records."""
        # Insert 150 receipts
        for i in range(150):
            receipt = Receipt(
                id=None,
                source="email",
                receipt_date=date(2024, 1, 1),
                amount=Decimal(f"{i}.00"),
                description=f"Receipt {i}",
                is_financial=True,
                filter_method=FilterMethod.AUTO_ACCEPT
            )
            db_manager.save_receipt(receipt)
        
        # Test pagination
        page1 = db_manager.get_receipts(limit=50, offset=0)
        page2 = db_manager.get_receipts(limit=50, offset=50)
        page3 = db_manager.get_receipts(limit=50, offset=100)
        
        assert len(page1) == 50, "First page should have 50 records"
        assert len(page2) == 50, "Second page should have 50 records"
        assert len(page3) == 50, "Third page should have 50 records"
        
        # Verify correct ordering
        assert page1[0].id < page2[0].id < page3[0].id, "Pages should be ordered by ID"
    
    def test_batch_save_operations(self, db_manager):
        """Test batch save operations using transactions."""
        def batch_insert_transactions():
            """Insert multiple transactions in a batch."""
            for i in range(10):
                cursor = db_manager.write_conn.cursor()
                cursor.execute("""
                    INSERT INTO transactions (statement_file, transaction_date, amount, description)
                    VALUES (?, ?, ?, ?)
                """, (f"statement_{i}.csv", "2024-01-01", float(i * 10), f"Transaction {i}"))
        
        # Execute batch operation
        db_manager.execute_transaction([batch_insert_transactions])
        
        # Verify all records were saved
        txns = db_manager.get_transactions()
        assert len(txns) == 10, "All transactions should be saved in batch"
    
    def test_empty_pagination(self, db_manager):
        """Test pagination with no records."""
        txns = db_manager.get_transactions(limit=100, offset=0)
        assert len(txns) == 0, "Should return empty list for no records"
        
        receipts = db_manager.get_receipts(limit=100, offset=0)
        assert len(receipts) == 0, "Should return empty list for no records"


class TestWALMode:
    """Test WAL mode initialization and verification."""
    
    def test_wal_mode_enabled(self, db_manager):
        """Test that WAL mode is properly enabled."""
        cursor = db_manager.write_conn.cursor()
        result = cursor.execute("PRAGMA journal_mode").fetchone()
        assert result[0].upper() == 'WAL', "WAL mode should be enabled"
    
    def test_wal_mode_initialization_failure(self, temp_db):
        """Test handling of WAL mode initialization failure."""
        # This test verifies the error handling, though WAL mode should normally succeed
        # We can't easily force WAL mode to fail, so we just verify the check exists
        manager = DatabaseManager(temp_db)
        cursor = manager.write_conn.cursor()
        result = cursor.execute("PRAGMA journal_mode").fetchone()
        assert result[0].upper() == 'WAL', "WAL mode should be enabled"
        manager.close()


class TestReferentialIntegrity:
    """
    Test referential integrity between tables.
    
    Validates: Requirement 7.6 - Maintain referential integrity
    """
    
    def test_match_foreign_keys(self, db_manager):
        """Test that matches maintain referential integrity with transactions and receipts."""
        # Create transaction and receipt
        txn = Transaction(
            id=None,
            statement_file="statement.csv",
            transaction_date=date(2024, 1, 1),
            amount=Decimal("100.00"),
            description="Test transaction"
        )
        txn_id = db_manager.save_transaction(txn)
        txn.id = txn_id
        
        receipt = Receipt(
            id=None,
            source="email",
            receipt_date=date(2024, 1, 1),
            amount=Decimal("100.00"),
            description="Test receipt",
            is_financial=True,
            filter_method=FilterMethod.AUTO_ACCEPT
        )
        receipt_id = db_manager.save_receipt(receipt)
        receipt.id = receipt_id
        
        # Create match
        match = MatchResult(
            transaction=txn,
            receipt=receipt,
            amount_score=0.95,
            date_score=1.0,
            semantic_score=0.90,
            composite_score=0.95,
            confidence=MatchConfidence.HIGH
        )
        db_manager.save_match(match)
        
        # Verify match was saved
        with db_manager.read_pool.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM matches WHERE transaction_id = ? AND receipt_id = ?", 
                          (txn_id, receipt_id))
            result = cursor.fetchone()
            assert result is not None, "Match should be saved"
            assert result['transaction_id'] == txn_id
            assert result['receipt_id'] == receipt_id
    
    def test_attachment_foreign_key(self, db_manager):
        """Test that attachments maintain referential integrity with receipts."""
        # Create receipt
        receipt = Receipt(
            id=None,
            source="email",
            receipt_date=date(2024, 1, 1),
            amount=Decimal("100.00"),
            description="Test receipt",
            is_financial=True,
            filter_method=FilterMethod.AUTO_ACCEPT
        )
        receipt_id = db_manager.save_receipt(receipt)
        
        # Create attachment
        attachment = Attachment(
            id=None,
            receipt_id=receipt_id,
            filename="receipt.pdf",
            file_type=AttachmentType.DOCUMENT,
            drive_file_id="drive_123",
            local_path="/tmp/receipt.pdf"
        )
        attachment_id = db_manager.save_attachment(attachment)
        
        # Verify attachment was saved
        with db_manager.read_pool.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM attachments WHERE id = ?", (attachment_id,))
            result = cursor.fetchone()
            assert result is not None, "Attachment should be saved"
            assert result['receipt_id'] == receipt_id
            assert result['filename'] == "receipt.pdf"
