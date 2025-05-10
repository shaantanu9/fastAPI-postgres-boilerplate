import asyncio
from typing import Callable, Any, Dict
from loguru import logger

class AsyncTaskQueue:
    """
    A simple in-memory async task queue for demonstration and lightweight background task processing.
    For production, consider using Celery, Dramatiq, or RQ with Redis/RabbitMQ.
    """
    def __init__(self):
        self.queue = asyncio.Queue()
        self.running = False

    async def worker(self):
        while self.running:
            func, args, kwargs = await self.queue.get()
            try:
                logger.info(f"Running async task: {func.__name__}")
                await func(*args, **kwargs)
            except Exception as e:
                logger.exception(f"Error in async task: {e}")
            self.queue.task_done()

    def start(self):
        if not self.running:
            self.running = True
            asyncio.create_task(self.worker())

    def stop(self):
        self.running = False

    async def add_task(self, func: Callable, *args, **kwargs):
        await self.queue.put((func, args, kwargs))

# Singleton for app-wide usage
async_task_queue = AsyncTaskQueue()
