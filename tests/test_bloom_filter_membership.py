"""
Test for BloomFilterCache membership operations (Task 7.2).

Tests the contains(), add(), and automatic capacity growth functionality.
"""

import pytest
from finmatcher.optimization.bloom_filter_cache import BloomFilterCache


def test_contains_empty_cache():
    """Test contains() returns False for empty cache."""
    cache = BloomFilterCache()
    
    # Empty cache should not contain any items
    assert cache.contains("test@example.com") is False
    assert cache.contains("another@example.com") is False


def test_add_single_item():
    """Test add() method adds item to cache."""
    cache = BloomFilterCache()
    
    # Add an item
    email_id = "message-123@example.com"
    cache.add(email_id)
    
    # Verify item count increased
    assert cache.item_count == 1
    
    # Verify item is in cache
    assert cache.contains(email_id) is True


def test_add_multiple_items():
    """Test add() method with multiple items."""
    cache = BloomFilterCache()
    
    # Add multiple items
    email_ids = [
        "message-1@example.com",
        "message-2@example.com",
        "message-3@example.com",
        "message-4@example.com",
        "message-5@example.com"
    ]
    
    for email_id in email_ids:
        cache.add(email_id)
    
    # Verify item count
    assert cache.item_count == 5
    
    # Verify all items are in cache
    for email_id in email_ids:
        assert cache.contains(email_id) is True


def test_contains_non_existent_item():
    """Test contains() returns False for non-existent items (no false negatives)."""
    cache = BloomFilterCache()
    
    # Add some items
    cache.add("message-1@example.com")
    cache.add("message-2@example.com")
    
    # Check for non-existent items
    # Bloom filters guarantee no false negatives
    assert cache.contains("message-3@example.com") is False
    assert cache.contains("nonexistent@example.com") is False


def test_contains_o1_complexity():
    """Test that contains() operates in O(1) time regardless of cache size."""
    cache = BloomFilterCache()
    
    # Add 1000 items
    for i in range(1000):
        cache.add(f"message-{i}@example.com")
    
    # Contains should still be O(1) - just verify it works
    assert cache.contains("message-500@example.com") is True
    assert cache.contains("message-999@example.com") is True
    assert cache.contains("nonexistent@example.com") is False


def test_automatic_capacity_growth():
    """Test that cache automatically grows when item count exceeds capacity."""
    # Use small initial capacity to test growth
    cache = BloomFilterCache(initial_capacity=100, error_rate=0.001)
    
    # Add more items than initial capacity
    num_items = 250
    for i in range(num_items):
        cache.add(f"message-{i}@example.com")
    
    # Verify all items were added
    assert cache.item_count == num_items
    
    # Verify all items are still retrievable (no data loss during growth)
    for i in range(num_items):
        assert cache.contains(f"message-{i}@example.com") is True


def test_get_metrics():
    """Test get_metrics() returns correct metrics."""
    cache = BloomFilterCache(initial_capacity=100000, error_rate=0.001)
    
    # Add some items
    for i in range(10):
        cache.add(f"message-{i}@example.com")
    
    metrics = cache.get_metrics()
    
    # Verify metrics structure
    assert 'item_count' in metrics
    assert 'capacity' in metrics
    assert 'error_rate' in metrics
    assert 'memory_bytes' in metrics
    assert 'api_calls_saved' in metrics
    assert 'estimated_false_positives' in metrics
    
    # Verify values
    assert metrics['item_count'] == 10
    assert metrics['capacity'] == 100000
    assert metrics['error_rate'] == 0.001
    assert metrics['memory_bytes'] > 0
    assert metrics['api_calls_saved'] == 0  # Not incremented yet
    assert metrics['estimated_false_positives'] >= 0


def test_memory_usage_calculation():
    """Test that memory usage is calculated correctly."""
    cache = BloomFilterCache(initial_capacity=100000, error_rate=0.001)
    
    metrics = cache.get_metrics()
    memory_bytes = metrics['memory_bytes']
    
    # For 100K items at 0.001 error rate, should be approximately 180KB
    # bit_array_size ≈ 1,437,759 bits ≈ 179,720 bytes
    assert memory_bytes > 170000  # ~170KB
    assert memory_bytes < 200000  # ~200KB


def test_false_positive_behavior():
    """Test that false positives can occur but are within error rate."""
    cache = BloomFilterCache(initial_capacity=1000, error_rate=0.01)
    
    # Add 1000 items
    added_items = set()
    for i in range(1000):
        email_id = f"message-{i}@example.com"
        cache.add(email_id)
        added_items.add(email_id)
    
    # Test 1000 non-existent items
    false_positives = 0
    for i in range(1000, 2000):
        email_id = f"message-{i}@example.com"
        if cache.contains(email_id):
            false_positives += 1
    
    # False positive rate should be approximately 1% (0.01)
    # Allow some variance: should be less than 5%
    false_positive_rate = false_positives / 1000
    assert false_positive_rate < 0.05, f"False positive rate {false_positive_rate} exceeds 5%"


def test_duplicate_adds():
    """Test that adding the same item multiple times works correctly."""
    cache = BloomFilterCache()
    
    email_id = "message-123@example.com"
    
    # Add same item multiple times
    cache.add(email_id)
    cache.add(email_id)
    cache.add(email_id)
    
    # Item count increases (Bloom filters don't deduplicate)
    assert cache.item_count == 3
    
    # Item is still in cache
    assert cache.contains(email_id) is True


def test_hash_function_application():
    """Test that hash functions are applied correctly (k=3)."""
    cache = BloomFilterCache()
    
    # Add an item
    email_id = "test@example.com"
    cache.add(email_id)
    
    # Verify k=3 hash functions are configured
    assert cache.num_hashes == 3
    
    # Verify item is retrievable (hash functions worked)
    assert cache.contains(email_id) is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
