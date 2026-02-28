"""
Structured Logging
JSON-formatted logging for easy parsing and monitoring
"""

import logging
import json
import sys
from datetime import datetime
from typing import Any, Dict, Optional
from pythonjsonlogger import jsonlogger


class CustomJsonFormatter(jsonlogger.JsonFormatter):
    """Custom JSON formatter with additional fields"""
    
    def add_fields(self, log_record: Dict[str, Any], record: logging.LogRecord, message_dict: Dict[str, Any]):
        super().add_fields(log_record, record, message_dict)
        
        # Add timestamp
        log_record['timestamp'] = datetime.utcnow().isoformat()
        
        # Add log level
        log_record['level'] = record.levelname
        
        # Add logger name
        log_record['logger'] = record.name
        
        # Add thread info
        log_record['thread'] = record.thread
        log_record['thread_name'] = record.threadName
        
        # Add process info
        log_record['process'] = record.process


def setup_logger(
    name: str,
    level: str = "INFO",
    json_format: bool = True,
    correlation_id: Optional[str] = None
) -> logging.Logger:
    """
    Setup structured logger
    
    Args:
        name: Logger name (usually service name)
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        json_format: Use JSON formatting
        correlation_id: Optional correlation ID for request tracing
    
    Returns:
        Configured logger
    """
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper()))
    
    # Remove existing handlers
    logger.handlers = []
    
    # Create console handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(getattr(logging, level.upper()))
    
    if json_format:
        # JSON formatter
        formatter = CustomJsonFormatter(
            '%(timestamp)s %(level)s %(name)s %(message)s'
        )
    else:
        # Standard formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    
    # Add correlation ID if provided
    if correlation_id:
        logger = logging.LoggerAdapter(logger, {'correlation_id': correlation_id})
    
    return logger


class MetricsLogger:
    """Logger for performance metrics"""
    
    def __init__(self, logger: logging.Logger):
        self.logger = logger
    
    def log_metric(
        self,
        metric_name: str,
        value: float,
        unit: str,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Log a performance metric
        
        Args:
            metric_name: Name of the metric
            value: Metric value
            unit: Unit of measurement
            metadata: Additional metadata
        """
        log_data = {
            'metric_name': metric_name,
            'value': value,
            'unit': unit,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        if metadata:
            log_data['metadata'] = metadata
        
        self.logger.info(f"METRIC: {json.dumps(log_data)}")
    
    def log_latency(self, operation: str, duration_ms: float, metadata: Optional[Dict[str, Any]] = None):
        """Log operation latency"""
        self.log_metric(
            metric_name=f"{operation}_latency",
            value=duration_ms,
            unit="milliseconds",
            metadata=metadata
        )
    
    def log_throughput(self, operation: str, count: int, duration_s: float, metadata: Optional[Dict[str, Any]] = None):
        """Log operation throughput"""
        throughput = count / duration_s if duration_s > 0 else 0
        self.log_metric(
            metric_name=f"{operation}_throughput",
            value=throughput,
            unit="ops/second",
            metadata={
                'count': count,
                'duration_seconds': duration_s,
                **(metadata or {})
            }
        )
    
    def log_error_rate(self, operation: str, error_count: int, total_count: int, metadata: Optional[Dict[str, Any]] = None):
        """Log error rate"""
        error_rate = (error_count / total_count * 100) if total_count > 0 else 0
        self.log_metric(
            metric_name=f"{operation}_error_rate",
            value=error_rate,
            unit="percent",
            metadata={
                'error_count': error_count,
                'total_count': total_count,
                **(metadata or {})
            }
        )


# Global logger instances
_loggers: Dict[str, logging.Logger] = {}


def get_logger(name: str, level: str = "INFO", json_format: bool = True) -> logging.Logger:
    """Get or create logger instance"""
    if name not in _loggers:
        _loggers[name] = setup_logger(name, level, json_format)
    return _loggers[name]


def get_metrics_logger(name: str) -> MetricsLogger:
    """Get metrics logger"""
    logger = get_logger(name)
    return MetricsLogger(logger)
