"""
Advanced Task Scheduling System using Procrastinate

This module extends the existing Procrastinate implementation with advanced scheduling
capabilities including:
- Periodic task scheduling with cron-like patterns
- Task dependencies and workflows
- Runtime configuration of schedules
- Monitoring and alerting for failed tasks
"""

import asyncio
import json
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Callable, Union, TypeVar
import time
from uuid import uuid4
from enum import Enum
from croniter import croniter
from loguru import logger

import procrastinate
from procrastinate import App, PsycopgConnector, AiopgConnector
from procrastinate.tasks import Task

from app.core.config import get_settings
from app.utils.procrastinate_manager import (
    procrastinate_app, 
    procrastinate_manager, 
    ProcrastinateTaskPriority,
    ProcrastinateTaskType
)

settings = get_settings()

# Task result type
T = TypeVar('T')


class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SCHEDULED = "scheduled"
    CANCELLED = "cancelled"


class TaskScheduleType(Enum):
    ONCE = "once"           # Run once at a specific time
    INTERVAL = "interval"   # Run every N minutes/hours/days
    CRON = "cron"           # Run according to cron expression
    EVENT = "event"         # Run when triggered by an event


class ScheduleMetadata:
    """Class to store schedule metadata"""
    
    def __init__(
        self,
        schedule_type: TaskScheduleType,
        job_id: str,
        schedule_config: Dict[str, Any],
        created_by: str = "system",
        description: str = "",
        tags: List[str] = None,
        priority: ProcrastinateTaskPriority = ProcrastinateTaskPriority.NORMAL,
    ):
        self.job_id = job_id
        self.schedule_type = schedule_type
        self.schedule_config = schedule_config
        self.created_by = created_by
        self.created_at = datetime.now()
        self.description = description
        self.tags = tags or []
        self.priority = priority
        self.last_run = None
        self.next_run = self._calculate_next_run()
        self.run_count = 0
    
    def _calculate_next_run(self) -> Optional[datetime]:
        """Calculate next run time based on schedule type"""
        if self.schedule_type == TaskScheduleType.ONCE:
            return self.schedule_config.get("run_at")
        
        elif self.schedule_type == TaskScheduleType.INTERVAL:
            interval = self.schedule_config.get("interval", 60)  # default 60 seconds
            start_from = self.schedule_config.get("start_from", datetime.now())
            return start_from + timedelta(seconds=interval)
        
        elif self.schedule_type == TaskScheduleType.CRON:
            cron_expr = self.schedule_config.get("cron_expr", "0 0 * * *")  # default: daily at midnight
            base_time = datetime.now()
            try:
                cron = croniter(cron_expr, base_time)
                return cron.get_next(datetime)
            except Exception as e:
                logger.error(f"Invalid cron expression: {cron_expr} - {e}")
                return None
        
        return None
    
    def update_after_run(self):
        """Update metadata after task runs"""
        self.last_run = datetime.now()
        self.run_count += 1
        self.next_run = self._calculate_next_run()
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage/serialization"""
        return {
            "job_id": self.job_id,
            "schedule_type": self.schedule_type.value,
            "schedule_config": self.schedule_config,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat(),
            "description": self.description,
            "tags": self.tags,
            "priority": self.priority.value if isinstance(self.priority, Enum) else self.priority,
            "last_run": self.last_run.isoformat() if self.last_run else None,
            "next_run": self.next_run.isoformat() if self.next_run else None,
            "run_count": self.run_count
        }


class TaskScheduler:
    """
    Enhanced task scheduler using Procrastinate.

    This class manages scheduled, periodic, and one-time tasks using Procrastinate as the backend.
    It maintains in-memory metadata for schedules, results, and execution history, and provides methods
    to schedule, cancel, and inspect tasks.
    """
    
    def __init__(self):
        self.procrastinate_app = procrastinate_app
        self.schedules: Dict[str, ScheduleMetadata] = {}
        self.is_running = False
        self.scheduler_task = None
        self.task_results = {}
        self.task_history = {}
    
    async def initialize(self):
        """
        Initialize the task scheduler and start the main scheduling loop.

        This function ensures the procrastinate manager is initialized and starts the loop that
        checks for due tasks and executes them.
        """
        if not self.is_running:
            logger.info("Initializing task scheduler")
            await procrastinate_manager.initialize()
            
            # Start the scheduler loop
            self.is_running = True
            self.scheduler_task = asyncio.create_task(self._scheduler_loop())
            logger.info("Task scheduler initialized and running")
    
    async def stop(self):
        """
        Stop the scheduler loop and cancel any running scheduling tasks.
        """
        if self.is_running:
            self.is_running = False
            if self.scheduler_task:
                self.scheduler_task.cancel()
                try:
                    await self.scheduler_task
                except asyncio.CancelledError:
                    pass
            logger.info("Task scheduler stopped")
    
    async def _scheduler_loop(self):
        """
        Main scheduler loop.

        Periodically checks all scheduled tasks and triggers those whose next_run is due.
        Handles errors gracefully and sleeps between checks.
        """
        logger.info("Scheduler loop started")
        
        while self.is_running:
            try:
                now = datetime.now()
                
                # Check for tasks to run
                tasks_to_run = []
                for job_id, metadata in list(self.schedules.items()):
                    if metadata.next_run and metadata.next_run <= now:
                        tasks_to_run.append((job_id, metadata))
                
                # Execute due tasks
                for job_id, metadata in tasks_to_run:
                    logger.info(f"Running scheduled task: {job_id}")
                    await self._execute_scheduled_task(job_id, metadata)
                
                # Sleep briefly
                await asyncio.sleep(1)
            
            except Exception as e:
                logger.error(f"Error in scheduler loop: {e}")
                await asyncio.sleep(5)  # Sleep longer on error
    
    async def _execute_scheduled_task(self, job_id: str, metadata: ScheduleMetadata):
        """
        Execute a scheduled task by deferring it to Procrastinate.

        Args:
            job_id (str): The unique identifier for the scheduled job.
            metadata (ScheduleMetadata): The metadata describing the schedule and task details.
        """
        try:
            # Get task details
            task_info = metadata.schedule_config.get("task_info", {})
            task_name = task_info.get("task_name", "")
            task_kwargs = task_info.get("task_kwargs", {})
            
            # Record task execution
            task_run_id = str(uuid4())
            execution_record = {
                "task_run_id": task_run_id,
                "job_id": job_id,
                "task_name": task_name,
                "start_time": datetime.now().isoformat(),
                "status": TaskStatus.RUNNING.value,
                "end_time": None,
                "result": None,
                "error": None
            }
            
            self.task_history[task_run_id] = execution_record
            
            # Execute the task via Procrastinate
            result = None
            error = None
            try:
                if hasattr(procrastinate_manager, f"defer_{task_name}"):
                    # Use specific defer method if exists
                    defer_method = getattr(procrastinate_manager, f"defer_{task_name}")
                    proc_job_id = await defer_method(**task_kwargs)
                    result = {"procrastinate_job_id": proc_job_id}
                else:
                    # Generic task execution
                    proc_job_id = await procrastinate_manager.app.configure_task(name=task_name).defer(**task_kwargs)
                    result = {"procrastinate_job_id": proc_job_id}
                
                # Store result
                self.task_results[job_id] = result
                execution_record["status"] = TaskStatus.COMPLETED.value
                execution_record["result"] = result
                
            except Exception as e:
                logger.error(f"Error executing scheduled task {job_id}: {e}")
                error = str(e)
                execution_record["status"] = TaskStatus.FAILED.value
                execution_record["error"] = error
            
            # Update metadata and record
            execution_record["end_time"] = datetime.now().isoformat()
            metadata.update_after_run()
            
            # Remove one-time schedules after execution
            if metadata.schedule_type == TaskScheduleType.ONCE:
                del self.schedules[job_id]
                
        except Exception as e:
            logger.error(f"Error in task execution wrapper: {e}")
    
    async def schedule_task(
        self,
        task_name: str,
        schedule_type: TaskScheduleType,
        task_kwargs: Dict[str, Any] = None,
        schedule_config: Dict[str, Any] = None,
        description: str = "",
        tags: List[str] = None,
        priority: ProcrastinateTaskPriority = ProcrastinateTaskPriority.NORMAL,
        created_by: str = "system"
    ) -> str:
        """
        Schedule a task with the specified configuration.

        Args:
            task_name (str): Name of the task to schedule.
            schedule_type (TaskScheduleType): Type of schedule (ONCE, INTERVAL, CRON, EVENT).
            task_kwargs (Dict[str, Any], optional): Arguments to pass to the task.
            schedule_config (Dict[str, Any], optional): Additional scheduling configuration.
            description (str, optional): Description of the scheduled task.
            tags (List[str], optional): Tags for filtering/grouping.
            priority (ProcrastinateTaskPriority, optional): Task priority.
            created_by (str, optional): Creator of the schedule.

        Returns:
            str: The job ID of the scheduled task.
        """
        # Generate a unique job ID
        job_id = str(uuid4())
        
        # Prepare schedule configuration
        config = schedule_config or {}
        config["task_info"] = {
            "task_name": task_name,
            "task_kwargs": task_kwargs or {}
        }
        
        # Create schedule metadata
        metadata = ScheduleMetadata(
            schedule_type=schedule_type,
            job_id=job_id,
            schedule_config=config,
            created_by=created_by,
            description=description,
            tags=tags,
            priority=priority
        )
        
        # Store the schedule
        self.schedules[job_id] = metadata
        logger.info(f"Scheduled task {task_name} with job ID: {job_id}")
        
        return job_id
    
    async def schedule_cron_task(
        self,
        task_name: str,
        cron_expression: str,  # e.g., "*/5 * * * *" for every 5 minutes
        task_kwargs: Dict[str, Any] = None,
        description: str = "",
        tags: List[str] = None,
        priority: ProcrastinateTaskPriority = ProcrastinateTaskPriority.NORMAL
    ) -> str:
        """
        Schedule a task to run on a cron schedule.

        Args:
            task_name (str): Name of the task.
            cron_expression (str): Cron expression for scheduling.
            task_kwargs (Dict[str, Any], optional): Arguments for the task.
            description (str, optional): Description for the schedule.
            tags (List[str], optional): Tags for grouping/filtering.
            priority (ProcrastinateTaskPriority, optional): Task priority.

        Returns:
            str: The job ID of the scheduled task.
        """
        return await self.schedule_task(
            task_name=task_name,
            schedule_type=TaskScheduleType.CRON,
            task_kwargs=task_kwargs,
            schedule_config={"cron_expr": cron_expression},
            description=description,
            tags=tags,
            priority=priority
        )
    
    async def schedule_interval_task(
        self,
        task_name: str,
        interval_seconds: int,
        start_from: Optional[datetime] = None,
        task_kwargs: Dict[str, Any] = None,
        description: str = "",
        tags: List[str] = None,
        priority: ProcrastinateTaskPriority = ProcrastinateTaskPriority.NORMAL
    ) -> str:
        """
        Schedule a task to run at regular intervals.

        Args:
            task_name (str): Name of the task.
            interval_seconds (int): Interval in seconds between runs.
            start_from (datetime, optional): When to start the interval schedule.
            task_kwargs (Dict[str, Any], optional): Arguments for the task.
            description (str, optional): Description for the schedule.
            tags (List[str], optional): Tags for grouping/filtering.
            priority (ProcrastinateTaskPriority, optional): Task priority.

        Returns:
            str: The job ID of the scheduled task.
        """
        return await self.schedule_task(
            task_name=task_name,
            schedule_type=TaskScheduleType.INTERVAL,
            task_kwargs=task_kwargs,
            schedule_config={
                "interval": interval_seconds,
                "start_from": start_from or datetime.now()
            },
            description=description,
            tags=tags,
            priority=priority
        )
    
    async def schedule_one_time_task(
        self,
        task_name: str,
        run_at: datetime,
        task_kwargs: Dict[str, Any] = None,
        description: str = "",
        tags: List[str] = None,
        priority: ProcrastinateTaskPriority = ProcrastinateTaskPriority.NORMAL
    ) -> str:
        """
        Schedule a one-time task to run at a specific time.

        Args:
            task_name (str): Name of the task.
            run_at (datetime): When to run the task.
            task_kwargs (Dict[str, Any], optional): Arguments for the task.
            description (str, optional): Description for the schedule.
            tags (List[str], optional): Tags for grouping/filtering.
            priority (ProcrastinateTaskPriority, optional): Task priority.

        Returns:
            str: The job ID of the scheduled task.
        """
        return await self.schedule_task(
            task_name=task_name,
            schedule_type=TaskScheduleType.ONCE,
            task_kwargs=task_kwargs,
            schedule_config={"run_at": run_at},
            description=description,
            tags=tags,
            priority=priority
        )
    
    async def cancel_scheduled_task(self, job_id: str) -> bool:
        """
        Cancel a scheduled task by its job ID.

        Args:
            job_id (str): The job ID of the scheduled task to cancel.

        Returns:
            bool: True if the task was cancelled, False if not found.
        """
        if job_id in self.schedules:
            del self.schedules[job_id]
            logger.info(f"Cancelled scheduled task with job ID: {job_id}")
            return True
        return False
    
    def get_scheduled_tasks(self, tags: List[str] = None) -> List[Dict[str, Any]]:
        """
        Get all scheduled tasks, optionally filtered by tags.

        Args:
            tags (List[str], optional): List of tags to filter tasks.

        Returns:
            List[Dict[str, Any]]: List of scheduled task metadata dictionaries.
        """
        results = []
        
        for job_id, metadata in self.schedules.items():
            # Filter by tags if provided
            if tags and not any(tag in metadata.tags for tag in tags):
                continue
                
            task_dict = metadata.to_dict()
            # Add result if available
            if job_id in self.task_results:
                task_dict["last_result"] = self.task_results[job_id]
                
            results.append(task_dict)
            
        return results
    
    def get_task_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get task execution history, most recent first.

        Args:
            limit (int, optional): Maximum number of history entries to return.

        Returns:
            List[Dict[str, Any]]: List of task execution history records.
        """
        history = list(self.task_history.values())
        # Sort by start time, most recent first
        history.sort(key=lambda x: x["start_time"], reverse=True)
        return history[:limit]
    
    def get_task_stats(self) -> Dict[str, Any]:
        """
        Get statistics about scheduled tasks and their execution.

        Returns:
            Dict[str, Any]: Dictionary with counts by status, tags, and success rate.
        """
        total_tasks = len(self.schedules)
        task_history = list(self.task_history.values())
        
        # Count tasks by status
        status_counts = {}
        for status in TaskStatus:
            status_counts[status.value] = sum(1 for task in task_history if task["status"] == status.value)
        
        # Count by tags
        tag_counts = {}
        for metadata in self.schedules.values():
            for tag in metadata.tags:
                tag_counts[tag] = tag_counts.get(tag, 0) + 1
        
        # Calculate success rate
        completed = status_counts.get(TaskStatus.COMPLETED.value, 0)
        failed = status_counts.get(TaskStatus.FAILED.value, 0)
        total_completed = completed + failed
        success_rate = (completed / total_completed * 100) if total_completed > 0 else 0
        
        return {
            "total_scheduled_tasks": total_tasks,
            "total_executions": len(task_history),
            "status_counts": status_counts,
            "tag_counts": tag_counts,
            "success_rate": round(success_rate, 2)
        }


# Singleton instance
task_scheduler = TaskScheduler()


async def init_task_scheduler():
    """Initialize the task scheduler"""
    await task_scheduler.initialize()
    return task_scheduler


def get_task_scheduler() -> TaskScheduler:
    """Get the task scheduler instance"""
    return task_scheduler


# Register common periodic tasks
async def register_common_tasks():
    """Register common periodic tasks at application startup"""
    scheduler = get_task_scheduler()
    
    # Database cleanup task - every day at 2 AM
    await scheduler.schedule_cron_task(
        task_name="cleanup_old_data",
        cron_expression="0 2 * * *",
        task_kwargs={"days_old": 30},
        description="Clean up old data from the database",
        tags=["maintenance", "cleanup"]
    )
    
    # System health check - every 15 minutes
    await scheduler.schedule_interval_task(
        task_name="system_health_check", 
        interval_seconds=15*60,
        description="System health monitoring",
        tags=["monitoring", "health"]
    )
    
    # Cache statistics reporting - every hour
    await scheduler.schedule_interval_task(
        task_name="cache_stats_report",
        interval_seconds=60*60,
        description="Cache statistics reporting",
        tags=["monitoring", "cache"]
    )
    
    logger.info("Common periodic tasks registered")
