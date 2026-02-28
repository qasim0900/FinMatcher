"""
Test for BloomFilterCache initialization (Task 7.1).
"""

import math
import pytest
from finmatcher.optimization.bloom_filter_cache import BloomFilterCache


def test_bloom_filter_cache_initialization_default():
    """Test BloomFilterCache initialization with default parameters."""
    cache = BloomFilterCache()
    
    # Verify default parameters
    assert cache.initial_capacity == 100000
    assert cache.error_rate == 0.001
    assert cache.num_hashes == 3
    assert cache.item_count == 0
    assert cache.api_calls_saved == 0
    
    # Verify bloom_filter is initialized
    assert cache.bloom_filter is not None


def test_bloom_filter_cache_initialization_custom():
    """Test BloomFilterCache initialization with custom parameters."""
    cache = BloomFilterCache(initial_capacity=50000, error_rate=0.01)
    
    # Verify custom parameters
    assert cache.initial_capacity == 50000
    assert cache.error_rate == 0.01
    assert cache.num_hashes == 3
    assert cache.item_count == 0
    assert cache.api_calls_saved == 0


def test_bloom_filter_bit_array_size_calculation():
    """Test that bit array size is calculated correctly using the formula."""
    # Formula: m = -(n * ln(p)) / (ln(2)^2)
    n = 100000
    p = 0.001
    expected_size = int(-((n * math.log(p)) / (math.log(2) ** 2)))
    
    cache = BloomFilterCache(initial_capacity=n, error_rate=p)
    
    # Verify the calculated bit array size matches the formula
    assert cache.bit_array_size == expected_size
    # For n=100K, p=0.001, expected size is approximately 1,437,759 bits
    assert cache.bit_array_size > 1400000
    assert cache.bit_array_size < 1500000


def test_bloom_filter_hash_functions():
    """Test that k=3 hash functions are configured."""
    cache = BloomFilterCache()
    
    # Verify k=3 hash functions as specified in requirements
    assert cache.num_hashes == 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
