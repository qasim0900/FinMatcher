"""
Property-based tests for Spatial Indexer.

This module contains property-based tests using Hypothesis to verify
universal properties of the SpatialIndexer component, specifically
testing that K-D tree spatial indexing returns all receipts within
tolerance radius with no false negatives.

Testing Framework: pytest + Hypothesis
Feature: finmatcher-math-optimization
Task: 3.5 - Write property test for spatial indexing correctness
"""

import pytest
from hypothesis import given, strategies as st, settings, assume
from decimal import Decimal
from datetime import date, datetime, timedelta
from typing import List
import numpy as np

from finmatcher.optimization.spatial_indexer import SpatialIndexer
from finmatcher.optimization.config import OptimizationConfig
from finmatcher.storage.models import Transaction, Receipt


# Configure Hypothesis settings for FinMatcher
settings.register_profile("finmatcher_opt", max_examples=100, deadline=5000)
settings.load_profile("finmatcher_opt")


# ============================================================================
# Strategy Generators
# ============================================================================

def generate_receipt_data(min_receipts=5, max_receipts=50):
    """
    Generate random receipt data for property testing.
    
    Constrains the input space intelligently:
    - Amounts: $1 to $10,000 (realistic transaction range)
    - Dates: Within 1 year window (realistic matching window)
    - Minimum 5 receipts to ensure meaningful K-D tree structure
    """
    return st.lists(
        st.tuples(
            st.decimals(
                min_value=Decimal('1.00'),
                max_value=Decimal('10000.00'),
                places=2
            ),
            st.dates(
                min_value=date(2024, 1, 1),
                max_value=date(2024, 12, 31)
            )
        ),
        min_size=min_receipts,
        max_size=max_receipts
    )


def generate_transaction_data():
    """
    Generate random transaction data for property testing.
    
    Uses same ranges as receipts to ensure transactions can potentially
    match receipts in the dataset.
    """
    return st.tuples(
        st.decimals(
            min_value=Decimal('1.00'),
            max_value=Decimal('10000.00'),
            places=2
        ),
        st.dates(
            min_value=date(2024, 1, 1),
            max_value=date(2024, 12, 31)
        )
    )


def generate_tolerance_params():
    """
    Generate random tolerance parameters for property testing.
    
    Constrains to realistic tolerance ranges:
    - Amount tolerance: $1 to $100
    - Date tolerance: 1 to 30 days
    """
    return st.tuples(
        st.decimals(
            min_value=Decimal('1.00'),
            max_value=Decimal('100.00'),
            places=2
        ),
        st.integers(min_value=1, max_value=30)
    )


# ============================================================================
# Helper Functions
# ============================================================================

def brute_force_filter(
    transaction: Transaction,
    receipts: List[Receipt],
    tolerance_amount: Decimal,
    tolerance_days: int,
    weights: tuple
) -> List[int]:
    """
    Brute-force filtering to find all receipts within tolerance.
    
    This is the ground truth implementation that the K-D tree should match.
    Uses the same weighted Euclidean distance calculation as the K-D tree.
    
    Args:
        transaction: Transaction to match
        receipts: List of all receipts
        tolerance_amount: Amount tolerance in dollars
        tolerance_days: Date tolerance in days
        weights: Tuple (w_amount, w_date) for weighted distance
        
    Returns:
        List of receipt indices within tolerance radius
    """
    # Calculate normalization parameters
    amounts = np.array([float(r.amount) for r in receipts])
    dates = np.array([
        int(datetime.combine(r.receipt_date, datetime.min.time()).timestamp())
        for r in receipts
    ])
    
    amount_min, amount_max = amounts.min(), amounts.max()
    date_min, date_max = dates.min(), dates.max()
    
    amount_range = amount_max - amount_min
    date_range = date_max - date_min
    
    # Normalize transaction
    txn_amount = float(transaction.amount)
    txn_timestamp = int(datetime.combine(
        transaction.transaction_date,
        datetime.min.time()
    ).timestamp())
    
    if amount_range == 0:
        txn_amount_norm = 0.5
    else:
        txn_amount_norm = (txn_amount - amount_min) / amount_range
    
    if date_range == 0:
        txn_date_norm = 0.5
    else:
        txn_date_norm = (txn_timestamp - date_min) / date_range
    
    # Calculate tolerance radius
    if amount_range == 0:
        tolerance_amount_norm = 0.0
    else:
        tolerance_amount_norm = float(tolerance_amount) / amount_range
    
    tolerance_days_seconds = tolerance_days * 86400
    if date_range == 0:
        tolerance_days_norm = 0.0
    else:
        tolerance_days_norm = tolerance_days_seconds / date_range
    
    w_amount, w_date = weights
    radius = np.sqrt(
        w_amount * (tolerance_amount_norm ** 2) +
        w_date * (tolerance_days_norm ** 2)
    )
    
    # Brute-force check each receipt
    matching_indices = []
    for i, receipt in enumerate(receipts):
        # Normalize receipt
        rec_amount = float(receipt.amount)
        rec_timestamp = int(datetime.combine(
            receipt.receipt_date,
            datetime.min.time()
        ).timestamp())
        
        if amount_range == 0:
            rec_amount_norm = 0.5
        else:
            rec_amount_norm = (rec_amount - amount_min) / amount_range
        
        if date_range == 0:
            rec_date_norm = 0.5
        else:
            rec_date_norm = (rec_timestamp - date_min) / date_range
        
        # Calculate weighted Euclidean distance
        distance = np.sqrt(
            w_amount * ((txn_amount_norm - rec_amount_norm) ** 2) +
            w_date * ((txn_date_norm - rec_date_norm) ** 2)
        )
        
        # Check if within radius
        if distance <= radius:
            matching_indices.append(i)
    
    return matching_indices


# ============================================================================
# Property Tests
# ============================================================================

@given(
    receipt_data=generate_receipt_data(),
    transaction_data=generate_transaction_data(),
    tolerance_params=generate_tolerance_params()
)
def test_property_5_kdtree_no_false_negatives(
    receipt_data,
    transaction_data,
    tolerance_params
):
    """
    **Validates: Requirements 10.5**
    
    Property 5: K-D tree returns all receipts within tolerance radius (no false negatives)
    
    This property verifies that the K-D tree spatial indexing implementation
    returns ALL receipts that fall within the tolerance radius. We verify this
    by comparing the K-D tree results against a brute-force filtering approach
    that checks every receipt.
    
    The property ensures:
    1. Every receipt found by brute-force is also found by K-D tree (no false negatives)
    2. K-D tree may return additional receipts (false positives are acceptable for candidate filtering)
    3. The weighted Euclidean distance calculation matches between both approaches
    
    Test Strategy:
    - Generate random receipts with varying amounts and dates
    - Generate random transaction to match against
    - Generate random tolerance parameters
    - Build K-D tree index
    - Query K-D tree for candidates
    - Compare against brute-force filtering
    - Assert: brute_force_results ⊆ kdtree_results (no false negatives)
    """
    # Unpack test data
    txn_amount, txn_date = transaction_data
    tolerance_amount, tolerance_days = tolerance_params
    
    # Assume we have diverse receipt data (avoid degenerate cases)
    assume(len(receipt_data) >= 5)
    assume(len(set(receipt_data)) >= 3)  # At least 3 unique receipts
    
    # Create Receipt objects
    receipts = [
        Receipt(
            id=i + 1,
            source="email",
            receipt_date=rec_date,
            amount=rec_amount,
            description=f"Receipt {i}",
            is_financial=True,
            filter_method=None
        )
        for i, (rec_amount, rec_date) in enumerate(receipt_data)
    ]
    
    # Create Transaction object
    transaction = Transaction(
        id=1,
        statement_file="stmt_1",
        transaction_date=txn_date,
        amount=txn_amount,
        description="Test Transaction"
    )
    
    # Build K-D tree index
    config = OptimizationConfig()
    indexer = SpatialIndexer(config)
    indexer.build_index(receipts)
    
    # Query K-D tree for candidates
    kdtree_indices = indexer.query_candidates(
        transaction,
        tolerance_amount,
        tolerance_days
    )
    
    # Get brute-force ground truth
    brute_force_indices = brute_force_filter(
        transaction,
        receipts,
        tolerance_amount,
        tolerance_days,
        indexer.weights
    )
    
    # Convert to sets for comparison
    kdtree_set = set(kdtree_indices)
    brute_force_set = set(brute_force_indices)
    
    # Property: K-D tree must return ALL receipts found by brute-force (no false negatives)
    # brute_force_set ⊆ kdtree_set
    missing_receipts = brute_force_set - kdtree_set
    
    assert missing_receipts == set(), (
        f"K-D tree missed {len(missing_receipts)} receipts that should be within tolerance. "
        f"Missing indices: {sorted(missing_receipts)}. "
        f"Brute-force found {len(brute_force_set)} receipts, "
        f"K-D tree found {len(kdtree_set)} receipts. "
        f"Transaction: amount={txn_amount}, date={txn_date}. "
        f"Tolerances: amount={tolerance_amount}, days={tolerance_days}."
    )
    
    # Additional validation: K-D tree may return extra receipts (false positives)
    # but should not return significantly more (sanity check)
    extra_receipts = kdtree_set - brute_force_set
    
    # Allow some false positives due to floating-point precision and K-D tree approximation
    # but flag if more than 20% extra receipts (indicates potential bug)
    if len(brute_force_set) > 0:
        false_positive_rate = len(extra_receipts) / len(brute_force_set)
        assert false_positive_rate <= 0.2, (
            f"K-D tree returned {len(extra_receipts)} extra receipts "
            f"({false_positive_rate:.1%} false positive rate). "
            f"This may indicate a bug in radius calculation."
        )


@given(
    receipt_data=generate_receipt_data(min_receipts=10, max_receipts=30),
    transaction_data=generate_transaction_data(),
    tolerance_params=generate_tolerance_params()
)
def test_property_5_kdtree_consistency(
    receipt_data,
    transaction_data,
    tolerance_params
):
    """
    **Validates: Requirements 10.5**
    
    Property 5 (Consistency): K-D tree returns consistent results across multiple queries
    
    This property verifies that querying the K-D tree multiple times with the
    same parameters returns identical results, ensuring deterministic behavior.
    
    Test Strategy:
    - Build K-D tree once
    - Query multiple times with same parameters
    - Assert all queries return identical results
    """
    # Unpack test data
    txn_amount, txn_date = transaction_data
    tolerance_amount, tolerance_days = tolerance_params
    
    # Assume we have diverse receipt data
    assume(len(receipt_data) >= 10)
    
    # Create Receipt objects
    receipts = [
        Receipt(
            id=i + 1,
            source="email",
            receipt_date=rec_date,
            amount=rec_amount,
            description=f"Receipt {i}",
            is_financial=True,
            filter_method=None
        )
        for i, (rec_amount, rec_date) in enumerate(receipt_data)
    ]
    
    # Create Transaction object
    transaction = Transaction(
        id=1,
        statement_file="stmt_1",
        transaction_date=txn_date,
        amount=txn_amount,
        description="Test Transaction"
    )
    
    # Build K-D tree index
    config = OptimizationConfig()
    indexer = SpatialIndexer(config)
    indexer.build_index(receipts)
    
    # Query K-D tree multiple times
    results = []
    for _ in range(3):
        indices = indexer.query_candidates(
            transaction,
            tolerance_amount,
            tolerance_days
        )
        results.append(sorted(indices))
    
    # Property: All queries should return identical results
    assert results[0] == results[1] == results[2], (
        f"K-D tree returned inconsistent results across multiple queries. "
        f"Query 1: {results[0]}, Query 2: {results[1]}, Query 3: {results[2]}"
    )


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--hypothesis-show-statistics"])
