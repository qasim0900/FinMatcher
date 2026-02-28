"""
Unit tests for SpatialIndexer cache management functionality.

Tests cache hit/miss logic, cache expiration policy, and dataset hash validation.

Validates Requirements: 8.4, 8.5, 8.6, 8.7, 8.8, 8.9
"""

import pytest
import os
import time
import tempfile
from datetime import date
from decimal import Decimal

from finmatcher.optimization.spatial_indexer import SpatialIndexer
from finmatcher.optimization.config import OptimizationConfig
from finmatcher.storage.models import Receipt


class TestSpatialIndexerCacheManagement:
    """Test cache management functionality."""

    @pytest.fixture
    def temp_cache_dir(self):
        """Create a temporary cache directory for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    @pytest.fixture
    def sample_receipts(self):
        """Create sample receipts for testing."""
        return [
            Receipt(1, 'email1', date(2024, 1, 1), Decimal('100.00'), 'Test 1', True, None),
            Receipt(2, 'email2', date(2024, 1, 15), Decimal('200.00'), 'Test 2', True, None),
            Receipt(3, 'email3', date(2024, 2, 1), Decimal('150.00'), 'Test 3', True, None),
        ]

    def test_cache_hit_loads_from_cache(self, temp_cache_dir, sample_receipts):
        """
        Test that build_index loads from cache on cache hit.
        
        Validates Requirements: 8.4, 8.5, 8.8
        """
        # Create config with caching enabled
        config = OptimizationConfig(
            kdtree_cache_enabled=True,
            kdtree_cache_path=temp_cache_dir,
            kdtree_cache_expiration_days=7
        )
        
        # First build - should create cache
        indexer1 = SpatialIndexer(config)
        indexer1.build_index(sample_receipts)
        
        # Verify cache file was created
        dataset_hash = indexer1.normalization_params.dataset_hash
        cache_path = f"{temp_cache_dir}/kdtree_{dataset_hash}.pkl"
        assert os.path.exists(cache_path), "Cache file should be created"
        
        # Second build with same receipts - should load from cache
        indexer2 = SpatialIndexer(config)
        indexer2.build_index(sample_receipts)
        
        # Verify both indexers have same data
        assert indexer2.kdtree is not None
        assert indexer2.normalization_params.dataset_hash == dataset_hash
        assert indexer2.feature_vectors.shape == indexer1.feature_vectors.shape

    def test_cache_miss_on_different_dataset(self, temp_cache_dir, sample_receipts):
        """
        Test that build_index rebuilds on dataset hash mismatch.
        
        Validates Requirements: 8.5, 8.6
        """
        config = OptimizationConfig(
            kdtree_cache_enabled=True,
            kdtree_cache_path=temp_cache_dir,
            kdtree_cache_expiration_days=7
        )
        
        # First build with original receipts
        indexer1 = SpatialIndexer(config)
        indexer1.build_index(sample_receipts)
        original_hash = indexer1.normalization_params.dataset_hash
        
        # Second build with modified receipts (different dataset)
        modified_receipts = sample_receipts + [
            Receipt(4, 'email4', date(2024, 3, 1), Decimal('300.00'), 'Test 4', True, None)
        ]
        indexer2 = SpatialIndexer(config)
        indexer2.build_index(modified_receipts)
        new_hash = indexer2.normalization_params.dataset_hash
        
        # Verify different hashes
        assert new_hash != original_hash, "Different datasets should have different hashes"
        
        # Verify new cache file was created
        new_cache_path = f"{temp_cache_dir}/kdtree_{new_hash}.pkl"
        assert os.path.exists(new_cache_path), "New cache file should be created"

    def test_cache_expiration_policy(self, temp_cache_dir, sample_receipts):
        """
        Test that cache expires after configured days.
        
        Validates Requirements: 8.9
        """
        config = OptimizationConfig(
            kdtree_cache_enabled=True,
            kdtree_cache_path=temp_cache_dir,
            kdtree_cache_expiration_days=0  # Expire immediately for testing
        )
        
        # Build index to create cache
        indexer1 = SpatialIndexer(config)
        indexer1.build_index(sample_receipts)
        
        dataset_hash = indexer1.normalization_params.dataset_hash
        cache_path = f"{temp_cache_dir}/kdtree_{dataset_hash}.pkl"
        
        # Verify cache file exists
        assert os.path.exists(cache_path)
        
        # Wait a moment to ensure file is older than 0 days
        time.sleep(0.1)
        
        # Check cache validity - should be expired
        indexer2 = SpatialIndexer(config)
        is_valid = indexer2._is_cache_valid(cache_path)
        assert not is_valid, "Cache should be expired with 0 day expiration"

    def test_cache_not_expired_within_window(self, temp_cache_dir, sample_receipts):
        """
        Test that cache is valid within expiration window.
        
        Validates Requirements: 8.9
        """
        config = OptimizationConfig(
            kdtree_cache_enabled=True,
            kdtree_cache_path=temp_cache_dir,
            kdtree_cache_expiration_days=7  # 7 days expiration
        )
        
        # Build index to create cache
        indexer1 = SpatialIndexer(config)
        indexer1.build_index(sample_receipts)
        
        dataset_hash = indexer1.normalization_params.dataset_hash
        cache_path = f"{temp_cache_dir}/kdtree_{dataset_hash}.pkl"
        
        # Check cache validity immediately - should be valid
        indexer2 = SpatialIndexer(config)
        is_valid = indexer2._is_cache_valid(cache_path)
        assert is_valid, "Cache should be valid immediately after creation"

    def test_cache_miss_on_missing_file(self, temp_cache_dir):
        """
        Test that _is_cache_valid returns False for missing file.
        
        Validates Requirements: 8.6
        """
        config = OptimizationConfig(
            kdtree_cache_enabled=True,
            kdtree_cache_path=temp_cache_dir,
            kdtree_cache_expiration_days=7
        )
        
        indexer = SpatialIndexer(config)
        non_existent_path = f"{temp_cache_dir}/nonexistent.pkl"
        
        is_valid = indexer._is_cache_valid(non_existent_path)
        assert not is_valid, "Non-existent cache file should be invalid"

    def test_cache_disabled_always_rebuilds(self, temp_cache_dir, sample_receipts):
        """
        Test that caching disabled always rebuilds index.
        
        Validates Requirements: 8.4
        """
        config = OptimizationConfig(
            kdtree_cache_enabled=False,
            kdtree_cache_path=temp_cache_dir,
            kdtree_cache_expiration_days=7
        )
        
        # First build
        indexer1 = SpatialIndexer(config)
        indexer1.build_index(sample_receipts)
        
        # Verify no cache file was created
        dataset_hash = indexer1.normalization_params.dataset_hash
        cache_path = f"{temp_cache_dir}/kdtree_{dataset_hash}.pkl"
        assert not os.path.exists(cache_path), "Cache file should not be created when caching disabled"
        
        # Second build - should rebuild (not load from cache)
        indexer2 = SpatialIndexer(config)
        indexer2.build_index(sample_receipts)
        
        # Both should work but no cache interaction
        assert indexer2.kdtree is not None
        assert indexer2.normalization_params.dataset_hash == dataset_hash

    def test_cache_hit_preserves_query_results(self, temp_cache_dir, sample_receipts):
        """
        Test that cached K-D tree produces same query results.
        
        Validates Requirements: 8.5, 8.7
        """
        from finmatcher.storage.models import Transaction
        
        config = OptimizationConfig(
            kdtree_cache_enabled=True,
            kdtree_cache_path=temp_cache_dir,
            kdtree_cache_expiration_days=7
        )
        
        # First build
        indexer1 = SpatialIndexer(config)
        indexer1.build_index(sample_receipts)
        
        # Query with first indexer
        txn = Transaction(1, 'stmt', date(2024, 1, 10), Decimal('110.00'), 'Test')
        results1 = indexer1.query_candidates(txn, Decimal('50.00'), 30)
        
        # Second build (should load from cache)
        indexer2 = SpatialIndexer(config)
        indexer2.build_index(sample_receipts)
        
        # Query with second indexer
        results2 = indexer2.query_candidates(txn, Decimal('50.00'), 30)
        
        # Results should be identical
        assert sorted(results1) == sorted(results2), "Cached K-D tree should produce same query results"

    def test_dataset_hash_validation(self, temp_cache_dir, sample_receipts):
        """
        Test that dataset hash is validated when loading from cache.
        
        Validates Requirements: 8.5
        """
        config = OptimizationConfig(
            kdtree_cache_enabled=True,
            kdtree_cache_path=temp_cache_dir,
            kdtree_cache_expiration_days=7
        )
        
        # Build with original receipts
        indexer1 = SpatialIndexer(config)
        indexer1.build_index(sample_receipts)
        original_hash = indexer1.normalization_params.dataset_hash
        
        # Build with different receipts (but try to use same cache)
        different_receipts = [
            Receipt(10, 'email10', date(2024, 5, 1), Decimal('500.00'), 'Different', True, None),
            Receipt(11, 'email11', date(2024, 5, 15), Decimal('600.00'), 'Different', True, None),
        ]
        indexer2 = SpatialIndexer(config)
        indexer2.build_index(different_receipts)
        different_hash = indexer2.normalization_params.dataset_hash
        
        # Hashes should be different
        assert different_hash != original_hash, "Different datasets should have different hashes"
        
        # Both cache files should exist
        cache_path1 = f"{temp_cache_dir}/kdtree_{original_hash}.pkl"
        cache_path2 = f"{temp_cache_dir}/kdtree_{different_hash}.pkl"
        assert os.path.exists(cache_path1)
        assert os.path.exists(cache_path2)
