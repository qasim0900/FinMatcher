"""
Data models and enums for FinMatcher v2.0 Enterprise Upgrade.

This module defines dataclasses for Transaction, Receipt, Attachment, MatchResult,
MatchingConfig, FolderStructure, and Checkpoint, along with enums for MatchConfidence,
AttachmentType, and FilterMethod.

Validates Requirements: 1.1, 1.6, 1.7, 1.8, 5.1, 5.2, 5.3, 13.1
"""

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from enum import Enum
from typing import Optional, List, Dict


class MatchConfidence(Enum):
    """
    Match confidence levels based on composite score thresholds.
    
    Validates Requirements: 1.6, 1.7, 1.8
    """
    EXACT = "exact"        # Composite score >= 0.98
    HIGH = "high"          # Composite score >= 0.85 and < 0.98
    LOW = "low"            # Composite score < 0.85


class AttachmentType(Enum):
    """
    Attachment file type classification.
    
    Validates Requirements: 5.1, 5.2, 5.3
    """
    DOCUMENT = "document"  # PDF, DOC, DOCX
    IMAGE = "image"        # JPG, JPEG, PNG, GIF


class FilterMethod(Enum):
    """
    Financial email filtering method used.
    
    Validates Requirement: 13.1
    """
    AUTO_REJECT = "auto_reject"    # Rejected by marketing/spam keywords
    AUTO_ACCEPT = "auto_accept"    # Accepted by financial keywords
    AI_VERIFIED = "ai_verified"    # Verified by DeepSeek AI


@dataclass
class Transaction:
    """
    Represents a financial transaction from a bank or credit card statement.
    
    Validates Requirement: 1.1
    """
    id: Optional[int]
    statement_file: str
    transaction_date: date
    amount: Decimal
    description: str
    
    def __post_init__(self):
        """Validate and normalize data after initialization."""
        if not isinstance(self.amount, Decimal):
            self.amount = Decimal(str(self.amount))


@dataclass
class Attachment:
    """
    Represents a file attachment from a receipt email.
    
    Validates Requirements: 5.1, 5.2, 5.3
    """
    id: Optional[int]
    receipt_id: int
    filename: str
    file_type: AttachmentType
    drive_file_id: Optional[str]
    local_path: str


@dataclass
class Receipt:
    """
    Represents a financial document (email, PDF, image) representing proof of purchase.
    
    Validates Requirements: 1.1, 13.1
    """
    id: Optional[int]
    source: str  # 'email' or 'manual'
    receipt_date: date
    amount: Optional[Decimal]
    description: str
    is_financial: bool
    filter_method: Optional[FilterMethod]
    attachments: List[Attachment] = field(default_factory=list)
    
    def __post_init__(self):
        """Validate and normalize data after initialization."""
        if self.amount is not None and not isinstance(self.amount, Decimal):
            self.amount = Decimal(str(self.amount))


@dataclass
class MatchResult:
    """
    Represents the result of matching a transaction with a receipt.
    
    Validates Requirements: 1.1, 1.6, 1.7, 1.8
    """
    transaction: Transaction
    receipt: Receipt
    amount_score: float
    date_score: float
    semantic_score: float
    composite_score: float
    confidence: MatchConfidence


@dataclass
class MatchingConfig:
    """
    Configuration parameters for the matching engine.
    
    Validates Requirements: 12.1, 12.2, 12.3, 12.4, 12.5, 12.6
    """
    weight_amount: float
    weight_date: float
    weight_semantic: float
    amount_tolerance: Decimal
    date_variance: int
    exact_threshold: float
    high_threshold: float
    lambda_decay: float
    
    def __post_init__(self):
        """Validate configuration parameters."""
        if not isinstance(self.amount_tolerance, Decimal):
            self.amount_tolerance = Decimal(str(self.amount_tolerance))
        
        # Validate weights sum to 1.0 (within tolerance)
        total = self.weight_amount + self.weight_date + self.weight_semantic
        if abs(total - 1.0) > 0.001:
            raise ValueError(f"Weights must sum to 1.0, got {total}")


@dataclass
class FolderStructure:
    """
    Google Drive folder hierarchy structure.
    
    Validates Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 3.8
    """
    root_id: str
    statement_folders: Dict[str, str]  # statement_name -> folder_id
    other_receipts_id: str
    unmatch_email_id: str
    attach_files_id: str
    attach_image_id: str
    unmatch_attach_files_id: str
    unmatch_attach_image_id: str


@dataclass
class Checkpoint:
    """
    Checkpoint data for crash recovery and resume capability.
    
    Validates Requirements: 8.1, 8.2, 8.3
    """
    last_transaction_id: int
    last_receipt_id: int
    timestamp: date
