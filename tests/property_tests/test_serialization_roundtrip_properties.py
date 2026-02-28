"""
Property-based tests for K-D tree serialization round-trip.

This module contains property-based tests using Hypothesis to verify
that serializing and deserializing K-D tree structures produces equivalent
results. The tests ensure that queries return identical results after
round-trip serialization.

Testing Framework: pytest + Hypothesis
Feature: finmatcher-math-optimization
Task: 4.3 - Write property test for serialization round-trip
"""

import pytest
from hypothesis import given, strategies as st, settings, assume
from decimal import Decimal
from datetime import date, datetime
from typing import List
import tempfile
import os

from finmatcher.optimization.spatial_indexer import SpatialIndexer
from finmatcher.optimization.config import OptimizationConfig
from finmatcher.storage.models import Transaction, Receipt, FilterMethod


# Configure Hypothesis settings for FinMatcher
settings.register_profile("finmatcher_opt", max_examples=50, deadline=10000)
settings.load_profile("finmatcher_opt")


# ============================================================================
# Strategy Generators
# ============================================================================

def generate_receipt_data(min_receipts=10, max_receipts=100):
    """
    Generate random receipt data for property testing.
    
    Constrains the input space intelligently:
    - Amounts: $1 to $10,000 (realistic transaction range)
    - Dates: Within 1 year window (realistic matching window)
    - Minimum 10 receipts to ensure meaningful K-D tree structure
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
            ),
            st.text(
                min_size=5,
                max_size=50,
                alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd', 'Zs'))
            )
        ),
        min_size=min_receipts,
        max_size=max_receipts,
        unique_by=lambda x: (x[0], x[1])  # Unique by amount and date
    )


def generate_transaction_queries(num_queries=5):
    """
    Generate random transaction queries for testing.
    
    Uses same ranges as receipts to ensure transactions can potentially
    match receipts in the dataset.
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
            ),
            st.text(
                min_size=5,
                max_size=50,
                alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd', 'Zs'))
            )
        ),
        min_size=num_queries,
        max_size=num_queries
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
# Property Tests
# ============================================================================

@given(
    receipt_data=generate_receipt_data(min_receipts=10, max_receipts=100),
    transaction_queries=generate_transaction_queries(num_queries=5),
    tolerance_params=generate_tolerance_params()
)
def test_property_11_serialization_roundtrip_preserves_queries(
    receipt_data,
    transaction_queries,
    tolerance_params
):
    """
    **Validates: Requirements 8.11**
    
    Property 11: Serializing then deserializing produces equivalent K-D tree structure
    
    This property verifies that the K-D tree serialization round-trip preserves
    the structure and functionality of the index. We verify this by:
    1. Building a K-D tree from receipt data
    2. Executing queries and recording results
    3. Serializing the K-D tree to disk
    4. Deserializing into a new indexer instance
    5. Executing the same queries on the deserialized tree
    6. Verifying that query results are identical
    
    The property ensures:
    - Serialization preserves the K-D tree structure
    - Deserialization correctly reconstructs the tree
    - Queries return identical results (same receipt indices)
    - Normalization parameters are preserved
    - Feature vectors are preserved
    
    Test Strategy:
    - Generate random receipts with varying amounts and dates
    - Generate random transaction queries
    - Generate random tolerance parameters
    - Build K-D tree and execute queries (original results)
    - Serialize and deserialize the tree
    - Execute same queries on deserialized tree (roundtrip results)
    - Assert: original_results == roundtrip_results for all queries
    """
    # Unpack tolerance parameters
    tolerance_amount, tolerance_days = tolerance_params
    
    # Assume we have diverse receipt data (avoid degenerate cases)
    assume(len(receipt_data) >= 10)
    assume(len(transaction_queries) >= 1)
    
    # Create temporary directory for serialization
    with tempfile.TemporaryDirectory() as temp_dir:
        cache_path = os.path.join(temp_dir, 'test_kdtree.pkl')
        
        # Create receipts from generated data
        receipts = []
        for i, (amount, receipt_date, description) in enumerate(receipt_data):
            receipt = Receipt(
                id=i + 1,
                source='email',
                receipt_date=receipt_date,
                amount=amount,
                description=description,
                is_financial=True,
                filter_method=None
            )
            receipts.append(receipt)
        
        # Create transactions from generated queries
        transactions = []
        for i, (amount, txn_date, description) in enumerate(transaction_queries):
            transaction = Transaction(
                id=i + 1,
                statement_file=f'statement_{i}',
                transaction_date=txn_date,
                amount=amount,
                description=description
            )
            transactions.append(transaction)
        
        # Build original K-D tree
        config = OptimizationConfig(
            kdtree_cache_enabled=True,
            kdtree_cache_path=temp_dir
        )
        original_indexer = SpatialIndexer(config)
        original_indexer.build_index(receipts)
        
        # Execute queries on original tree and record results
        original_results = []
        for transaction in transactions:
            candidates = original_indexer.query_candidates(
                transaction,
                tolerance_amount,
                tolerance_days
            )
            # Sort for consistent comparison
            original_results.append(sorted(candidates))
        
        # Serialize the K-D tree
        original_indexer.serialize(cache_path)
        
        # Verify serialization file exists
        assert os.path.exists(cache_path), "Serialization file should exist"
        assert os.path.getsize(cache_path) > 0, "Serialization file should not be empty"
        
        # Create new indexer and deserialize
        roundtrip_indexer = SpatialIndexer(config)
        success = roundtrip_indexer.deserialize(cache_path)
        
        # Verify deserialization succeeded
        assert success, "Deserialization should succeed"
        assert roundtrip_indexer.kdtree is not None, "K-D tree should be loaded"
        assert roundtrip_indexer.feature_vectors is not None, "Feature vectors should be loaded"
        assert roundtrip_indexer.normalization_params is not None, "Normalization params should be loaded"
        
        # Execute same queries on deserialized tree
        roundtrip_results = []
        for transaction in transactions:
            candidates = roundtrip_indexer.query_candidates(
                transaction,
                tolerance_amount,
                tolerance_days
            )
            # Sort for consistent comparison
            roundtrip_results.append(sorted(candidates))
        
        # Verify query results are identical
        assert len(original_results) == len(roundtrip_results), \
            "Should have same number of query results"
        
        for i, (original, roundtrip) in enumerate(zip(original_results, roundtrip_results)):
            assert original == roundtrip, \
                f"Query {i} results should be identical after round-trip: " \
                f"original={original}, roundtrip={roundtrip}"
        
        # Additional verification: Check that feature vectors are preserved
        import numpy as np
        assert np.array_equal(
            original_indexer.feature_vectors,
            roundtrip_indexer.feature_vectors
        ), "Feature vectors should be identical after round-trip"
        
        # Verify normalization parameters are preserved
        assert original_indexer.normalization_params.amount_min == \
            roundtrip_indexer.normalization_params.amount_min, \
            "Amount min should be preserved"
        assert original_indexer.normalization_params.amount_max == \
            roundtrip_indexer.normalization_params.amount_max, \
            "Amount max should be preserved"
        assert original_indexer.normalization_params.date_min == \
            roundtrip_indexer.normalization_params.date_min, \
            "Date min should be preserved"
        assert original_indexer.normalization_params.date_max == \
            roundtrip_indexer.normalization_params.date_max, \
            "Date max should be preserved"


@given(
    receipt_data=generate_receipt_data(min_receipts=10, max_receipts=50)
)
def test_property_11_multiple_roundtrips_preserve_structure(receipt_data):
    """
    **Validates: Requirements 8.11, 10.10**
    
    Property 11 (Extended): Multiple serialization round-trips preserve structure
    
    This property verifies that multiple serialization/deserialization cycles
    do not degrade the K-D tree structure. This is important for scenarios
    where the cache might be loaded and re-saved multiple times.
    
    Test Strategy:
    - Build K-D tree from receipts
    - Perform 3 serialization/deserialization cycles
    - Verify structure is preserved after each cycle
    - Verify final structure matches original
    """
    # Assume we have diverse receipt data
    assume(len(receipt_data) >= 10)
    
    # Create temporary directory for serialization
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create receipts from generated data
        receipts = []
        for i, (amount, receipt_date, description) in enumerate(receipt_data):
            receipt = Receipt(
                id=i + 1,
                source='email',
                receipt_date=receipt_date,
                amount=amount,
                description=description,
                is_financial=True,
                filter_method=None
            )
            receipts.append(receipt)
        
        # Build original K-D tree
        config = OptimizationConfig(
            kdtree_cache_enabled=True,
            kdtree_cache_path=temp_dir
        )
        original_indexer = SpatialIndexer(config)
        original_indexer.build_index(receipts)
        
        # Store original feature vectors for comparison
        import numpy as np
        original_feature_vectors = original_indexer.feature_vectors.copy()
        original_norm_params = original_indexer.normalization_params
        
        # Perform multiple round-trips
        current_indexer = original_indexer
        for cycle in range(3):
            cache_path = os.path.join(temp_dir, f'kdtree_cycle_{cycle}.pkl')
            
            # Serialize
            current_indexer.serialize(cache_path)
            
            # Deserialize into new indexer
            next_indexer = SpatialIndexer(config)
            success = next_indexer.deserialize(cache_path)
            
            assert success, f"Deserialization should succeed in cycle {cycle}"
            
            # Verify structure is preserved
            assert np.array_equal(
                original_feature_vectors,
                next_indexer.feature_vectors
            ), f"Feature vectors should match original after cycle {cycle}"
            
            assert original_norm_params.amount_min == next_indexer.normalization_params.amount_min, \
                f"Amount min should match after cycle {cycle}"
            assert original_norm_params.amount_max == next_indexer.normalization_params.amount_max, \
                f"Amount max should match after cycle {cycle}"
            assert original_norm_params.date_min == next_indexer.normalization_params.date_min, \
                f"Date min should match after cycle {cycle}"
            assert original_norm_params.date_max == next_indexer.normalization_params.date_max, \
                f"Date max should match after cycle {cycle}"
            
            current_indexer = next_indexer


@given(
    receipt_data=generate_receipt_data(min_receipts=10, max_receipts=100),
    transaction_queries=generate_transaction_queries(num_queries=10),
    tolerance_params=generate_tolerance_params()
)
def test_property_11_roundtrip_with_edge_case_queries(
    receipt_data,
    transaction_queries,
    tolerance_params
):
    """
    **Validates: Requirements 8.11, 10.10**
    
    Property 11 (Edge Cases): Round-trip preserves correctness for edge case queries
    
    This property tests serialization round-trip with edge case scenarios:
    - Queries that match no receipts
    - Queries that match all receipts
    - Queries at the boundaries of the dataset
    
    Test Strategy:
    - Build K-D tree from receipts
    - Execute various edge case queries
    - Serialize and deserialize
    - Verify edge case queries return same results
    """
    # Unpack tolerance parameters
    tolerance_amount, tolerance_days = tolerance_params
    
    # Assume we have diverse receipt data
    assume(len(receipt_data) >= 10)
    
    # Create temporary directory for serialization
    with tempfile.TemporaryDirectory() as temp_dir:
        cache_path = os.path.join(temp_dir, 'test_kdtree.pkl')
        
        # Create receipts from generated data
        receipts = []
        for i, (amount, receipt_date, description) in enumerate(receipt_data):
            receipt = Receipt(
                id=i + 1,
                source='email',
                receipt_date=receipt_date,
                amount=amount,
                description=description,
                is_financial=True,
                filter_method=None
            )
            receipts.append(receipt)
        
        # Create edge case transactions
        edge_case_transactions = []
        
        # Add generated queries
        for i, (amount, txn_date, description) in enumerate(transaction_queries):
            transaction = Transaction(
                id=i + 1,
                statement_file=f'statement_{i}',
                transaction_date=txn_date,
                amount=amount,
                description=description
            )
            edge_case_transactions.append(transaction)
        
        # Add edge case: transaction with amount far outside receipt range
        min_amount = min(r.amount for r in receipts)
        max_amount = max(r.amount for r in receipts)
        
        edge_case_transactions.append(Transaction(
            id=len(edge_case_transactions) + 1,
            statement_file='edge_far_below',
            transaction_date=date(2024, 6, 15),
            amount=min_amount - Decimal('1000.00'),
            description='Far below range'
        ))
        
        edge_case_transactions.append(Transaction(
            id=len(edge_case_transactions) + 1,
            statement_file='edge_far_above',
            transaction_date=date(2024, 6, 15),
            amount=max_amount + Decimal('1000.00'),
            description='Far above range'
        ))
        
        # Build original K-D tree
        config = OptimizationConfig(
            kdtree_cache_enabled=True,
            kdtree_cache_path=temp_dir
        )
        original_indexer = SpatialIndexer(config)
        original_indexer.build_index(receipts)
        
        # Execute edge case queries on original tree
        original_results = []
        for transaction in edge_case_transactions:
            candidates = original_indexer.query_candidates(
                transaction,
                tolerance_amount,
                tolerance_days
            )
            original_results.append(sorted(candidates))
        
        # Serialize and deserialize
        original_indexer.serialize(cache_path)
        
        roundtrip_indexer = SpatialIndexer(config)
        success = roundtrip_indexer.deserialize(cache_path)
        assert success, "Deserialization should succeed"
        
        # Execute same edge case queries on deserialized tree
        roundtrip_results = []
        for transaction in edge_case_transactions:
            candidates = roundtrip_indexer.query_candidates(
                transaction,
                tolerance_amount,
                tolerance_days
            )
            roundtrip_results.append(sorted(candidates))
        
        # Verify all edge case queries return identical results
        assert len(original_results) == len(roundtrip_results), \
            "Should have same number of edge case results"
        
        for i, (original, roundtrip) in enumerate(zip(original_results, roundtrip_results)):
            assert original == roundtrip, \
                f"Edge case query {i} should return identical results: " \
                f"original={original}, roundtrip={roundtrip}"
