"""
Property-based tests for CheckpointManager.

This module contains property-based tests using Hypothesis to verify:
- Property 14: Checkpoint Frequency and Content

Testing Framework: pytest + hypothesis
Feature: finmatcher-v2-upgrade
Validates: Requirements 8.1, 8.2
"""

import pytest
import tempfile
import os
from datetime import date
from decimal import Decimal
from contextlib import contextmanager
from hypothesis import given, strategies as st, assume, settings

from finmatcher.storage.checkpoint_manager import CheckpointManager
from finmatcher.storage.database_manager import DatabaseManager
from finmatcher.storage.models import Transaction


@contextmanager
def create_temp_db():
    """Context manager to create and cleanup temporary database."""
    fd, path = tempfile.mkstemp(suffix='.db')
    os.close(fd)
    try:
        yield path
    finally:
        if os.path.exists(path):
            os.unlink(path)


@contextmanager
def create_db_manager(db_path):
    """Context manager to create and cleanup DatabaseManager."""
    manager = DatabaseManager(db_path, pool_size=5)
    manager.initialize_schema()
    try:
        yield manager
    finally:
        manager.close()


class TestCheckpointFrequencyProperty:
    """
    Property 14: Checkpoint Frequency and Content
    
    Universal Property:
    FOR ALL checkpoint_interval N > 0,
    FOR ALL sequences of record processing,
    WHEN records_processed reaches N,
    THEN should_checkpoint() returns True
    AND checkpoint contains last_transaction_id, last_receipt_id, and timestamp
    
    Validates Requirements:
    - 8.1: Save checkpoint after processing every 1000 records
    - 8.2: Checkpoint contains last processed record identifier and timestamp
    """
    
    @given(
        checkpoint_interval=st.integers(min_value=1, max_value=10000),
        records_to_process=st.integers(min_value=1, max_value=20000)
    )
    @settings(max_examples=10, deadline=None)
    def test_checkpoint_frequency_triggers_at_interval(
        self,
        checkpoint_interval, 
        records_to_process
    ):
        """
        Property: Checkpoint should trigger exactly when records_processed reaches interval.
        
        Validates Requirement 8.1: Save checkpoint after processing every N records
        """
        # Setup using context managers
        with create_temp_db() as db_path:
            with create_db_manager(db_path) as db_manager:
                checkpoint_manager = CheckpointManager(db_manager, checkpoint_interval=checkpoint_interval)
                
                checkpoint_triggered_count = 0
                
                # Process records one by one
                for i in range(1, records_to_process + 1):
                    should_checkpoint = checkpoint_manager.should_checkpoint(records_processed=1)
                    
                    if should_checkpoint:
                        checkpoint_triggered_count += 1
                        checkpoint_manager.reset_record_count()
                
                # Calculate expected checkpoint count
                expected_checkpoints = records_to_process // checkpoint_interval
                
                # Property: Checkpoint should trigger exactly expected_checkpoints times
                assert checkpoint_triggered_count == expected_checkpoints, (
                    f"Expected {expected_checkpoints} checkpoints for {records_to_process} records "
                    f"with interval {checkpoint_interval}, but got {checkpoint_triggered_count}"
                )
    
    @given(
        checkpoint_interval=st.integers(min_value=100, max_value=5000),
        batch_sizes=st.lists(
            st.integers(min_value=1, max_value=500),
            min_size=1,
            max_size=50
        )
    )
    @settings(max_examples=10, deadline=None)
    def test_checkpoint_frequency_with_variable_batch_sizes(
        self,
        checkpoint_interval,
        batch_sizes
    ):
        """
        Property: Checkpoint triggers when accumulated records reach or exceed interval.
        
        Validates Requirement 8.1: Save checkpoint after processing every N records
        
        Note: The checkpoint manager's should_checkpoint() method triggers once when
        the accumulated count reaches or exceeds the interval. If a single batch
        contains multiple intervals worth of records, it still only triggers once.
        This test validates that checkpoints trigger appropriately with variable batches.
        """
        # Setup using context managers
        with create_temp_db() as db_path:
            with create_db_manager(db_path) as db_manager:
                checkpoint_manager = CheckpointManager(db_manager, checkpoint_interval=checkpoint_interval)
                
                checkpoint_positions = []
                running_total = 0
                
                # Process records in variable batch sizes
                for batch_size in batch_sizes:
                    should_checkpoint = checkpoint_manager.should_checkpoint(records_processed=batch_size)
                    running_total += batch_size
                    
                    if should_checkpoint:
                        checkpoint_positions.append(running_total)
                        checkpoint_manager.reset_record_count()
                
                # Property: Each checkpoint should occur after at least checkpoint_interval records
                for i, pos in enumerate(checkpoint_positions):
                    if i == 0:
                        # First checkpoint should be at or after the interval
                        assert pos >= checkpoint_interval, (
                            f"First checkpoint at {pos} should be >= {checkpoint_interval}"
                        )
                    else:
                        # Subsequent checkpoints should be at least interval apart
                        distance = pos - checkpoint_positions[i-1]
                        assert distance >= checkpoint_interval, (
                            f"Checkpoint distance {distance} should be >= {checkpoint_interval}"
                        )
    
    @given(
        last_transaction_id=st.integers(min_value=1, max_value=1000000),
        last_receipt_id=st.integers(min_value=1, max_value=1000000)
    )
    @settings(max_examples=50, deadline=None)
    def test_checkpoint_content_contains_required_fields(
        self,
        last_transaction_id,
        last_receipt_id
    ):
        """
        Property: Saved checkpoint must contain last_transaction_id, last_receipt_id, and timestamp.
        
        Validates Requirement 8.2: Checkpoint contains last processed record identifier and timestamp
        """
        # Setup using context managers
        with create_temp_db() as db_path:
            with create_db_manager(db_path) as db_manager:
                checkpoint_manager = CheckpointManager(db_manager, checkpoint_interval=1000)
                
                # Save checkpoint
                checkpoint_manager.save_checkpoint(last_transaction_id, last_receipt_id)
                
                # Load checkpoint
                checkpoint = checkpoint_manager.load_checkpoint()
                
                # Property: Checkpoint must exist and contain all required fields
                assert checkpoint is not None, "Checkpoint should be saved and loadable"
                assert checkpoint.last_transaction_id == last_transaction_id, (
                    f"Expected last_transaction_id={last_transaction_id}, "
                    f"got {checkpoint.last_transaction_id}"
                )
                assert checkpoint.last_receipt_id == last_receipt_id, (
                    f"Expected last_receipt_id={last_receipt_id}, "
                    f"got {checkpoint.last_receipt_id}"
                )
                assert checkpoint.timestamp is not None, "Checkpoint must have a timestamp"
                assert isinstance(checkpoint.timestamp, date), "Timestamp must be a date object"
    
    @given(
        checkpoint_interval=st.integers(min_value=1, max_value=1000),
        records_before_checkpoint=st.integers(min_value=0, max_value=999)
    )
    @settings(max_examples=10, deadline=None)
    def test_checkpoint_does_not_trigger_before_interval(
        self,
        checkpoint_interval,
        records_before_checkpoint
    ):
        """
        Property: Checkpoint should NOT trigger before reaching the interval.
        
        Validates Requirement 8.1: Save checkpoint after processing every N records (not before)
        """
        # Ensure we don't reach the interval
        assume(records_before_checkpoint < checkpoint_interval)
        
        # Setup using context managers
        with create_temp_db() as db_path:
            with create_db_manager(db_path) as db_manager:
                checkpoint_manager = CheckpointManager(db_manager, checkpoint_interval=checkpoint_interval)
                
                # Process records one by one
                for i in range(records_before_checkpoint):
                    should_checkpoint = checkpoint_manager.should_checkpoint(records_processed=1)
                    
                    # Property: Should NOT trigger checkpoint before interval
                    assert not should_checkpoint, (
                        f"Checkpoint should not trigger at {i+1} records "
                        f"when interval is {checkpoint_interval}"
                    )
    
    @given(
        checkpoint_interval=st.integers(min_value=1, max_value=1000),
        records_at_interval=st.integers(min_value=1, max_value=10)
    )
    @settings(max_examples=50, deadline=None)
    def test_checkpoint_triggers_exactly_at_interval(
        self,
        checkpoint_interval,
        records_at_interval
    ):
        """
        Property: Checkpoint should trigger exactly when reaching N records, not before or after.
        
        Validates Requirement 8.1: Save checkpoint after processing every N records
        """
        # Setup using context managers
        with create_temp_db() as db_path:
            with create_db_manager(db_path) as db_manager:
                checkpoint_manager = CheckpointManager(db_manager, checkpoint_interval=checkpoint_interval)
                
                # Process exactly checkpoint_interval * records_at_interval records
                total_records = checkpoint_interval * records_at_interval
                
                for i in range(1, total_records + 1):
                    should_checkpoint = checkpoint_manager.should_checkpoint(records_processed=1)
                    
                    # Property: Should trigger exactly at multiples of checkpoint_interval
                    if i % checkpoint_interval == 0:
                        assert should_checkpoint, (
                            f"Checkpoint should trigger at record {i} "
                            f"(multiple of {checkpoint_interval})"
                        )
                        checkpoint_manager.reset_record_count()
                    else:
                        assert not should_checkpoint, (
                            f"Checkpoint should not trigger at record {i} "
                            f"(not a multiple of {checkpoint_interval})"
                        )
    
    @given(
        checkpoint_interval=st.integers(min_value=100, max_value=2000),
        num_checkpoints=st.integers(min_value=1, max_value=10)
    )
    @settings(max_examples=50, deadline=None)
    def test_checkpoint_content_updates_correctly(
        self,
        checkpoint_interval,
        num_checkpoints
    ):
        """
        Property: Each checkpoint save should update with new IDs and timestamp.
        
        Validates Requirement 8.2: Checkpoint contains last processed record identifier and timestamp
        """
        # Setup using context managers
        with create_temp_db() as db_path:
            with create_db_manager(db_path) as db_manager:
                checkpoint_manager = CheckpointManager(db_manager, checkpoint_interval=checkpoint_interval)
                
                previous_checkpoint = None
                
                for i in range(1, num_checkpoints + 1):
                    # Simulate processing checkpoint_interval records
                    last_txn_id = i * checkpoint_interval
                    last_rec_id = i * checkpoint_interval + 100
                    
                    # Save checkpoint
                    checkpoint_manager.save_checkpoint(last_txn_id, last_rec_id)
                    
                    # Load checkpoint
                    current_checkpoint = checkpoint_manager.load_checkpoint()
                    
                    # Property: Checkpoint should contain the latest IDs
                    assert current_checkpoint.last_transaction_id == last_txn_id, (
                        f"Checkpoint should have last_transaction_id={last_txn_id}"
                    )
                    assert current_checkpoint.last_receipt_id == last_rec_id, (
                        f"Checkpoint should have last_receipt_id={last_rec_id}"
                    )
                    
                    # Property: Each checkpoint should have a timestamp
                    assert current_checkpoint.timestamp is not None, (
                        "Checkpoint must have a timestamp"
                    )
                    
                    # Property: Subsequent checkpoints should have equal or later timestamps
                    if previous_checkpoint is not None:
                        assert current_checkpoint.timestamp >= previous_checkpoint.timestamp, (
                            "Checkpoint timestamp should not go backwards"
                        )
                    
                    previous_checkpoint = current_checkpoint
    
    @given(
        checkpoint_interval=st.integers(min_value=1, max_value=1000)
    )
    @settings(max_examples=50, deadline=None)
    def test_checkpoint_reset_clears_counter(
        self,
        checkpoint_interval
    ):
        """
        Property: Resetting checkpoint counter should prevent premature triggering.
        
        Validates Requirement 8.1: Checkpoint frequency is maintained after reset
        """
        # Setup using context managers
        with create_temp_db() as db_path:
            with create_db_manager(db_path) as db_manager:
                checkpoint_manager = CheckpointManager(db_manager, checkpoint_interval=checkpoint_interval)
                
                # Process records up to interval - 1
                for i in range(checkpoint_interval - 1):
                    should_checkpoint = checkpoint_manager.should_checkpoint(records_processed=1)
                    assert not should_checkpoint, "Should not trigger before interval"
                
                # Reset counter
                checkpoint_manager.reset_record_count()
                
                # Property: After reset, should need another full interval before triggering
                for i in range(checkpoint_interval - 1):
                    should_checkpoint = checkpoint_manager.should_checkpoint(records_processed=1)
                    assert not should_checkpoint, (
                        f"Should not trigger at {i+1} records after reset "
                        f"(interval is {checkpoint_interval})"
                    )
                
                # Now at interval - 1, one more should trigger
                should_checkpoint = checkpoint_manager.should_checkpoint(records_processed=1)
                assert should_checkpoint, (
                    f"Should trigger after {checkpoint_interval} records following reset"
                )
