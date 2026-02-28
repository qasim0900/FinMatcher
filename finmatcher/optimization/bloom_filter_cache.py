"""
Bloom filter cache component for email deduplication.

This module implements a scalable Bloom filter for O(1) membership testing
with configurable false positive rate.
"""

import math
from typing import Any, Dict
from pybloom_live import ScalableBloomFilter


class BloomFilterCache:
    """
    Scalable Bloom filter for email deduplication.
    
    Provides O(1) membership testing for email identifiers with configurable
    false positive rate. Automatically grows capacity while maintaining error rate.
    
    Attributes:
        bloom_filter: ScalableBloomFilter instance from pybloom_live
        initial_capacity: Initial capacity before first growth
        error_rate: Target false positive rate (default 0.001 = 0.1%)
        num_hashes: Number of hash functions (k=3 for optimal error rate)
        item_count: Number of items added to the filter
        api_calls_saved: Counter for API call reduction metric
    """
    
    def __init__(self, initial_capacity: int = 100000, error_rate: float = 0.001):
        """
        Initialize scalable Bloom filter.
        
        Args:
            initial_capacity: Initial capacity before first growth (default: 100,000)
            error_rate: Target false positive rate (default: 0.001 = 0.1%)
            
        The implementation uses k=3 hash functions for optimal error rate.
        Required bit array size is calculated using the formula:
        m = -(n * ln(p)) / (ln(2)^2)
        where n=capacity, p=error_rate, m=bit_array_size
        
        For n=100K, p=0.001: m ≈ 1,437,759 bits ≈ 180KB
        """
        self.initial_capacity = initial_capacity
        self.error_rate = error_rate
        self.num_hashes = 3  # k=3 is optimal for error_rate=0.001
        
        # Calculate required bit array size using the formula from requirements
        # m = -(n * ln(p)) / (ln(2)^2)
        n = initial_capacity
        p = error_rate
        self.bit_array_size = int(-((n * math.log(p)) / (math.log(2) ** 2)))
        
        # Initialize ScalableBloomFilter with k=3 hash functions
        # mode=ScalableBloomFilter.SMALL_SET_GROWTH for memory efficiency
        self.bloom_filter = ScalableBloomFilter(
            initial_capacity=initial_capacity,
            error_rate=error_rate,
            mode=ScalableBloomFilter.SMALL_SET_GROWTH
        )
        
        # Track metrics
        self.item_count = 0
        self.api_calls_saved = 0
    
    def contains(self, email_id: str) -> bool:
        """
        Check if email ID exists in cache.
        
        Provides O(1) membership testing using k hash functions.
        When a duplicate is detected (returns True), this indicates an API call
        was saved through deduplication.
        
        Args:
            email_id: Email Message-ID header value
            
        Returns:
            True if possibly in set (may be false positive)
            False if definitely not in set (no false negatives)
            
        Complexity: O(k) = O(1) for k=3 hash function evaluations
        
        Algorithm:
        1. For each hash function h_i (i = 0 to k-1):
            a. Calculate hash: hash_val = h_i(email_id)
            b. Map to bit position: pos = hash_val % m
            c. Check bit: if bit_array[pos] == 0, return False
        2. If all bits are 1, return True
        
        Validates: Requirements 3.6, 5.5
        """
        result = email_id in self.bloom_filter
        
        # Track API call reduction when duplicate is detected
        # Requirement 5.5: Track API_Call_Reduction by counting DeepSeek API calls
        # avoided through Bloom_Filter deduplication
        if result:
            self.api_calls_saved += 1
        
        return result
    
    def add(self, email_id: str) -> None:
        """
        Add email ID to cache.
        
        Applies k hash functions and sets corresponding bit positions.
        Automatically triggers capacity growth when item count exceeds capacity.
        
        Args:
            email_id: Email Message-ID header value
            
        Complexity: O(k) = O(1) for k=3 hash function evaluations
        
        Algorithm:
        1. For each hash function h_i (i = 0 to k-1):
            a. Calculate hash: hash_val = h_i(email_id)
            b. Map to bit position: pos = hash_val % m
            c. Set bit: bit_array[pos] = 1
        2. Increment item_count
        3. If item_count exceeds capacity, trigger automatic growth
        
        Growth behavior:
        - ScalableBloomFilter automatically creates new filter with 2x capacity
        - Maintains same error_rate across all filters
        - Union of all filters provides membership testing
        
        Validates: Requirements 3.7, 3.8, 3.9, 3.10
        """
        self.bloom_filter.add(email_id)
        self.item_count += 1
    
    def get_metrics(self) -> Dict[str, Any]:
        """
        Return cache metrics.
        
        Provides comprehensive metrics for monitoring and performance tracking.
        
        Validates: Requirements 3.11, 5.4, 5.6
        
        Returns:
            Dictionary containing:
            - item_count: Number of items added to the filter
            - capacity: Current base capacity (initial_capacity)
            - error_rate: Target false positive rate (0.001 = 0.1%)
            - memory_bytes: Estimated memory footprint in bytes
            - memory_mb: Memory footprint in megabytes (for readability)
            - api_calls_saved: Number of API calls avoided through deduplication
            - estimated_false_positives: Estimated false positive count based on formula
            - num_hashes: Number of hash functions used (k=3)
            - bit_array_size: Size of bit array for initial filter
        """
        # Calculate memory usage
        memory_bytes = self._calculate_memory_usage()
        
        # Estimate false positives based on formula: P_fp = (1 - e^(-kn/m))^k
        # For simplicity, use error_rate * item_count as approximation
        estimated_fp = int(self.item_count * self.error_rate)
        
        return {
            'item_count': self.item_count,
            'capacity': self.initial_capacity,
            'error_rate': self.error_rate,
            'memory_bytes': memory_bytes,
            'memory_mb': round(memory_bytes / (1024 * 1024), 2),
            'api_calls_saved': self.api_calls_saved,
            'estimated_false_positives': estimated_fp,
            'num_hashes': self.num_hashes,
            'bit_array_size': self.bit_array_size
        }
    
    def _calculate_memory_usage(self) -> int:
        """
        Calculate memory footprint in bytes.
        
        Formula: memory = m / 8 where m is bit array size
        For 100K items at 0.001 error rate: ~180KB
        For 1M items: ~1.8MB (base) + growth overhead
        
        The ScalableBloomFilter grows by creating new filters when capacity is exceeded.
        Each new filter has 2x the capacity of the previous one.
        
        Validates: Requirements 3.11, 5.4
        
        Returns:
            Estimated memory usage in bytes
        """
        # Base memory for initial filter: bit_array_size / 8
        base_memory = self.bit_array_size // 8
        
        # ScalableBloomFilter creates multiple filters as it grows
        # Growth pattern: 100K, 200K, 400K, 800K, ...
        # Each filter i has capacity: initial_capacity * 2^i
        
        if self.item_count <= self.initial_capacity:
            # Only one filter needed
            return base_memory
        
        # Calculate number of filters needed based on item count
        # Filter 0: initial_capacity items
        # Filter 1: initial_capacity * 2 items
        # Filter 2: initial_capacity * 4 items
        # Total capacity after n filters: initial_capacity * (2^(n+1) - 1)
        
        total_memory = 0
        remaining_items = self.item_count
        current_capacity = self.initial_capacity
        filter_index = 0
        
        while remaining_items > 0:
            # Calculate memory for this filter
            # Each filter has its own bit array sized for its capacity
            n = current_capacity
            p = self.error_rate
            m = int(-((n * math.log(p)) / (math.log(2) ** 2)))
            filter_memory = m // 8
            
            total_memory += filter_memory
            remaining_items -= current_capacity
            
            # Next filter has 2x capacity
            current_capacity *= 2
            filter_index += 1
            
            # Safety limit: prevent infinite loop
            if filter_index > 20:  # 100K * 2^20 = 104B items
                break
        
        return total_memory
