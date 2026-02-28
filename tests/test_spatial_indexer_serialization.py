"""
Unit tests for SpatialIndexer serialization and deserialization.

Tests the serialize() and deserialize() methods to ensure K-D tree structures
can be cached to disk and restored correctly.

Validates Requirements: 8.1, 8.2, 8.3, 8.5, 8.7
"""

import unittest
import os
import tempfile
import shutil
from datetime import date
from decimal import Decimal

from finmatcher.storage.models import Receipt
from finmatcher.optimization.config import OptimizationConfig
from finmatcher.optimization.spatial_indexer import SpatialIndexer


class TestSpatialIndexerSerialization(unittest.TestCase):
    """Test cases for K-D tree serialization and deserialization."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create temporary directory for cache files
        self.temp_dir = tempfile.mkdtemp()
        
        # Create test receipts
        self.receipts = [
            Receipt(1, 'email1', date(2024, 1, 1), Decimal('100.00'), 'Test 1', True, None),
            Receipt(2, 'email2', date(2024, 1, 15), Decimal('200.00'), 'Test 2', True, None),
            Receipt(3, 'email3', date(2024, 2, 1), Decimal('150.00'), 'Test 3', True, None),
            Receipt(4, 'email4', date(2024, 2, 15), Decimal('250.00'), 'Test 4', True, None),
        ]
        
        # Create config with caching enabled
        self.config = OptimizationConfig(
            kdtree_cache_enabled=True,
            kdtree_cache_path=self.temp_dir
        )
    
    def tearDown(self):
        """Clean up test fixtures."""
        # Remove temporary directory
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_serialize_creates_file(self):
        """Test that serialize() creates a pickle file."""
        # Build index
        indexer = SpatialIndexer(self.config)
        indexer.build_index(self.receipts)
        
        # Serialize
        cache_path = os.path.join(self.temp_dir, 'test_kdtree.pkl')
        indexer.serialize(cache_path)
        
        # Verify file exists
        self.assertTrue(os.path.exists(cache_path))
        
        # Verify file is not empty
        self.assertGreater(os.path.getsize(cache_path), 0)
    
    def test_serialize_without_build_raises_error(self):
        """Test that serialize() raises error if K-D tree not built."""
        indexer = SpatialIndexer(self.config)
        cache_path = os.path.join(self.temp_dir, 'test_kdtree.pkl')
        
        with self.assertRaises(ValueError) as context:
            indexer.serialize(cache_path)
        
        self.assertIn("K-D tree has not been built", str(context.exception))
    
    def test_serialize_creates_directory_if_missing(self):
        """Test that serialize() creates cache directory if it doesn't exist."""
        # Build index
        indexer = SpatialIndexer(self.config)
        indexer.build_index(self.receipts)
        
        # Serialize to non-existent directory
        cache_path = os.path.join(self.temp_dir, 'subdir', 'test_kdtree.pkl')
        indexer.serialize(cache_path)
        
        # Verify file exists
        self.assertTrue(os.path.exists(cache_path))
    
    def test_deserialize_loads_kdtree(self):
        """Test that deserialize() loads K-D tree from file."""
        # Build and serialize
        indexer1 = SpatialIndexer(self.config)
        indexer1.build_index(self.receipts)
        cache_path = os.path.join(self.temp_dir, 'test_kdtree.pkl')
        indexer1.serialize(cache_path)
        
        # Deserialize into new indexer
        indexer2 = SpatialIndexer(self.config)
        success = indexer2.deserialize(cache_path)
        
        # Verify success
        self.assertTrue(success)
        self.assertIsNotNone(indexer2.kdtree)
        self.assertIsNotNone(indexer2.feature_vectors)
        self.assertIsNotNone(indexer2.normalization_params)
    
    def test_deserialize_missing_file_returns_false(self):
        """Test that deserialize() returns False for missing file."""
        indexer = SpatialIndexer(self.config)
        cache_path = os.path.join(self.temp_dir, 'nonexistent.pkl')
        
        success = indexer.deserialize(cache_path)
        
        self.assertFalse(success)
    
    def test_deserialize_preserves_feature_vectors(self):
        """Test that deserialized K-D tree has same feature vectors."""
        # Build and serialize
        indexer1 = SpatialIndexer(self.config)
        indexer1.build_index(self.receipts)
        cache_path = os.path.join(self.temp_dir, 'test_kdtree.pkl')
        indexer1.serialize(cache_path)
        
        # Store original feature vectors
        original_vectors = indexer1.feature_vectors.copy()
        
        # Deserialize
        indexer2 = SpatialIndexer(self.config)
        indexer2.deserialize(cache_path)
        
        # Verify feature vectors match
        import numpy as np
        np.testing.assert_array_equal(indexer2.feature_vectors, original_vectors)
    
    def test_deserialize_preserves_normalization_params(self):
        """Test that deserialized K-D tree has same normalization params."""
        # Build and serialize
        indexer1 = SpatialIndexer(self.config)
        indexer1.build_index(self.receipts)
        cache_path = os.path.join(self.temp_dir, 'test_kdtree.pkl')
        indexer1.serialize(cache_path)
        
        # Store original params
        original_params = indexer1.normalization_params
        
        # Deserialize
        indexer2 = SpatialIndexer(self.config)
        indexer2.deserialize(cache_path)
        
        # Verify params match
        self.assertEqual(indexer2.normalization_params.amount_min, original_params.amount_min)
        self.assertEqual(indexer2.normalization_params.amount_max, original_params.amount_max)
        self.assertEqual(indexer2.normalization_params.date_min, original_params.date_min)
        self.assertEqual(indexer2.normalization_params.date_max, original_params.date_max)
        self.assertEqual(indexer2.normalization_params.dataset_hash, original_params.dataset_hash)
    
    def test_deserialize_preserves_weights(self):
        """Test that deserialized K-D tree has same weights."""
        # Build and serialize with custom weights
        indexer1 = SpatialIndexer(self.config)
        indexer1.weights = (0.7, 0.3)
        indexer1.build_index(self.receipts)
        cache_path = os.path.join(self.temp_dir, 'test_kdtree.pkl')
        indexer1.serialize(cache_path)
        
        # Deserialize
        indexer2 = SpatialIndexer(self.config)
        indexer2.deserialize(cache_path)
        
        # Verify weights match
        self.assertEqual(indexer2.weights, (0.7, 0.3))
    
    def test_deserialize_kdtree_produces_same_query_results(self):
        """Test that deserialized K-D tree produces same query results."""
        from finmatcher.storage.models import Transaction
        
        # Build and serialize
        indexer1 = SpatialIndexer(self.config)
        indexer1.build_index(self.receipts)
        cache_path = os.path.join(self.temp_dir, 'test_kdtree.pkl')
        indexer1.serialize(cache_path)
        
        # Query original
        txn = Transaction(1, 'stmt', date(2024, 1, 10), Decimal('150.00'), 'Test')
        results1 = indexer1.query_candidates(txn, Decimal('50.00'), 10)
        
        # Deserialize and query
        indexer2 = SpatialIndexer(self.config)
        indexer2.deserialize(cache_path)
        results2 = indexer2.query_candidates(txn, Decimal('50.00'), 10)
        
        # Verify results match
        self.assertEqual(sorted(results1), sorted(results2))
    
    def test_build_index_with_caching_enabled_serializes_automatically(self):
        """Test that build_index() serializes automatically when caching enabled."""
        # Build index with caching enabled
        indexer = SpatialIndexer(self.config)
        indexer.build_index(self.receipts)
        
        # Verify cache file was created
        cache_file = f"{self.temp_dir}/kdtree_{indexer.normalization_params.dataset_hash}.pkl"
        self.assertTrue(os.path.exists(cache_file))
    
    def test_calculate_dataset_hash_consistent(self):
        """Test that _calculate_dataset_hash() produces consistent results."""
        indexer = SpatialIndexer(self.config)
        
        # Calculate hash twice
        hash1 = indexer._calculate_dataset_hash(self.receipts)
        hash2 = indexer._calculate_dataset_hash(self.receipts)
        
        # Verify hashes match
        self.assertEqual(hash1, hash2)
    
    def test_calculate_dataset_hash_different_for_different_receipts(self):
        """Test that _calculate_dataset_hash() produces different hashes for different receipts."""
        indexer = SpatialIndexer(self.config)
        
        # Calculate hash for original receipts
        hash1 = indexer._calculate_dataset_hash(self.receipts)
        
        # Calculate hash for modified receipts
        modified_receipts = self.receipts + [
            Receipt(5, 'email5', date(2024, 3, 1), Decimal('300.00'), 'Test 5', True, None)
        ]
        hash2 = indexer._calculate_dataset_hash(modified_receipts)
        
        # Verify hashes differ
        self.assertNotEqual(hash1, hash2)
    
    def test_calculate_dataset_hash_is_sha256(self):
        """Test that _calculate_dataset_hash() produces SHA-256 hash (64 hex chars)."""
        indexer = SpatialIndexer(self.config)
        hash_val = indexer._calculate_dataset_hash(self.receipts)
        
        # Verify hash is 64 characters (SHA-256 hex)
        self.assertEqual(len(hash_val), 64)
        
        # Verify hash is hexadecimal
        self.assertTrue(all(c in '0123456789abcdef' for c in hash_val))
    
    def test_deserialize_validates_feature_vector_shape(self):
        """Test that deserialize() validates feature vector shape."""
        import pickle
        
        # Create invalid serialization data with wrong shape
        invalid_data = {
            'kdtree': None,
            'feature_vectors': [[1, 2, 3]],  # Wrong shape (should be (M, 2))
            'normalization_params': None,
            'weights': (1.0, 1.0)
        }
        
        # Write invalid data to file
        cache_path = os.path.join(self.temp_dir, 'invalid.pkl')
        with open(cache_path, 'wb') as f:
            pickle.dump(invalid_data, f)
        
        # Try to deserialize
        indexer = SpatialIndexer(self.config)
        success = indexer.deserialize(cache_path)
        
        # Verify deserialization failed
        self.assertFalse(success)
    
    def test_deserialize_validates_required_keys(self):
        """Test that deserialize() validates required keys are present."""
        import pickle
        
        # Create invalid serialization data missing keys
        invalid_data = {
            'kdtree': None,
            'feature_vectors': [[1, 2]]
            # Missing 'normalization_params' and 'weights'
        }
        
        # Write invalid data to file
        cache_path = os.path.join(self.temp_dir, 'invalid.pkl')
        with open(cache_path, 'wb') as f:
            pickle.dump(invalid_data, f)
        
        # Try to deserialize
        indexer = SpatialIndexer(self.config)
        success = indexer.deserialize(cache_path)
        
        # Verify deserialization failed
        self.assertFalse(success)


if __name__ == '__main__':
    unittest.main()
