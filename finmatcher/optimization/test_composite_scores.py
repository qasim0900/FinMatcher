"""
Unit tests for VectorizedScorer composite score calculation.

Validates Requirements: 2.9
"""

import pytest
import numpy as np
from decimal import Decimal
from finmatcher.optimization.vectorized_scorer import VectorizedScorer
from finmatcher.storage.models import MatchingConfig


def test_calculate_composite_scores_basic():
    """Test basic composite score calculation with simple inputs."""
    # Create a valid MatchingConfig
    config = MatchingConfig(
        weight_amount=0.4,
        weight_date=0.3,
        weight_semantic=0.3,
        amount_tolerance=Decimal("1.00"),
        date_variance=3,
        exact_threshold=0.98,
        high_threshold=0.85,
        lambda_decay=0.1
    )
    
    # Initialize VectorizedScorer
    scorer = VectorizedScorer(config)
    
    # Create test score arrays (2x3 matrix)
    amount_scores = np.array([[0.9, 0.8, 0.7], [0.6, 0.5, 0.4]])
    date_scores = np.array([[1.0, 0.9, 0.8], [0.7, 0.6, 0.5]])
    semantic_scores = np.array([[0.8, 0.7, 0.6], [0.5, 0.4, 0.3]])
    
    # Calculate composite scores
    composite = scorer._calculate_composite_scores(amount_scores, date_scores, semantic_scores)
    
    # Verify shape
    assert composite.shape == (2, 3), f"Expected shape (2, 3), got {composite.shape}"
    
    # Verify values using the formula: w_a * S_a + w_d * S_d + w_s * S_s
    # For [0,0]: 0.4 * 0.9 + 0.3 * 1.0 + 0.3 * 0.8 = 0.36 + 0.3 + 0.24 = 0.9
    expected_00 = 0.4 * 0.9 + 0.3 * 1.0 + 0.3 * 0.8
    assert abs(composite[0, 0] - expected_00) < 1e-6, f"Expected {expected_00}, got {composite[0, 0]}"
    
    # For [1,2]: 0.4 * 0.4 + 0.3 * 0.5 + 0.3 * 0.3 = 0.16 + 0.15 + 0.09 = 0.4
    expected_12 = 0.4 * 0.4 + 0.3 * 0.5 + 0.3 * 0.3
    assert abs(composite[1, 2] - expected_12) < 1e-6, f"Expected {expected_12}, got {composite[1, 2]}"


def test_calculate_composite_scores_with_zeros():
    """Test composite score calculation with zero scores."""
    config = MatchingConfig(
        weight_amount=0.4,
        weight_date=0.3,
        weight_semantic=0.3,
        amount_tolerance=Decimal("1.00"),
        date_variance=3,
        exact_threshold=0.98,
        high_threshold=0.85,
        lambda_decay=0.1
    )
    
    scorer = VectorizedScorer(config)
    
    # All zeros
    amount_scores = np.zeros((2, 3))
    date_scores = np.zeros((2, 3))
    semantic_scores = np.zeros((2, 3))
    
    composite = scorer._calculate_composite_scores(amount_scores, date_scores, semantic_scores)
    
    # All composite scores should be zero
    assert np.allclose(composite, 0.0), f"Expected all zeros, got {composite}"


def test_calculate_composite_scores_with_ones():
    """Test composite score calculation with perfect scores."""
    config = MatchingConfig(
        weight_amount=0.4,
        weight_date=0.3,
        weight_semantic=0.3,
        amount_tolerance=Decimal("1.00"),
        date_variance=3,
        exact_threshold=0.98,
        high_threshold=0.85,
        lambda_decay=0.1
    )
    
    scorer = VectorizedScorer(config)
    
    # All ones
    amount_scores = np.ones((2, 3))
    date_scores = np.ones((2, 3))
    semantic_scores = np.ones((2, 3))
    
    composite = scorer._calculate_composite_scores(amount_scores, date_scores, semantic_scores)
    
    # All composite scores should be 1.0 (0.4 + 0.3 + 0.3 = 1.0)
    expected = 0.4 * 1.0 + 0.3 * 1.0 + 0.3 * 1.0
    assert np.allclose(composite, expected), f"Expected all {expected}, got {composite}"


def test_calculate_composite_scores_different_weights():
    """Test composite score calculation with different weight configurations."""
    config = MatchingConfig(
        weight_amount=0.5,
        weight_date=0.3,
        weight_semantic=0.2,
        amount_tolerance=Decimal("1.00"),
        date_variance=3,
        exact_threshold=0.98,
        high_threshold=0.85,
        lambda_decay=0.1
    )
    
    scorer = VectorizedScorer(config)
    
    # Create test arrays
    amount_scores = np.array([[0.8]])
    date_scores = np.array([[0.6]])
    semantic_scores = np.array([[0.4]])
    
    composite = scorer._calculate_composite_scores(amount_scores, date_scores, semantic_scores)
    
    # Expected: 0.5 * 0.8 + 0.3 * 0.6 + 0.2 * 0.4 = 0.4 + 0.18 + 0.08 = 0.66
    expected = 0.5 * 0.8 + 0.3 * 0.6 + 0.2 * 0.4
    assert abs(composite[0, 0] - expected) < 1e-6, f"Expected {expected}, got {composite[0, 0]}"


def test_calculate_composite_scores_large_matrix():
    """Test composite score calculation with larger matrices."""
    config = MatchingConfig(
        weight_amount=0.4,
        weight_date=0.3,
        weight_semantic=0.3,
        amount_tolerance=Decimal("1.00"),
        date_variance=3,
        exact_threshold=0.98,
        high_threshold=0.85,
        lambda_decay=0.1
    )
    
    scorer = VectorizedScorer(config)
    
    # Create larger test arrays (10x20)
    np.random.seed(42)
    amount_scores = np.random.rand(10, 20)
    date_scores = np.random.rand(10, 20)
    semantic_scores = np.random.rand(10, 20)
    
    composite = scorer._calculate_composite_scores(amount_scores, date_scores, semantic_scores)
    
    # Verify shape
    assert composite.shape == (10, 20), f"Expected shape (10, 20), got {composite.shape}"
    
    # Verify a few random elements
    for i in range(3):
        for j in range(3):
            expected = (0.4 * amount_scores[i, j] + 
                       0.3 * date_scores[i, j] + 
                       0.3 * semantic_scores[i, j])
            assert abs(composite[i, j] - expected) < 1e-6, \
                f"Mismatch at [{i},{j}]: expected {expected}, got {composite[i, j]}"
