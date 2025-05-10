from fastapi import APIRouter, BackgroundTasks
from app.utils.task_queue import async_task_queue
from loguru import logger
import asyncio

router = APIRouter()

async def example_long_task(task_id: int, duration: int = 5):
    logger.info(f"[Task {task_id}] Started, will sleep for {duration}s")
    await asyncio.sleep(duration)
    logger.info(f"[Task {task_id}] Completed")

@router.post("/trigger")
async def trigger_task(task_id: int, duration: int = 5):
    # Add a long-running task to the async queue
    await async_task_queue.add_task(example_long_task, task_id, duration)
    return {"status": "queued", "task_id": task_id, "duration": duration}
