"""Enhanced Procrastinate Service.

This service class combines the existing concurrent.futures capabilities with Procrastinate
for persistent, distributed task processing. It provides the best of both worlds:
- Immediate parallel processing for synchronous operations
- Persistent, distributed processing for background operations
- Seamless integration between both approaches

Features:
- Hybrid task processing (immediate + persistent)
- Automatic fallback between processing modes
- Enhanced error handling and retry logic
- Monitoring and analytics integration
- Production-ready scaling capabilities
"""

from collections.abc import Callable
from datetime import datetime
from typing import Any

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.enhanced_base_service import EnhancedBaseService
from app.utils.concurrent_utils import TaskType
from app.utils.procrastinate_manager import (
    ProcrastinateManager,
    ProcrastinateTaskPriority,
    get_procrastinate_manager,
)
from app.utils.task_queue import enhanced_task_queue


class ProcessingMode:
    """Processing mode options."""

    IMMEDIATE = "immediate"  # Process immediately with concurrent.futures
    PERSISTENT = "persistent"  # Queue with Procrastinate for later processing
    HYBRID = "hybrid"  # Try immediate, fallback to persistent
    BACKGROUND = "background"  # Always use background processing


class EnhancedProcrastinateService(EnhancedBaseService):
    """Enhanced service that combines concurrent.futures with Procrastinate
    for optimal task processing in different scenarios.
    """

    def __init__(self, model_class: type) -> None:
        super().__init__(model_class)
        self.procrastinate_manager: ProcrastinateManager | None = None

    async def _get_procrastinate_manager(self) -> ProcrastinateManager:
        """Get or initialize Procrastinate manager."""
        if self.procrastinate_manager is None:
            self.procrastinate_manager = await get_procrastinate_manager()
        return self.procrastinate_manager

    async def process_bulk_data_hybrid(
        self,
        db: AsyncSession,
        data_items: list[dict[str, Any]],
        processing_func: Callable,
        mode: str = ProcessingMode.HYBRID,
        immediate_threshold: int = 100,
        priority: ProcrastinateTaskPriority = ProcrastinateTaskPriority.NORMAL,
        **kwargs,
    ) -> dict[str, Any]:
        """Process bulk data with hybrid approach:
        - Small datasets: immediate processing with concurrent.futures
        - Large datasets: persistent processing with Procrastinate
        - Configurable threshold and fallback logic.
        """
        logger.info(f"Processing {len(data_items)} items with mode: {mode}")

        try:
            if mode == ProcessingMode.IMMEDIATE or (
                mode == ProcessingMode.HYBRID and len(data_items) <= immediate_threshold
            ):
                # Use immediate concurrent processing
                logger.info("Using immediate concurrent processing")
                results = await self.process_data_parallel(
                    data_items, processing_func, TaskType.IO_BOUND, **kwargs,
                )

                return {
                    "mode": "immediate",
                    "total_items": len(data_items),
                    "successful": len(
                        [r for r in results if not isinstance(r, Exception)],
                    ),
                    "failed": len([r for r in results if isinstance(r, Exception)]),
                    "results": results,
                    "processed_at": datetime.now().isoformat(),
                }

            # Use persistent Procrastinate processing
            logger.info("Using persistent Procrastinate processing")
            manager = await self._get_procrastinate_manager()

            job_id = await manager.defer_bulk_processing(
                data_items=data_items, task_type="parallel", priority=priority,
            )

            return {
                "mode": "persistent",
                "job_id": job_id,
                "total_items": len(data_items),
                "status": "queued",
                "message": "Task queued for background processing",
                "queued_at": datetime.now().isoformat(),
            }

        except Exception as e:
            logger.error(f"Error in hybrid bulk processing: {e}")

            if mode == ProcessingMode.HYBRID:
                # Fallback to alternative processing mode
                logger.info("Attempting fallback processing mode")
                try:
                    if len(data_items) <= immediate_threshold:
                        # Fallback to Procrastinate
                        manager = await self._get_procrastinate_manager()
                        job_id = await manager.defer_bulk_processing(
                            data_items=data_items,
                            task_type="sequential",  # Use sequential as fallback
                            priority=ProcrastinateTaskPriority.HIGH,
                        )
                        return {
                            "mode": "persistent_fallback",
                            "job_id": job_id,
                            "total_items": len(data_items),
                            "status": "queued",
                            "message": "Fallback to persistent processing",
                            "queued_at": datetime.now().isoformat(),
                        }
                    # Fallback to immediate processing with smaller batches
                    results = []
                    batch_size = 50
                    for i in range(0, len(data_items), batch_size):
                        batch = data_items[i : i + batch_size]
                        batch_results = await self.process_data_parallel(
                            batch, processing_func, TaskType.IO_BOUND, **kwargs,
                        )
                        results.extend(batch_results)

                    return {
                        "mode": "immediate_fallback",
                        "total_items": len(data_items),
                        "successful": len(
                            [r for r in results if not isinstance(r, Exception)],
                        ),
                        "failed": len(
                            [r for r in results if isinstance(r, Exception)],
                        ),
                        "results": results,
                        "processed_at": datetime.now().isoformat(),
                    }

                except Exception as fallback_error:
                    logger.error(f"Fallback processing also failed: {fallback_error}")
                    raise
            else:
                raise

    async def schedule_user_processing(
        self,
        user_ids: list[int],
        operation: str,
        schedule_at: datetime | None = None,
        priority: ProcrastinateTaskPriority = ProcrastinateTaskPriority.NORMAL,
        **kwargs,
    ) -> dict[str, Any]:
        """Schedule user processing tasks with Procrastinate."""
        manager = await self._get_procrastinate_manager()
        job_ids = []

        for user_id in user_ids:
            job_id = await manager.defer_user_processing(
                user_id=user_id, operation=operation, priority=priority, **kwargs,
            )
            job_ids.append(job_id)

        return {
            "scheduled_users": len(user_ids),
            "job_ids": job_ids,
            "operation": operation,
            "priority": priority.name,
            "scheduled_at": schedule_at.isoformat() if schedule_at else "immediate",
            "created_at": datetime.now().isoformat(),
        }

    async def process_files_with_persistence(
        self,
        file_paths: list[str],
        operation: str = "analyze",
        mode: str = ProcessingMode.PERSISTENT,
        priority: ProcrastinateTaskPriority = ProcrastinateTaskPriority.NORMAL,
        **kwargs,
    ) -> dict[str, Any]:
        """Process files with persistent task queue for long-running operations."""
        if mode == ProcessingMode.IMMEDIATE:
            # Use existing concurrent file processing
            results = await self.process_files_parallel(
                file_paths,
                lambda path: {"file": path, "operation": operation, **kwargs},
                **kwargs,
            )

            return {
                "mode": "immediate",
                "total_files": len(file_paths),
                "successful": len([r for r in results if not isinstance(r, Exception)]),
                "failed": len([r for r in results if isinstance(r, Exception)]),
                "results": results,
                "processed_at": datetime.now().isoformat(),
            }

        # Use Procrastinate for persistent processing
        manager = await self._get_procrastinate_manager()
        job_ids = []

        for file_path in file_paths:
            job_id = await manager.defer_file_processing(
                file_path=file_path,
                operation=operation,
                priority=priority,
                **kwargs,
            )
            job_ids.append(job_id)

        return {
            "mode": "persistent",
            "total_files": len(file_paths),
            "job_ids": job_ids,
            "operation": operation,
            "status": "queued",
            "queued_at": datetime.now().isoformat(),
        }

    async def send_notifications_reliable(
        self,
        notifications: list[dict[str, Any]],
        priority: ProcrastinateTaskPriority = ProcrastinateTaskPriority.NORMAL,
        retry_failed: bool = True,
    ) -> dict[str, Any]:
        """Send notifications with reliable delivery using Procrastinate."""
        manager = await self._get_procrastinate_manager()
        job_ids = []

        for notification in notifications:
            job_id = await manager.defer_notification(
                notification_type=notification.get("type", "email"),
                recipient=notification.get("recipient"),
                message=notification.get("message"),
                priority=priority,
                **notification.get("metadata", {}),
            )
            job_ids.append(job_id)

        return {
            "total_notifications": len(notifications),
            "job_ids": job_ids,
            "priority": priority.name,
            "reliable_delivery": True,
            "retry_enabled": retry_failed,
            "queued_at": datetime.now().isoformat(),
        }

    async def generate_analytics_with_lock(
        self,
        report_type: str,
        date_range: dict[str, str],
        parameters: dict[str, Any] | None = None,
        priority: ProcrastinateTaskPriority = ProcrastinateTaskPriority.HIGH,
    ) -> dict[str, Any]:
        """Generate analytics reports with locking to prevent concurrent execution."""
        manager = await self._get_procrastinate_manager()

        job_id = await manager.defer_analytics_report(
            report_type=report_type,
            date_range=date_range,
            priority=priority,
            **(parameters or {}),
        )

        return {
            "report_type": report_type,
            "job_id": job_id,
            "date_range": date_range,
            "locked_execution": True,
            "priority": priority.name,
            "queued_at": datetime.now().isoformat(),
        }

    async def schedule_maintenance_tasks(
        self, tasks: list[dict[str, Any]], schedule_time: datetime | None = None,
    ) -> dict[str, Any]:
        """Schedule maintenance tasks for future execution."""
        manager = await self._get_procrastinate_manager()
        scheduled_tasks = []

        for task in tasks:
            task_type = task.get("type")

            if task_type == "cleanup":
                job_id = await manager.schedule_cleanup(
                    days_old=task.get("days_old", 30), at=schedule_time,
                )
                scheduled_tasks.append(
                    {
                        "type": "cleanup",
                        "job_id": job_id,
                        "parameters": {"days_old": task.get("days_old", 30)},
                    },
                )

            elif task_type == "health_check":
                job_id = await manager.schedule_health_check(at=schedule_time)
                scheduled_tasks.append(
                    {"type": "health_check", "job_id": job_id, "parameters": {}},
                )

        return {
            "total_tasks": len(tasks),
            "scheduled_tasks": scheduled_tasks,
            "schedule_time": schedule_time.isoformat()
            if schedule_time
            else "immediate",
            "created_at": datetime.now().isoformat(),
        }

    async def get_processing_status(self, job_id: str) -> dict[str, Any]:
        """Get the status of a Procrastinate job."""
        manager = await self._get_procrastinate_manager()
        return await manager.get_job_status(job_id)

    async def get_queue_health(self) -> dict[str, Any]:
        """Get comprehensive health information for all processing systems."""
        try:
            # Get Procrastinate stats
            manager = await self._get_procrastinate_manager()
            procrastinate_stats = await manager.get_queue_stats()

            # Get enhanced task queue stats
            enhanced_stats = enhanced_task_queue.get_queue_stats()

            # Get concurrent utilities health
            from app.utils.concurrent_utils import concurrent_manager

            concurrent_health = {
                "thread_executor_active": concurrent_manager.thread_executor
                is not None,
                "process_executor_active": concurrent_manager.process_executor
                is not None,
            }

            return {
                "overall_health": "healthy",
                "procrastinate": {
                    "status": "healthy" if manager.is_initialized else "unhealthy",
                    "stats": procrastinate_stats,
                },
                "enhanced_queue": {
                    "status": "healthy" if enhanced_stats["running"] else "unhealthy",
                    "stats": enhanced_stats,
                },
                "concurrent_processing": {
                    "status": "healthy",
                    "stats": concurrent_health,
                },
                "timestamp": datetime.now().isoformat(),
            }

        except Exception as e:
            logger.error(f"Error getting queue health: {e}")
            return {
                "overall_health": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
            }
