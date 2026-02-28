"""
Unit tests for VectorizedScorer.score_batch() method.

Validates Requirements: 2.1, 2.10, 2.11
"""

import pytest
import numpy as np
from datetime import date, datetime
from decimal import Decimal
from finmatcher.optimization.vectorized_scorer import VectorizedScorer
from finmatcher.storage.models import MatchingConfig


class MockTransaction:
    """Mock transaction for testing."""
    def __init__(self, amount, transaction_date, description):
        self.amount = Decimal(str(amount))
        self.transaction_date = transaction_date
        self.description = description


class MockReceipt:
    """Mock receipt for testing."""
    def __init__(self, amount, receipt_date, description):
        self.amount = Decimal(str(amount)) if amount is not None else None
        self.receipt_date = receipt_date
        self.description = description


def test_score_batch_returns_correct_shape():
    """
    Test that score_batch returns a 2D array with shape (N, M).
    
    Validates Requirements:
    - 2.11: Return a 2D NumPy_Array of shape (N_transactions, M_receipts)
    """
    # Create mock config
    config = MatchingConfig(
        weight_amount=0.4,
        weight_date=0.3,
        weight_semantic=0.3,
        amount_tolerance=Decimal("10.0"),
        date_variance=30,
        exact_threshold=0.98,
        high_threshold=0.85,
        lambda_decay=0.1
    )
    config.date_tolerance_days = 30  # Add custom attribute for testing
    
    scorer = VectorizedScorer(config, deepseek_client=None, batch_size=100000)
    
    # Create test data
    transactions = [
        MockTransaction(100.0, date(2024, 1, 15), "Coffee shop"),
        MockTransaction(50.0, date(2024, 1, 16), "Gas station"),
        MockTransaction(200.0, date(2024, 1, 17), "Restaurant"),
    ]
    
    receipts = [
        MockReceipt(100.0, date(2024, 1, 15), "Starbucks"),
        MockReceipt(50.0, date(2024, 1, 16), "Shell"),
    ]
    
    # Call score_batch
    scores = scorer.score_batch(transactions, receipts)
    
    # Verify shape
    assert scores.shape == (3, 2), f"Expected shape (3, 2), got {scores.shape}"
    assert isinstance(scores, np.ndarray), "Expected NumPy array"


def test_score_batch_values_in_valid_range():
    """
    Test that score_batch returns scores in valid range [0, 1].
    
    Validates Requirements:
    - 2.1: Convert transaction and receipt data to NumPy_Array structures
    - 2.10: Process transaction-receipt pairs in a single vectorized operation
    """
    config = MatchingConfig(
        weight_amount=0.4,
        weight_date=0.3,
        weight_semantic=0.3,
        amount_tolerance=Decimal("10.0"),
        date_variance=30,
        exact_threshold=0.98,
        high_threshold=0.85,
        lambda_decay=0.1
    )
    config.date_tolerance_days = 30  # Add custom attribute for testing
    
    scorer = VectorizedScorer(config, deepseek_client=None, batch_size=100000)
    
    transactions = [
        MockTransaction(100.0, date(2024, 1, 15), "Test transaction"),
    ]
    
    receipts = [
        MockReceipt(100.0, date(2024, 1, 15), "Test receipt"),
    ]
    
    scores = scorer.score_batch(transactions, receipts)
    
    # Verify all scores are in valid range
    assert np.all(scores >= 0), "All scores should be >= 0"
    assert np.all(scores <= 1), "All scores should be <= 1"


def test_score_batch_perfect_match_high_score():
    """
    Test that identical transaction and receipt produce high composite score.
    
    Validates Requirements:
    - 2.9: Calculate composite scores using Broadcasting with weighted sum
    """
    config = MatchingConfig(
        weight_amount=0.4,
        weight_date=0.3,
        weight_semantic=0.3,
        amount_tolerance=Decimal("10.0"),
        date_variance=30,
        exact_threshold=0.98,
        high_threshold=0.85,
        lambda_decay=0.1
    )
    config.date_tolerance_days = 30  # Add custom attribute for testing
    
    scorer = VectorizedScorer(config, deepseek_client=None, batch_size=100000)
    
    # Create identical transaction and receipt
    transactions = [
        MockTransaction(100.0, date(2024, 1, 15), "Coffee"),
    ]
    
    receipts = [
        MockReceipt(100.0, date(2024, 1, 15), "Coffee"),
    ]
    
    scores = scorer.score_batch(transactions, receipts)
    
    # Perfect match on amount and date should give high score
    # Amount score: exp(-0.1 * 0) = 1.0
    # Date score: max(0, 1 - 0/30) = 1.0
    # Semantic score: 0 (no client)
    # Composite: 0.4 * 1.0 + 0.3 * 1.0 + 0.3 * 0 = 0.7
    assert scores[0, 0] >= 0.6, f"Expected high score for perfect match, got {scores[0, 0]}"


def test_score_batch_empty_inputs():
    """
    Test that score_batch handles empty inputs gracefully.
    
    Validates Requirements:
    - 2.1: Convert transaction and receipt data to NumPy_Array structures
    """
    config = MatchingConfig(
        weight_amount=0.4,
        weight_date=0.3,
        weight_semantic=0.3,
        amount_tolerance=Decimal("10.0"),
        date_variance=30,
        exact_threshold=0.98,
        high_threshold=0.85,
        lambda_decay=0.1
    )
    config.date_tolerance_days = 30  # Add custom attribute for testing
    
    scorer = VectorizedScorer(config, deepseek_client=None, batch_size=100000)
    
    # Test with empty lists
    scores = scorer.score_batch([], [])
    
    assert scores.shape == (0, 0), f"Expected shape (0, 0), got {scores.shape}"


def test_score_batch_large_dataset():
    """
    Test that score_batch can handle large datasets efficiently.
    
    Validates Requirements:
    - 2.10: Process 100,000 transaction-receipt pairs in a single vectorized operation
    """
    config = MatchingConfig(
        weight_amount=0.4,
        weight_date=0.3,
        weight_semantic=0.3,
        amount_tolerance=Decimal("10.0"),
        date_variance=30,
        exact_threshold=0.98,
        high_threshold=0.85,
        lambda_decay=0.1
    )
    config.date_tolerance_days = 30  # Add custom attribute for testing
    
    scorer = VectorizedScorer(config, deepseek_client=None, batch_size=100000)
    
    # Create larger dataset (100 x 100 = 10,000 pairs)
    transactions = [
        MockTransaction(100.0 + i, date(2024, 1, 15), f"Transaction {i}")
        for i in range(100)
    ]
    
    receipts = [
        MockReceipt(100.0 + j, date(2024, 1, 15), f"Receipt {j}")
        for j in range(100)
    ]
    
    scores = scorer.score_batch(transactions, receipts)
    
    assert scores.shape == (100, 100), f"Expected shape (100, 100), got {scores.shape}"
    assert isinstance(scores, np.ndarray), "Expected NumPy array"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
