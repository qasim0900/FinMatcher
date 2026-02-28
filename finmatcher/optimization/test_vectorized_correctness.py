"""
Unit tests for vectorized scoring correctness against v2.0 baseline.

This module validates that the VectorizedScorer component produces mathematically
identical results to the v2.0 baseline implementation within floating-point
precision tolerance (1e-6).

Validates Requirements: 10.3, 10.4
"""

import pytest
import numpy as np
import math
from decimal import Decimal
from datetime import date, datetime
from finmatcher.storage.models import MatchingConfig
from finmatcher.optimization.vectorized_scorer import VectorizedScorer


# Mock Transaction and Receipt classes for testing
class MockTransaction:
    """Mock Transaction for testing."""
    def __init__(self, amount, transaction_date, description):
        self.amount = Decimal(str(amount))
        self.transaction_date = transaction_date
        self.description = description


class MockReceipt:
    """Mock Receipt for testing."""
    def __init__(self, amount, receipt_date, description):
        self.amount = Decimal(str(amount)) if amount is not None else None
        self.receipt_date = receipt_date
        self.description = description


# V2.0 Baseline Implementation Functions
def v2_calculate_amount_score(txn_amount: Decimal, rec_amount: Decimal, lambda_decay: float) -> float:
    """
    V2.0 baseline amount score calculation using exponential decay.
    
    Formula: S = e^(-λ|A_txn - A_rec|)
    """
    if rec_amount is None:
        return 0.0
    
    amount_diff = abs(float(txn_amount) - float(rec_amount))
    score = math.exp(-lambda_decay * amount_diff)
    
    return score


def v2_calculate_date_score(txn_date: date, rec_date: date, date_variance: float) -> float:
    """
    V2.0 baseline date score calculation using linear decay.
    
    Formula: S = max(0, 1 - |Days_diff| / date_variance)
    """
    days_diff = abs((txn_date - rec_date).days)
    score = max(0.0, 1.0 - (days_diff / date_variance))
    
    return score


def v2_calculate_composite_score(amount_score: float, date_score: float, 
                                 semantic_score: float, config: MatchingConfig) -> float:
    """
    V2.0 baseline composite score calculation.
    
    Formula: S = W_a·S_a + W_d·S_d + W_s·S_s
    """
    composite = (
        config.weight_amount * amount_score +
        config.weight_date * date_score +
        config.weight_semantic * semantic_score
    )
    
    return composite


def test_amount_scores_match_v2_exponential_decay():
    """
    Test amount scores match v2.0 exponential decay within 1e-6 tolerance.
    
    Validates Requirement: 10.3 - Vectorized Amount_Score matches v2.0 exponential 
    decay calculation within 1e-6 tolerance
    """
    # Create config with lambda_decay parameter
    config = MatchingConfig(
        weight_amount=0.4,
        weight_date=0.3,
        weight_semantic=0.3,
        lambda_decay=0.1,
        date_variance=3,
        amount_tolerance=Decimal("10.0"),
        exact_threshold=0.98,
        high_threshold=0.85
    )
    
    # Create VectorizedScorer
    scorer = VectorizedScorer(config=config, deepseek_client=None)
    
    # Test data: various amount combinations
    txn_amounts = [100.0, 50.0, 200.0, 75.50, 1000.0]
    rec_amounts = [100.0, 55.0, 180.0, 75.50, 950.0]
    
    # Create mock transactions and receipts
    transactions = [
        MockTransaction(amount=amt, transaction_date=date(2024, 1, 1), description="test")
        for amt in txn_amounts
    ]
    receipts = [
        MockReceipt(amount=amt, receipt_date=date(2024, 1, 1), description="test")
        for amt in rec_amounts
    ]
    
    # Calculate vectorized scores
    txn_amounts_np = np.array([float(t.amount) for t in transactions])
    rec_amounts_np = np.array([float(r.amount) for r in receipts])
    vectorized_scores = scorer._calculate_amount_scores(txn_amounts_np, rec_amounts_np)
    
    # Calculate v2.0 baseline scores for each pair
    for i, txn in enumerate(transactions):
        for j, rec in enumerate(receipts):
            v2_score = v2_calculate_amount_score(txn.amount, rec.amount, config.lambda_decay)
            vectorized_score = vectorized_scores[i, j]
            
            # Assert scores match within 1e-6 tolerance
            assert abs(v2_score - vectorized_score) < 1e-6, (
                f"Amount score mismatch for txn[{i}]={txn.amount}, rec[{j}]={rec.amount}: "
                f"v2.0={v2_score}, vectorized={vectorized_score}, diff={abs(v2_score - vectorized_score)}"
            )


def test_date_scores_match_v2_linear_decay():
    """
    Test date scores match v2.0 linear decay within 1e-6 tolerance.
    
    Validates Requirement: 10.4 - Vectorized Date_Score matches v2.0 linear decay 
    calculation within 1e-6 tolerance
    """
    # Create config with date_variance parameter
    config = MatchingConfig(
        weight_amount=0.4,
        weight_date=0.3,
        weight_semantic=0.3,
        lambda_decay=0.1,
        date_variance=3,
        amount_tolerance=Decimal("10.0"),
        exact_threshold=0.98,
        high_threshold=0.85
    )
    
    # Create VectorizedScorer
    scorer = VectorizedScorer(config=config, deepseek_client=None)
    
    # Test data: various date combinations
    txn_dates = [
        date(2024, 1, 1),
        date(2024, 1, 5),
        date(2024, 1, 10),
        date(2024, 1, 15),
        date(2024, 2, 1)
    ]
    rec_dates = [
        date(2024, 1, 1),
        date(2024, 1, 3),
        date(2024, 1, 12),
        date(2024, 1, 15),
        date(2024, 1, 28)
    ]
    
    # Create mock transactions and receipts
    transactions = [
        MockTransaction(amount=100.0, transaction_date=dt, description="test")
        for dt in txn_dates
    ]
    receipts = [
        MockReceipt(amount=100.0, receipt_date=dt, description="test")
        for dt in rec_dates
    ]
    
    # Calculate vectorized scores
    txn_dates_np = np.array([datetime.combine(dt, datetime.min.time()).timestamp() for dt in txn_dates])
    rec_dates_np = np.array([datetime.combine(dt, datetime.min.time()).timestamp() for dt in rec_dates])
    vectorized_scores = scorer._calculate_date_scores(txn_dates_np, rec_dates_np, config.date_variance)
    
    # Calculate v2.0 baseline scores for each pair
    for i, txn in enumerate(transactions):
        for j, rec in enumerate(receipts):
            v2_score = v2_calculate_date_score(txn.transaction_date, rec.receipt_date, config.date_variance)
            vectorized_score = vectorized_scores[i, j]
            
            # Assert scores match within 1e-6 tolerance
            assert abs(v2_score - vectorized_score) < 1e-6, (
                f"Date score mismatch for txn[{i}]={txn.transaction_date}, rec[{j}]={rec.receipt_date}: "
                f"v2.0={v2_score}, vectorized={vectorized_score}, diff={abs(v2_score - vectorized_score)}"
            )


def test_composite_scores_match_v2_calculations():
    """
    Test composite scores match v2.0 calculations within 1e-6 tolerance.
    
    Validates Requirement: 10.4 - Vectorized composite scores match v2.0 calculations 
    within 1e-6 tolerance
    """
    # Create config with all weights
    config = MatchingConfig(
        weight_amount=0.4,
        weight_date=0.3,
        weight_semantic=0.3,
        lambda_decay=0.1,
        date_variance=3,
        amount_tolerance=Decimal("10.0"),
        exact_threshold=0.98,
        high_threshold=0.85
    )
    
    # Create VectorizedScorer
    scorer = VectorizedScorer(config=config, deepseek_client=None)
    
    # Test data: various score combinations
    test_cases = [
        # (amount_scores, date_scores, semantic_scores)
        (np.array([[1.0, 0.8], [0.6, 0.4]]), 
         np.array([[1.0, 0.9], [0.7, 0.5]]), 
         np.array([[0.8, 0.7], [0.6, 0.5]])),
        
        (np.array([[0.95, 0.85], [0.75, 0.65]]), 
         np.array([[0.90, 0.80], [0.70, 0.60]]), 
         np.array([[0.85, 0.75], [0.65, 0.55]])),
        
        (np.array([[1.0, 0.0], [0.5, 1.0]]), 
         np.array([[0.0, 1.0], [0.5, 0.0]]), 
         np.array([[0.5, 0.5], [0.0, 1.0]])),
    ]
    
    for test_idx, (amount_scores, date_scores, semantic_scores) in enumerate(test_cases):
        # Calculate vectorized composite scores
        vectorized_composite = scorer._calculate_composite_scores(
            amount_scores, date_scores, semantic_scores
        )
        
        # Calculate v2.0 baseline composite scores for each element
        for i in range(amount_scores.shape[0]):
            for j in range(amount_scores.shape[1]):
                v2_composite = v2_calculate_composite_score(
                    amount_scores[i, j],
                    date_scores[i, j],
                    semantic_scores[i, j],
                    config
                )
                vectorized_score = vectorized_composite[i, j]
                
                # Assert scores match within 1e-6 tolerance
                assert abs(v2_composite - vectorized_score) < 1e-6, (
                    f"Composite score mismatch in test case {test_idx} at [{i},{j}]: "
                    f"v2.0={v2_composite}, vectorized={vectorized_score}, "
                    f"diff={abs(v2_composite - vectorized_score)}"
                )


def test_end_to_end_scoring_matches_v2():
    """
    Test end-to-end scoring pipeline matches v2.0 for all score components.
    
    This test validates that the complete score_batch() method produces results
    that match v2.0 calculations within 1e-6 tolerance for amount, date, and
    composite scores.
    """
    # Create config
    config = MatchingConfig(
        weight_amount=0.4,
        weight_date=0.3,
        weight_semantic=0.3,
        lambda_decay=0.1,
        date_variance=3,
        amount_tolerance=Decimal("10.0"),
        exact_threshold=0.98,
        high_threshold=0.85
    )
    
    # Create VectorizedScorer (no DeepSeek client, so semantic scores will be 0)
    scorer = VectorizedScorer(config=config, deepseek_client=None)
    
    # Create test transactions and receipts
    transactions = [
        MockTransaction(amount=100.0, transaction_date=date(2024, 1, 1), description="Coffee"),
        MockTransaction(amount=50.0, transaction_date=date(2024, 1, 5), description="Lunch"),
        MockTransaction(amount=200.0, transaction_date=date(2024, 1, 10), description="Groceries"),
    ]
    
    receipts = [
        MockReceipt(amount=100.0, receipt_date=date(2024, 1, 1), description="Coffee Shop"),
        MockReceipt(amount=55.0, receipt_date=date(2024, 1, 3), description="Restaurant"),
        MockReceipt(amount=180.0, receipt_date=date(2024, 1, 12), description="Supermarket"),
        MockReceipt(amount=100.0, receipt_date=date(2024, 1, 2), description="Cafe"),
    ]
    
    # Calculate vectorized scores
    vectorized_composite = scorer.score_batch(transactions, receipts)
    
    # Calculate v2.0 baseline scores for each pair
    for i, txn in enumerate(transactions):
        for j, rec in enumerate(receipts):
            # Calculate individual v2.0 scores
            v2_amount = v2_calculate_amount_score(txn.amount, rec.amount, config.lambda_decay)
            v2_date = v2_calculate_date_score(txn.transaction_date, rec.receipt_date, config.date_variance)
            v2_semantic = 0.0  # No DeepSeek client
            v2_composite = v2_calculate_composite_score(v2_amount, v2_date, v2_semantic, config)
            
            vectorized_score = vectorized_composite[i, j]
            
            # Assert composite scores match within 1e-6 tolerance
            assert abs(v2_composite - vectorized_score) < 1e-6, (
                f"End-to-end score mismatch for txn[{i}] and rec[{j}]: "
                f"v2.0={v2_composite}, vectorized={vectorized_score}, "
                f"diff={abs(v2_composite - vectorized_score)}"
            )


def test_edge_cases_match_v2():
    """
    Test edge cases match v2.0 behavior within 1e-6 tolerance.
    
    Tests:
    - Identical amounts and dates (score = 1.0)
    - Large differences (scores near 0.0)
    - Zero amounts
    - Same-day transactions
    """
    config = MatchingConfig(
        weight_amount=0.4,
        weight_date=0.3,
        weight_semantic=0.3,
        lambda_decay=0.1,
        date_variance=3,
        amount_tolerance=Decimal("10.0"),
        exact_threshold=0.98,
        high_threshold=0.85
    )
    
    scorer = VectorizedScorer(config=config, deepseek_client=None)
    
    # Edge case 1: Identical amounts and dates
    txn1 = MockTransaction(amount=100.0, transaction_date=date(2024, 1, 1), description="test")
    rec1 = MockReceipt(amount=100.0, receipt_date=date(2024, 1, 1), description="test")
    
    vectorized_scores = scorer.score_batch([txn1], [rec1])
    v2_amount = v2_calculate_amount_score(txn1.amount, rec1.amount, config.lambda_decay)
    v2_date = v2_calculate_date_score(txn1.transaction_date, rec1.receipt_date, config.date_variance)
    v2_composite = v2_calculate_composite_score(v2_amount, v2_date, 0.0, config)
    
    assert abs(v2_composite - vectorized_scores[0, 0]) < 1e-6
    assert abs(1.0 - v2_amount) < 1e-6  # Perfect amount match
    assert abs(1.0 - v2_date) < 1e-6  # Perfect date match
    
    # Edge case 2: Large amount difference
    txn2 = MockTransaction(amount=100.0, transaction_date=date(2024, 1, 1), description="test")
    rec2 = MockReceipt(amount=1000.0, receipt_date=date(2024, 1, 1), description="test")
    
    vectorized_scores = scorer.score_batch([txn2], [rec2])
    v2_amount = v2_calculate_amount_score(txn2.amount, rec2.amount, config.lambda_decay)
    v2_date = v2_calculate_date_score(txn2.transaction_date, rec2.receipt_date, config.date_variance)
    v2_composite = v2_calculate_composite_score(v2_amount, v2_date, 0.0, config)
    
    assert abs(v2_composite - vectorized_scores[0, 0]) < 1e-6
    
    # Edge case 3: Large date difference (beyond tolerance)
    txn3 = MockTransaction(amount=100.0, transaction_date=date(2024, 1, 1), description="test")
    rec3 = MockReceipt(amount=100.0, receipt_date=date(2024, 2, 1), description="test")
    
    vectorized_scores = scorer.score_batch([txn3], [rec3])
    v2_amount = v2_calculate_amount_score(txn3.amount, rec3.amount, config.lambda_decay)
    v2_date = v2_calculate_date_score(txn3.transaction_date, rec3.receipt_date, config.date_variance)
    v2_composite = v2_calculate_composite_score(v2_amount, v2_date, 0.0, config)
    
    assert abs(v2_composite - vectorized_scores[0, 0]) < 1e-6
    assert v2_date == 0.0  # Date score should be 0 (beyond tolerance)
    
    # Edge case 4: Zero amounts
    txn4 = MockTransaction(amount=0.0, transaction_date=date(2024, 1, 1), description="test")
    rec4 = MockReceipt(amount=0.0, receipt_date=date(2024, 1, 1), description="test")
    
    vectorized_scores = scorer.score_batch([txn4], [rec4])
    v2_amount = v2_calculate_amount_score(txn4.amount, rec4.amount, config.lambda_decay)
    v2_date = v2_calculate_date_score(txn4.transaction_date, rec4.receipt_date, config.date_variance)
    v2_composite = v2_calculate_composite_score(v2_amount, v2_date, 0.0, config)
    
    assert abs(v2_composite - vectorized_scores[0, 0]) < 1e-6
