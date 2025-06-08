"""
Endpoint to test Procrastinate task queue.
"""
from fastapi import APIRouter, BackgroundTasks
from app.utils.procrastinate_manager import procrastinate_app

router = APIRouter()

@procrastinate_app.task(name="test_procrastinate_task")
def test_procrastinate_task(message: str = "Hello from Procrastinate!"):
    # This will show up in the worker logs
    print(f"[Procrastinate] Executing test task: {message}")
    return {"status": "success", "message": message}

@router.post("/test-task", tags=["procrastinate-test"])
def trigger_test_task(background_tasks: BackgroundTasks):
    # Enqueue the test task
    test_procrastinate_task.defer(message="Triggered from /test-task endpoint!")
    return {"detail": "Test task enqueued. Check your worker logs for execution."}
