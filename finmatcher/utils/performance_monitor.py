"""
Performance monitoring utilities for FinMatcher v2.0 Enterprise Upgrade.

This module provides performance monitoring including memory usage tracking,
throughput measurement, performance metrics logging, and memory management
with automatic warnings and garbage collection triggers.

Validates Requirements: 11.4, 11.5, 13.1, 13.2
"""

import time
import psutil
import os
import gc
from typing import Optional, Dict
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class PerformanceMonitor:
    """
    Performance monitoring for the FinMatcher system.
    
    Tracks memory usage, throughput, execution time, and provides
    automatic memory management with warnings and garbage collection.
    
    Validates Requirements:
    - 11.4: Monitor memory usage and log warnings at 80% usage
    - 11.5: Pause processing and trigger GC at 90% usage
    - 13.1: Monitor throughput (emails/second, matches/second)
    - 13.2: Monitor memory usage
    """
    
    def __init__(self, warning_threshold: float = 0.80, pause_threshold: float = 0.90):
        """
        Initialize performance monitor.
        
        Args:
            warning_threshold: Memory usage percentage to trigger warning (default: 0.80 = 80%)
            pause_threshold: Memory usage percentage to trigger pause and GC (default: 0.90 = 90%)
            
        Validates Requirements: 11.4, 11.5
        """
        self.process = psutil.Process(os.getpid())
        self.start_time = time.time()
        self.metrics: Dict[str, float] = {}
        self.warning_threshold = warning_threshold
        self.pause_threshold = pause_threshold
        
        logger.info(f"Performance monitor initialized: "
                   f"warning={warning_threshold*100}%, pause={pause_threshold*100}%")
    
    def get_memory_usage(self) -> Dict[str, float]:
        """
        Get current memory usage statistics.
        
        Returns:
            Dictionary with memory usage in MB and percentage
            
        Validates Requirement 13.2: Memory usage monitoring
        """
        memory_info = self.process.memory_info()
        virtual_memory = psutil.virtual_memory()
        
        return {
            'rss_mb': memory_info.rss / (1024 * 1024),  # Resident Set Size
            'vms_mb': memory_info.vms / (1024 * 1024),  # Virtual Memory Size
            'percent': self.process.memory_percent(),
            'system_percent': virtual_memory.percent,  # System-wide memory usage
            'available_mb': virtual_memory.available / (1024 * 1024),
        }
    
    def check_memory_and_manage(self) -> bool:
        """
        Check memory usage and manage according to thresholds.
        
        Returns:
            True if processing can continue, False if should pause
            
        Validates Requirements:
        - 11.4: Log warnings when usage exceeds 80% of available memory
        - 11.5: Pause processing and trigger GC when usage exceeds 90%
        """
        memory = self.get_memory_usage()
        usage_percent = memory['system_percent'] / 100.0
        
        if usage_percent >= self.pause_threshold:
            # Critical: Pause and trigger garbage collection
            logger.critical(
                f"Memory usage at {usage_percent*100:.1f}% (>= {self.pause_threshold*100}%) - "
                f"PAUSING processing and triggering garbage collection"
            )
            logger.info(f"Memory before GC: RSS={memory['rss_mb']:.2f}MB, "
                       f"Available={memory['available_mb']:.2f}MB")
            
            # Trigger garbage collection
            gc.collect()
            
            # Wait a moment for GC to complete
            time.sleep(2)
            
            # Check memory after GC
            memory_after = self.get_memory_usage()
            logger.info(f"Memory after GC: RSS={memory_after['rss_mb']:.2f}MB, "
                       f"Available={memory_after['available_mb']:.2f}MB")
            
            return False  # Signal to pause processing
            
        elif usage_percent >= self.warning_threshold:
            # Warning: Log but continue processing
            logger.warning(
                f"Memory usage at {usage_percent*100:.1f}% (>= {self.warning_threshold*100}%) - "
                f"approaching limit. RSS={memory['rss_mb']:.2f}MB, "
                f"Available={memory['available_mb']:.2f}MB"
            )
            return True  # Continue processing
        
        else:
            # Normal: Continue processing
            return True
    
    def process_with_memory_check(self, items: list, process_func, chunk_size: int = 1000):
        """
        Process items in chunks with memory monitoring.
        
        Args:
            items: List of items to process
            process_func: Function to process each item
            chunk_size: Number of items per chunk (default: 1000)
            
        Yields:
            Results from process_func
            
        Validates Requirements:
        - 11.1: Process records in chunks of 1000
        - 11.2: Release memory after each chunk
        - 11.4: Monitor memory and log warnings
        - 11.5: Pause and trigger GC when needed
        """
        total_items = len(items)
        logger.info(f"Processing {total_items} items in chunks of {chunk_size}")
        
        for i in range(0, total_items, chunk_size):
            chunk = items[i:i + chunk_size]
            chunk_num = i // chunk_size + 1
            total_chunks = (total_items + chunk_size - 1) // chunk_size
            
            logger.debug(f"Processing chunk {chunk_num}/{total_chunks} "
                        f"({len(chunk)} items)")
            
            # Check memory before processing chunk
            can_continue = self.check_memory_and_manage()
            
            if not can_continue:
                # Memory critical, wait and retry
                logger.info("Waiting 5 seconds before retrying...")
                time.sleep(5)
                
                # Check again
                can_continue = self.check_memory_and_manage()
                if not can_continue:
                    logger.error("Memory still critical after GC, skipping chunk")
                    continue
            
            # Process chunk
            for item in chunk:
                try:
                    result = process_func(item)
                    yield result
                except Exception as e:
                    logger.error(f"Error processing item: {e}")
                    yield None
            
            # Release memory after chunk
            del chunk
            
            # Periodic garbage collection every 10 chunks
            if chunk_num % 10 == 0:
                gc.collect()
                logger.debug(f"Periodic GC after chunk {chunk_num}")
        
        logger.info(f"Completed processing {total_items} items")
    
    def log_memory_usage(self, context: str = ""):
        """
        Log current memory usage.
        
        Args:
            context: Context description for the log
        """
        memory = self.get_memory_usage()
        logger.info(
            f"Memory usage {context}: "
            f"RSS={memory['rss_mb']:.2f}MB, "
            f"VMS={memory['vms_mb']:.2f}MB, "
            f"Percent={memory['percent']:.2f}%"
        )
    
    def calculate_throughput(
        self,
        items_processed: int,
        duration_seconds: float
    ) -> float:
        """
        Calculate throughput (items per second).
        
        Args:
            items_processed: Number of items processed
            duration_seconds: Duration in seconds
            
        Returns:
            Throughput in items/second
            
        Validates Requirement 13.1: Throughput measurement
        """
        if duration_seconds <= 0:
            return 0.0
        
        return items_processed / duration_seconds
    
    def log_throughput(
        self,
        items_processed: int,
        duration_seconds: float,
        item_type: str = "items"
    ):
        """
        Log throughput metrics.
        
        Args:
            items_processed: Number of items processed
            duration_seconds: Duration in seconds
            item_type: Type of items (e.g., "emails", "matches")
        """
        throughput = self.calculate_throughput(items_processed, duration_seconds)
        logger.info(
            f"Throughput: {throughput:.2f} {item_type}/second "
            f"({items_processed} {item_type} in {duration_seconds:.2f}s)"
        )
    
    def extrapolate_to_target(
        self,
        items_processed: int,
        duration_seconds: float,
        target_items: int = 1_000_000
    ) -> Dict[str, float]:
        """
        Extrapolate performance to target scale.
        
        Args:
            items_processed: Number of items processed in test
            duration_seconds: Duration of test in seconds
            target_items: Target number of items (default: 1M)
            
        Returns:
            Dictionary with extrapolated metrics
            
        Validates Requirement 13.1: Extrapolate to 1M emails
        """
        throughput = self.calculate_throughput(items_processed, duration_seconds)
        
        if throughput <= 0:
            return {
                'target_items': target_items,
                'estimated_duration_seconds': 0,
                'estimated_duration_hours': 0,
                'throughput': 0,
            }
        
        estimated_duration_seconds = target_items / throughput
        estimated_duration_hours = estimated_duration_seconds / 3600
        
        return {
            'target_items': target_items,
            'estimated_duration_seconds': estimated_duration_seconds,
            'estimated_duration_hours': estimated_duration_hours,
            'throughput': throughput,
        }
    
    def log_extrapolation(
        self,
        items_processed: int,
        duration_seconds: float,
        target_items: int = 1_000_000,
        item_type: str = "emails"
    ):
        """
        Log extrapolated performance metrics.
        
        Args:
            items_processed: Number of items processed
            duration_seconds: Duration in seconds
            target_items: Target number of items
            item_type: Type of items
        """
        metrics = self.extrapolate_to_target(items_processed, duration_seconds, target_items)
        
        logger.info("=" * 80)
        logger.info(f"PERFORMANCE EXTRAPOLATION TO {target_items:,} {item_type}")
        logger.info("=" * 80)
        logger.info(f"Current throughput: {metrics['throughput']:.2f} {item_type}/second")
        logger.info(f"Estimated duration: {metrics['estimated_duration_hours']:.2f} hours")
        logger.info(f"Target: {'✓ PASS' if metrics['estimated_duration_hours'] <= 24 else '✗ FAIL'} (24-hour requirement)")
        logger.info("=" * 80)
    
    def check_memory_threshold(self, threshold_mb: float = 4096) -> bool:
        """
        Check if memory usage is below threshold.
        
        Args:
            threshold_mb: Memory threshold in MB (default: 4GB)
            
        Returns:
            True if below threshold, False otherwise
        """
        memory = self.get_memory_usage()
        return memory['rss_mb'] < threshold_mb
    
    def get_elapsed_time(self) -> float:
        """
        Get elapsed time since monitor initialization.
        
        Returns:
            Elapsed time in seconds
        """
        return time.time() - self.start_time
    
    def log_performance_summary(
        self,
        emails_processed: int,
        matches_found: int,
        duration_seconds: Optional[float] = None
    ):
        """
        Log comprehensive performance summary.
        
        Args:
            emails_processed: Number of emails processed
            matches_found: Number of matches found
            duration_seconds: Duration (defaults to elapsed time)
        """
        if duration_seconds is None:
            duration_seconds = self.get_elapsed_time()
        
        logger.info("=" * 80)
        logger.info("PERFORMANCE SUMMARY")
        logger.info("=" * 80)
        
        # Throughput metrics
        email_throughput = self.calculate_throughput(emails_processed, duration_seconds)
        match_throughput = self.calculate_throughput(matches_found, duration_seconds)
        
        logger.info(f"Emails processed: {emails_processed:,}")
        logger.info(f"Matches found: {matches_found:,}")
        logger.info(f"Duration: {duration_seconds:.2f} seconds ({duration_seconds/60:.2f} minutes)")
        logger.info(f"Email throughput: {email_throughput:.2f} emails/second")
        logger.info(f"Match throughput: {match_throughput:.2f} matches/second")
        
        # Memory usage
        memory = self.get_memory_usage()
        logger.info(f"Memory usage: {memory['rss_mb']:.2f}MB ({memory['percent']:.2f}%)")
        
        # Extrapolation to 1M emails
        if emails_processed > 0:
            extrapolation = self.extrapolate_to_target(emails_processed, duration_seconds)
            logger.info(f"Extrapolated time for 1M emails: {extrapolation['estimated_duration_hours']:.2f} hours")
            
            if extrapolation['estimated_duration_hours'] <= 24:
                logger.info("✓ Performance target met (< 24 hours for 1M emails)")
            else:
                logger.warning("✗ Performance target not met (> 24 hours for 1M emails)")
        
        logger.info("=" * 80)


# Global performance monitor instance
_performance_monitor: Optional[PerformanceMonitor] = None


def get_performance_monitor() -> PerformanceMonitor:
    """
    Get the global performance monitor instance.
    
    Returns:
        PerformanceMonitor: The performance monitor
    """
    global _performance_monitor
    if _performance_monitor is None:
        _performance_monitor = PerformanceMonitor()
    return _performance_monitor


def reset_performance_monitor():
    """Reset the global performance monitor instance."""
    global _performance_monitor
    _performance_monitor = None
