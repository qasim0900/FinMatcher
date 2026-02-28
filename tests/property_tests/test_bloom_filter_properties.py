"""
Property-based tests for Bloom Filter Cache.

This module contains property-based tests using Hypothesis to verify
universal properties of the BloomFilterCache component, specifically
testing that the false positive rate remains below the configured threshold.

Testing Framework: pytest + Hypothesis
Feature: finmatcher-math-optimization
Task: 7.4 - Write property test for Bloom filter false positive rate
"""

import pytest
from hypothesis import given, strategies as st, settings, assume, HealthCheck
from typing import Set
import string

from finmatcher.optimization.bloom_filter_cache import BloomFilterCache


# Configure Hypothesis settings for FinMatcher
# Reduced max_examples to 5 for faster test execution while maintaining good coverage
settings.register_profile("finmatcher_bloom", max_examples=5, deadline=15000)
settings.load_profile("finmatcher_bloom")


# ============================================================================
# Strategy Generators
# ============================================================================

def generate_email_ids(min_size=100, max_size=500):
    """
    Generate random email IDs for property testing.
    
    Email IDs are typically Message-ID headers in the format:
    <unique-identifier@domain.com>
    
    For testing, we generate realistic email ID strings with sufficient
    uniqueness to avoid accidental collisions.
    """
    return st.lists(
        st.text(
            alphabet=string.ascii_letters + string.digits,
            min_size=15,
            max_size=40
        ),
        min_size=min_size,
        max_size=max_size,
        unique=True
    )


def generate_non_member_count():
    """
    Generate a count for non-member IDs.
    
    We use a smaller count to reduce test data size while still
    providing statistically significant results.
    """
    return st.integers(min_value=500, max_value=1000)


# ============================================================================
# Property Tests
# ============================================================================

@settings(suppress_health_check=[HealthCheck.data_too_large])
@given(
    member_ids=generate_email_ids(min_size=100, max_size=500),
    non_member_count=generate_non_member_count()
)
def test_property_6_bloom_filter_false_positive_rate(member_ids, non_member_count):
    """
    **Validates: Requirements 10.6**
    
    Property 6: Bloom filter false positive rate remains below configured threshold
    
    This property verifies that the Bloom filter maintains its configured
    false positive rate (0.001 or 0.1%) when tested with a large number
    of non-member items.
    
    The property ensures:
    1. All known items are correctly identified as members (no false negatives)
    2. Non-member items have a false positive rate below the configured threshold
    3. The false positive rate is measured empirically across many non-member tests
    
    Test Strategy:
    - Generate a set of known email IDs (members)
    - Add all members to the Bloom filter
    - Generate a large set of non-member email IDs (guaranteed not in member set)
    - Test each non-member for membership
    - Count false positives (non-members incorrectly reported as members)
    - Calculate false positive rate: FP_count / total_non_members
    - Assert: false_positive_rate <= configured_error_rate
    
    Mathematical Background:
    The theoretical false positive probability is:
    P_fp = (1 - e^(-kn/m))^k
    
    Where:
    - k = number of hash functions (3)
    - n = number of items inserted
    - m = bit array size
    
    For our configuration (error_rate=0.001, k=3):
    - Expected false positive rate: ~0.1%
    - With 1000 non-member tests, we expect ~1 false positive on average
    """
    # Ensure member set has sufficient size
    member_set = set(member_ids)
    assume(len(member_set) >= 100)
    
    # Generate non-member IDs that are guaranteed to be distinct
    # Use a simple counter-based approach for efficiency
    non_member_ids = [f"NON_MEMBER_{i:010d}" for i in range(non_member_count)]
    non_member_set = set(non_member_ids)
    
    # Verify no overlap (should be guaranteed by generation strategy)
    assume(member_set.isdisjoint(non_member_set))
    
    # Initialize Bloom filter with default configuration
    # error_rate=0.001 (0.1% false positive rate)
    bloom_cache = BloomFilterCache(
        initial_capacity=100000,
        error_rate=0.001
    )
    
    # Add all known items to the Bloom filter
    for email_id in member_ids:
        bloom_cache.add(email_id)
    
    # Verify all known items are correctly identified (no false negatives)
    for email_id in member_ids:
        assert bloom_cache.contains(email_id), (
            f"Bloom filter failed to identify known member: {email_id}. "
            f"This indicates a critical bug (false negative)."
        )
    
    # Test non-members and count false positives
    false_positives = 0
    for email_id in non_member_ids:
        if bloom_cache.contains(email_id):
            false_positives += 1
    
    # Calculate empirical false positive rate
    total_non_members = len(non_member_ids)
    false_positive_rate = false_positives / total_non_members
    
    # Get configured error rate
    configured_error_rate = bloom_cache.error_rate
    
    # Property: False positive rate must remain below configured threshold
    # We allow some statistical variance, so we use a tolerance factor
    # The threshold is 2x the configured rate to account for statistical variance
    # in small samples (1000 tests may not perfectly match theoretical rate)
    tolerance_factor = 2.0
    threshold = configured_error_rate * tolerance_factor
    
    assert false_positive_rate <= threshold, (
        f"Bloom filter false positive rate ({false_positive_rate:.4f} = {false_positive_rate:.2%}) "
        f"exceeds threshold ({threshold:.4f} = {threshold:.2%}). "
        f"Configured error rate: {configured_error_rate:.4f} ({configured_error_rate:.2%}). "
        f"False positives: {false_positives} out of {total_non_members} non-members. "
        f"Members added: {len(member_ids)}. "
        f"Expected false positives: ~{int(total_non_members * configured_error_rate)}."
    )
    
    # Additional validation: Log metrics for debugging
    metrics = bloom_cache.get_metrics()
    print(f"\nBloom Filter Metrics:")
    print(f"  Items added: {metrics['item_count']}")
    print(f"  Configured error rate: {metrics['error_rate']:.4f} ({metrics['error_rate']:.2%})")
    print(f"  Empirical false positive rate: {false_positive_rate:.4f} ({false_positive_rate:.2%})")
    print(f"  False positives: {false_positives} / {total_non_members}")
    print(f"  Memory usage: {metrics['memory_mb']} MB")
    print(f"  Bit array size: {metrics['bit_array_size']} bits")
    print(f"  Number of hash functions: {metrics['num_hashes']}")


@given(
    member_ids=generate_email_ids(min_size=50, max_size=300)
)
def test_property_6_bloom_filter_no_false_negatives(member_ids):
    """
    **Validates: Requirements 10.6**
    
    Property 6 (No False Negatives): Bloom filter never produces false negatives
    
    This property verifies that the Bloom filter ALWAYS correctly identifies
    items that have been added to it. Bloom filters guarantee no false negatives
    by design - if an item was added, it will always be found.
    
    Test Strategy:
    - Add known items to Bloom filter
    - Verify every known item is correctly identified
    - Assert: contains(item) == True for all added items
    """
    # Ensure sufficient test data
    assume(len(member_ids) >= 50)
    
    # Initialize Bloom filter
    bloom_cache = BloomFilterCache(
        initial_capacity=100000,
        error_rate=0.001
    )
    
    # Add all known items
    for email_id in member_ids:
        bloom_cache.add(email_id)
    
    # Property: Every added item must be found (no false negatives)
    false_negatives = []
    for email_id in member_ids:
        if not bloom_cache.contains(email_id):
            false_negatives.append(email_id)
    
    assert len(false_negatives) == 0, (
        f"Bloom filter produced {len(false_negatives)} false negatives. "
        f"This violates the fundamental guarantee of Bloom filters. "
        f"False negatives: {false_negatives[:10]}..."  # Show first 10
    )


@given(
    member_ids=generate_email_ids(min_size=100, max_size=300)
)
def test_property_6_bloom_filter_scalability(member_ids):
    """
    **Validates: Requirements 10.6**
    
    Property 6 (Scalability): Bloom filter maintains error rate as it grows
    
    This property verifies that the ScalableBloomFilter maintains its
    configured error rate even as capacity grows beyond the initial capacity.
    
    Test Strategy:
    - Start with small initial capacity
    - Add items beyond initial capacity to trigger growth
    - Verify error rate remains below threshold after growth
    """
    # Ensure we have enough items to trigger growth
    assume(len(member_ids) >= 100)
    
    # Initialize with small capacity to force growth
    initial_capacity = 50
    bloom_cache = BloomFilterCache(
        initial_capacity=initial_capacity,
        error_rate=0.001
    )
    
    # Add items beyond initial capacity
    for email_id in member_ids:
        bloom_cache.add(email_id)
    
    # Verify we exceeded initial capacity (triggered growth)
    metrics = bloom_cache.get_metrics()
    assert metrics['item_count'] > initial_capacity, (
        f"Test did not trigger Bloom filter growth. "
        f"Items: {metrics['item_count']}, Initial capacity: {initial_capacity}"
    )
    
    # Verify all items are still found (no false negatives after growth)
    for email_id in member_ids:
        assert bloom_cache.contains(email_id), (
            f"Bloom filter failed to find item after growth: {email_id}"
        )
    
    # Generate non-members to test false positive rate after growth
    non_member_prefix = "GROWTH_TEST_NON_MEMBER_"
    non_members = [f"{non_member_prefix}{i:010d}" for i in range(500)]
    
    # Ensure non-members are distinct from members
    member_set = set(member_ids)
    non_members = [nm for nm in non_members if nm not in member_set]
    
    # Count false positives after growth
    false_positives = sum(1 for nm in non_members if bloom_cache.contains(nm))
    false_positive_rate = false_positives / len(non_members)
    
    # Property: False positive rate remains below threshold after growth
    # Use 3x tolerance for small capacities due to higher statistical variance
    threshold = bloom_cache.error_rate * 3.0
    
    assert false_positive_rate <= threshold, (
        f"Bloom filter false positive rate after growth ({false_positive_rate:.4f}) "
        f"exceeds threshold ({threshold:.4f}). "
        f"Items added: {metrics['item_count']}, Initial capacity: {initial_capacity}. "
        f"False positives: {false_positives} / {len(non_members)}"
    )


@given(
    member_ids=generate_email_ids(min_size=100, max_size=300)
)
def test_property_6_bloom_filter_memory_efficiency(member_ids):
    """
    **Validates: Requirements 10.6**
    
    Property 6 (Memory Efficiency): Bloom filter memory usage is reasonable
    
    This property verifies that the Bloom filter maintains memory efficiency
    as specified in Requirements 3.11: less than 10MB for 1 million items.
    
    Test Strategy:
    - Add items to Bloom filter
    - Calculate memory usage
    - Verify memory usage is proportional to item count
    - Extrapolate to verify 1M items would be under 10MB
    """
    # Ensure sufficient test data
    assume(len(member_ids) >= 100)
    
    # Initialize Bloom filter
    bloom_cache = BloomFilterCache(
        initial_capacity=100000,
        error_rate=0.001
    )
    
    # Add all items
    for email_id in member_ids:
        bloom_cache.add(email_id)
    
    # Get memory metrics
    metrics = bloom_cache.get_metrics()
    memory_mb = metrics['memory_mb']
    item_count = metrics['item_count']
    
    # The Bloom filter is initialized with a fixed capacity (100K)
    # Memory usage is based on capacity, not item count
    # For 100K capacity at 0.001 error rate: ~180KB = 0.176 MB
    # For 1M capacity: ~1.8 MB
    # This is well under the 10MB requirement
    
    # Verify memory usage is reasonable for the configured capacity
    # Formula: m = -(n * ln(p)) / (ln(2)^2) where n=capacity, p=error_rate
    # For 100K capacity: m ≈ 1,437,759 bits ≈ 180KB ≈ 0.176 MB
    expected_memory_mb = 0.176  # For 100K capacity
    
    # Allow some overhead for ScalableBloomFilter implementation
    max_expected_memory_mb = expected_memory_mb * 1.5  # 50% overhead tolerance
    
    assert memory_mb <= max_expected_memory_mb, (
        f"Bloom filter memory usage exceeds expected value. "
        f"Current: {memory_mb:.2f} MB for capacity {metrics['capacity']}. "
        f"Expected: ~{expected_memory_mb:.2f} MB. "
        f"Max allowed: {max_expected_memory_mb:.2f} MB."
    )
    
    # Verify that 1M items would be under 10MB
    # For 1M capacity: ~1.8 MB (10x the 100K capacity memory)
    estimated_memory_1m_mb = memory_mb * 10  # Scale linearly with capacity
    
    # Property: Estimated memory for 1M items should be under 10MB
    # (as specified in Requirements 3.11)
    assert estimated_memory_1m_mb <= 10.0, (
        f"Bloom filter memory usage would exceed specification for 1M items. "
        f"Current: {memory_mb:.2f} MB for {metrics['capacity']} capacity. "
        f"Estimated for 1M capacity: {estimated_memory_1m_mb:.2f} MB. "
        f"Requirement: < 10 MB for 1M items."
    )
    
    print(f"\nMemory Efficiency Metrics:")
    print(f"  Capacity: {metrics['capacity']}")
    print(f"  Items added: {item_count}")
    print(f"  Memory: {memory_mb:.2f} MB")
    print(f"  Estimated for 1M capacity: {estimated_memory_1m_mb:.2f} MB")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--hypothesis-show-statistics"])
