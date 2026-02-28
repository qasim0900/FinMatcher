"""
Database migration script from FinMatcher v1.0 to v2.0.

This script migrates the existing v1.0 database to the v2.0 schema by:
1. Backing up the existing database
2. Adding new columns for semantic scores and filter_method
3. Migrating existing matches to the new schema
4. Preserving all existing data

Usage:
    python -m finmatcher.migration.database_migration --db-path finmatcher.db
"""

import sqlite3
import shutil
import logging
import argparse
from pathlib import Path
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)


class DatabaseMigration:
    """
    Handles database migration from v1.0 to v2.0.
    
    Migration steps:
    1. Backup existing database
    2. Add semantic_score column to matches table (default 0.0)
    3. Add filter_method column to receipts table (default NULL)
    4. Update composite_score calculation if needed
    5. Verify data integrity
    """
    
    def __init__(self, db_path: str):
        """
        Initialize database migration.
        
        Args:
            db_path: Path to the v1.0 database file
        """
        self.db_path = Path(db_path)
        self.backup_path = None
        self.conn = None
        
        if not self.db_path.exists():
            raise FileNotFoundError(f"Database file not found: {db_path}")
        
        logger.info(f"Initialized database migration for: {db_path}")
    
    def create_backup(self) -> Path:
        """
        Create a backup of the existing database.
        
        Returns:
            Path to the backup file
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.backup_path = self.db_path.parent / f"{self.db_path.stem}_v1_backup_{timestamp}.db"
        
        logger.info(f"Creating backup: {self.backup_path}")
        shutil.copy2(self.db_path, self.backup_path)
        
        # Verify backup
        if not self.backup_path.exists():
            raise RuntimeError("Backup creation failed")
        
        backup_size = self.backup_path.stat().st_size
        original_size = self.db_path.stat().st_size
        
        if backup_size != original_size:
            raise RuntimeError(f"Backup size mismatch: {backup_size} != {original_size}")
        
        logger.info(f"Backup created successfully: {self.backup_path} ({backup_size} bytes)")
        return self.backup_path
    
    def connect(self):
        """Connect to the database."""
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        logger.info("Connected to database")
    
    def check_schema_version(self) -> str:
        """
        Check the current schema version.
        
        Returns:
            Schema version ('v1.0' or 'v2.0')
        """
        cursor = self.conn.cursor()
        
        # Check if semantic_score column exists in matches table
        cursor.execute("PRAGMA table_info(matches)")
        columns = [row[1] for row in cursor.fetchall()]
        
        if 'semantic_score' in columns:
            return 'v2.0'
        else:
            return 'v1.0'
    
    def add_semantic_score_column(self):
        """
        Add semantic_score column to matches table.
        
        In v1.0, matches only had amount_score and date_score.
        In v2.0, we add semantic_score (default 0.0 for existing records).
        """
        cursor = self.conn.cursor()
        
        logger.info("Adding semantic_score column to matches table")
        
        try:
            cursor.execute("""
                ALTER TABLE matches 
                ADD COLUMN semantic_score REAL DEFAULT 0.0
            """)
            self.conn.commit()
            logger.info("semantic_score column added successfully")
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e).lower():
                logger.warning("semantic_score column already exists, skipping")
            else:
                raise
    
    def add_filter_method_column(self):
        """
        Add filter_method column to receipts table.
        
        In v1.0, receipts didn't track the filtering method.
        In v2.0, we track whether emails were auto-rejected, auto-accepted, or AI-verified.
        """
        cursor = self.conn.cursor()
        
        logger.info("Adding filter_method column to receipts table")
        
        try:
            cursor.execute("""
                ALTER TABLE receipts 
                ADD COLUMN filter_method TEXT DEFAULT NULL
            """)
            self.conn.commit()
            logger.info("filter_method column added successfully")
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e).lower():
                logger.warning("filter_method column already exists, skipping")
            else:
                raise
    
    def recalculate_composite_scores(self):
        """
        Recalculate composite scores for existing matches.
        
        In v1.0: composite_score = W_a * amount_score + W_d * date_score
        In v2.0: composite_score = W_a * amount_score + W_d * date_score + W_s * semantic_score
        
        Since semantic_score is 0.0 for migrated records, we need to adjust the weights
        to maintain the same relative scoring. We'll normalize the existing scores.
        """
        cursor = self.conn.cursor()
        
        logger.info("Recalculating composite scores for existing matches")
        
        # Get default weights from v2.0 config (W_a=0.4, W_d=0.3, W_s=0.3)
        # For v1.0 records with semantic_score=0.0, we need to renormalize
        # Old: W_a=0.5, W_d=0.5 (assumed v1.0 weights)
        # New: W_a=0.4, W_d=0.3, W_s=0.3 (but W_s=0 for old records)
        # Renormalized: W_a=0.57, W_d=0.43 (to maintain relative importance)
        
        cursor.execute("""
            SELECT id, amount_score, date_score, semantic_score, composite_score
            FROM matches
            WHERE semantic_score = 0.0 OR semantic_score IS NULL
        """)
        
        matches_to_update = cursor.fetchall()
        logger.info(f"Found {len(matches_to_update)} matches to recalculate")
        
        for match in matches_to_update:
            match_id = match['id']
            amount_score = match['amount_score']
            date_score = match['date_score']
            
            # Recalculate with renormalized weights (excluding semantic)
            # W_a = 0.4 / (0.4 + 0.3) = 0.571
            # W_d = 0.3 / (0.4 + 0.3) = 0.429
            new_composite_score = 0.571 * amount_score + 0.429 * date_score
            
            cursor.execute("""
                UPDATE matches
                SET composite_score = ?
                WHERE id = ?
            """, (new_composite_score, match_id))
        
        self.conn.commit()
        logger.info(f"Recalculated composite scores for {len(matches_to_update)} matches")
    
    def verify_data_integrity(self) -> bool:
        """
        Verify data integrity after migration.
        
        Returns:
            True if data integrity is maintained, False otherwise
        """
        cursor = self.conn.cursor()
        
        logger.info("Verifying data integrity")
        
        # Check that all tables exist
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name IN ('transactions', 'receipts', 'matches', 'attachments')
        """)
        tables = [row[0] for row in cursor.fetchall()]
        
        if len(tables) != 4:
            logger.error(f"Missing tables. Found: {tables}")
            return False
        
        # Check that semantic_score column exists
        cursor.execute("PRAGMA table_info(matches)")
        columns = [row[1] for row in cursor.fetchall()]
        
        if 'semantic_score' not in columns:
            logger.error("semantic_score column not found in matches table")
            return False
        
        # Check that filter_method column exists
        cursor.execute("PRAGMA table_info(receipts)")
        columns = [row[1] for row in cursor.fetchall()]
        
        if 'filter_method' not in columns:
            logger.error("filter_method column not found in receipts table")
            return False
        
        # Check record counts
        cursor.execute("SELECT COUNT(*) FROM transactions")
        txn_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM receipts")
        rec_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM matches")
        match_count = cursor.fetchone()[0]
        
        logger.info(f"Record counts: {txn_count} transactions, {rec_count} receipts, {match_count} matches")
        
        # Check that all matches have valid scores
        cursor.execute("""
            SELECT COUNT(*) FROM matches
            WHERE amount_score IS NULL OR date_score IS NULL OR 
                  semantic_score IS NULL OR composite_score IS NULL
        """)
        invalid_matches = cursor.fetchone()[0]
        
        if invalid_matches > 0:
            logger.error(f"Found {invalid_matches} matches with NULL scores")
            return False
        
        logger.info("Data integrity verification passed")
        return True
    
    def migrate(self) -> bool:
        """
        Execute the complete migration process.
        
        Returns:
            True if migration succeeded, False otherwise
        """
        try:
            # Step 1: Create backup
            logger.info("=" * 60)
            logger.info("Starting database migration from v1.0 to v2.0")
            logger.info("=" * 60)
            
            self.create_backup()
            
            # Step 2: Connect to database
            self.connect()
            
            # Step 3: Check current schema version
            version = self.check_schema_version()
            logger.info(f"Current schema version: {version}")
            
            if version == 'v2.0':
                logger.info("Database is already at v2.0, no migration needed")
                return True
            
            # Step 4: Add new columns
            self.add_semantic_score_column()
            self.add_filter_method_column()
            
            # Step 5: Recalculate composite scores
            self.recalculate_composite_scores()
            
            # Step 6: Verify data integrity
            if not self.verify_data_integrity():
                logger.error("Data integrity verification failed")
                logger.error(f"Restore from backup: {self.backup_path}")
                return False
            
            logger.info("=" * 60)
            logger.info("Migration completed successfully!")
            logger.info(f"Backup saved at: {self.backup_path}")
            logger.info("=" * 60)
            
            return True
            
        except Exception as e:
            logger.error(f"Migration failed: {e}", exc_info=True)
            logger.error(f"Restore from backup: {self.backup_path}")
            return False
        
        finally:
            if self.conn:
                self.conn.close()
                logger.info("Database connection closed")
    
    def rollback(self):
        """
        Rollback migration by restoring from backup.
        """
        if not self.backup_path or not self.backup_path.exists():
            raise RuntimeError("No backup found to rollback")
        
        logger.info(f"Rolling back migration from backup: {self.backup_path}")
        
        if self.conn:
            self.conn.close()
        
        shutil.copy2(self.backup_path, self.db_path)
        logger.info("Rollback completed successfully")


def main():
    """Main entry point for database migration."""
    parser = argparse.ArgumentParser(
        description="Migrate FinMatcher database from v1.0 to v2.0"
    )
    parser.add_argument(
        "--db-path",
        type=str,
        default="finmatcher.db",
        help="Path to the database file (default: finmatcher.db)"
    )
    parser.add_argument(
        "--log-level",
        type=str,
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging level (default: INFO)"
    )
    
    args = parser.parse_args()
    
    # Configure logging
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Run migration
    migration = DatabaseMigration(args.db_path)
    success = migration.migrate()
    
    if success:
        print("\n✓ Migration completed successfully!")
        print(f"✓ Backup saved at: {migration.backup_path}")
        return 0
    else:
        print("\n✗ Migration failed!")
        print(f"✗ Restore from backup: {migration.backup_path}")
        return 1


if __name__ == "__main__":
    exit(main())
