"""
Procrastinate Integration Manager

This module provides a PostgreSQL-based task queue using Procrastinate that complements
the existing concurrent.futures implementation. It handles:
- Persistent task storage in PostgreSQL
- Distributed task processing across multiple workers
- Task scheduling, priorities, and retries
- Integration with the existing FastAPI architecture

Features:
- Async/await support
- Job persistence and durability
- Distributed processing
- Scheduled and periodic tasks
- Task monitoring and management
- Integration with existing concurrent processing
"""

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Callable, Union
from enum import Enum

import procrastinate
from procrastinate import App, PsycopgConnector
from loguru import logger

from app.core.config import get_settings
from app.utils.concurrent_utils import TaskType, execute_parallel

settings = get_settings()

# Procrastinate app instance
procrastinate_app = App(
    connector=PsycopgConnector(
        kwargs={
            "host": settings.postgres_host,
            "port": settings.postgres_port,
            "user": settings.postgres_user,
            "password": settings.postgres_password,
            "dbname": settings.postgres_database,
        }
    )
)


class ProcrastinateTaskPriority(Enum):
    """Task priority levels for Procrastinate"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


class ProcrastinateTaskType(Enum):
    """Task types for different processing requirements"""
    IMMEDIATE = "immediate"      # Execute immediately
    SCHEDULED = "scheduled"      # Execute at specific time
    PERIODIC = "periodic"        # Execute on schedule
    BACKGROUND = "background"    # Execute in background
    BULK = "bulk"               # Bulk processing tasks


# Task definitions for different use cases
@procrastinate_app.task(queue="user_processing", retry=3)
async def process_user_data(user_id: int, operation: str, **kwargs) -> Dict[str, Any]:
    """Process user data with persistence and retry capabilities"""
    logger.info(f"Processing user {user_id} with operation: {operation}")
    
    try:
        # Simulate user processing - replace with actual logic
        await asyncio.sleep(1)  # Simulated processing time
        
        result = {
            "user_id": user_id,
            "operation": operation,
            "processed_at": datetime.now(timezone.utc).isoformat(),
            "status": "completed",
            "details": kwargs
        }
        
        logger.info(f"User {user_id} processing completed")
        return result
        
    except Exception as e:
        logger.error(f"Error processing user {user_id}: {e}")
        raise


@procrastinate_app.task(queue="data_processing", retry=3)
async def process_bulk_data(data_items: List[Dict[str, Any]], 
                           task_type: str = "parallel") -> Dict[str, Any]:
    """Process bulk data using concurrent processing"""
    logger.info(f"Processing {len(data_items)} items with type: {task_type}")
    
    try:
        if task_type == "parallel":
            # Use asyncio.gather for parallel processing instead of concurrent utilities
            async def process_item(item: Dict[str, Any]) -> Dict[str, Any]:
                # Simulate item processing
                await asyncio.sleep(0.1)
                return {
                    "item_id": item.get("id", "unknown"),
                    "processed": True,
                    "processed_at": datetime.now(timezone.utc).isoformat()
                }
            
            # Execute in parallel using asyncio.gather
            try:
                results = await asyncio.gather(
                    *[process_item(item) for item in data_items],
                    return_exceptions=True
                )
                
                successful = [r for r in results if not isinstance(r, Exception)]
                failed = [r for r in results if isinstance(r, Exception)]
                
                return {
                    "total_items": len(data_items),
                    "successful": len(successful),
                    "failed": len(failed),
                    "results": successful[:10],  # Return first 10 for brevity
                    "processed_at": datetime.now(timezone.utc).isoformat(),
                    "processing_type": "parallel_asyncio"
                }
            except Exception as e:
                logger.error(f"Error in parallel processing: {e}")
                # Fall back to sequential processing
                results = []
                for item in data_items:
                    try:
                        result = await process_item(item)
                        results.append(result)
                    except Exception as item_error:
                        logger.error(f"Error processing item {item}: {item_error}")
                        results.append({"error": str(item_error), "item": item})
                
                return {
                    "total_items": len(data_items),
                    "successful": len([r for r in results if "error" not in r]),
                    "failed": len([r for r in results if "error" in r]),
                    "results": results[:10],
                    "processed_at": datetime.now(timezone.utc).isoformat(),
                    "processing_type": "sequential_fallback"
                }
        else:
            # Sequential processing
            results = []
            for item in data_items:
                await asyncio.sleep(0.1)  # Simulated processing
                results.append({
                    "item_id": item.get("id", "unknown"),
                    "processed": True,
                    "processed_at": datetime.now(timezone.utc).isoformat()
                })
            
            return {
                "total_items": len(data_items),
                "successful": len(results),
                "failed": 0,
                "results": results[:10],
                "processed_at": datetime.now(timezone.utc).isoformat(),
                "processing_type": "sequential"
            }
    
    except Exception as e:
        logger.error(f"Error processing bulk data: {e}")
        raise


@procrastinate_app.task(queue="notifications", retry=2)
async def send_notification(notification_type: str, 
                          recipient: str, 
                          message: str, 
                          **kwargs) -> Dict[str, Any]:
    """Send notifications via various channels"""
    logger.info(f"Sending {notification_type} notification to {recipient}")
    
    try:
        # Simulate notification sending
        await asyncio.sleep(0.5)
        
        result = {
            "notification_type": notification_type,
            "recipient": recipient,
            "message": message,
            "sent_at": datetime.now(timezone.utc).isoformat(),
            "status": "sent",
            "details": kwargs
        }
        
        logger.info(f"Notification sent to {recipient}")
        return result
        
    except Exception as e:
        logger.error(f"Error sending notification to {recipient}: {e}")
        raise


@procrastinate_app.task(queue="file_processing", retry=2)
async def process_file(file_path: str, 
                      operation: str = "analyze", 
                      **kwargs) -> Dict[str, Any]:
    """Process files with different operations"""
    logger.info(f"Processing file: {file_path} with operation: {operation}")
    
    try:
        # Simulate file processing
        await asyncio.sleep(2)
        
        result = {
            "file_path": file_path,
            "operation": operation,
            "file_size": kwargs.get("file_size", "unknown"),
            "processed_at": datetime.now(timezone.utc).isoformat(),
            "status": "completed",
            "details": kwargs
        }
        
        logger.info(f"File processing completed: {file_path}")
        return result
        
    except Exception as e:
        logger.error(f"Error processing file {file_path}: {e}")
        raise


@procrastinate_app.task(queue="analytics", retry=2, lock="analytics_lock")
async def generate_analytics_report(report_type: str, 
                                  date_range: Dict[str, str],
                                  **kwargs) -> Dict[str, Any]:
    """Generate analytics reports (locked to prevent concurrent execution)"""
    logger.info(f"Generating {report_type} analytics report")
    
    try:
        # Simulate report generation
        await asyncio.sleep(5)
        
        result = {
            "report_type": report_type,
            "date_range": date_range,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "status": "completed",
            "metrics": {
                "users_processed": 1250,
                "data_points": 15000,
                "processing_time": "5.2s"
            },
            "details": kwargs
        }
        
        logger.info(f"Analytics report generated: {report_type}")
        return result
        
    except Exception as e:
        logger.error(f"Error generating analytics report: {e}")
        raise


# Periodic tasks for scheduled operations
@procrastinate_app.task(queue="maintenance", retry=1)
async def cleanup_old_data(days_old: int = 30, scheduled_for: str = None) -> Dict[str, Any]:
    """Cleanup old data periodically"""
    logger.info(f"Starting cleanup of data older than {days_old} days")
    if scheduled_for:
        logger.info(f"Originally scheduled for: {scheduled_for}")
    
    try:
        # Simulate cleanup operation
        await asyncio.sleep(3)
        
        result = {
            "cleanup_type": "old_data",
            "days_old": days_old,
            "records_cleaned": 150,
            "cleaned_at": datetime.now(timezone.utc).isoformat(),
            "originally_scheduled_for": scheduled_for,
            "status": "completed"
        }
        
        logger.info(f"Cleanup completed: {result['records_cleaned']} records")
        return result
        
    except Exception as e:
        logger.error(f"Error during cleanup: {e}")
        raise


@procrastinate_app.task(queue="health_checks", retry=1)
async def system_health_check(scheduled_for: str = None) -> Dict[str, Any]:
    """Perform system health checks"""
    logger.info("Performing system health check")
    if scheduled_for:
        logger.info(f"Originally scheduled for: {scheduled_for}")
    
    try:
        # Simulate health check operations
        await asyncio.sleep(1)
        
        result = {
            "check_type": "system_health",
            "database_status": "healthy",
            "memory_usage": "75%",
            "cpu_usage": "45%",
            "disk_space": "80%",
            "checked_at": datetime.now(timezone.utc).isoformat(),
            "originally_scheduled_for": scheduled_for,
            "status": "healthy"
        }
        
        logger.info("System health check completed")
        return result
        
    except Exception as e:
        logger.error(f"Error during health check: {e}")
        raise


class ProcrastinateManager:
    """
    Manager class for Procrastinate operations.

    Provides a high-level interface for managing, deferring, and scheduling background tasks
    using the Procrastinate library. Handles initialization, deferral of various task types,
    and provides status and statistics utilities for task management.
    """
    
    def __init__(self):
        """
        Initialize the ProcrastinateManager instance.
        Sets up the procrastinate app and initialization state.
        """
        self.app = procrastinate_app
        self.is_initialized = False
    
    def _initialize_sync(self):
        """
        Synchronous initialization for use during startup.
        Applies the Procrastinate schema synchronously to avoid event loop conflicts.
        """
        try:
            # Use sync version to avoid event loop conflicts during startup
            with self.app.open():
                self.app.schema_manager.apply_schema()
            
            self.is_initialized = True
            logger.info("Procrastinate manager initialized successfully (sync)")
            
        except Exception as e:
            logger.error(f"Failed to initialize Procrastinate: {e}")
            # Don't raise during startup - allow app to start even if Procrastinate fails
            logger.warning("Procrastinate initialization failed, tasks will be disabled")
    
    async def initialize(self):
        """
        Asynchronous initialization for use in async contexts.
        Applies the Procrastinate schema asynchronously if not already initialized.
        """
        if self.is_initialized:
            return
            
        try:
            # Try async initialization for async contexts
            async with self.app.open_async():
                await self.app.schema_manager.apply_schema()
            
            self.is_initialized = True
            logger.info("Procrastinate manager initialized successfully (async)")
            
        except Exception as e:
            logger.error(f"Failed to initialize Procrastinate async: {e}")
            # Fallback to sync initialization
            try:
                self._initialize_sync()
            except Exception as sync_error:
                logger.error(f"Sync fallback also failed: {sync_error}")
                raise
    
    async def defer_user_processing(self, user_id: int, operation: str, 
                                  **kwargs) -> str:
        """
        Defer a user processing task to the background queue.

        Args:
            user_id (int): ID of the user to process.
            operation (str): Operation to perform on the user.
            **kwargs: Additional arguments for the task.

        Returns:
            str: Job ID of the deferred task.
        """
        if not self.is_initialized:
            await self.initialize()
        
        async with self.app.open_async():
            job_id = await process_user_data.defer_async(
                user_id=user_id,
                operation=operation,
                **kwargs
            )
            logger.info(f"Deferred user processing task: {job_id}")
            return str(job_id)
    
    async def defer_bulk_processing(self, data_items: List[Dict[str, Any]], 
                                  task_type: str = "parallel") -> str:
        """
        Defer a bulk data processing task.

        Args:
            data_items (List[Dict[str, Any]]): List of data items to process.
            task_type (str, optional): Type of processing ("parallel" or "sequential").

        Returns:
            str: Job ID of the deferred task.
        """
        if not self.is_initialized:
            await self.initialize()
        
        async with self.app.open_async():
            job_id = await process_bulk_data.defer_async(
                data_items=data_items,
                task_type=task_type
            )
            logger.info(f"Deferred bulk processing task: {job_id}")
            return str(job_id)
    
    async def defer_notification(self, notification_type: str, recipient: str, 
                               message: str, 
                               **kwargs) -> str:
        """
        Defer a notification task.

        Args:
            notification_type (str): Type of notification to send.
            recipient (str): Recipient of the notification.
            message (str): Message content.
            **kwargs: Additional arguments for the task.

        Returns:
            str: Job ID of the deferred task.
        """
        if not self.is_initialized:
            await self.initialize()
        
        async with self.app.open_async():
            job_id = await send_notification.defer_async(
                notification_type=notification_type,
                recipient=recipient,
                message=message,
                **kwargs
            )
            logger.info(f"Deferred notification task: {job_id}")
            return str(job_id)
    
    async def defer_file_processing(self, file_path: str, operation: str = "analyze",
                                  **kwargs) -> str:
        """
        Defer a file processing task.

        Args:
            file_path (str): Path to the file to process.
            operation (str, optional): Operation to perform on the file.
            **kwargs: Additional arguments for the task.

        Returns:
            str: Job ID of the deferred task.
        """
        if not self.is_initialized:
            await self.initialize()
        
        async with self.app.open_async():
            job_id = await process_file.defer_async(
                file_path=file_path,
                operation=operation,
                **kwargs
            )
            logger.info(f"Deferred file processing task: {job_id}")
            return str(job_id)
    
    async def defer_analytics_report(self, report_type: str, date_range: Dict[str, str],
                                   **kwargs) -> str:
        """
        Defer an analytics report generation task (locked to prevent concurrent execution).

        Args:
            report_type (str): Type of analytics report to generate.
            date_range (Dict[str, str]): Date range for the report.
            **kwargs: Additional arguments for the task.

        Returns:
            str: Job ID of the deferred task.
        """
        if not self.is_initialized:
            await self.initialize()
        
        async with self.app.open_async():
            job_id = await generate_analytics_report.defer_async(
                report_type=report_type,
                date_range=date_range,
                **kwargs
            )
            logger.info(f"Deferred analytics report task: {job_id}")
            return str(job_id)
    
    async def schedule_cleanup(self, days_old: int = 30, 
                              at: datetime = None) -> str:
        """
        Schedule a cleanup task to run at a specific time.

        Args:
            days_old (int, optional): Age threshold for data cleanup.
            at (datetime, optional): When to schedule the cleanup.

        Returns:
            str: Job ID of the scheduled cleanup task.
        """
        if not self.is_initialized:
            await self.initialize()
        
        if at is None:
            at = datetime.now(timezone.utc) + timedelta(hours=1)  # Default to 1 hour from now
            
        async with self.app.open_async():
            # Use Procrastinate's schedule_in parameter with dict format for timedelta
            # Ensure both datetimes are timezone-aware for proper calculation
            now = datetime.now(timezone.utc)
            if at.tzinfo is None:
                # If at is naive, assume it's UTC
                at = at.replace(tzinfo=timezone.utc)
            
            delay_seconds = int((at - now).total_seconds())
            if delay_seconds < 0:
                delay_seconds = 0  # Execute immediately if scheduled in the past
                
            job_id = await cleanup_old_data.configure(schedule_in={"seconds": delay_seconds}).defer_async(
                days_old=days_old,
                scheduled_for=at.isoformat()  # Keep as metadata
            )
            logger.info(f"Scheduled cleanup task: {job_id} for {at}")
            return str(job_id)
    
    async def schedule_health_check(self, at: datetime = None) -> str:
        """
        Schedule a system health check task.

        Args:
            at (datetime, optional): When to schedule the health check.

        Returns:
            str: Job ID of the scheduled health check task.
        """
        if not self.is_initialized:
            await self.initialize()
        
        if at is None:
            at = datetime.now(timezone.utc) + timedelta(minutes=5)  # Default to 5 minutes from now
            
        async with self.app.open_async():
            # Use Procrastinate's schedule_in parameter with dict format for timedelta
            # Ensure both datetimes are timezone-aware for proper calculation
            now = datetime.now(timezone.utc)
            if at.tzinfo is None:
                # If at is naive, assume it's UTC
                at = at.replace(tzinfo=timezone.utc)
            
            delay_seconds = int((at - now).total_seconds())
            if delay_seconds < 0:
                delay_seconds = 0  # Execute immediately if scheduled in the past
                
            job_id = await system_health_check.configure(schedule_in={"seconds": delay_seconds}).defer_async(
                scheduled_for=at.isoformat()  # Keep as metadata
            )
            logger.info(f"Scheduled health check task: {job_id} for {at}")
            return str(job_id)
    
    async def get_job_status(self, job_id: str) -> Dict[str, Any]:
        """
        Get the status and result of a background job.

        Args:
            job_id (str): The job ID to query.

        Returns:
            Dict[str, Any]: Status and result information for the job.
        """
        if not self.is_initialized:
            await self.initialize()
        
        try:
            async with self.app.open_async():
                # Note: Procrastinate doesn't have built-in job status checking
                # You would need to implement this using the database directly
                return {
                    "job_id": job_id,
                    "status": "unknown",
                    "message": "Job status checking requires custom implementation"
                }
        except Exception as e:
            logger.error(f"Error getting job status: {e}")
            return {
                "job_id": job_id,
                "status": "error",
                "error": str(e)
            }
    
    async def get_queue_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the Procrastinate task queue.

        Returns:
            Dict[str, Any]: Dictionary with queue statistics.
        """
        if not self.is_initialized:
            await self.initialize()
        
        try:
            from app.db.session import get_db
            from sqlalchemy import text
            
            async for session in get_db():
                # Get overall statistics
                stats_query = text("""
                    SELECT 
                        COUNT(*) as total_jobs,
                        SUM(CASE WHEN status = 'todo' THEN 1 ELSE 0 END) as pending_jobs,
                        SUM(CASE WHEN status = 'doing' THEN 1 ELSE 0 END) as running_jobs,
                        SUM(CASE WHEN status = 'succeeded' THEN 1 ELSE 0 END) as succeeded_jobs,
                        SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed_jobs,
                        SUM(CASE WHEN status = 'cancelled' THEN 1 ELSE 0 END) as cancelled_jobs
                    FROM procrastinate_jobs
                """)
                
                stats_result = await session.execute(stats_query)
                stats_row = stats_result.first()
                
                # Get statistics by queue
                queue_stats_query = text("""
                    SELECT 
                        queue_name,
                        COUNT(*) as total_jobs,
                        SUM(CASE WHEN status = 'todo' THEN 1 ELSE 0 END) as pending_jobs,
                        SUM(CASE WHEN status = 'doing' THEN 1 ELSE 0 END) as running_jobs,
                        SUM(CASE WHEN status = 'succeeded' THEN 1 ELSE 0 END) as succeeded_jobs,
                        SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed_jobs,
                        SUM(CASE WHEN status = 'cancelled' THEN 1 ELSE 0 END) as cancelled_jobs
                    FROM procrastinate_jobs 
                    GROUP BY queue_name
                    ORDER BY queue_name
                """)
                
                queue_result = await session.execute(queue_stats_query)
                queue_stats = {}
                
                for row in queue_result:
                    queue_stats[row.queue_name] = {
                        "total_jobs": row.total_jobs,
                        "pending_jobs": row.pending_jobs,
                        "running_jobs": row.running_jobs,
                        "succeeded_jobs": row.succeeded_jobs,
                        "failed_jobs": row.failed_jobs,
                        "cancelled_jobs": row.cancelled_jobs
                    }
                
                # Get recent activity (last 24 hours)
                recent_activity_query = text("""
                    SELECT 
                        COUNT(*) as jobs_last_24h,
                        SUM(CASE WHEN status = 'succeeded' THEN 1 ELSE 0 END) as succeeded_last_24h,
                        SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed_last_24h
                    FROM procrastinate_jobs 
                    WHERE scheduled_at >= NOW() - INTERVAL '24 hours'
                """)
                
                recent_result = await session.execute(recent_activity_query)
                recent_row = recent_result.first()
                
                return {
                    "overall": {
                        "total_jobs": stats_row.total_jobs,
                        "pending_jobs": stats_row.pending_jobs,
                        "running_jobs": stats_row.running_jobs,
                        "succeeded_jobs": stats_row.succeeded_jobs,
                        "failed_jobs": stats_row.failed_jobs,
                        "cancelled_jobs": stats_row.cancelled_jobs
                    },
                    "by_queue": queue_stats,
                    "recent_activity": {
                        "jobs_last_24h": recent_row.jobs_last_24h,
                        "succeeded_last_24h": recent_row.succeeded_last_24h,
                        "failed_last_24h": recent_row.failed_last_24h
                    },
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                
        except Exception as e:
            logger.error(f"Error getting queue stats: {e}")
            return {"error": str(e)}

    async def purge_queue(self, queue_name: str, status_filter: Optional[str] = None) -> Dict[str, Any]:
        """
        Purge all jobs from a specific queue
        
        Args:
            queue_name: Name of the queue to purge
            status_filter: Optional status filter
            
        Returns:
            Dict with purge results
        """
        if not self.is_initialized:
            await self.initialize()
            
        try:
            from app.db.session import get_db
            from sqlalchemy import text
            
            async for session in get_db():
                # Build the delete query
                if status_filter:
                    query = text(
                        "DELETE FROM procrastinate_jobs WHERE queue_name = :queue_name AND status = :status"
                    )
                    result = await session.execute(query, {"queue_name": queue_name, "status": status_filter})
                else:
                    query = text(
                        "DELETE FROM procrastinate_jobs WHERE queue_name = :queue_name"
                    )
                    result = await session.execute(query, {"queue_name": queue_name})
                
                await session.commit()
                deleted_count = result.rowcount
                
                logger.info(f"Purged {deleted_count} jobs from queue {queue_name}")
                return {
                    "queue_name": queue_name,
                    "deleted_count": deleted_count,
                    "status_filter": status_filter,
                    "message": f"Successfully purged {deleted_count} jobs"
                }
                
        except Exception as e:
            logger.error(f"Error purging queue {queue_name}: {e}")
            return {"error": str(e), "queue_name": queue_name}
    
    async def retry_failed_jobs(self, queue_name: str, limit: int = 100) -> Dict[str, Any]:
        """
        Retry all failed jobs in a specific queue
        
        Args:
            queue_name: Name of the queue
            limit: Maximum number of jobs to retry
            
        Returns:
            Dict with retry results
        """
        if not self.is_initialized:
            await self.initialize()
            
        try:
            from app.db.session import get_db
            from sqlalchemy import text
            
            async for session in get_db():
                # Update failed jobs to todo status
                query = text("""
                    UPDATE procrastinate_jobs 
                    SET status = 'todo', attempts = 0, abort_requested = false
                    WHERE queue_name = :queue_name 
                    AND status = 'failed' 
                    AND id IN (
                        SELECT id FROM procrastinate_jobs 
                        WHERE queue_name = :queue_name AND status = 'failed' 
                        ORDER BY id DESC LIMIT :limit
                    )
                """)
                
                result = await session.execute(query, {
                    "queue_name": queue_name, 
                    "limit": limit
                })
                await session.commit()
                
                retried_count = result.rowcount
                logger.info(f"Retried {retried_count} failed jobs in queue {queue_name}")
                
                return {
                    "queue_name": queue_name,
                    "retried_count": retried_count,
                    "limit": limit,
                    "message": f"Successfully retried {retried_count} failed jobs"
                }
                
        except Exception as e:
            logger.error(f"Error retrying failed jobs in queue {queue_name}: {e}")
            return {"error": str(e), "queue_name": queue_name}
    
    async def cancel_job(self, job_id: str) -> Dict[str, Any]:
        """
        Cancel a specific job
        
        Args:
            job_id: ID of the job to cancel
            
        Returns:
            Dict with cancellation results
        """
        if not self.is_initialized:
            await self.initialize()
            
        try:
            from app.db.session import get_db
            from sqlalchemy import text
            
            async for session in get_db():
                # Update job status to cancelled
                query = text("""
                    UPDATE procrastinate_jobs 
                    SET status = 'cancelled', abort_requested = true
                    WHERE id = :job_id 
                    AND status IN ('todo', 'doing')
                """)
                
                result = await session.execute(query, {"job_id": int(job_id)})
                await session.commit()
                
                if result.rowcount > 0:
                    logger.info(f"Cancelled job {job_id}")
                    return {
                        "job_id": job_id,
                        "status": "cancelled",
                        "message": f"Successfully cancelled job {job_id}"
                    }
                else:
                    return {
                        "job_id": job_id,
                        "status": "not_found_or_completed",
                        "message": f"Job {job_id} not found or already completed"
                    }
                
        except Exception as e:
            logger.error(f"Error cancelling job {job_id}: {e}")
            return {"error": str(e), "job_id": job_id}
    
    async def search_jobs(self, queue_name: Optional[str] = None, status: Optional[str] = None,
                         task_name: Optional[str] = None, from_date: Optional[datetime] = None,
                         to_date: Optional[datetime] = None, limit: int = 50, 
                         offset: int = 0) -> Dict[str, Any]:
        """
        Search jobs with comprehensive filtering
        
        Returns:
            Dict with search results
        """
        if not self.is_initialized:
            await self.initialize()
            
        try:
            from app.db.session import get_db
            from sqlalchemy import text
            
            async for session in get_db():
                # Build dynamic query
                conditions = []
                params = {"limit": limit, "offset": offset}
                
                if queue_name:
                    conditions.append("queue_name = :queue_name")
                    params["queue_name"] = queue_name
                    
                if status:
                    conditions.append("status = :status")
                    params["status"] = status
                    
                if task_name:
                    conditions.append("task_name ILIKE :task_name")
                    params["task_name"] = f"%{task_name}%"
                    
                if from_date:
                    conditions.append("scheduled_at >= :from_date")
                    params["from_date"] = from_date
                    
                if to_date:
                    conditions.append("scheduled_at <= :to_date")
                    params["to_date"] = to_date
                
                where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""
                
                query = text(f"""
                    SELECT id, queue_name, task_name, status, priority, 
                           scheduled_at, attempts, args
                    FROM procrastinate_jobs 
                    {where_clause}
                    ORDER BY id DESC 
                    LIMIT :limit OFFSET :offset
                """)
                
                result = await session.execute(query, params)
                jobs = []
                
                for row in result:
                    jobs.append({
                        "id": row.id,
                        "queue_name": row.queue_name,
                        "task_name": row.task_name,
                        "status": row.status,
                        "priority": row.priority,
                        "scheduled_at": row.scheduled_at.isoformat() if row.scheduled_at else None,
                        "attempts": row.attempts,
                        "args": row.args
                    })
                
                # Get total count
                count_query = text(f"""
                    SELECT COUNT(*) FROM procrastinate_jobs {where_clause}
                """)
                count_result = await session.execute(count_query, {k: v for k, v in params.items() 
                                                                  if k not in ['limit', 'offset']})
                total_count = count_result.scalar()
                
                return {
                    "jobs": jobs,
                    "total_count": total_count,
                    "limit": limit,
                    "offset": offset,
                    "filters": {
                        "queue_name": queue_name,
                        "status": status,
                        "task_name": task_name,
                        "from_date": from_date.isoformat() if from_date else None,
                        "to_date": to_date.isoformat() if to_date else None
                    }
                }
                
        except Exception as e:
            logger.error(f"Error searching jobs: {e}")
            return {"error": str(e)}
    
    async def get_job_details(self, job_id: str) -> Dict[str, Any]:
        """
        Get comprehensive details about a specific job
        
        Args:
            job_id: ID of the job
            
        Returns:
            Dict with job details including events
        """
        if not self.is_initialized:
            await self.initialize()
            
        try:
            from app.db.session import get_db
            from sqlalchemy import text
            
            async for session in get_db():
                # Get job details
                job_query = text("""
                    SELECT id, queue_name, task_name, status, priority, lock, queueing_lock,
                           args, scheduled_at, attempts, abort_requested, worker_id
                    FROM procrastinate_jobs 
                    WHERE id = :job_id
                """)
                
                job_result = await session.execute(job_query, {"job_id": int(job_id)})
                job_row = job_result.first()
                
                if not job_row:
                    return {"error": f"Job {job_id} not found"}
                
                # Get job events
                events_query = text("""
                    SELECT id, type, at 
                    FROM procrastinate_events 
                    WHERE job_id = :job_id 
                    ORDER BY at DESC
                """)
                
                events_result = await session.execute(events_query, {"job_id": int(job_id)})
                events = []
                
                for event_row in events_result:
                    events.append({
                        "id": event_row.id,
                        "type": event_row.type,
                        "at": event_row.at.isoformat() if event_row.at else None
                    })
                
                return {
                    "job": {
                        "id": job_row.id,
                        "queue_name": job_row.queue_name,
                        "task_name": job_row.task_name,
                        "status": job_row.status,
                        "priority": job_row.priority,
                        "lock": job_row.lock,
                        "queueing_lock": job_row.queueing_lock,
                        "args": job_row.args,
                        "scheduled_at": job_row.scheduled_at.isoformat() if job_row.scheduled_at else None,
                        "attempts": job_row.attempts,
                        "abort_requested": job_row.abort_requested,
                        "worker_id": job_row.worker_id
                    },
                    "events": events,
                    "events_count": len(events)
                }
                
        except Exception as e:
            logger.error(f"Error getting job details for {job_id}: {e}")
            return {"error": str(e), "job_id": job_id}
    
    async def get_registered_tasks(self) -> Dict[str, Any]:
        """
        Get all registered Procrastinate tasks
        
        Returns:
            Dict with registered tasks information
        """
        try:
            tasks = {}
            
            for task_name, task in self.app.tasks.items():
                tasks[task_name] = {
                    "name": task_name,
                    "queue": getattr(task, 'queue', 'default'),
                    "retry": getattr(task, 'retry', 0),
                    "pass_context": getattr(task, 'pass_context', False),
                    "lock": getattr(task, 'lock', None)
                }
            
            return {
                "registered_tasks": tasks,
                "total_tasks": len(tasks),
                "queues": list(set(task["queue"] for task in tasks.values()))
            }
            
        except Exception as e:
            logger.error(f"Error getting registered tasks: {e}")
            return {"error": str(e)}
    
    async def get_worker_status(self) -> Dict[str, Any]:
        """
        Get status of all active Procrastinate workers
        
        Returns:
            Dict with worker status information
        """
        if not self.is_initialized:
            await self.initialize()
            
        try:
            from app.db.session import get_db
            from sqlalchemy import text
            
            async for session in get_db():
                # Get active workers (only id and last_heartbeat are available)
                workers_query = text("""
                    SELECT id, last_heartbeat
                    FROM procrastinate_workers 
                    WHERE last_heartbeat > NOW() - INTERVAL '1 minute'
                    ORDER BY id DESC
                """)
                
                workers_result = await session.execute(workers_query)
                workers = []
                
                for worker_row in workers_result:
                    workers.append({
                        "id": worker_row.id,
                        "last_heartbeat": worker_row.last_heartbeat.isoformat() if worker_row.last_heartbeat else None,
                        "status": "active" if worker_row.last_heartbeat and 
                                          (datetime.now(timezone.utc) - worker_row.last_heartbeat.replace(tzinfo=timezone.utc)).total_seconds() < 60 
                                          else "inactive"
                    })
                
                # Get jobs being processed by workers
                active_jobs_query = text("""
                    SELECT worker_id, COUNT(*) as job_count
                    FROM procrastinate_jobs 
                    WHERE status = 'doing' AND worker_id IS NOT NULL
                    GROUP BY worker_id
                """)
                
                active_jobs_result = await session.execute(active_jobs_query)
                worker_job_counts = {row.worker_id: row.job_count for row in active_jobs_result}
                
                # Add job counts to workers
                for worker in workers:
                    worker["active_jobs"] = worker_job_counts.get(worker["id"], 0)
                
                return {
                    "active_workers": workers,
                    "total_workers": len(workers),
                    "total_active_jobs": sum(worker_job_counts.values()),
                    "note": "Worker table only contains id and last_heartbeat columns"
                }
                
        except Exception as e:
            logger.error(f"Error getting worker status: {e}")
            return {"error": str(e)}
    
    async def cleanup_old_jobs(self, days_old: int = 30, status_filter: Optional[str] = None) -> Dict[str, Any]:
        """
        Clean up old jobs to free database space
        
        Args:
            days_old: Jobs older than this many days will be cleaned
            status_filter: Optional status filter
            
        Returns:
            Dict with cleanup results
        """
        if not self.is_initialized:
            await self.initialize()
            
        try:
            from app.db.session import get_db
            from sqlalchemy import text
            
            async for session in get_db():
                # Build the cleanup query
                if status_filter:
                    query = text("""
                        DELETE FROM procrastinate_jobs 
                        WHERE scheduled_at < NOW() - INTERVAL ':days days'
                        AND status = :status
                    """)
                    result = await session.execute(query, {"days": days_old, "status": status_filter})
                else:
                    query = text("""
                        DELETE FROM procrastinate_jobs 
                        WHERE scheduled_at < NOW() - INTERVAL ':days days'
                        AND status IN ('succeeded', 'failed', 'cancelled')
                    """)
                    result = await session.execute(query, {"days": days_old})
                
                await session.commit()
                cleaned_count = result.rowcount
                
                logger.info(f"Cleaned up {cleaned_count} old jobs (older than {days_old} days)")
                
                return {
                    "cleaned_count": cleaned_count,
                    "days_old": days_old,
                    "status_filter": status_filter,
                    "message": f"Successfully cleaned up {cleaned_count} old jobs"
                }
                
        except Exception as e:
            logger.error(f"Error cleaning up old jobs: {e}")
            return {"error": str(e)}


# Global manager instance
procrastinate_manager = ProcrastinateManager()


def get_procrastinate_app() -> App:
    """
    Get the global procrastinate app instance.

    Returns:
        App: The Procrastinate app instance.
    """
    return procrastinate_app


def register_plugin_blueprint(blueprint, namespace: str = None):
    """
    Register a plugin's Procrastinate blueprint with the main app.

    Args:
        blueprint: The Procrastinate blueprint to register.
        namespace (str, optional): Optional namespace for the blueprint.
    """
    try:
        if namespace:
            procrastinate_app.add_tasks_from(blueprint, namespace=namespace)
            logger.info(f"Registered plugin blueprint with namespace: {namespace}")
        else:
            procrastinate_app.add_tasks_from(blueprint)
            logger.info("Registered plugin blueprint without namespace")
    except Exception as e:
        logger.warning(f"Failed to register plugin blueprint: {e}")


def init_procrastinate():
    """
    Initialize Procrastinate for the application startup.
    This is a placeholder for any startup initialization logic needed.
    """
    procrastinate_manager._initialize_sync()


async def get_procrastinate_manager() -> ProcrastinateManager:
    """
    Dependency injection for the global Procrastinate manager instance.

    Returns:
        ProcrastinateManager: The global manager instance.
    """
    if not procrastinate_manager.is_initialized:
        await procrastinate_manager.initialize()
    return procrastinate_manager