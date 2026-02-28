"""
Error handling and graceful shutdown utilities.

This module provides error handling utilities including graceful shutdown
on critical errors with progress preservation.

Validates Requirements: 12.3, 12.6
"""

import sys
import signal
import traceback
from typing import Optional, Callable
from datetime import datetime

from utils.logger import get_logger
from database.cache_manager import get_cache_manager


logger = get_logger(__name__)


class CriticalError(Exception):
    """Exception raised for critical errors that require graceful shutdown."""
    pass


class GracefulShutdownHandler:
    """
    Handles graceful shutdown on critical errors.
    
    Ensures all progress is saved before exiting and logs detailed error information.
    
    Validates Requirements:
    - 12.6: Save progress and log errors before exiting on critical failures
    """
    
    def __init__(self):
        """Initialize graceful shutdown handler."""
        self.shutdown_in_progress = False
        self.cleanup_callbacks: list[Callable] = []
        
        # Register signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def register_cleanup(self, callback: Callable):
        """
        Register a cleanup callback to be called on shutdown.
        
        Args:
            callback: Function to call during cleanup
        """
        self.cleanup_callbacks.append(callback)
    
    def _signal_handler(self, signum, frame):
        """Handle interrupt signals (Ctrl+C, SIGTERM)."""
        logger.warning(f"Received signal {signum}, initiating graceful shutdown...")
        self.shutdown(exit_code=130)  # 128 + SIGINT
    
    def shutdown(
        self,
        error: Optional[Exception] = None,
        exit_code: int = 1
    ):
        """
        Perform graceful shutdown.
        
        Saves all progress, runs cleanup callbacks, logs errors, and exits.
        
        Args:
            error: Optional exception that triggered shutdown
            exit_code: Exit code (0 for success, non-zero for error)
            
        Validates Requirement 12.6: Graceful shutdown with progress preservation
        """
        if self.shutdown_in_progress:
            logger.warning("Shutdown already in progress, skipping...")
            return
        
        self.shutdown_in_progress = True
        
        logger.warning("=" * 80)
        logger.warning("INITIATING GRACEFUL SHUTDOWN")
        logger.warning("=" * 80)
        
        try:
            # Log error details if provided
            if error:
                logger.error(f"Critical error triggered shutdown: {type(error).__name__}")
                logger.error(f"Error message: {str(error)}")
                logger.error("Stack trace:")
                logger.error(traceback.format_exc())
            
            # Save all progress to cache
            logger.info("Saving progress to database...")
            try:
                cache_manager = get_cache_manager()
                cache_manager.commit()  # Ensure all changes are committed
                logger.info("✓ Progress saved successfully")
            except Exception as e:
                logger.error(f"✗ Failed to save progress: {e}")
            
            # Run cleanup callbacks
            logger.info(f"Running {len(self.cleanup_callbacks)} cleanup callbacks...")
            for i, callback in enumerate(self.cleanup_callbacks):
                try:
                    callback()
                    logger.debug(f"✓ Cleanup callback {i+1} completed")
                except Exception as e:
                    logger.error(f"✗ Cleanup callback {i+1} failed: {e}")
            
            # Log shutdown completion
            logger.warning("=" * 80)
            logger.warning(f"GRACEFUL SHUTDOWN COMPLETE (exit code: {exit_code})")
            logger.warning("=" * 80)
        
        except Exception as e:
            logger.error(f"Error during graceful shutdown: {e}")
            logger.error(traceback.format_exc())
        
        finally:
            sys.exit(exit_code)


# Global shutdown handler instance
_shutdown_handler: Optional[GracefulShutdownHandler] = None


def get_shutdown_handler() -> GracefulShutdownHandler:
    """
    Get the global shutdown handler instance.
    
    Returns:
        GracefulShutdownHandler: The shutdown handler
    """
    global _shutdown_handler
    if _shutdown_handler is None:
        _shutdown_handler = GracefulShutdownHandler()
    return _shutdown_handler


def handle_critical_error(error: Exception, context: str = ""):
    """
    Handle a critical error with graceful shutdown.
    
    Args:
        error: The critical error
        context: Additional context about where the error occurred
    """
    logger.error(f"CRITICAL ERROR in {context}: {error}")
    logger.error(traceback.format_exc())
    
    shutdown_handler = get_shutdown_handler()
    shutdown_handler.shutdown(error=error, exit_code=1)


def is_critical_error(error: Exception) -> bool:
    """
    Determine if an error is critical and requires shutdown.
    
    Critical errors include:
    - Database corruption
    - Configuration errors
    - File system errors
    - Memory errors
    
    Args:
        error: The error to check
        
    Returns:
        True if error is critical, False otherwise
    """
    critical_error_types = (
        CriticalError,
        MemoryError,
        OSError,  # File system errors
        IOError,
        SystemError,
    )
    
    # Check error type
    if isinstance(error, critical_error_types):
        return True
    
    # Check error message for critical keywords
    error_msg = str(error).lower()
    critical_keywords = [
        'database',
        'corruption',
        'disk full',
        'permission denied',
        'out of memory',
        'configuration',
        'config'
    ]
    
    return any(keyword in error_msg for keyword in critical_keywords)


def safe_execute(
    func: Callable,
    *args,
    context: str = "",
    reraise_critical: bool = True,
    **kwargs
):
    """
    Execute a function with error handling.
    
    Non-critical errors are logged and suppressed.
    Critical errors trigger graceful shutdown.
    
    Args:
        func: Function to execute
        *args: Positional arguments for func
        context: Context description for error logging
        reraise_critical: Whether to trigger shutdown on critical errors
        **kwargs: Keyword arguments for func
        
    Returns:
        Function result or None if error occurred
        
    Validates Requirement 12.3: Error isolation for individual operations
    """
    try:
        return func(*args, **kwargs)
    
    except Exception as e:
        # Log the error with context
        logger.error(f"Error in {context or func.__name__}: {e}")
        logger.debug(traceback.format_exc())
        
        # Check if critical
        if reraise_critical and is_critical_error(e):
            handle_critical_error(e, context or func.__name__)
        
        return None
