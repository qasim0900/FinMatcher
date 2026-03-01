"""
Data models for FinMatcher system.

This module defines data classes for transactions, receipts, and processed emails.

Validates Requirements: 6.1, 6.2
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List
from decimal import Decimal


@dataclass
class Transaction:
    """
    Represents a transaction from a bank statement.
    
    Validates Requirement 6.1: Data structure for statement transactions
    """
    transaction_id: str
    date: str  # YYYY-MM-DD format
    description: str
    amount: Decimal
    status: str = "UNMATCHED"  # MATCHED or UNMATCHED
    label: Optional[str] = None  # Unique identifier (e.g., "Amex_001")
    receipt_source: Optional[str] = None  # Email link or file path
    reference_number: Optional[str] = None
    transaction_type: str = "debit"  # debit or credit
    balance: Optional[Decimal] = None
    statement_name: Optional[str] = None  # e.g., "Meriwest", "Amex", "Chase"
    
    def __post_init__(self):
        """Validate and normalize data after initialization."""
        # Ensure amount is Decimal
        if not isinstance(self.amount, Decimal):
            self.amount = Decimal(str(self.amount))
        
        # Ensure balance is Decimal if provided
        if self.balance is not None and not isinstance(self.balance, Decimal):
            self.balance = Decimal(str(self.balance))
    
    def to_dict(self) -> dict:
        """Convert to dictionary for database storage."""
        return {
            'transaction_id': self.transaction_id,
            'date': self.date,
            'description': self.description,
            'amount': float(self.amount),
            'status': self.status,
            'label': self.label,
            'receipt_source': self.receipt_source,
            'reference_number': self.reference_number,
            'transaction_type': self.transaction_type,
            'balance': float(self.balance) if self.balance else None,
            'statement_name': self.statement_name
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Transaction':
        """Create Transaction from dictionary."""
        return cls(
            transaction_id=data['transaction_id'],
            date=data['date'],
            description=data['description'],
            amount=Decimal(str(data['amount'])),
            status=data.get('status', 'UNMATCHED'),
            label=data.get('label'),
            receipt_source=data.get('receipt_source'),
            reference_number=data.get('reference_number'),
            transaction_type=data.get('transaction_type', 'debit'),
            balance=Decimal(str(data['balance'])) if data.get('balance') else None,
            statement_name=data.get('statement_name')
        )


@dataclass
class Receipt:
    """
    Represents a receipt extracted from an email.
    
    Validates Requirement 6.1: Data structure for email receipts
    """
    receipt_id: str
    email_id: str
    sender_name: str
    sender_email: str
    subject: str
    received_date: str  # YYYY-MM-DD format
    amount: Optional[Decimal] = None
    transaction_date: Optional[str] = None  # YYYY-MM-DD format
    merchant_name: Optional[str] = None
    attachment_path: Optional[str] = None
    email_link: Optional[str] = None
    receiver_email: Optional[str] = None
    source: str = "email_body"  # "email_body" or "attachment"
    extracted_text: Optional[str] = None
    confidence_score: Optional[float] = None
    is_financial: bool = True
    matched_transaction_id: Optional[str] = None
    
    def __post_init__(self):
        """Validate and normalize data after initialization."""
        # Ensure amount is Decimal if provided
        if self.amount is not None and not isinstance(self.amount, Decimal):
            self.amount = Decimal(str(self.amount))
    
    def to_dict(self) -> dict:
        """Convert to dictionary for database storage."""
        return {
            'receipt_id': self.receipt_id,
            'email_id': self.email_id,
            'sender_name': self.sender_name,
            'sender_email': self.sender_email,
            'subject': self.subject,
            'received_date': self.received_date,
            'amount': float(self.amount) if self.amount else None,
            'transaction_date': self.transaction_date,
            'merchant_name': self.merchant_name,
            'attachment_path': self.attachment_path,
            'email_link': self.email_link,
            'receiver_email': self.receiver_email,
            'source': self.source,
            'extracted_text': self.extracted_text,
            'confidence_score': self.confidence_score,
            'is_financial': self.is_financial,
            'matched_transaction_id': self.matched_transaction_id
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Receipt':
        """Create Receipt from dictionary."""
        return cls(
            receipt_id=data['receipt_id'],
            email_id=data['email_id'],
            sender_name=data['sender_name'],
            sender_email=data['sender_email'],
            subject=data['subject'],
            received_date=data['received_date'],
            amount=Decimal(str(data['amount'])) if data.get('amount') else None,
            transaction_date=data.get('transaction_date'),
            merchant_name=data.get('merchant_name'),
            attachment_path=data.get('attachment_path'),
            email_link=data.get('email_link'),
            receiver_email=data.get('receiver_email'),
            source=data.get('source', 'email_body'),
            extracted_text=data.get('extracted_text'),
            confidence_score=data.get('confidence_score'),
            is_financial=data.get('is_financial', True),
            matched_transaction_id=data.get('matched_transaction_id')
        )


@dataclass
class ProcessedEmail:
    """
    Represents a processed email for deduplication tracking.
    
    Updated to work with new schema (message_id is primary key)
    """
    message_id: str
    processed_timestamp: datetime
    account_email: str
    email_id: str = ""  # Optional, for backward compatibility
    md5_hash: str = ""  # Optional, for backward compatibility
    folder: str = "INBOX"
    has_attachments: bool = False
    is_financial: bool = False
    subject: str = ""
    sender: str = ""
    
    def to_dict(self) -> dict:
        """Convert to dictionary for database storage."""
        return {
            'email_id': self.email_id,
            'message_id': self.message_id,
            'md5_hash': self.md5_hash,
            'processed_timestamp': self.processed_timestamp.isoformat(),
            'account_email': self.account_email,
            'folder': self.folder,
            'has_attachments': self.has_attachments,
            'is_financial': self.is_financial,
            'subject': self.subject,
            'sender': self.sender
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'ProcessedEmail':
        """Create ProcessedEmail from dictionary."""
        return cls(
            message_id=data['message_id'],
            processed_timestamp=datetime.fromisoformat(data['processed_timestamp']),
            account_email=data['account_email'],
            email_id=data.get('email_id', ''),
            md5_hash=data.get('md5_hash', ''),
            folder=data.get('folder', 'INBOX'),
            has_attachments=data.get('has_attachments', False),
            is_financial=data.get('is_financial', False),
            subject=data.get('subject', ''),
            sender=data.get('sender', '')
        )


@dataclass
class Match:
    """
    Represents a match between a transaction and a receipt.
    
    Used for tracking matching results and statistics.
    """
    match_id: str
    transaction_id: str
    receipt_id: str
    match_stage: str  # "exact", "fuzzy", or "semantic"
    confidence_score: float  # 0.0 to 1.0
    amount_match_score: float = 0.0
    date_match_score: float = 0.0
    semantic_match_score: float = 0.0
    matched_at: Optional[datetime] = None
    
    def __post_init__(self):
        """Set matched_at to current time if not provided."""
        if self.matched_at is None:
            self.matched_at = datetime.now()
    
    def to_dict(self) -> dict:
        """Convert to dictionary for database storage."""
        return {
            'match_id': self.match_id,
            'transaction_id': self.transaction_id,
            'receipt_id': self.receipt_id,
            'match_stage': self.match_stage,
            'confidence_score': self.confidence_score,
            'amount_match_score': self.amount_match_score,
            'date_match_score': self.date_match_score,
            'semantic_match_score': self.semantic_match_score,
            'matched_at': self.matched_at.isoformat() if self.matched_at else None
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Match':
        """Create Match from dictionary."""
        return cls(
            match_id=data['match_id'],
            transaction_id=data['transaction_id'],
            receipt_id=data['receipt_id'],
            match_stage=data['match_stage'],
            confidence_score=data['confidence_score'],
            amount_match_score=data.get('amount_match_score', 0.0),
            date_match_score=data.get('date_match_score', 0.0),
            semantic_match_score=data.get('semantic_match_score', 0.0),
            matched_at=datetime.fromisoformat(data['matched_at']) if data.get('matched_at') else None
        )


@dataclass
class MatchingStatistics:
    """
    Statistics for matching operations.
    
    Used for logging and reporting.
    """
    total_transactions: int = 0
    total_receipts: int = 0
    exact_matches: int = 0
    fuzzy_matches: int = 0
    semantic_matches: int = 0
    unmatched_transactions: int = 0
    unmatched_receipts: int = 0
    average_confidence_score: float = 0.0
    processing_time_seconds: float = 0.0
    
    @property
    def total_matches(self) -> int:
        """Total number of matches across all stages."""
        return self.exact_matches + self.fuzzy_matches + self.semantic_matches
    
    @property
    def match_rate(self) -> float:
        """Percentage of transactions that were matched."""
        if self.total_transactions == 0:
            return 0.0
        return (self.total_matches / self.total_transactions) * 100
    
    def to_dict(self) -> dict:
        """Convert to dictionary for logging."""
        return {
            'Total Transactions': self.total_transactions,
            'Total Receipts': self.total_receipts,
            'Exact Matches': self.exact_matches,
            'Fuzzy Matches': self.fuzzy_matches,
            'Semantic Matches': self.semantic_matches,
            'Total Matches': self.total_matches,
            'Unmatched Transactions': self.unmatched_transactions,
            'Unmatched Receipts': self.unmatched_receipts,
            'Match Rate': f"{self.match_rate:.2f}%",
            'Average Confidence Score': self.average_confidence_score,
            'Processing Time': f"{self.processing_time_seconds:.2f}s"
        }
