"""
Hybrid parallelism orchestrator for FinMatcher v2.0 Enterprise Upgrade.

This module manages thread and process pools for optimal resource utilization:
- ThreadPoolExecutor for I/O operations (IMAP, Drive API, database reads)
- ProcessPoolExecutor for CPU-bound operations (OCR, AI inference, matching calculations)

Implements producer-consumer pattern with task queue for efficient workload distribution.

Validates Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6, 6.7
"""

import logging
import multiprocessing
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, Future
from typing import Callable, Any, List
from queue import Queue
import threading

logger = logging.getLogger(__name__)


class ParallelismOrchestrator:
    """
    Manages hybrid parallelism with thread and process pools.
    
    Thread Pool: I/O operations (IMAP fetching, Drive API calls, database reads)
    Process Pool: CPU-bound operations (OCR processing, AI inference, matching calculations)
    
    Validates Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6, 6.7
    """
    
    def __init__(self, thread_count: int = 50, process_count: int = 10):
        """
        Initialize thread and process pools.
        
        Args:
            thread_count: Number of threads for I/O operations (default: 50)
            process_count: Number of processes for CPU-bound operations (default: 10)
            
        Validates Requirements:
        - 6.1: Use ThreadPoolExecutor for I/O operations
        - 6.2: Configure ThreadPoolExecutor with 20-100 threads
        - 6.3: Use ProcessPoolExecutor for CPU-bound operations
        - 6.4: Configure ProcessPoolExecutor with 10 worker processes
        """
        # Validate thread count
        if thread_count < 20 or thread_count > 100:
            logger.warning(f"Thread count {thread_count} outside recommended range [20-100]")
        
        # Initialize thread pool for I/O operations
        self.thread_pool = ThreadPoolExecutor(
            max_workers=thread_count,
            thread_name_prefix="io-worker"
        )
        logger.info(f"Thread pool initialized with {thread_count} workers")
        
        # Initialize process pool for CPU-bound operations
        self.process_pool = ProcessPoolExecutor(
            max_workers=process_count,
            mp_context=multiprocessing.get_context('spawn')
        )
        logger.info(f"Process pool initialized with {process_count} workers")
        
        # Task queue for producer-consumer pattern
        self.task_queue: Queue = Queue()
        
        # Shutdown flag
        self._shutdown = False
        self._shutdown_lock = threading.Lock()
        
        logger.info("Parallelism orchestrator initialized successfully")
    
    def submit_io_task(self, func: Callable, *args, **kwargs) -> Future:
        """
        Submit I/O task to thread pool.
        
        Use for:
        - IMAP email fetching
        - Google Drive API calls (upload, download, query)
        - Database read operations
        - HTTP requests to DeepSeek API
        
        Args:
            func: Function to execute
            *args: Positional arguments for function
            **kwargs: Keyword arguments for function
            
        Returns:
            Future object for tracking task completion
            
        Validates Requirement: 6.1 - Use ThreadPoolExecutor for I/O operations
        """
        if self._shutdown:
            raise RuntimeError("Orchestrator is shut down")
        
        future = self.thread_pool.submit(func, *args, **kwargs)
        logger.debug(f"Submitted I/O task: {func.__name__}")
        return future
    
    def submit_cpu_task(self, func: Callable, *args, **kwargs) -> Future:
        """
        Submit CPU-bound task to process pool.
        
        Use for:
        - OCR processing (Tesseract)
        - Matching engine calculations
        - AI inference (if running local models)
        - Large data transformations
        
        Args:
            func: Function to execute
            *args: Positional arguments for function
            **kwargs: Keyword arguments for function
            
        Returns:
            Future object for tracking task completion
            
        Validates Requirement: 6.3 - Use ProcessPoolExecutor for CPU-bound operations
        """
        if self._shutdown:
            raise RuntimeError("Orchestrator is shut down")
        
        future = self.process_pool.submit(func, *args, **kwargs)
        logger.debug(f"Submitted CPU task: {func.__name__}")
        return future
    
    def process_batch_parallel(self, items: List[Any], 
                              process_func: Callable,
                              use_processes: bool = False) -> List[Any]:
        """
        Process batch of items in parallel.
        
        Args:
            items: List of items to process
            process_func: Function to apply to each item
            use_processes: If True, use process pool; else use thread pool
            
        Returns:
            List of results in same order as input items
            
        Validates Requirements:
        - 6.5: Assign producer threads to fetch emails
        - 6.6: Assign consumer processes to calculate scores
        """
        if not items:
            return []
        
        pool = self.process_pool if use_processes else self.thread_pool
        pool_type = "process" if use_processes else "thread"
        
        logger.info(f"Processing batch of {len(items)} items using {pool_type} pool")
        
        # Submit all tasks
        futures = [pool.submit(process_func, item) for item in items]
        
        # Collect results in order
        results = []
        for i, future in enumerate(futures):
            try:
                result = future.result()
                results.append(result)
            except Exception as e:
                logger.error(f"Task {i} failed: {e}")
                results.append(None)
        
        logger.info(f"Batch processing complete: {len(results)} results")
        return results
    
    def producer_consumer_pattern(self, 
                                 producer_func: Callable,
                                 consumer_func: Callable,
                                 num_producers: int = 5,
                                 num_consumers: int = 10) -> None:
        """
        Implement producer-consumer pattern with task queue.
        
        Producer threads: Fetch emails, parse statements
        Consumer processes: Calculate matches, run OCR
        
        Args:
            producer_func: Function for producer threads (should put items in queue)
            consumer_func: Function for consumer processes (should get items from queue)
            num_producers: Number of producer threads
            num_consumers: Number of consumer processes
            
        Validates Requirement: 6.7 - Implement queue-based communication pattern
        """
        logger.info(f"Starting producer-consumer pattern: "
                   f"{num_producers} producers, {num_consumers} consumers")
        
        # Start producer threads
        producer_futures = []
        for i in range(num_producers):
            future = self.submit_io_task(producer_func, self.task_queue, i)
            producer_futures.append(future)
        
        # Start consumer processes
        consumer_futures = []
        for i in range(num_consumers):
            future = self.submit_cpu_task(consumer_func, self.task_queue, i)
            consumer_futures.append(future)
        
        # Wait for all producers to complete
        for future in producer_futures:
            try:
                future.result()
            except Exception as e:
                logger.error(f"Producer failed: {e}")
        
        # Signal consumers to stop (poison pill pattern)
        for _ in range(num_consumers):
            self.task_queue.put(None)
        
        # Wait for all consumers to complete
        for future in consumer_futures:
            try:
                future.result()
            except Exception as e:
                logger.error(f"Consumer failed: {e}")
        
        logger.info("Producer-consumer pattern completed")
    
    def shutdown(self, wait: bool = True):
        """
        Shutdown pools gracefully.
        
        Args:
            wait: If True, wait for all tasks to complete before shutdown
            
        Validates Requirement: 6.7 - Handle graceful shutdown and resource cleanup
        """
        with self._shutdown_lock:
            if self._shutdown:
                logger.warning("Orchestrator already shut down")
                return
            
            self._shutdown = True
        
        logger.info(f"Shutting down orchestrator (wait={wait})...")
        
        # Shutdown thread pool
        self.thread_pool.shutdown(wait=wait)
        logger.info("Thread pool shut down")
        
        # Shutdown process pool
        self.process_pool.shutdown(wait=wait)
        logger.info("Process pool shut down")
        
        logger.info("Parallelism orchestrator shut down successfully")
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit with automatic shutdown."""
        self.shutdown(wait=True)
        return False


# Example usage functions for producer-consumer pattern

def example_producer(task_queue: Queue, producer_id: int):
    """
    Example producer function that fetches data and puts it in queue.
    
    Args:
        task_queue: Queue to put tasks into
        producer_id: ID of this producer
    """
    logger.info(f"Producer {producer_id} started")
    
    # Simulate fetching data (e.g., emails from IMAP)
    for i in range(10):
        task = f"task_{producer_id}_{i}"
        task_queue.put(task)
        logger.debug(f"Producer {producer_id} queued: {task}")
    
    logger.info(f"Producer {producer_id} finished")


def example_consumer(task_queue: Queue, consumer_id: int):
    """
    Example consumer function that processes tasks from queue.
    
    Args:
        task_queue: Queue to get tasks from
        consumer_id: ID of this consumer
    """
    logger.info(f"Consumer {consumer_id} started")
    
    while True:
        task = task_queue.get()
        
        # Check for poison pill (stop signal)
        if task is None:
            logger.info(f"Consumer {consumer_id} received stop signal")
            break
        
        # Process task (e.g., run matching algorithm)
        logger.debug(f"Consumer {consumer_id} processing: {task}")
        # Simulate CPU-intensive work
        result = task.upper()
        
    logger.info(f"Consumer {consumer_id} finished")
