"""
Database manager for FinMatcher v2.0 Enterprise Upgrade.

This module provides SQLite database management with WAL mode, connection pooling,
serialized write operations, and ACID-compliant transactions.

Validates Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6
"""

import sqlite3
import logging
import threading
from typing import List, Optional, Tuple, Any
from queue import Queue
from contextlib import contextmanager
from datetime import date
from decimal import Decimal

from finmatcher.storage.models import (
    Transaction, Receipt, Attachment, MatchResult,
    MatchConfidence, AttachmentType, FilterMethod
)

logger = logging.getLogger(__name__)


class ConnectionPool:
    """
    Connection pool for concurrent read operations.
    
    Validates Requirement: 7.3 - Support concurrent read operations from multiple threads
    """
    
    def __init__(self, db_path: str, pool_size: int = 10):
        """
        Initialize connection pool.
        
        Args:
            db_path: Path to SQLite database file
            pool_size: Number of connections in pool
        """
        self.db_path = db_path
        self.pool = Queue(maxsize=pool_size)
        
        # Create connections
        for _ in range(pool_size):
            conn = self._create_connection()
            self.pool.put(conn)
        
        logger.info(f"Connection pool initialized with {pool_size} connections")
    
    def _create_connection(self) -> sqlite3.Connection:
        """Create a new database connection with WAL mode."""
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        
        # Enable WAL mode
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("PRAGMA cache_size=-64000")  # 64MB cache
        conn.execute("PRAGMA temp_store=MEMORY")
        
        return conn
    
    @contextmanager
    def get_connection(self):
        """
        Get a connection from the pool.
        
        Yields:
            Database connection
        """
        conn = self.pool.get()
        try:
            yield conn
        finally:
            self.pool.put(conn)
    
    def close_all(self):
        """Close all connections in the pool."""
        while not self.pool.empty():
            conn = self.pool.get()
            conn.close()


class DatabaseManager:
    """
    Manages SQLite database with WAL mode, connection pooling, and ACID compliance.
    
    Validates Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6
    """
    
    def __init__(self, db_path: str = "finmatcher.db", pool_size: int = 10):
        """
        Initialize database manager.
        
        Args:
            db_path: Path to SQLite database file
            pool_size: Number of connections in read pool
            
        Validates Requirements: 7.1, 7.2
        """
        self.db_path = db_path
        self.write_lock = threading.Lock()
        
        # Create write connection
        self.write_conn = sqlite3.connect(db_path, check_same_thread=False)
        self.write_conn.row_factory = sqlite3.Row
        
        # Initialize WAL mode (Requirement 7.1, 7.2)
        self._initialize_wal_mode()
        
        # Create connection pool for reads (Requirement 7.3)
        self.read_pool = ConnectionPool(db_path, pool_size)
        
        logger.info(f"Database manager initialized: {db_path}")
    
    def _initialize_wal_mode(self):
        """
        Initialize SQLite with WAL mode and optimizations.
        
        Validates Requirement: 7.2 - Execute pragma statement "PRAGMA journal_mode=WAL"
        """
        self.write_conn.execute("PRAGMA journal_mode=WAL")
        self.write_conn.execute("PRAGMA synchronous=NORMAL")
        self.write_conn.execute("PRAGMA cache_size=-64000")  # 64MB cache
        self.write_conn.execute("PRAGMA temp_store=MEMORY")
        self.write_conn.execute("PRAGMA mmap_size=30000000000")  # 30GB mmap
        
        # Verify WAL mode is enabled
        result = self.write_conn.execute("PRAGMA journal_mode").fetchone()
        if result[0].upper() != 'WAL':
            raise RuntimeError(f"Failed to enable WAL mode, got: {result[0]}")
        
        logger.info("WAL mode enabled successfully")
    
    def initialize_schema(self):
        """
        Create database tables with proper indexes and constraints.
        
        Validates Requirement: 7.6 - Maintain referential integrity
        """
        with self.write_lock:
            cursor = self.write_conn.cursor()
            
            # Transactions table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS transactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    statement_file TEXT NOT NULL,
                    transaction_date DATE NOT NULL,
                    amount DECIMAL(10, 2) NOT NULL,
                    description TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create indexes for transactions
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_transactions_amount 
                ON transactions(amount)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_transactions_date 
                ON transactions(transaction_date)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_transactions_amount_date 
                ON transactions(amount, transaction_date)
            """)
            
            # Receipts table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS receipts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source TEXT NOT NULL,
                    receipt_date DATE NOT NULL,
                    amount DECIMAL(10, 2),
                    description TEXT NOT NULL,
                    is_financial BOOLEAN DEFAULT TRUE,
                    filter_method TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create indexes for receipts
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_receipts_amount 
                ON receipts(amount)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_receipts_date 
                ON receipts(receipt_date)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_receipts_amount_date 
                ON receipts(amount, receipt_date)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_receipts_filter_method 
                ON receipts(filter_method)
            """)
            
            # Matches table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS matches (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    transaction_id INTEGER NOT NULL,
                    receipt_id INTEGER NOT NULL,
                    amount_score REAL NOT NULL,
                    date_score REAL NOT NULL,
                    semantic_score REAL NOT NULL,
                    composite_score REAL NOT NULL,
                    confidence_level TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (transaction_id) REFERENCES transactions(id),
                    FOREIGN KEY (receipt_id) REFERENCES receipts(id)
                )
            """)
            
            # Create indexes for matches
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_matches_composite_score 
                ON matches(composite_score DESC)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_matches_transaction 
                ON matches(transaction_id)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_matches_receipt 
                ON matches(receipt_id)
            """)
            
            # Attachments table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS attachments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    receipt_id INTEGER NOT NULL,
                    filename TEXT NOT NULL,
                    file_type TEXT NOT NULL,
                    drive_file_id TEXT,
                    local_path TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (receipt_id) REFERENCES receipts(id)
                )
            """)
            
            # Checkpoints table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS checkpoints (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    last_transaction_id INTEGER NOT NULL,
                    last_receipt_id INTEGER NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            self.write_conn.commit()
            logger.info("Database schema initialized successfully")
    
    def save_transaction(self, transaction: Transaction) -> int:
        """
        Save transaction record and return ID.
        
        Args:
            transaction: Transaction object to save
            
        Returns:
            Transaction ID
            
        Validates Requirement: 7.4 - Serialize write operations to prevent conflicts
        """
        with self.write_lock:
            cursor = self.write_conn.cursor()
            cursor.execute("""
                INSERT INTO transactions (statement_file, transaction_date, amount, description)
                VALUES (?, ?, ?, ?)
            """, (
                transaction.statement_file,
                transaction.transaction_date.isoformat(),
                float(transaction.amount),
                transaction.description
            ))
            self.write_conn.commit()
            return cursor.lastrowid
    
    def save_receipt(self, receipt: Receipt) -> int:
        """
        Save receipt record and return ID.
        
        Args:
            receipt: Receipt object to save
            
        Returns:
            Receipt ID
            
        Validates Requirement: 7.4 - Serialize write operations to prevent conflicts
        """
        with self.write_lock:
            cursor = self.write_conn.cursor()
            cursor.execute("""
                INSERT INTO receipts (source, receipt_date, amount, description, 
                                     is_financial, filter_method)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                receipt.source,
                receipt.receipt_date.isoformat(),
                float(receipt.amount) if receipt.amount else None,
                receipt.description,
                receipt.is_financial,
                receipt.filter_method.value if receipt.filter_method else None
            ))
            self.write_conn.commit()
            return cursor.lastrowid
    
    def save_match(self, match: MatchResult):
        """
        Save match result with scores.
        
        Args:
            match: MatchResult object to save
            
        Validates Requirement: 7.4 - Serialize write operations to prevent conflicts
        """
        with self.write_lock:
            cursor = self.write_conn.cursor()
            cursor.execute("""
                INSERT INTO matches (transaction_id, receipt_id, amount_score, 
                                   date_score, semantic_score, composite_score, 
                                   confidence_level)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                match.transaction.id,
                match.receipt.id,
                match.amount_score,
                match.date_score,
                match.semantic_score,
                match.composite_score,
                match.confidence.value
            ))
            self.write_conn.commit()
    
    def save_attachment(self, attachment: Attachment) -> int:
        """
        Save attachment record and return ID.
        
        Args:
            attachment: Attachment object to save
            
        Returns:
            Attachment ID
        """
        with self.write_lock:
            cursor = self.write_conn.cursor()
            cursor.execute("""
                INSERT INTO attachments (receipt_id, filename, file_type, 
                                        drive_file_id, local_path)
                VALUES (?, ?, ?, ?, ?)
            """, (
                attachment.receipt_id,
                attachment.filename,
                attachment.file_type.value,
                attachment.drive_file_id,
                attachment.local_path
            ))
            self.write_conn.commit()
            return cursor.lastrowid
    
    def get_transactions(self, limit: int = 1000, offset: int = 0) -> List[Transaction]:
        """
        Retrieve transactions with pagination.
        
        Args:
            limit: Maximum number of records to return
            offset: Number of records to skip
            
        Returns:
            List of Transaction objects
            
        Validates Requirement: 7.3 - Support concurrent read operations
        """
        with self.read_pool.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, statement_file, transaction_date, amount, description
                FROM transactions
                ORDER BY id
                LIMIT ? OFFSET ?
            """, (limit, offset))
            
            transactions = []
            for row in cursor.fetchall():
                transactions.append(Transaction(
                    id=row['id'],
                    statement_file=row['statement_file'],
                    transaction_date=date.fromisoformat(row['transaction_date']),
                    amount=Decimal(str(row['amount'])),
                    description=row['description']
                ))
            
            return transactions
    
    def get_receipts(self, limit: int = 1000, offset: int = 0) -> List[Receipt]:
        """
        Retrieve receipts with pagination.
        
        Args:
            limit: Maximum number of records to return
            offset: Number of records to skip
            
        Returns:
            List of Receipt objects
            
        Validates Requirement: 7.3 - Support concurrent read operations
        """
        with self.read_pool.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, source, receipt_date, amount, description, 
                       is_financial, filter_method
                FROM receipts
                ORDER BY id
                LIMIT ? OFFSET ?
            """, (limit, offset))
            
            receipts = []
            for row in cursor.fetchall():
                receipts.append(Receipt(
                    id=row['id'],
                    source=row['source'],
                    receipt_date=date.fromisoformat(row['receipt_date']),
                    amount=Decimal(str(row['amount'])) if row['amount'] else None,
                    description=row['description'],
                    is_financial=bool(row['is_financial']),
                    filter_method=FilterMethod(row['filter_method']) if row['filter_method'] else None,
                    attachments=[]
                ))
            
            return receipts
    
    def execute_transaction(self, operations: List[Any]):
        """
        Execute multiple operations in a single transaction.
        
        Args:
            operations: List of callable operations to execute
            
        Validates Requirement: 7.5 - Ensure atomicity by committing or rolling back all operations together
        """
        with self.write_lock:
            try:
                self.write_conn.execute("BEGIN TRANSACTION")
                
                for operation in operations:
                    operation()
                
                self.write_conn.execute("COMMIT")
                logger.debug(f"Transaction committed successfully ({len(operations)} operations)")
                
            except Exception as e:
                self.write_conn.execute("ROLLBACK")
                logger.error(f"Transaction rolled back due to error: {e}")
                raise
    
    def close(self):
        """Close all database connections."""
        self.write_conn.close()
        self.read_pool.close_all()
        logger.info("Database connections closed")
