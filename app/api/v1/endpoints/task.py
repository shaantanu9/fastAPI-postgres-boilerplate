import asyncio

from fastapi import APIRouter
from loguru import logger

from app.utils.task_queue import async_task_queue

router = APIRouter()


async def example_long_task(task_id: int, duration: int = 5) -> None:
    """Example of a long-running asynchronous background task.

    Args:
        task_id (int): Unique identifier for the task.
        duration (int, optional): Duration in seconds for which the task sleeps. Defaults to 5.

    Returns:
        None
    Raises:
        None

    """
    logger.info(f"[Task {task_id}] Started, will sleep for {duration}s")
    await asyncio.sleep(duration)
    logger.info(f"[Task {task_id}] Completed")


@router.post("/trigger")
async def trigger_task(task_id: int, duration: int = 5):
    """Endpoint to trigger a long-running background task by adding it to the async queue.

    Args:
        task_id (int): Unique identifier for the task.
        duration (int, optional): Duration in seconds for which the task should run. Defaults to 5.

    Returns:
        dict: Status message with task ID and duration.

    Raises:
        None: Always queues the task; does not raise.

    """
    # Add a long-running task to the async queue
    await async_task_queue.add_task(example_long_task, task_id, duration)
    return {"status": "queued", "task_id": task_id, "duration": duration}
