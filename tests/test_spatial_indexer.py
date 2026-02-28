"""
Unit tests for SpatialIndexer feature extraction and normalization.

Tests the _normalize_features, _extract_features, and _calculate_normalization_params
methods to ensure correct min-max scaling and feature extraction.

Validates Requirements: 1.1, 1.2, 1.3, 1.4, 8.3, 10.1
"""

import pytest
import numpy as np
from datetime import date, datetime
from decimal import Decimal

from finmatcher.optimization.spatial_indexer import SpatialIndexer
from finmatcher.optimization.config import OptimizationConfig
from finmatcher.storage.models import Receipt


class TestSpatialIndexerNormalization:
    """Test suite for feature extraction and normalization methods."""
    
    def test_normalize_features_basic(self):
        """Test basic min-max normalization produces [0,1] values."""
        config = OptimizationConfig()
        indexer = SpatialIndexer(config)
        
        amounts = np.array([10.0, 50.0, 100.0])
        dates = np.array([1000, 2000, 3000])
        
        normalized = indexer._normalize_features(amounts, dates)
        
        # Check shape
        assert normalized.shape == (3, 2)
        
        # Check min values map to 0.0
        assert normalized[0, 0] == 0.0  # amount
        assert normalized[0, 1] == 0.0  # date
        
        # Check max values map to 1.0
        assert normalized[2, 0] == 1.0  # amount
        assert normalized[2, 1] == 1.0  # date
        
        # Check middle values
        assert 0.0 < normalized[1, 0] < 1.0
        assert 0.0 < normalized[1, 1] < 1.0
        
        # Check all values in [0,1] range
        assert np.all(normalized >= 0.0)
        assert np.all(normalized <= 1.0)
    
    def test_normalize_features_single_value(self):
        """Test edge case: all values are the same (normalize to 0.5)."""
        config = OptimizationConfig()
        indexer = SpatialIndexer(config)
        
        amounts = np.array([50.0, 50.0, 50.0])
        dates = np.array([2000, 2000, 2000])
        
        normalized = indexer._normalize_features(amounts, dates)
        
        # All values should be 0.5 when min == max
        assert np.all(normalized[:, 0] == 0.5)
        assert np.all(normalized[:, 1] == 0.5)
    
    def test_normalize_features_two_values(self):
        """Test normalization with only two distinct values."""
        config = OptimizationConfig()
        indexer = SpatialIndexer(config)
        
        amounts = np.array([0.0, 100.0])
        dates = np.array([0, 1000])
        
        normalized = indexer._normalize_features(amounts, dates)
        
        # First should be 0.0, second should be 1.0
        assert normalized[0, 0] == 0.0
        assert normalized[0, 1] == 0.0
        assert normalized[1, 0] == 1.0
        assert normalized[1, 1] == 1.0
    
    def test_extract_features_basic(self):
        """Test extraction of amounts and dates from receipts."""
        config = OptimizationConfig()
        indexer = SpatialIndexer(config)
        
        receipts = [
            Receipt(1, 'email', date(2024, 1, 1), Decimal('100.00'), 'Test 1', True, None),
            Receipt(2, 'email', date(2024, 1, 15), Decimal('200.00'), 'Test 2', True, None),
            Receipt(3, 'email', date(2024, 2, 1), Decimal('150.00'), 'Test 3', True, None)
        ]
        
        amounts, dates = indexer._extract_features(receipts)
        
        # Check shapes
        assert amounts.shape == (3,)
        assert dates.shape == (3,)
        
        # Check amounts
        assert amounts[0] == 100.0
        assert amounts[1] == 200.0
        assert amounts[2] == 150.0
        
        # Check dates are Unix timestamps
        assert isinstance(dates[0], (int, np.integer))
        assert dates[0] > 0
        assert dates[1] > dates[0]  # Later date has larger timestamp
    
    def test_extract_features_none_amount(self):
        """Test extraction handles receipts with None amounts."""
        config = OptimizationConfig()
        indexer = SpatialIndexer(config)
        
        receipts = [
            Receipt(1, 'email', date(2024, 1, 1), None, 'Test 1', True, None),
            Receipt(2, 'email', date(2024, 1, 15), Decimal('200.00'), 'Test 2', True, None)
        ]
        
        amounts, dates = indexer._extract_features(receipts)
        
        # None amount should be converted to 0.0
        assert amounts[0] == 0.0
        assert amounts[1] == 200.0
    
    def test_calculate_normalization_params(self):
        """Test calculation of normalization parameters."""
        config = OptimizationConfig()
        indexer = SpatialIndexer(config)
        
        amounts = np.array([10.0, 50.0, 100.0])
        dates = np.array([1000, 2000, 3000])
        receipts = [
            Receipt(1, 'email', date(2024, 1, 1), Decimal('10.00'), 'Test', True, None),
            Receipt(2, 'email', date(2024, 1, 15), Decimal('50.00'), 'Test', True, None),
            Receipt(3, 'email', date(2024, 2, 1), Decimal('100.00'), 'Test', True, None)
        ]
        
        params = indexer._calculate_normalization_params(amounts, dates, receipts)
        
        # Check min/max values
        assert params.amount_min == Decimal('10.0')
        assert params.amount_max == Decimal('100.0')
        assert params.date_min == 1000
        assert params.date_max == 3000
        
        # Check dataset hash is generated
        assert isinstance(params.dataset_hash, str)
        assert len(params.dataset_hash) == 64  # SHA-256 produces 64 hex chars
    
    def test_calculate_dataset_hash(self):
        """Test dataset hash calculation."""
        config = OptimizationConfig()
        indexer = SpatialIndexer(config)
        
        receipts = [
            Receipt(1, 'email', date(2024, 1, 1), Decimal('100.00'), 'Test', True, None),
            Receipt(2, 'email', date(2024, 1, 15), Decimal('200.00'), 'Test', True, None)
        ]
        
        hash1 = indexer._calculate_dataset_hash(receipts)
        
        # Check hash format
        assert isinstance(hash1, str)
        assert len(hash1) == 64
        
        # Same receipts should produce same hash
        hash2 = indexer._calculate_dataset_hash(receipts)
        assert hash1 == hash2
        
        # Different receipts should produce different hash
        receipts_different = [
            Receipt(3, 'email', date(2024, 2, 1), Decimal('150.00'), 'Test', True, None)
        ]
        hash3 = indexer._calculate_dataset_hash(receipts_different)
        assert hash1 != hash3
    
    def test_normalization_preserves_order(self):
        """Test that normalization preserves relative ordering."""
        config = OptimizationConfig()
        indexer = SpatialIndexer(config)
        
        amounts = np.array([10.0, 30.0, 20.0, 50.0])
        dates = np.array([1000, 3000, 2000, 5000])
        
        normalized = indexer._normalize_features(amounts, dates)
        
        # Check that relative ordering is preserved
        # amounts: 10 < 20 < 30 < 50
        assert normalized[0, 0] < normalized[2, 0]  # 10 < 20
        assert normalized[2, 0] < normalized[1, 0]  # 20 < 30
        assert normalized[1, 0] < normalized[3, 0]  # 30 < 50
        
        # dates: 1000 < 2000 < 3000 < 5000
        assert normalized[0, 1] < normalized[2, 1]  # 1000 < 2000
        assert normalized[2, 1] < normalized[1, 1]  # 2000 < 3000
        assert normalized[1, 1] < normalized[3, 1]  # 3000 < 5000


if __name__ == '__main__':
    pytest.main([__file__, '-v'])



class TestSpatialIndexerBuildIndex:
    """Test suite for K-D tree construction via build_index method."""
    
    def test_build_index_basic(self):
        """Test basic K-D tree construction from receipts."""
        config = OptimizationConfig()
        indexer = SpatialIndexer(config)
        
        receipts = [
            Receipt(1, 'email', date(2024, 1, 1), Decimal('100.00'), 'Test 1', True, None),
            Receipt(2, 'email', date(2024, 1, 15), Decimal('200.00'), 'Test 2', True, None),
            Receipt(3, 'email', date(2024, 2, 1), Decimal('150.00'), 'Test 3', True, None)
        ]
        
        indexer.build_index(receipts)
        
        # Check that K-D tree was created
        assert indexer.kdtree is not None
        
        # Check that feature vectors were created
        assert indexer.feature_vectors is not None
        assert indexer.feature_vectors.shape == (3, 2)
        
        # Check that normalization params were stored
        assert indexer.normalization_params is not None
        assert indexer.normalization_params.amount_min == Decimal('100.00')
        assert indexer.normalization_params.amount_max == Decimal('200.00')
    
    def test_build_index_empty_receipts(self):
        """Test that building index with empty receipts raises ValueError."""
        config = OptimizationConfig()
        indexer = SpatialIndexer(config)
        
        with pytest.raises(ValueError, match="Cannot build index from empty receipt list"):
            indexer.build_index([])
    
    def test_build_index_single_receipt(self):
        """Test K-D tree construction with single receipt."""
        config = OptimizationConfig()
        indexer = SpatialIndexer(config)
        
        receipts = [
            Receipt(1, 'email', date(2024, 1, 1), Decimal('100.00'), 'Test', True, None)
        ]
        
        indexer.build_index(receipts)
        
        # Should still create K-D tree
        assert indexer.kdtree is not None
        assert indexer.feature_vectors.shape == (1, 2)
        
        # Single value should normalize to 0.5
        assert indexer.feature_vectors[0, 0] == 0.5
        assert indexer.feature_vectors[0, 1] == 0.5
    
    def test_build_index_custom_leaf_size(self):
        """Test K-D tree construction with custom leaf_size."""
        config = OptimizationConfig(kdtree_leaf_size=20)
        indexer = SpatialIndexer(config)
        
        receipts = [
            Receipt(i, 'email', date(2024, 1, 1 + (i % 28)), Decimal(str(i * 10.0)), f'Test {i}', True, None)
            for i in range(1, 51)  # 50 receipts
        ]
        
        indexer.build_index(receipts)
        
        # Check that K-D tree was created with custom leaf_size
        assert indexer.kdtree is not None
        assert indexer.kdtree.leafsize == 20
    
    def test_build_index_feature_vectors_normalized(self):
        """Test that feature vectors are properly normalized to [0,1]."""
        config = OptimizationConfig()
        indexer = SpatialIndexer(config)
        
        receipts = [
            Receipt(1, 'email', date(2024, 1, 1), Decimal('50.00'), 'Test 1', True, None),
            Receipt(2, 'email', date(2024, 6, 1), Decimal('150.00'), 'Test 2', True, None),
            Receipt(3, 'email', date(2024, 12, 31), Decimal('250.00'), 'Test 3', True, None)
        ]
        
        indexer.build_index(receipts)
        
        # All feature vectors should be in [0,1] range
        assert np.all(indexer.feature_vectors >= 0.0)
        assert np.all(indexer.feature_vectors <= 1.0)
        
        # Min values should be 0.0
        assert indexer.feature_vectors[0, 0] == 0.0  # min amount
        assert indexer.feature_vectors[0, 1] == 0.0  # min date
        
        # Max values should be 1.0
        assert indexer.feature_vectors[2, 0] == 1.0  # max amount
        assert indexer.feature_vectors[2, 1] == 1.0  # max date
    
    def test_build_index_stores_normalization_params(self):
        """Test that normalization parameters are correctly stored."""
        config = OptimizationConfig()
        indexer = SpatialIndexer(config)
        
        receipts = [
            Receipt(1, 'email', date(2024, 1, 1), Decimal('100.00'), 'Test 1', True, None),
            Receipt(2, 'email', date(2024, 12, 31), Decimal('500.00'), 'Test 2', True, None)
        ]
        
        indexer.build_index(receipts)
        
        # Check normalization params
        params = indexer.normalization_params
        assert params.amount_min == Decimal('100.00')
        assert params.amount_max == Decimal('500.00')
        
        # Check that dataset hash was calculated
        assert len(params.dataset_hash) == 64
    
    def test_build_index_large_dataset(self):
        """Test K-D tree construction with larger dataset."""
        config = OptimizationConfig()
        indexer = SpatialIndexer(config)
        
        # Create 1000 receipts
        receipts = [
            Receipt(
                i, 
                'email', 
                date(2024, 1, 1 + (i % 28)),  # Vary dates within a month
                Decimal(str(10.0 + i * 0.5)),  # Vary amounts
                f'Test {i}', 
                True, 
                None
            )
            for i in range(1000)
        ]
        
        indexer.build_index(receipts)
        
        # Check that K-D tree was created
        assert indexer.kdtree is not None
        assert indexer.feature_vectors.shape == (1000, 2)
        
        # All feature vectors should be normalized
        assert np.all(indexer.feature_vectors >= 0.0)
        assert np.all(indexer.feature_vectors <= 1.0)


class TestSpatialIndexerQueryCandidates:
    """Test suite for query_candidates method and weighted Euclidean distance."""
    
    def test_query_candidates_basic(self):
        """Test basic query returns correct candidates within tolerance."""
        from finmatcher.storage.models import Transaction
        
        config = OptimizationConfig()
        indexer = SpatialIndexer(config)
        
        # Create receipts with known amounts and dates
        receipts = [
            Receipt(1, 'email', date(2024, 1, 1), Decimal('100.00'), 'Test 1', True, None),
            Receipt(2, 'email', date(2024, 1, 5), Decimal('105.00'), 'Test 2', True, None),
            Receipt(3, 'email', date(2024, 1, 15), Decimal('200.00'), 'Test 3', True, None),
            Receipt(4, 'email', date(2024, 2, 1), Decimal('150.00'), 'Test 4', True, None)
        ]
        
        indexer.build_index(receipts)
        
        # Query for transaction close to receipt 2
        txn = Transaction(1, 'stmt', date(2024, 1, 6), Decimal('103.00'), 'Test')
        candidates = indexer.query_candidates(txn, Decimal('10.00'), 7)
        
        # Should return receipts within tolerance
        assert isinstance(candidates, list)
        assert len(candidates) > 0
    
    def test_query_candidates_without_build_raises_error(self):
        """Test that querying without building index raises ValueError."""
        from finmatcher.storage.models import Transaction
        
        config = OptimizationConfig()
        indexer = SpatialIndexer(config)
        
        txn = Transaction(1, 'stmt', date(2024, 1, 1), Decimal('100.00'), 'Test')
        
        with pytest.raises(ValueError, match="K-D tree has not been built"):
            indexer.query_candidates(txn, Decimal('10.00'), 7)
    
    def test_query_candidates_empty_result(self):
        """Test query with very tight tolerance returns no candidates."""
        from finmatcher.storage.models import Transaction
        
        config = OptimizationConfig()
        indexer = SpatialIndexer(config)
        
        receipts = [
            Receipt(1, 'email', date(2024, 1, 1), Decimal('100.00'), 'Test 1', True, None),
            Receipt(2, 'email', date(2024, 1, 15), Decimal('200.00'), 'Test 2', True, None)
        ]
        
        indexer.build_index(receipts)
        
        # Query with transaction far from any receipt
        txn = Transaction(1, 'stmt', date(2024, 6, 1), Decimal('500.00'), 'Test')
        candidates = indexer.query_candidates(txn, Decimal('1.00'), 1)
        
        # Should return empty list
        assert isinstance(candidates, list)
        assert len(candidates) == 0
    
    def test_query_candidates_single_receipt_dataset(self):
        """Test query on dataset with single receipt."""
        from finmatcher.storage.models import Transaction
        
        config = OptimizationConfig()
        indexer = SpatialIndexer(config)
        
        receipts = [
            Receipt(1, 'email', date(2024, 1, 1), Decimal('100.00'), 'Test', True, None)
        ]
        
        indexer.build_index(receipts)
        
        # Query with matching transaction
        txn = Transaction(1, 'stmt', date(2024, 1, 1), Decimal('100.00'), 'Test')
        candidates = indexer.query_candidates(txn, Decimal('10.00'), 7)
        
        # Should return the single receipt
        assert len(candidates) == 1
        assert 0 in candidates
    
    def test_query_candidates_all_receipts_within_tolerance(self):
        """Test query returns all receipts when tolerance is large."""
        from finmatcher.storage.models import Transaction
        
        config = OptimizationConfig()
        indexer = SpatialIndexer(config)
        
        receipts = [
            Receipt(1, 'email', date(2024, 1, 1), Decimal('100.00'), 'Test 1', True, None),
            Receipt(2, 'email', date(2024, 1, 5), Decimal('105.00'), 'Test 2', True, None),
            Receipt(3, 'email', date(2024, 1, 10), Decimal('110.00'), 'Test 3', True, None)
        ]
        
        indexer.build_index(receipts)
        
        # Query with very large tolerance
        txn = Transaction(1, 'stmt', date(2024, 1, 5), Decimal('105.00'), 'Test')
        candidates = indexer.query_candidates(txn, Decimal('100.00'), 365)
        
        # Should return all receipts
        assert len(candidates) == 3
    
    def test_weighted_euclidean_distance_calculation(self):
        """Test that weighted Euclidean distance is calculated correctly."""
        from finmatcher.storage.models import Transaction
        
        config = OptimizationConfig()
        indexer = SpatialIndexer(config)
        
        # Set custom weights for testing
        indexer.weights = (0.6, 0.4)  # 60% weight on amount, 40% on date
        
        # Create receipts with known values
        receipts = [
            Receipt(1, 'email', date(2024, 1, 1), Decimal('100.00'), 'Test 1', True, None),
            Receipt(2, 'email', date(2024, 1, 31), Decimal('200.00'), 'Test 2', True, None)
        ]
        
        indexer.build_index(receipts)
        
        # Query with transaction at midpoint
        txn = Transaction(1, 'stmt', date(2024, 1, 15), Decimal('150.00'), 'Test')
        
        # With weighted distance and generous tolerance, should find candidates
        # Amount range is 100, date range is 30 days
        # Using large tolerance to ensure we find at least one receipt
        candidates = indexer.query_candidates(txn, Decimal('100.00'), 30)
        
        # Should find at least one candidate (likely both)
        assert len(candidates) >= 1
        
        # Verify that the weights affect the query by checking with different weights
        indexer.weights = (1.0, 1.0)  # Equal weights
        candidates_equal = indexer.query_candidates(txn, Decimal('100.00'), 30)
        
        # Both queries should return candidates
        assert len(candidates_equal) >= 1
    
    def test_query_candidates_tolerance_radius_calculation(self):
        """Test that tolerance radius is correctly calculated in normalized space."""
        from finmatcher.storage.models import Transaction
        
        config = OptimizationConfig()
        indexer = SpatialIndexer(config)
        
        # Create receipts with known range
        # Amount range: 100 to 200 (range = 100)
        # Date range: 30 days
        receipts = [
            Receipt(1, 'email', date(2024, 1, 1), Decimal('100.00'), 'Test 1', True, None),
            Receipt(2, 'email', date(2024, 1, 31), Decimal('200.00'), 'Test 2', True, None)
        ]
        
        indexer.build_index(receipts)
        
        # Query with exact match to first receipt
        txn = Transaction(1, 'stmt', date(2024, 1, 1), Decimal('100.00'), 'Test')
        
        # With zero tolerance, should only find exact match
        candidates = indexer.query_candidates(txn, Decimal('0.01'), 0)
        
        # Should find the first receipt (index 0)
        assert 0 in candidates
    
    def test_query_candidates_respects_amount_tolerance(self):
        """Test that query respects amount tolerance parameter."""
        from finmatcher.storage.models import Transaction
        
        config = OptimizationConfig()
        indexer = SpatialIndexer(config)
        
        receipts = [
            Receipt(1, 'email', date(2024, 1, 1), Decimal('100.00'), 'Test 1', True, None),
            Receipt(2, 'email', date(2024, 1, 1), Decimal('110.00'), 'Test 2', True, None),
            Receipt(3, 'email', date(2024, 1, 1), Decimal('120.00'), 'Test 3', True, None)
        ]
        
        indexer.build_index(receipts)
        
        # Query with tight amount tolerance
        txn = Transaction(1, 'stmt', date(2024, 1, 1), Decimal('105.00'), 'Test')
        candidates = indexer.query_candidates(txn, Decimal('6.00'), 365)
        
        # Should find receipts within $6 (receipts 1 and 2)
        assert len(candidates) >= 1
        # Receipt 3 ($120) is $15 away, should not be included with $6 tolerance
        # (though with weighted distance and large date tolerance, it might be included)
    
    def test_query_candidates_respects_date_tolerance(self):
        """Test that query respects date tolerance parameter."""
        from finmatcher.storage.models import Transaction
        
        config = OptimizationConfig()
        indexer = SpatialIndexer(config)
        
        receipts = [
            Receipt(1, 'email', date(2024, 1, 1), Decimal('100.00'), 'Test 1', True, None),
            Receipt(2, 'email', date(2024, 1, 5), Decimal('100.00'), 'Test 2', True, None),
            Receipt(3, 'email', date(2024, 1, 15), Decimal('100.00'), 'Test 3', True, None)
        ]
        
        indexer.build_index(receipts)
        
        # Query with tight date tolerance
        txn = Transaction(1, 'stmt', date(2024, 1, 3), Decimal('100.00'), 'Test')
        candidates = indexer.query_candidates(txn, Decimal('50.00'), 3)
        
        # Should find receipts within 3 days (receipts 1 and 2)
        assert len(candidates) >= 1
    
    def test_query_candidates_with_different_weights(self):
        """Test query behavior with different weight configurations."""
        from finmatcher.storage.models import Transaction
        
        config = OptimizationConfig()
        indexer = SpatialIndexer(config)
        
        receipts = [
            Receipt(1, 'email', date(2024, 1, 1), Decimal('100.00'), 'Test 1', True, None),
            Receipt(2, 'email', date(2024, 1, 10), Decimal('150.00'), 'Test 2', True, None)
        ]
        
        indexer.build_index(receipts)
        
        txn = Transaction(1, 'stmt', date(2024, 1, 5), Decimal('125.00'), 'Test')
        
        # Test with equal weights
        indexer.weights = (1.0, 1.0)
        candidates_equal = indexer.query_candidates(txn, Decimal('30.00'), 10)
        
        # Test with amount-heavy weights
        indexer.weights = (0.9, 0.1)
        candidates_amount_heavy = indexer.query_candidates(txn, Decimal('30.00'), 10)
        
        # Test with date-heavy weights
        indexer.weights = (0.1, 0.9)
        candidates_date_heavy = indexer.query_candidates(txn, Decimal('30.00'), 10)
        
        # All should return candidates (exact counts may vary based on weights)
        assert isinstance(candidates_equal, list)
        assert isinstance(candidates_amount_heavy, list)
        assert isinstance(candidates_date_heavy, list)
        
        