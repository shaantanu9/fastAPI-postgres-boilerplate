"""Task Monitoring Dashboard.

This module provides FastAPI endpoints for a comprehensive task monitoring dashboard,
including:
- Real-time task status monitoring
- Historical task execution data
- Task performance metrics
- Task management controls
"""

from datetime import datetime, timedelta
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.security.api_key import api_key_security
from app.utils.procrastinate_manager import (
    ProcrastinateTaskPriority,
    get_procrastinate_manager,
)
from app.utils.task_scheduler import get_task_scheduler

router = APIRouter(
    prefix="/tasks", tags=["task-monitoring"], dependencies=[Depends(api_key_security)],
)


@router.get("/dashboard-data")
async def get_dashboard_data() -> dict[str, Any]:
    """Get comprehensive dashboard data for task monitoring."""
    scheduler = get_task_scheduler()
    proc_manager = await get_procrastinate_manager()

    # Get scheduled tasks
    scheduled_tasks = scheduler.get_scheduled_tasks()

    # Get task history
    task_history = scheduler.get_task_history(limit=50)

    # Get task stats
    task_stats = scheduler.get_task_stats()

    # Get queue stats from Procrastinate
    try:
        queue_stats = await proc_manager.get_queue_stats()
    except Exception as e:
        queue_stats = {"error": str(e)}

    # Prepare chart data
    executions_by_day = _group_executions_by_day(task_history)
    status_distribution = task_stats.get("status_counts", {})
    tag_distribution = task_stats.get("tag_counts", {})

    return {
        "summary": {
            "active_schedules": len(scheduled_tasks),
            "success_rate": task_stats.get("success_rate", 0),
            "total_executions": task_stats.get("total_executions", 0),
            "queued_tasks": queue_stats.get("total_queued", 0),
        },
        "charts": {
            "executions_by_day": executions_by_day,
            "status_distribution": status_distribution,
            "tag_distribution": tag_distribution,
        },
        "scheduled_tasks": scheduled_tasks[:20],  # Limit to 20 for UI
        "recent_executions": task_history[:20],  # Limit to 20 for UI
        "queue_stats": queue_stats,
    }


@router.get("/scheduled")
async def get_scheduled_tasks(
    tags: Annotated[list[str] | None, Query()] = None, limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> list[dict[str, Any]]:
    """Get all scheduled tasks, optionally filtered by tags."""
    scheduler = get_task_scheduler()
    tasks = scheduler.get_scheduled_tasks(tags=tags)
    return tasks[:limit]


@router.get("/history")
async def get_task_history(
    status: str | None = None,
    tag: str | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> list[dict[str, Any]]:
    """Get task execution history with optional filters."""
    scheduler = get_task_scheduler()
    history = scheduler.get_task_history(limit=limit)

    # Apply filters if provided
    if status:
        history = [task for task in history if task["status"] == status]

    if tag:
        # Filter by tasks that have the specified tag
        scheduler_tasks = scheduler.get_scheduled_tasks(tags=[tag])
        job_ids = [task["job_id"] for task in scheduler_tasks]
        history = [task for task in history if task["job_id"] in job_ids]

    return history


@router.post("/schedule/cron")
async def schedule_cron_task(
    task_name: str,
    cron_expression: str,
    task_kwargs: dict[str, Any] | None = None,
    description: str = "",
    tags: list[str] | None = None,
    priority: str = "NORMAL",
) -> dict[str, Any]:
    """Schedule a new task with cron expression."""
    if tags is None:
        tags = []
    if task_kwargs is None:
        task_kwargs = {}
    scheduler = get_task_scheduler()

    # Map string priority to enum
    priority_enum = getattr(
        ProcrastinateTaskPriority, priority, ProcrastinateTaskPriority.NORMAL,
    )

    job_id = await scheduler.schedule_cron_task(
        task_name=task_name,
        cron_expression=cron_expression,
        task_kwargs=task_kwargs,
        description=description,
        tags=tags,
        priority=priority_enum,
    )

    return {
        "job_id": job_id,
        "task_name": task_name,
        "schedule_type": "cron",
        "cron_expression": cron_expression,
        "status": "scheduled",
    }


@router.post("/schedule/interval")
async def schedule_interval_task(
    task_name: str,
    interval_seconds: int,
    task_kwargs: dict[str, Any] | None = None,
    description: str = "",
    tags: list[str] | None = None,
    priority: str = "NORMAL",
) -> dict[str, Any]:
    """Schedule a new task with interval in seconds."""
    if tags is None:
        tags = []
    if task_kwargs is None:
        task_kwargs = {}
    scheduler = get_task_scheduler()

    # Map string priority to enum
    priority_enum = getattr(
        ProcrastinateTaskPriority, priority, ProcrastinateTaskPriority.NORMAL,
    )

    job_id = await scheduler.schedule_interval_task(
        task_name=task_name,
        interval_seconds=interval_seconds,
        task_kwargs=task_kwargs,
        description=description,
        tags=tags,
        priority=priority_enum,
    )

    return {
        "job_id": job_id,
        "task_name": task_name,
        "schedule_type": "interval",
        "interval_seconds": interval_seconds,
        "status": "scheduled",
    }


@router.post("/schedule/once")
async def schedule_one_time_task(
    task_name: str,
    run_at: datetime,
    task_kwargs: dict[str, Any] | None = None,
    description: str = "",
    tags: list[str] | None = None,
    priority: str = "NORMAL",
) -> dict[str, Any]:
    """Schedule a one-time task at a specific time."""
    if tags is None:
        tags = []
    if task_kwargs is None:
        task_kwargs = {}
    scheduler = get_task_scheduler()

    # Map string priority to enum
    priority_enum = getattr(
        ProcrastinateTaskPriority, priority, ProcrastinateTaskPriority.NORMAL,
    )

    job_id = await scheduler.schedule_one_time_task(
        task_name=task_name,
        run_at=run_at,
        task_kwargs=task_kwargs,
        description=description,
        tags=tags,
        priority=priority_enum,
    )

    return {
        "job_id": job_id,
        "task_name": task_name,
        "schedule_type": "once",
        "run_at": run_at.isoformat(),
        "status": "scheduled",
    }


@router.delete("/schedule/{job_id}")
async def cancel_scheduled_task(job_id: str) -> dict[str, Any]:
    """Cancel a scheduled task."""
    scheduler = get_task_scheduler()
    success = await scheduler.cancel_scheduled_task(job_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task with job_id {job_id} not found",
        )

    return {
        "job_id": job_id,
        "status": "cancelled",
        "message": "Task successfully cancelled",
    }


@router.get("/stats")
async def get_task_stats() -> dict[str, Any]:
    """Get statistics about scheduled tasks and their execution."""
    scheduler = get_task_scheduler()
    return scheduler.get_task_stats()


@router.get("/procrastinate/jobs")
async def get_procrastinate_jobs(
    status: str | None = None,
    queue: str | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> list[dict[str, Any]]:
    """Get Procrastinate jobs with optional filters."""
    proc_manager = await get_procrastinate_manager()

    try:
        return await proc_manager.get_jobs(status=status, queue=queue, limit=limit)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch Procrastinate jobs: {e!s}",
        )


# Helper functions for dashboard data processing


def _group_executions_by_day(task_history: list[dict[str, Any]]) -> dict[str, Any]:
    """Group task executions by day for time-series charts."""
    today = datetime.now().date()
    date_counts = {(today - timedelta(days=i)).isoformat(): 0 for i in range(7)}

    for task in task_history:
        try:
            # Extract date from start_time
            start_time = datetime.fromisoformat(task["start_time"])
            date_str = start_time.date().isoformat()

            # Count executions in the last 7 days
            if date_str in date_counts:
                date_counts[date_str] += 1
        except (ValueError, KeyError):
            # Skip records with invalid dates
            continue

    # Convert to list format for charts
    return {"dates": list(date_counts.keys()), "counts": list(date_counts.values())}
