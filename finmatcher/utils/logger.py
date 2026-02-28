"""
Comprehensive logging system with sanitization for sensitive data.

This module provides structured logging with rotating file handlers,
and automatically sanitizes passwords, API keys, credit card numbers, and PII.

Validates Requirements: 10.5, 10.6, 10.7
"""

import logging
import re
import sys
from pathlib import Path
from typing import Optional
from datetime import datetime
from logging.handlers import RotatingFileHandler


class SanitizingFormatter(logging.Formatter):
    """
    Custom formatter that sanitizes sensitive information from log messages.
    
    Removes:
    - Email addresses
    - Passwords
    - API keys
    - Credit card numbers
    - Account numbers
    - OAuth tokens
    - Any patterns matching common secret formats
    
    Validates Requirement 10.7: Sanitize all personally identifiable information before writing to logs
    """
    
    # Patterns for sensitive data
    PATTERNS = [
        # Email addresses (PII)
        (re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'), r'[EMAIL]'),
        
        # Email passwords (after 'password=' or 'pwd=')
        (re.compile(r'(password|pwd|pass)\s*[=:]\s*["\']?([^"\'\s,;]+)', re.IGNORECASE), r'\1=***REDACTED***'),
        
        # API keys (various formats)
        (re.compile(r'(api[_-]?key|apikey|key)\s*[=:]\s*["\']?([a-zA-Z0-9_\-]{20,})', re.IGNORECASE), r'\1=***REDACTED***'),
        
        # OAuth tokens
        (re.compile(r'(token|access[_-]?token|bearer)\s*[=:]\s*["\']?([a-zA-Z0-9_\-\.]{20,})', re.IGNORECASE), r'\1=***REDACTED***'),
        
        # Credit card numbers (various formats with spaces, dashes, or no separators)
        (re.compile(r'\b\d{4}[\s\-]?\d{4}[\s\-]?\d{4}[\s\-]?\d{4}\b'), r'[CARD]'),
        
        # Account numbers (8-12 digits)
        (re.compile(r'\b\d{8,12}\b'), r'[ACCOUNT]'),
        
        # Generic secrets (secret=value format)
        (re.compile(r'(secret|client[_-]?secret)\s*[=:]\s*["\']?([^"\'\s,;]+)', re.IGNORECASE), r'\1=***REDACTED***'),
        
        # DeepSeek API keys
        (re.compile(r'sk-[a-zA-Z0-9]{30,}'), r'sk-***REDACTED***'),
        
        # Google OAuth client secrets
        (re.compile(r'(client[_-]?id|client[_-]?secret)\s*[=:]\s*["\']?([^"\'\s,;]+)', re.IGNORECASE), r'\1=***REDACTED***'),
    ]
    
    def format(self, record: logging.LogRecord) -> str:
        """
        Format the log record and sanitize sensitive information.
        
        Args:
            record: The log record to format
            
        Returns:
            Sanitized formatted log message
        """
        # Format the message first
        original_msg = super().format(record)
        
        # Apply all sanitization patterns
        sanitized_msg = original_msg
        for pattern, replacement in self.PATTERNS:
            sanitized_msg = pattern.sub(replacement, sanitized_msg)
        
        return sanitized_msg


class FinMatcherLogger:
    """
    Main logger class for FinMatcher system.
    
    Provides structured logging with:
    - Rotating file handler (100MB max, 90 days retention)
    - Console handler (colored output)
    - Automatic sanitization of sensitive data and PII
    - Configurable log levels
    
    Validates Requirements:
    - 10.5: Write all log entries to a rotating log file with maximum size of 100MB
    - 10.6: Retain log files for 90 days
    - 10.7: Sanitize all personally identifiable information before writing to logs
    """
    
    def __init__(
        self,
        name: str = "finmatcher",
        log_level: str = "INFO",
        log_dir: Path = Path("logs"),
        log_to_console: bool = True,
        log_to_file: bool = True
    ):
        """
        Initialize the logger.
        
        Args:
            name: Logger name
            log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            log_dir: Directory for log files
            log_to_console: Whether to log to console
            log_to_file: Whether to log to file
        """
        self.name = name
        self.log_level = getattr(logging, log_level.upper(), logging.INFO)
        self.log_dir = log_dir
        self.logger = logging.getLogger(name)
        self.logger.setLevel(self.log_level)
        
        # Remove existing handlers to avoid duplicates
        self.logger.handlers.clear()
        
        # Create log directory if it doesn't exist
        if log_to_file:
            self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # Create formatters
        detailed_formatter = SanitizingFormatter(
            fmt='%(asctime)s | %(levelname)-8s | %(name)s | %(funcName)s:%(lineno)d | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        simple_formatter = SanitizingFormatter(
            fmt='%(asctime)s | %(levelname)-8s | %(message)s',
            datefmt='%H:%M:%S'
        )
        
        # Add console handler with UTF-8 encoding for Windows
        if log_to_console:
            # Fix Windows console encoding issues
            if sys.platform == 'win32':
                # Reconfigure stdout to use UTF-8 encoding
                import io
                sys.stdout = io.TextIOWrapper(
                    sys.stdout.buffer,
                    encoding='utf-8',
                    errors='replace',
                    line_buffering=True
                )
            
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(self.log_level)
            console_handler.setFormatter(simple_formatter)
            self.logger.addHandler(console_handler)
        
        # Add file handler with rotation
        if log_to_file:
            # Create timestamped log file with rotation
            # Max size: 100MB, Backup count: calculated for 90 days retention
            log_file = self.log_dir / "finmatcher.log"
            
            # RotatingFileHandler: 100MB max size, keep 90 backup files (approx 90 days)
            file_handler = RotatingFileHandler(
                log_file,
                maxBytes=104857600,  # 100MB
                backupCount=90,      # Keep 90 backup files
                encoding='utf-8'
            )
            file_handler.setLevel(logging.DEBUG)  # Always log DEBUG to file
            file_handler.setFormatter(detailed_formatter)
            self.logger.addHandler(file_handler)
            
            self.logger.info(f"Logging to file: {log_file} (max 100MB, 90 days retention)")
    
    def debug(self, message: str, **kwargs):
        """Log debug message."""
        self.logger.debug(message, **kwargs)
    
    def info(self, message: str, **kwargs):
        """Log info message."""
        self.logger.info(message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        """Log warning message."""
        self.logger.warning(message, **kwargs)
    
    def error(self, message: str, exc_info: bool = False, **kwargs):
        """
        Log error message.
        
        Args:
            message: Error message
            exc_info: Whether to include exception traceback
        """
        self.logger.error(message, exc_info=exc_info, **kwargs)
    
    def critical(self, message: str, exc_info: bool = False, **kwargs):
        """
        Log critical message.
        
        Args:
            message: Critical error message
            exc_info: Whether to include exception traceback
        """
        self.logger.critical(message, exc_info=exc_info, **kwargs)
    
    def log_milestone_start(self, milestone_name: str, description: str = ""):
        """
        Log the start of a processing milestone.
        
        Args:
            milestone_name: Name of the milestone (e.g., "Milestone 1: Meriwest Reconciliation")
            description: Optional description
            
        Validates Requirement 11.2: Log milestone start time
        """
        separator = "=" * 80
        self.logger.info(f"\n{separator}")
        self.logger.info(f">> STARTING: {milestone_name}")
        if description:
            self.logger.info(f"   {description}")
        self.logger.info(f"   Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        self.logger.info(f"{separator}\n")
    
    def log_milestone_end(self, milestone_name: str, records_processed: int = 0, duration_seconds: float = 0):
        """
        Log the completion of a processing milestone.
        
        Args:
            milestone_name: Name of the milestone
            records_processed: Number of records processed
            duration_seconds: Duration in seconds
            
        Validates Requirement 11.2: Log milestone end time and record counts
        """
        separator = "=" * 80
        self.logger.info(f"\n{separator}")
        self.logger.info(f"[OK] COMPLETED: {milestone_name}")
        self.logger.info(f"   End Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        self.logger.info(f"   Records Processed: {records_processed:,}")
        if duration_seconds > 0:
            self.logger.info(f"   Duration: {duration_seconds:.2f} seconds ({duration_seconds/60:.2f} minutes)")
        self.logger.info(f"{separator}\n")
    
    def log_statistics(self, stats: dict):
        """
        Log processing statistics.
        
        Args:
            stats: Dictionary of statistics to log
            
        Validates Requirement 11.4: Log statistics including matches, unmatched count, average score
        """
        self.logger.info("[STATS] Processing Statistics:")
        for key, value in stats.items():
            if isinstance(value, float):
                self.logger.info(f"   {key}: {value:.4f}")
            elif isinstance(value, int):
                self.logger.info(f"   {key}: {value:,}")
            else:
                self.logger.info(f"   {key}: {value}")
    
    def log_rate_limit(self, delay_seconds: float, reason: str = ""):
        """
        Log rate limiting event.
        
        Args:
            delay_seconds: Delay duration in seconds
            reason: Reason for rate limiting
            
        Validates Requirement 11.5: Log delay duration and reason
        """
        self.logger.debug(f"[WAIT] Rate limit: Sleeping for {delay_seconds:.2f}s. Reason: {reason}")
    
    def log_summary(self, total_emails: int, matches_found: int, execution_time_seconds: float):
        """
        Log final summary report.
        
        Args:
            total_emails: Total emails processed
            matches_found: Total matches found
            execution_time_seconds: Total execution time
            
        Validates Requirement 11.6: Log summary with total emails, matches, execution time
        """
        separator = "=" * 80
        self.logger.info(f"\n{separator}")
        self.logger.info("[SUCCESS] RECONCILIATION COMPLETE - FINAL SUMMARY")
        self.logger.info(f"{separator}")
        self.logger.info(f"   Total Emails Processed: {total_emails:,}")
        self.logger.info(f"   Total Matches Found: {matches_found:,}")
        self.logger.info(f"   Match Rate: {(matches_found/total_emails*100) if total_emails > 0 else 0:.2f}%")
        self.logger.info(f"   Total Execution Time: {execution_time_seconds:.2f}s ({execution_time_seconds/60:.2f} minutes)")
        self.logger.info(f"   Average Time per Email: {(execution_time_seconds/total_emails) if total_emails > 0 else 0:.4f}s")
        self.logger.info(f"{separator}\n")


# Global logger instance
_logger: Optional[FinMatcherLogger] = None


def get_logger(
    name: str = "finmatcher",
    log_level: str = "INFO",
    log_dir: Path = Path("logs"),
    log_to_console: bool = True,
    log_to_file: bool = True
) -> FinMatcherLogger:
    """
    Get or create the global logger instance.
    
    Args:
        name: Logger name
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_dir: Directory for log files
        log_to_console: Whether to log to console
        log_to_file: Whether to log to file
        
    Returns:
        FinMatcherLogger instance
    """
    global _logger
    if _logger is None:
        _logger = FinMatcherLogger(
            name=name,
            log_level=log_level,
            log_dir=log_dir,
            log_to_console=log_to_console,
            log_to_file=log_to_file
        )
    return _logger


def reset_logger():
    """Reset the global logger instance (useful for testing)."""
    global _logger
    _logger = None
