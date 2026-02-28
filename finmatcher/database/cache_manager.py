"""
PostgreSQL-based cache manager for progress tracking and resumability.

This module provides database operations for tracking processed emails,
transactions, receipts, and matches using PostgreSQL.

Validates Requirements: 6.1, 6.2, 6.3, 6.4
"""

import psycopg2
from psycopg2.extras import execute_values, RealDictCursor
import hashlib
import os
from pathlib import Path
from typing import Optional, List, Set, Dict
from datetime import datetime
from contextlib import contextmanager

from database.models import ProcessedEmail, Transaction, Receipt, Match


class CacheManager:
    """
    PostgreSQL-based cache manager for progress tracking.
    
    Provides:
    - Email deduplication using MD5 hashes
    - Progress persistence with transaction support
    - Fast lookups for processed emails
    
    Validates Requirements:
    - 6.1: Initialize PostgreSQL database connection
    - 6.2: Store email Message-ID hash
    - 6.3: Skip emails already in database
    - 6.4: Commit transactions to persist progress
    """
    
    def __init__(self, db_url: Optional[str] = None):
        """
        Initialize the cache manager.
        
        Args:
            db_url: PostgreSQL connection URL (defaults to DATABASE_URL from env)
            
        Validates Requirement 6.1: Initialize PostgreSQL database connection
        """
        self.db_url = db_url or os.getenv('DATABASE_URL')
        if not self.db_url:
            raise ValueError("DATABASE_URL not found in environment variables")
        
        self._init_database()
    
    def _init_database(self):
        """
        Initialize database schema.
        
        Creates tables for:
        - processed_emails: Track processed emails for deduplication
        - transactions_cache: Store statement transactions
        - receipts_cache: Store email receipts
        - matches_cache: Store matching results
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Table for processed emails (deduplication)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS processed_emails (
                    email_id TEXT PRIMARY KEY,
                    message_id TEXT NOT NULL,
                    md5_hash TEXT NOT NULL UNIQUE,
                    processed_timestamp TIMESTAMP NOT NULL,
                    account_email TEXT NOT NULL,
                    folder TEXT DEFAULT 'INBOX',
                    has_attachments BOOLEAN DEFAULT FALSE,
                    is_financial BOOLEAN DEFAULT FALSE
                )
            ''')
            
            # Index on md5_hash for fast lookups
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_md5_hash 
                ON processed_emails(md5_hash)
            ''')
            
            # Table for transactions cache
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS transactions_cache (
                    transaction_id TEXT PRIMARY KEY,
                    date TEXT NOT NULL,
                    description TEXT NOT NULL,
                    amount DECIMAL(10,2) NOT NULL,
                    status TEXT DEFAULT 'UNMATCHED',
                    label TEXT,
                    receipt_source TEXT,
                    reference_number TEXT,
                    transaction_type TEXT DEFAULT 'debit',
                    balance DECIMAL(10,2),
                    statement_name TEXT
                )
            ''')
            
            # Table for receipts cache
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS receipts_cache (
                    receipt_id TEXT PRIMARY KEY,
                    email_id TEXT NOT NULL,
                    sender_name TEXT NOT NULL,
                    sender_email TEXT NOT NULL,
                    subject TEXT NOT NULL,
                    received_date TEXT NOT NULL,
                    amount DECIMAL(10,2),
                    transaction_date TEXT,
                    merchant_name TEXT,
                    attachment_path TEXT,
                    email_link TEXT,
                    receiver_email TEXT,
                    source TEXT DEFAULT 'email_body',
                    extracted_text TEXT,
                    confidence_score DECIMAL(5,4),
                    is_financial BOOLEAN DEFAULT TRUE,
                    matched_transaction_id TEXT
                )
            ''')
            
            # Table for matches cache
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS matches_cache (
                    match_id TEXT PRIMARY KEY,
                    transaction_id TEXT NOT NULL,
                    receipt_id TEXT NOT NULL,
                    match_stage TEXT NOT NULL,
                    confidence_score DECIMAL(5,4) NOT NULL,
                    amount_match_score DECIMAL(5,4) DEFAULT 0.0,
                    date_match_score DECIMAL(5,4) DEFAULT 0.0,
                    semantic_match_score DECIMAL(5,4) DEFAULT 0.0,
                    matched_at TIMESTAMP
                )
            ''')
            
            conn.commit()
    
    @contextmanager
    def _get_connection(self):
        """
        Context manager for database connections.
        
        Ensures connections are properly closed.
        """
        conn = psycopg2.connect(self.db_url)
        try:
            yield conn
        finally:
            conn.close()
    
    @staticmethod
    def calculate_md5_hash(message_id: str) -> str:
        """
        Calculate MD5 hash of Message-ID for deduplication.
        
        Args:
            message_id: Email Message-ID header
            
        Returns:
            MD5 hash as hex string
            
        Validates Requirement 1.4: Calculate MD5 hash of Message-ID
        """
        return hashlib.md5(message_id.encode('utf-8')).hexdigest()
    
    def is_email_processed(self, message_id: str) -> bool:
        """
        Check if an email has already been processed.
        
        Args:
            message_id: Email Message-ID header
            
        Returns:
            True if email was already processed, False otherwise
            
        Validates Requirement 6.3: Skip emails with Message-IDs already in database
        """
        md5_hash = self.calculate_md5_hash(message_id)
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'SELECT 1 FROM processed_emails WHERE md5_hash = %s LIMIT 1',
                (md5_hash,)
            )
            return cursor.fetchone() is not None
    
    def mark_email_processed(self, processed_email: ProcessedEmail) -> bool:
        """
        Mark an email as processed.
        
        Args:
            processed_email: ProcessedEmail object
            
        Returns:
            True if successful, False otherwise
            
        Validates Requirement 6.2: Store Message-ID hash in database
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO processed_emails 
                    (email_id, message_id, md5_hash, processed_timestamp, 
                     account_email, folder, has_attachments, is_financial)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (email_id) DO UPDATE SET
                        processed_timestamp = EXCLUDED.processed_timestamp
                ''', (
                    processed_email.email_id,
                    processed_email.message_id,
                    processed_email.md5_hash,
                    processed_email.processed_timestamp,
                    processed_email.account_email,
                    processed_email.folder,
                    processed_email.has_attachments,
                    processed_email.is_financial
                ))
                conn.commit()
                return True
        except psycopg2.Error as e:
            print(f"Error marking email as processed: {e}")
            return False
    
    def mark_emails_processed_batch(self, processed_emails: List[ProcessedEmail]) -> bool:
        """
        Mark multiple emails as processed in a single transaction (optimized).
        
        Args:
            processed_emails: List of ProcessedEmail objects
            
        Returns:
            True if successful, False otherwise
        """
        if not processed_emails:
            return True
        
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Prepare batch data
                batch_data = [
                    (
                        email.email_id,
                        email.message_id,
                        email.md5_hash,
                        email.processed_timestamp,
                        email.account_email,
                        email.folder,
                        email.has_attachments,
                        email.is_financial
                    )
                    for email in processed_emails
                ]
                
                # Execute batch insert using execute_values for better performance
                execute_values(
                    cursor,
                    '''
                    INSERT INTO processed_emails 
                    (email_id, message_id, md5_hash, processed_timestamp, 
                     account_email, folder, has_attachments, is_financial)
                    VALUES %s
                    ON CONFLICT (email_id) DO UPDATE SET
                        processed_timestamp = EXCLUDED.processed_timestamp
                    ''',
                    batch_data
                )
                
                conn.commit()
                return True
        except psycopg2.Error as e:
            print(f"Error marking emails as processed (batch): {e}")
            return False
    
    def get_processed_email_count(self) -> int:
        """
        Get total count of processed emails.
        
        Returns:
            Number of processed emails
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM processed_emails')
            return cursor.fetchone()[0]
    
    def save_transaction(self, transaction: Transaction) -> bool:
        """
        Save a transaction to the database.
        
        Args:
            transaction: Transaction object
            
        Returns:
            True if successful, False otherwise
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                data = transaction.to_dict()
                cursor.execute('''
                    INSERT INTO transactions_cache 
                    (transaction_id, date, description, amount, status, label, 
                     receipt_source, reference_number, transaction_type, balance, statement_name)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (transaction_id) DO UPDATE SET
                        status = EXCLUDED.status,
                        label = EXCLUDED.label,
                        receipt_source = EXCLUDED.receipt_source
                ''', (
                    data['transaction_id'], data['date'], data['description'],
                    data['amount'], data['status'], data['label'],
                    data['receipt_source'], data['reference_number'],
                    data['transaction_type'], data['balance'], data['statement_name']
                ))
                conn.commit()
                return True
        except psycopg2.Error as e:
            print(f"Error saving transaction: {e}")
            return False
    
    def save_receipt(self, receipt: Receipt) -> bool:
        """
        Save a receipt to the database.
        
        Args:
            receipt: Receipt object
            
        Returns:
            True if successful, False otherwise
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                data = receipt.to_dict()
                cursor.execute('''
                    INSERT INTO receipts_cache 
                    (receipt_id, email_id, sender_name, sender_email, subject, 
                     received_date, amount, transaction_date, merchant_name, 
                     attachment_path, email_link, receiver_email, source, 
                     extracted_text, confidence_score, is_financial, matched_transaction_id)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (receipt_id) DO UPDATE SET
                        matched_transaction_id = EXCLUDED.matched_transaction_id
                ''', (
                    data['receipt_id'], data['email_id'], data['sender_name'],
                    data['sender_email'], data['subject'], data['received_date'],
                    data['amount'], data['transaction_date'], data['merchant_name'],
                    data['attachment_path'], data['email_link'], data['receiver_email'],
                    data['source'], data['extracted_text'], data['confidence_score'],
                    data['is_financial'], data['matched_transaction_id']
                ))
                conn.commit()
                return True
        except psycopg2.Error as e:
            print(f"Error saving receipt: {e}")
            return False
    
    def save_match(self, match: Match) -> bool:
        """
        Save a match to the database.
        
        Args:
            match: Match object
            
        Returns:
            True if successful, False otherwise
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                data = match.to_dict()
                cursor.execute('''
                    INSERT INTO matches_cache 
                    (match_id, transaction_id, receipt_id, match_stage, 
                     confidence_score, amount_match_score, date_match_score, 
                     semantic_match_score, matched_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (match_id) DO UPDATE SET
                        confidence_score = EXCLUDED.confidence_score
                ''', (
                    data['match_id'], data['transaction_id'], data['receipt_id'],
                    data['match_stage'], data['confidence_score'],
                    data['amount_match_score'], data['date_match_score'],
                    data['semantic_match_score'], data['matched_at']
                ))
                conn.commit()
                return True
        except psycopg2.Error as e:
            print(f"Error saving match: {e}")
            return False
    
    def get_unmatched_receipts(self) -> List[Receipt]:
        """
        Get all receipts that haven't been matched to transactions.
        
        Returns:
            List of unmatched Receipt objects
            
        Validates Requirement 8.1: Query cache for emails not linked to transactions
        """
        receipts = []
        with self._get_connection() as conn:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            cursor.execute('''
                SELECT * FROM receipts_cache 
                WHERE matched_transaction_id IS NULL 
                AND is_financial = TRUE
            ''')
            
            for row in cursor.fetchall():
                receipts.append(Receipt.from_dict(dict(row)))
        
        return receipts
    
    def get_all_receipts(self) -> List[Dict]:
        """
        Get all receipts from cache.
        
        Returns:
            List of receipt dictionaries
        """
        receipts = []
        with self._get_connection() as conn:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            cursor.execute('SELECT * FROM receipts_cache')
            
            for row in cursor.fetchall():
                row_dict = dict(row)
                receipts.append({
                    'sender_name': row_dict.get('sender_name', ''),
                    'sender_email': row_dict.get('sender_email', ''),
                    'subject': row_dict.get('subject', ''),
                    'date': row_dict.get('received_date'),
                    'amount': row_dict.get('amount'),
                    'attachment_path': row_dict.get('attachment_path', ''),
                    'email_link': row_dict.get('email_link', ''),
                    'receiver_email': row_dict.get('receiver_email', '')
                })
        
        return receipts
    
    def get_all_transactions(self, statement_name: Optional[str] = None) -> List[Transaction]:
        """
        Get all transactions, optionally filtered by statement name.
        
        Args:
            statement_name: Optional statement name filter (e.g., "Meriwest")
            
        Returns:
            List of Transaction objects
        """
        transactions = []
        with self._get_connection() as conn:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            if statement_name:
                cursor.execute(
                    'SELECT * FROM transactions_cache WHERE statement_name = %s',
                    (statement_name,)
                )
            else:
                cursor.execute('SELECT * FROM transactions_cache')
            
            for row in cursor.fetchall():
                transactions.append(Transaction.from_dict(dict(row)))
        
        return transactions
    
    def clear_cache(self):
        """
        Clear all data from the cache (useful for testing).
        
        WARNING: This deletes all progress!
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM processed_emails')
            cursor.execute('DELETE FROM transactions_cache')
            cursor.execute('DELETE FROM receipts_cache')
            cursor.execute('DELETE FROM matches_cache')
            conn.commit()
    
    def get_statistics(self) -> dict:
        """
        Get cache statistics.
        
        Returns:
            Dictionary with counts of various entities
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute('SELECT COUNT(*) FROM processed_emails')
            processed_emails = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM transactions_cache')
            transactions = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM receipts_cache')
            receipts = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM matches_cache')
            matches = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM transactions_cache WHERE status = %s', ('MATCHED',))
            matched_transactions = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM receipts_cache WHERE matched_transaction_id IS NOT NULL')
            matched_receipts = cursor.fetchone()[0]
        
        return {
            'processed_emails': processed_emails,
            'transactions': transactions,
            'receipts': receipts,
            'matches': matches,
            'matched_transactions': matched_transactions,
            'matched_receipts': matched_receipts,
            'unmatched_transactions': transactions - matched_transactions,
            'unmatched_receipts': receipts - matched_receipts
        }
    
    def close(self):
        """Close database connection."""
        # Context manager handles connection closing
        pass
    
    def commit(self):
        """Commit any pending transactions."""
        # Context manager handles commits
        pass


# Global cache manager instance
_cache_manager: Optional[CacheManager] = None


def get_cache_manager(db_url: Optional[str] = None) -> CacheManager:
    """
    Get or create the global cache manager instance.
    
    Args:
        db_url: PostgreSQL connection URL (defaults to DATABASE_URL from env)
        
    Returns:
        CacheManager instance
    """
    global _cache_manager
    if _cache_manager is None:
        _cache_manager = CacheManager(db_url)
    return _cache_manager


def reset_cache_manager():
    """Reset the global cache manager instance (useful for testing)."""
    global _cache_manager
    _cache_manager = None
