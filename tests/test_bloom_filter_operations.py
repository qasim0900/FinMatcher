"""
Unit tests for Bloom filter operations (Task 7.5).

Tests basic operations of the BloomFilterCache component:
- contains() returns false for non-members (no false negatives)
- add() and contains() for known items
- Memory footprint under 10MB for 1M items

Validates: Requirements 3.11
"""

import pytest
from finmatcher.optimization.bloom_filter_cache import BloomFilterCache


class TestBloomFilterNoFalseNegatives:
    """Test that contains() never returns false for members (no false negatives)."""
    
    def test_contains_returns_false_for_non_members(self):
        """Test contains() returns False for items not in the cache."""
        cache = BloomFilterCache(initial_capacity=1000, error_rate=0.001)
        
        # Add some items