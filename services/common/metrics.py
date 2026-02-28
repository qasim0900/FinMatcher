"""
Metrics Collection
Collects and persists performance metrics to database
"""

import time
from typing import Optional, Dict, Any
from datetime import datetime
import psutil
import os

from .db_pool import DatabasePool
from .logger import get_logger

logger = get_logger(__name__)


class MetricsCollector:
    """Collects and persists metrics to database"""
    
    def __init__(self, db_pool: DatabasePool, service_name: str, worker_id: str):
        self.db_pool = db_pool
        self.service_name = service_name
        self.worker_id = worker_id
        self._buffer = []
        self._buffer_size = 100
    
    def record_metric(
        self,
        metric_name: str,
        value: float,
        unit: str,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Record a metric
        
        Args:
            metric_name: Name of the metric
            value: Metric value
            unit: Unit of measurement
            metadata: Additional metadata
        """
        metric = {
            'service_name': self.service_name,
            'metric_name': metric_name,
            'metric_value': value,
            'metric_unit': unit,
            'worker_id': self.worker_id,
            'metadata': metadata
        }
        
        self._buffer.append(metric)
        
        # Flush if buffer is full
        if len(self._buffer) >= self._buffer_size:
            self.flush()
    
    def flush(self):
        """Flush metrics buffer to database"""
        if not self._buffer:
            return
        
        try:
            values = [
                (
                    m['service_name'],
                    m['metric_name'],
                    m['metric_value'],
                    m['metric_unit'],
                    m['worker_id'],
                    m['metadata']
                )
                for m in self._buffer
            ]
            
            self.db_pool.execute_values(
                """
                INSERT INTO metrics (
                    service_name, metric_name, metric_value, 
                    metric_unit, worker_id, metadata
                )
                VALUES %s
                """,
                values
            )
            
            logger.debug(f"Flushed {len(self._buffer)} metrics to database")
            self._buffer = []
            
        except Exception as e:
            logger.error(f"Failed to flush metrics: {e}")
    
    def record_latency(self, operation: str, duration_ms: float, metadata: Optional[Dict[str, Any]] = None):
        """Record operation latency"""
        self.record_metric(
            metric_name=f"{operation}_latency",
            value=duration_ms,
            unit="milliseconds",
            metadata=metadata
        )
    
    def record_throughput(self, operation: str, count: int, duration_s: float, metadata: Optional[Dict[str, Any]] = None):
        """Record operation throughput"""
        throughput = count / duration_s if duration_s > 0 else 0
        self.record_metric(
            metric_name=f"{operation}_throughput",
            value=throughput,
            unit="ops/second",
            metadata={
                'count': count,
                'duration_seconds': duration_s,
                **(metadata or {})
            }
        )
    
    def record_memory_usage(self):
        """Record current memory usage"""
        process = psutil.Process(os.getpid())
        memory_mb = process.memory_info().rss / 1024 / 1024
        
        self.record_metric(
            metric_name="memory_usage",
            value=memory_mb,
            unit="megabytes"
        )
    
    def record_cpu_usage(self):
        """Record current CPU usage"""
        cpu_percent = psutil.cpu_percent(interval=1)
        
        self.record_metric(
            metric_name="cpu_usage",
            value=cpu_percent,
            unit="percent"
        )
    
    def __del__(self):
        """Flush remaining metrics on destruction"""
        self.flush()


class PerformanceTimer:
    """Context manager for timing operations"""
    
    def __init__(self, metrics_collector: MetricsCollector, operation: str, metadata: Optional[Dict[str, Any]] = None):
        self.metrics_collector = metrics_collector
        self.operation = operation
        self.metadata = metadata or {}
        self.start_time = None
    
    def __enter__(self):
        self.start_time = time.perf_counter()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        duration_ms = (time.perf_counter() - self.start_time) * 1000
        
        # Add error info if exception occurred
        if exc_type:
            self.metadata['error'] = str(exc_val)
            self.metadata['error_type'] = exc_type.__name__
        
        self.metrics_collector.record_latency(
            self.operation,
            duration_ms,
            self.metadata
        )


class BatchMetrics:
    """Track metrics for batch operations"""
    
    def __init__(self, metrics_collector: MetricsCollector, operation: str):
        self.metrics_collector = metrics_collector
        self.operation = operation
        self.start_time = time.perf_counter()
        self.count = 0
        self.error_count = 0
    
    def increment(self, count: int = 1):
        """Increment success count"""
        self.count += count
    
    def increment_errors(self, count: int = 1):
        """Increment error count"""
        self.error_count += count
    
    def finish(self, metadata: Optional[Dict[str, Any]] = None):
        """Finish batch and record metrics"""
        duration_s = time.perf_counter() - self.start_time
        
        # Record throughput
        self.metrics_collector.record_throughput(
            self.operation,
            self.count,
            duration_s,
            metadata
        )
        
        # Record error rate if there were errors
        if self.error_count > 0:
            total = self.count + self.error_count
            error_rate = (self.error_count / total * 100) if total > 0 else 0
            
            self.metrics_collector.record_metric(
                metric_name=f"{self.operation}_error_rate",
                value=error_rate,
                unit="percent",
                metadata={
                    'error_count': self.error_count,
                    'total_count': total,
                    **(metadata or {})
                }
            )
