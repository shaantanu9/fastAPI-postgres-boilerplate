import asyncio
import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any

from loguru import logger

from app.utils.concurrent_utils import TaskType, concurrent_manager, execute_parallel


@dataclass
class TaskResult:
    """Task execution result."""

    task_id: str
    status: str  # 'pending', 'running', 'completed', 'failed'
    result: Any = None
    error: str | None = None
    start_time: datetime | None = None
    end_time: datetime | None = None
    execution_time: float | None = None


class TaskPriority(Enum):
    """Task priority levels."""

    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class Task:
    """Enhanced task representation."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    func: Callable = None
    args: tuple = ()
    kwargs: dict = field(default_factory=dict)
    priority: TaskPriority = TaskPriority.NORMAL
    task_type: TaskType = TaskType.IO_BOUND
    max_retries: int = 3
    retry_count: int = 0
    created_at: datetime = field(default_factory=datetime.now)
    scheduled_at: datetime | None = None


class EnhancedAsyncTaskQueue:
    """Enhanced async task queue with concurrent processing capabilities.

    Features:
    - Parallel task execution using ThreadPoolExecutor and ProcessPoolExecutor
    - Task priorities and scheduling
    - Retry mechanism with exponential backoff
    - Task result tracking
    - Batch task processing
    - Health monitoring
    """

    def __init__(self, max_workers: int = 10) -> None:
        self.queue = asyncio.PriorityQueue()
        self.results: dict[str, TaskResult] = {}
        self.running = False
        self.workers: list[asyncio.Task] = []
        self.max_workers = max_workers
        self.worker_count = 0
        self.processed_tasks = 0
        self.failed_tasks = 0

    async def worker(self, worker_id: int) -> None:
        """Enhanced worker with parallel processing capabilities."""
        logger.info(f"Starting task queue worker {worker_id}")

        while self.running:
            try:
                # Get task from priority queue
                priority, task = await asyncio.wait_for(self.queue.get(), timeout=1.0)

                # Update task status
                task_result = self.results.get(task.id)
                if task_result:
                    task_result.status = "running"
                    task_result.start_time = datetime.now()

                start_time = time.time()
                logger.info(
                    f"Worker {worker_id} executing task: {task.func.__name__} (ID: {task.id})",
                )

                try:
                    # Execute task based on type
                    if task.task_type == TaskType.CPU_BOUND:
                        # Use ProcessPoolExecutor for CPU-bound tasks
                        executor = concurrent_manager.process_executor
                    else:
                        # Use ThreadPoolExecutor for I/O-bound tasks
                        executor = concurrent_manager.thread_executor

                    # Execute task
                    if asyncio.iscoroutinefunction(task.func):
                        result = await task.func(*task.args, **task.kwargs)
                    else:
                        loop = asyncio.get_event_loop()
                        result = await loop.run_in_executor(
                            executor, task.func, *task.args, **task.kwargs,
                        )

                    # Update result
                    execution_time = time.time() - start_time
                    if task_result:
                        task_result.status = "completed"
                        task_result.result = result
                        task_result.end_time = datetime.now()
                        task_result.execution_time = execution_time

                    self.processed_tasks += 1
                    logger.info(f"Task {task.id} completed in {execution_time:.2f}s")

                except Exception as e:
                    # Handle task failure with retry logic
                    execution_time = time.time() - start_time
                    logger.error(f"Task {task.id} failed: {e}")

                    if task.retry_count < task.max_retries:
                        # Retry the task
                        task.retry_count += 1
                        retry_delay = min(
                            2**task.retry_count, 60,
                        )  # Exponential backoff

                        logger.info(
                            f"Retrying task {task.id} in {retry_delay}s (attempt {task.retry_count}/{task.max_retries})",
                        )
                        await asyncio.sleep(retry_delay)
                        await self.queue.put((task.priority.value, task))
                    else:
                        # Max retries exceeded
                        self.failed_tasks += 1
                        if task_result:
                            task_result.status = "failed"
                            task_result.error = str(e)
                            task_result.end_time = datetime.now()
                            task_result.execution_time = execution_time

                self.queue.task_done()

            except TimeoutError:
                # No tasks available, continue waiting
                continue
            except Exception as e:
                logger.exception(f"Worker {worker_id} error: {e}")
                await asyncio.sleep(1)

        logger.info(f"Task queue worker {worker_id} stopped")

    def start(self, num_workers: int | None = None) -> None:
        """Start the task queue with multiple workers."""
        if not self.running:
            self.running = True
            worker_count = num_workers or self.max_workers

            for i in range(worker_count):
                worker_task = asyncio.create_task(self.worker(i))
                self.workers.append(worker_task)

            self.worker_count = worker_count
            logger.info(f"Started task queue with {worker_count} workers")

    async def stop(self) -> None:
        """Stop the task queue and all workers gracefully."""
        if not self.running:
            return
            
        logger.info("Stopping task queue...")
        self.running = False

        # Cancel all workers
        for worker in self.workers:
            worker.cancel()

        # Wait for workers to finish with timeout
        if self.workers:
            try:
                await asyncio.wait_for(
                    asyncio.gather(*self.workers, return_exceptions=True),
                    timeout=5.0
                )
            except TimeoutError:
                logger.warning("Some workers didn't stop within timeout")

        self.workers.clear()
        self.worker_count = 0
        
        # Clear pending tasks
        while not self.queue.empty():
            try:
                self.queue.get_nowait()
                self.queue.task_done()
            except asyncio.QueueEmpty:
                break
                
        logger.info("Task queue stopped gracefully")

    async def add_task(
        self,
        func: Callable,
        *args,
        priority: TaskPriority = TaskPriority.NORMAL,
        task_type: TaskType = TaskType.IO_BOUND,
        max_retries: int = 3,
        **kwargs,
    ) -> str:
        """Add a single task to the queue."""
        task = Task(
            func=func,
            args=args,
            kwargs=kwargs,
            priority=priority,
            task_type=task_type,
            max_retries=max_retries,
        )

        # Create task result tracker
        self.results[task.id] = TaskResult(task_id=task.id, status="pending")

        # Add to priority queue (lower priority value = higher priority)
        await self.queue.put((priority.value, task))

        logger.info(f"Added task {task.id}: {func.__name__}")
        return task.id

    async def add_batch_tasks(
        self,
        func: Callable,
        items: list[Any],
        priority: TaskPriority = TaskPriority.NORMAL,
        task_type: TaskType = TaskType.IO_BOUND,
        max_retries: int = 3,
        **common_kwargs,
    ) -> list[str]:
        """Add multiple tasks for batch processing."""
        task_ids = []

        for item in items:
            task_id = await self.add_task(
                func,
                item,
                priority=priority,
                task_type=task_type,
                max_retries=max_retries,
                **common_kwargs,
            )
            task_ids.append(task_id)

        logger.info(f"Added {len(task_ids)} batch tasks for {func.__name__}")
        return task_ids

    async def add_parallel_batch(
        self,
        func: Callable,
        items: list[Any],
        task_type: TaskType = TaskType.IO_BOUND,
        max_workers: int | None = None,
        batch_size: int | None = None,
        **kwargs,
    ) -> str:
        """Add a single task that processes multiple items in parallel."""

        async def parallel_batch_processor():
            """Execute the batch in parallel."""
            return await execute_parallel(
                func, items, task_type, max_workers, batch_size, **kwargs,
            )

        return await self.add_task(
            parallel_batch_processor,
            priority=TaskPriority.NORMAL,
            task_type=TaskType.IO_BOUND,  # The coordinator is I/O bound
            max_retries=1,
        )

    def get_task_result(self, task_id: str) -> TaskResult | None:
        """Get the result of a specific task."""
        return self.results.get(task_id)

    async def wait_for_task(
        self, task_id: str, timeout: float | None = None,
    ) -> TaskResult:
        """Wait for a specific task to complete."""
        start_time = time.time()

        while True:
            result = self.get_task_result(task_id)
            if result and result.status in ["completed", "failed"]:
                return result

            if timeout and (time.time() - start_time) > timeout:
                msg = f"Task {task_id} did not complete within {timeout}s"
                raise TimeoutError(msg)

            await asyncio.sleep(0.1)

    async def wait_for_batch(
        self, task_ids: list[str], timeout: float | None = None,
    ) -> list[TaskResult]:
        """Wait for multiple tasks to complete."""
        results = []

        for task_id in task_ids:
            try:
                result = await self.wait_for_task(task_id, timeout)
                results.append(result)
            except TimeoutError as e:
                logger.error(f"Timeout waiting for task {task_id}: {e}")
                results.append(TaskResult(task_id=task_id, status="timeout"))

        return results

    def get_queue_stats(self) -> dict[str, Any]:
        """Get queue statistics."""
        pending_tasks = sum(1 for r in self.results.values() if r.status == "pending")
        running_tasks = sum(1 for r in self.results.values() if r.status == "running")
        completed_tasks = sum(
            1 for r in self.results.values() if r.status == "completed"
        )
        failed_tasks = sum(1 for r in self.results.values() if r.status == "failed")

        return {
            "queue_size": self.queue.qsize(),
            "worker_count": self.worker_count,
            "running": self.running,
            "pending_tasks": pending_tasks,
            "running_tasks": running_tasks,
            "completed_tasks": completed_tasks,
            "failed_tasks": failed_tasks,
            "total_processed": self.processed_tasks,
            "total_failed": self.failed_tasks,
            "success_rate": (
                self.processed_tasks / max(self.processed_tasks + self.failed_tasks, 1)
            )
            * 100,
        }

    async def health_check(self) -> dict[str, Any]:
        """Perform health check on the task queue."""
        stats = self.get_queue_stats()

        # Add health indicators
        health_status = "healthy"
        issues = []

        if not self.running:
            health_status = "unhealthy"
            issues.append("Task queue is not running")

        if stats["failed_tasks"] > stats["completed_tasks"]:
            health_status = "degraded"
            issues.append("High failure rate")

        if stats["queue_size"] > 1000:
            health_status = "degraded"
            issues.append("Queue backlog is high")

        return {
            **stats,
            "health_status": health_status,
            "issues": issues,
            "timestamp": datetime.now().isoformat(),
        }

    def clear_completed_results(self, older_than_hours: int = 24) -> None:
        """Clear old completed task results to prevent memory buildup."""
        cutoff_time = datetime.now() - timedelta(hours=older_than_hours)

        to_remove = [
            task_id
            for task_id, result in self.results.items()
            if result.status in ["completed", "failed"]
            and result.end_time
            and result.end_time < cutoff_time
        ]

        for task_id in to_remove:
            del self.results[task_id]

        logger.info(f"Cleared {len(to_remove)} old task results")


# Backward compatibility with original AsyncTaskQueue
class AsyncTaskQueue(EnhancedAsyncTaskQueue):
    """Backward-compatible wrapper for the enhanced task queue.
    Maintains the original simple interface while providing enhanced capabilities.
    """

    def __init__(self) -> None:
        super().__init__(
            max_workers=5,
        )  # Conservative default for backward compatibility

    async def add_task(self, func: Callable, *args, **kwargs):
        """Original interface for adding tasks."""
        return await super().add_task(
            func,
            *args,
            priority=TaskPriority.NORMAL,
            task_type=TaskType.IO_BOUND,
            **kwargs,
        )


# Singleton for app-wide usage (enhanced version)
enhanced_task_queue = EnhancedAsyncTaskQueue()

# Singleton for backward compatibility
async_task_queue = AsyncTaskQueue()
