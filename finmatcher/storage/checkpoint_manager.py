"""
Checkpoint manager for FinMatcher v2.0 Enterprise Upgrade.

This module provides checkpoint and resume capability for crash recovery,
saving processing state every 1000 records.

Validates Requirements: 8.1, 8.2, 8.3, 8.4, 8.5, 8.6, 8.7
"""

import logging
from datetime import datetime
from typing import Optional

from finmatcher.storage.models import Checkpoint
from finmatcher.storage.database_manager import DatabaseManager

logger = logging.getLogger(__name__)


class CheckpointManager:
    """
    Manages checkpoints for crash recovery and resume capability.
    
    Validates Requirements: 8.1, 8.2, 8.3, 8.4, 8.5, 8.6, 8.7
    """
    
    def __init__(self, db_manager: DatabaseManager, checkpoint_interval: int = 1000):
        """
        Initialize checkpoint manager.
        
        Args:
            db_manager: Database manager instance
            checkpoint_interval: Number of records between checkpoints
            
        Validates Requirement: 8.1 - Save checkpoint after processing every 1000 records
        """
        self.db_manager = db_manager
        self.checkpoint_interval = checkpoint_interval
        self.records_since_checkpoint = 0
        
        logger.info(f"Checkpoint manager initialized (interval: {checkpoint_interval} records)")
    
    def save_checkpoint(self, last_transaction_id: int, last_receipt_id: int):
        """
        Save current processing state.
        
        Args:
            last_transaction_id: ID of last processed transaction
            last_receipt_id: ID of last processed receipt
            
        Validates Requirements:
        - 8.1: Save checkpoint after processing every 1000 records
        - 8.2: Checkpoint contains last processed record identifier and timestamp
        - 8.6: Persist checkpoint to database using a transaction
        """
        with self.db_manager.write_lock:
            cursor = self.db_manager.write_conn.cursor()
            
            try:
                # Use INSERT OR REPLACE to ensure only one checkpoint exists
                cursor.execute("""
                    INSERT OR REPLACE INTO checkpoints 
                    (id, last_transaction_id, last_receipt_id, timestamp)
                    VALUES (1, ?, ?, ?)
                """, (
                    last_transaction_id,
                    last_receipt_id,
                    datetime.now().isoformat()
                ))
                
                self.db_manager.write_conn.commit()
                self.records_since_checkpoint = 0
                
                logger.info(
                    f"Checkpoint saved: transaction_id={last_transaction_id}, "
                    f"receipt_id={last_receipt_id}"
                )
                
            except Exception as e:
                self.db_manager.write_conn.rollback()
                logger.error(f"Failed to save checkpoint: {e}")
                raise
    
    def load_checkpoint(self) -> Optional[Checkpoint]:
        """
        Load last checkpoint if exists.
        
        Returns:
            Checkpoint object or None if no checkpoint exists
            
        Validates Requirements:
        - 8.3: Check for existing checkpoint data on startup
        - 8.4: Resume processing from last saved record identifier if checkpoint exists
        """
        with self.db_manager.read_pool.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT last_transaction_id, last_receipt_id, timestamp
                FROM checkpoints
                WHERE id = 1
            """)
            
            row = cursor.fetchone()
            
            if row:
                checkpoint = Checkpoint(
                    last_transaction_id=row['last_transaction_id'],
                    last_receipt_id=row['last_receipt_id'],
                    timestamp=datetime.fromisoformat(row['timestamp']).date()
                )
                
                logger.info(
                    f"Checkpoint loaded: transaction_id={checkpoint.last_transaction_id}, "
                    f"receipt_id={checkpoint.last_receipt_id}, "
                    f"timestamp={checkpoint.timestamp}"
                )
                
                return checkpoint
            else:
                logger.info("No checkpoint found, starting fresh")
                return None
    
    def delete_checkpoint(self):
        """
        Delete checkpoint after successful completion.
        
        Validates Requirement: 8.7 - Delete checkpoint after successful completion of all processing
        """
        with self.db_manager.write_lock:
            cursor = self.db_manager.write_conn.cursor()
            
            try:
                cursor.execute("DELETE FROM checkpoints WHERE id = 1")
                self.db_manager.write_conn.commit()
                
                logger.info("Checkpoint deleted after successful completion")
                
            except Exception as e:
                self.db_manager.write_conn.rollback()
                logger.error(f"Failed to delete checkpoint: {e}")
                raise
    
    def should_checkpoint(self, records_processed: int = 1) -> bool:
        """
        Check if checkpoint should be saved.
        
        Args:
            records_processed: Number of records processed since last check (default: 1)
            
        Returns:
            True if checkpoint should be saved, False otherwise
            
        Validates Requirement: 8.1 - Save checkpoint after processing every 1000 records
        """
        self.records_since_checkpoint += records_processed
        
        if self.records_since_checkpoint >= self.checkpoint_interval:
            return True
        
        return False
    
    def increment_record_count(self, count: int = 1):
        """
        Increment the count of records processed since last checkpoint.
        
        Args:
            count: Number of records to add to count (default: 1)
        """
        self.records_since_checkpoint += count
    
    def reset_record_count(self):
        """Reset the count of records processed since last checkpoint."""
        self.records_since_checkpoint = 0
