"""
Concurrent processing utilities for FastAPI applications.

This module provides decorators and utilities for parallel processing using
concurrent.futures ThreadPoolExecutor and ProcessPoolExecutor.
Designed to work seamlessly with async FastAPI applications.
"""

import asyncio
import functools
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed
from typing import Callable, List, Any, Dict, Union, Optional
from enum import Enum
from loguru import logger
import time


class TaskType(Enum):
    """Task type enumeration for concurrent processing"""
    IO_BOUND = "io_bound"
    CPU_BOUND = "cpu_bound"


class ConcurrentConfig:
    """Configuration for concurrent processing"""
    DEFAULT_THREAD_WORKERS = 20
    DEFAULT_PROCESS_WORKERS = 4
    DEFAULT_BATCH_SIZE = 100
    MAX_THREAD_WORKERS = 50
    MAX_PROCESS_WORKERS = 8


class ConcurrentManager:
    """Singleton manager for concurrent executors"""
    
    _instance = None
    _thread_executor = None
    _process_executor = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._thread_executor is None:
            self._thread_executor = ThreadPoolExecutor(
                max_workers=ConcurrentConfig.DEFAULT_THREAD_WORKERS,
                thread_name_prefix="FastAPI-Thread"
            )
        if self._process_executor is None:
            self._process_executor = ProcessPoolExecutor(
                max_workers=ConcurrentConfig.DEFAULT_PROCESS_WORKERS
            )
    
    @property
    def thread_executor(self) -> ThreadPoolExecutor:
        return self._thread_executor
    
    @property
    def process_executor(self) -> ProcessPoolExecutor:
        return self._process_executor
    
    def shutdown(self):
        """Shutdown all executors"""
        if self._thread_executor:
            self._thread_executor.shutdown(wait=True)
        if self._process_executor:
            self._process_executor.shutdown(wait=True)


# Global concurrent manager instance
concurrent_manager = ConcurrentManager()


def parallel_io(max_workers: Optional[int] = None, batch_size: Optional[int] = None):
    """
    Decorator for I/O-bound parallel processing using ThreadPoolExecutor.
    
    Args:
        max_workers: Maximum number of threads (default: uses global config)
        batch_size: Batch size for processing large datasets
    
    Usage:
        @parallel_io(max_workers=10)
        async def process_files(file_paths: List[str]) -> List[str]:
            # This will run each file processing in parallel threads
            pass
    """
    def decorator(func: Callable):
        @functools.wraps(func)
        async def wrapper(items: List[Any], *args, **kwargs) -> List[Any]:
            if not items:
                return []
            
            start_time = time.time()
            logger.info(f"Starting parallel I/O processing: {func.__name__} with {len(items)} items")
            
            # Use custom executor if max_workers specified, otherwise use global
            if max_workers:
                executor = ThreadPoolExecutor(max_workers=max_workers)
            else:
                executor = concurrent_manager.thread_executor
            
            try:
                loop = asyncio.get_event_loop()
                
                # Process in batches if batch_size specified
                if batch_size and len(items) > batch_size:
                    results = []
                    for i in range(0, len(items), batch_size):
                        batch = items[i:i + batch_size]
                        batch_futures = [
                            loop.run_in_executor(executor, func, item, *args, **kwargs) 
                            for item in batch
                        ]
                        batch_results = await asyncio.gather(*batch_futures, return_exceptions=True)
                        results.extend(batch_results)
                else:
                    # Process all items in parallel
                    futures = [
                        loop.run_in_executor(executor, func, item, *args, **kwargs) 
                        for item in items
                    ]
                    results = await asyncio.gather(*futures, return_exceptions=True)
                
                # Log performance metrics
                duration = time.time() - start_time
                logger.info(f"Completed parallel I/O processing: {func.__name__} in {duration:.2f}s")
                
                return results
                
            finally:
                # Only shutdown if we created a custom executor
                if max_workers:
                    executor.shutdown(wait=False)
        
        return wrapper
    return decorator


def parallel_cpu(max_workers: Optional[int] = None, batch_size: Optional[int] = None):
    """
    Decorator for CPU-bound parallel processing using ProcessPoolExecutor.
    
    Args:
        max_workers: Maximum number of processes (default: uses global config)
        batch_size: Batch size for processing large datasets
    
    Usage:
        @parallel_cpu(max_workers=4)
        async def process_images(image_paths: List[str]) -> List[str]:
            # This will run each image processing in parallel processes
            pass
    """
    def decorator(func: Callable):
        @functools.wraps(func)
        async def wrapper(items: List[Any], *args, **kwargs) -> List[Any]:
            if not items:
                return []
            
            start_time = time.time()
            logger.info(f"Starting parallel CPU processing: {func.__name__} with {len(items)} items")
            
            # Use custom executor if max_workers specified, otherwise use global
            if max_workers:
                executor = ProcessPoolExecutor(max_workers=max_workers)
            else:
                executor = concurrent_manager.process_executor
            
            try:
                loop = asyncio.get_event_loop()
                
                # Process in batches if batch_size specified
                if batch_size and len(items) > batch_size:
                    results = []
                    for i in range(0, len(items), batch_size):
                        batch = items[i:i + batch_size]
                        batch_futures = [
                            loop.run_in_executor(executor, func, item, *args, **kwargs) 
                            for item in batch
                        ]
                        batch_results = await asyncio.gather(*batch_futures, return_exceptions=True)
                        results.extend(batch_results)
                else:
                    # Process all items in parallel
                    futures = [
                        loop.run_in_executor(executor, func, item, *args, **kwargs) 
                        for item in items
                    ]
                    results = await asyncio.gather(*futures, return_exceptions=True)
                
                # Log performance metrics
                duration = time.time() - start_time
                logger.info(f"Completed parallel CPU processing: {func.__name__} in {duration:.2f}s")
                
                return results
                
            finally:
                # Only shutdown if we created a custom executor
                if max_workers:
                    executor.shutdown(wait=False)
        
        return wrapper
    return decorator


async def execute_parallel(
    func: Callable, 
    items: List[Any], 
    task_type: TaskType = TaskType.IO_BOUND,
    max_workers: Optional[int] = None,
    batch_size: Optional[int] = None,
    *args, **kwargs
) -> List[Any]:
    """
    Execute a function in parallel for a list of items.
    
    Args:
        func: Function to execute
        items: List of items to process
        task_type: TaskType.IO_BOUND or TaskType.CPU_BOUND
        max_workers: Maximum number of workers
        batch_size: Batch size for large datasets
        *args, **kwargs: Additional arguments for the function
    
    Returns:
        List of results from parallel execution
    """
    if not items:
        return []
    
    start_time = time.time()
    logger.info(f"Starting parallel execution: {func.__name__} ({task_type.value}) with {len(items)} items")
    
    # Choose executor based on task type
    if task_type == TaskType.IO_BOUND:
        executor = ThreadPoolExecutor(max_workers=max_workers or ConcurrentConfig.DEFAULT_THREAD_WORKERS)
    else:
        executor = ProcessPoolExecutor(max_workers=max_workers or ConcurrentConfig.DEFAULT_PROCESS_WORKERS)
    
    try:
        loop = asyncio.get_event_loop()
        
        # Process in batches if specified
        if batch_size and len(items) > batch_size:
            results = []
            for i in range(0, len(items), batch_size):
                batch = items[i:i + batch_size]
                batch_futures = [
                    loop.run_in_executor(executor, func, item, *args, **kwargs) 
                    for item in batch
                ]
                batch_results = await asyncio.gather(*batch_futures, return_exceptions=True)
                results.extend(batch_results)
        else:
            futures = [
                loop.run_in_executor(executor, func, item, *args, **kwargs) 
                for item in items
            ]
            results = await asyncio.gather(*futures, return_exceptions=True)
        
        duration = time.time() - start_time
        success_count = len([r for r in results if not isinstance(r, Exception)])
        error_count = len(results) - success_count
        
        logger.info(
            f"Completed parallel execution: {func.__name__} in {duration:.2f}s "
            f"(Success: {success_count}, Errors: {error_count})"
        )
        
        return results
        
    finally:
        executor.shutdown(wait=False)


async def map_parallel(
    func: Callable,
    items: List[Any],
    task_type: TaskType = TaskType.IO_BOUND,
    max_workers: Optional[int] = None,
    chunk_size: Optional[int] = None
) -> List[Any]:
    """
    Map function over items in parallel, similar to built-in map() but async.
    
    Args:
        func: Function to map over items
        items: Items to process
        task_type: Type of task (IO_BOUND or CPU_BOUND)
        max_workers: Maximum number of workers
        chunk_size: Chunk size for processing
    
    Returns:
        List of results
    """
    if task_type == TaskType.IO_BOUND:
        executor = concurrent_manager.thread_executor
    else:
        executor = concurrent_manager.process_executor
    
    loop = asyncio.get_event_loop()
    futures = [loop.run_in_executor(executor, func, item) for item in items]
    
    return await asyncio.gather(*futures, return_exceptions=True)


def batch_processor(batch_size: int = 100):
    """
    Decorator for processing large datasets in batches.
    
    Usage:
        @batch_processor(batch_size=50)
        @parallel_io()
        async def process_large_dataset(items: List[Any]) -> List[Any]:
            # Will process items in batches of 50
            pass
    """
    def decorator(func: Callable):
        @functools.wraps(func)
        async def wrapper(items: List[Any], *args, **kwargs):
            if len(items) <= batch_size:
                return await func(items, *args, **kwargs)
            
            results = []
            for i in range(0, len(items), batch_size):
                batch = items[i:i + batch_size]
                batch_result = await func(batch, *args, **kwargs)
                if isinstance(batch_result, list):
                    results.extend(batch_result)
                else:
                    results.append(batch_result)
            
            return results
        
        return wrapper
    return decorator


# Cleanup function for application shutdown
async def shutdown_concurrent_manager():
    """Shutdown the concurrent manager - call this during app shutdown"""
    concurrent_manager.shutdown()
    logger.info("Concurrent processing manager shutdown complete") 