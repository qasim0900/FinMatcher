"""
Data models for FinMatcher v2.1 Mathematical Performance Optimization.

This module defines dataclasses for FeatureVector and NormalizationParams
used in spatial indexing and geometric nearest neighbor search.

Validates Requirements: 1.4, 10.11
"""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
import numpy as np


@dataclass
class FeatureVector:
    """
    Normalized feature representation for spatial indexing.
    
    Represents normalized coordinates of receipts in [0,1]^2 unit space
    for geometric indexing. Used by the Spatial Indexer component for
    K-D tree construction and nearest neighbor queries.
    
    Attributes:
        amount_normalized: Amount mapped to [0,1] via min-max scaling
        date_normalized: Date mapped to [0,1] via min-max scaling
        receipt_id: Original receipt identifier for lookup
        original_amount: Raw amount value (for denormalization)
        original_date: Raw date value (for denormalization)
    
    Validates Requirements: 1.4, 10.11
    """
    amount_normalized: float  # [0, 1]
    date_normalized: float    # [0, 1]
    receipt_id: int
    original_amount: Decimal
    original_date: date
    
    def to_array(self) -> np.ndarray:
        """
        Convert to NumPy array for K-D tree operations.
        
        Returns:
            NumPy array of shape (2,) containing [amount_norm, date_norm]
        
        Example:
            >>> fv = FeatureVector(0.5, 0.75, 1, Decimal("100.00"), date(2024, 1, 1))
            >>> fv.to_array()
            array([0.5, 0.75])
        """
        return np.array([self.amount_normalized, self.date_normalized])
    
    def __str__(self) -> str:
        """
        Pretty print for debugging and validation.
        
        Returns:
            Human-readable string representation showing both normalized
            and original values for easy debugging.
        
        Example:
            >>> fv = FeatureVector(0.5, 0.75, 1, Decimal("100.00"), date(2024, 1, 1))
            >>> print(fv)
            FeatureVector(id=1, amount=100.00 -> 0.5000, date=2024-01-01 -> 0.7500)
        """
        return (f"FeatureVector(id={self.receipt_id}, "
                f"amount={self.original_amount} -> {self.amount_normalized:.4f}, "
                f"date={self.original_date} -> {self.date_normalized:.4f})")


@dataclass
class NormalizationParams:
    """
    Parameters for min-max normalization and denormalization.
    
    Stores min/max values for min-max scaling transformations used to
    map receipt amounts and dates to [0,1] unit space. These parameters
    are calculated during K-D tree construction and used for normalizing
    query points at search time.
    
    Attributes:
        amount_min: Minimum amount in dataset
        amount_max: Maximum amount in dataset
        date_min: Minimum date in dataset (Unix timestamp)
        date_max: Maximum date in dataset (Unix timestamp)
        dataset_hash: SHA-256 hash for cache validation
    
    Validates Requirements: 1.4, 10.11
    """
    amount_min: Decimal
    amount_max: Decimal
    date_min: int  # Unix timestamp
    date_max: int  # Unix timestamp
    dataset_hash: str
    
    def normalize_amount(self, amount: Decimal) -> float:
        """
        Map amount to [0,1] using stored min/max.
        
        Applies min-max scaling formula: x_norm = (x - x_min) / (x_max - x_min)
        
        Args:
            amount: Raw amount value to normalize
        
        Returns:
            Normalized amount in [0,1] range
        
        Example:
            >>> params = NormalizationParams(
            ...     Decimal("0"), Decimal("100"), 0, 100, "hash"
            ... )
            >>> params.normalize_amount(Decimal("50"))
            0.5
        """
        if self.amount_max == self.amount_min:
            return 0.5  # Handle edge case of single value
        return float((amount - self.amount_min) / 
                    (self.amount_max - self.amount_min))
    
    def normalize_date(self, date_val: date) -> float:
        """
        Map date to [0,1] using stored min/max.
        
        Converts date to Unix timestamp and applies min-max scaling.
        
        Args:
            date_val: Raw date value to normalize
        
        Returns:
            Normalized date in [0,1] range
        
        Example:
            >>> from datetime import date, datetime
            >>> params = NormalizationParams(
            ...     Decimal("0"), Decimal("100"),
            ...     int(datetime.combine(date(2024, 1, 1), datetime.min.time()).timestamp()),
            ...     int(datetime.combine(date(2024, 12, 31), datetime.min.time()).timestamp()),
            ...     "hash"
            ... )
            >>> params.normalize_date(date(2024, 7, 1))  # Mid-year
            # Returns value close to 0.5
        """
        from datetime import datetime
        timestamp = int(datetime.combine(date_val, datetime.min.time()).timestamp())
        if self.date_max == self.date_min:
            return 0.5  # Handle edge case of single value
        return (timestamp - self.date_min) / (self.date_max - self.date_min)
