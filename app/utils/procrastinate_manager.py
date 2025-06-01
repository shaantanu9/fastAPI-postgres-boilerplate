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
from datetime import datetime, timedelta
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
            "processed_at": datetime.now().isoformat(),
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
            # Use existing concurrent utilities for parallel processing
            async def process_item(item: Dict[str, Any]) -> Dict[str, Any]:
                # Simulate item processing
                await asyncio.sleep(0.1)
                return {
                    "item_id": item.get("id", "unknown"),
                    "processed": True,
                    "processed_at": datetime.now().isoformat()
                }
            
            # Execute in parallel using existing concurrent utilities
            results = await execute_parallel(
                process_item, 
                data_items, 
                TaskType.IO_BOUND, 
                max_workers=10
            )
            
            successful = [r for r in results if not isinstance(r, Exception)]
            failed = [r for r in results if isinstance(r, Exception)]
            
            return {
                "total_items": len(data_items),
                "successful": len(successful),
                "failed": len(failed),
                "results": successful[:10],  # Return first 10 for brevity
                "processed_at": datetime.now().isoformat()
            }
        
        else:
            # Sequential processing
            results = []
            for item in data_items:
                await asyncio.sleep(0.1)  # Simulated processing
                results.append({
                    "item_id": item.get("id", "unknown"),
                    "processed": True,
                    "processed_at": datetime.now().isoformat()
                })
            
            return {
                "total_items": len(data_items),
                "successful": len(results),
                "failed": 0,
                "results": results[:10],
                "processed_at": datetime.now().isoformat()
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
            "sent_at": datetime.now().isoformat(),
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
            "processed_at": datetime.now().isoformat(),
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
            "generated_at": datetime.now().isoformat(),
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
async def cleanup_old_data(days_old: int = 30) -> Dict[str, Any]:
    """Cleanup old data periodically"""
    logger.info(f"Starting cleanup of data older than {days_old} days")
    
    try:
        # Simulate cleanup operation
        await asyncio.sleep(3)
        
        result = {
            "cleanup_type": "old_data",
            "days_old": days_old,
            "records_cleaned": 150,
            "cleaned_at": datetime.now().isoformat(),
            "status": "completed"
        }
        
        logger.info(f"Cleanup completed: {result['records_cleaned']} records")
        return result
        
    except Exception as e:
        logger.error(f"Error during cleanup: {e}")
        raise


@procrastinate_app.task(queue="health_checks", retry=1)
async def system_health_check() -> Dict[str, Any]:
    """Perform system health checks"""
    logger.info("Performing system health check")
    
    try:
        # Simulate health check operations
        await asyncio.sleep(1)
        
        result = {
            "check_type": "system_health",
            "database_status": "healthy",
            "memory_usage": "75%",
            "cpu_usage": "45%",
            "disk_space": "80%",
            "checked_at": datetime.now().isoformat(),
            "status": "healthy"
        }
        
        logger.info("System health check completed")
        return result
        
    except Exception as e:
        logger.error(f"Error during health check: {e}")
        raise


class ProcrastinateManager:
    """
    Manager class for Procrastinate operations
    Provides high-level interface for task management
    """
    
    def __init__(self):
        self.app = procrastinate_app
        self.is_initialized = False
    
    def _initialize_sync(self):
        """Synchronous initialization for use during startup"""
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
        """Async initialization for use in async contexts"""
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
                                  priority: ProcrastinateTaskPriority = ProcrastinateTaskPriority.NORMAL,
                                  **kwargs) -> str:
        """Defer user processing task"""
        job = await process_user_data.defer_async(
            user_id=user_id,
            operation=operation,
            **kwargs,
            priority=priority.value
        )
        logger.info(f"Deferred user processing task: {job.id}")
        return str(job.id)
    
    async def defer_bulk_processing(self, data_items: List[Dict[str, Any]], 
                                  task_type: str = "parallel",
                                  priority: ProcrastinateTaskPriority = ProcrastinateTaskPriority.NORMAL) -> str:
        """Defer bulk data processing task"""
        job = await process_bulk_data.defer_async(
            data_items=data_items,
            task_type=task_type,
            priority=priority.value
        )
        logger.info(f"Deferred bulk processing task: {job.id}")
        return str(job.id)
    
    async def defer_notification(self, notification_type: str, recipient: str, 
                               message: str, 
                               priority: ProcrastinateTaskPriority = ProcrastinateTaskPriority.NORMAL,
                               **kwargs) -> str:
        """Defer notification task"""
        job = await send_notification.defer_async(
            notification_type=notification_type,
            recipient=recipient,
            message=message,
            priority=priority.value,
            **kwargs
        )
        logger.info(f"Deferred notification task: {job.id}")
        return str(job.id)
    
    async def defer_file_processing(self, file_path: str, operation: str = "analyze",
                                  priority: ProcrastinateTaskPriority = ProcrastinateTaskPriority.NORMAL,
                                  **kwargs) -> str:
        """Defer file processing task"""
        job = await process_file.defer_async(
            file_path=file_path,
            operation=operation,
            priority=priority.value,
            **kwargs
        )
        logger.info(f"Deferred file processing task: {job.id}")
        return str(job.id)
    
    async def defer_analytics_report(self, report_type: str, date_range: Dict[str, str],
                                   priority: ProcrastinateTaskPriority = ProcrastinateTaskPriority.HIGH,
                                   **kwargs) -> str:
        """Defer analytics report generation (locked task)"""
        job = await generate_analytics_report.defer_async(
            report_type=report_type,
            date_range=date_range,
            priority=priority.value,
            **kwargs
        )
        logger.info(f"Deferred analytics report task: {job.id}")
        return str(job.id)
    
    async def schedule_cleanup(self, days_old: int = 30, 
                              at: datetime = None) -> str:
        """Schedule cleanup task for specific time"""
        if at is None:
            at = datetime.now() + timedelta(hours=1)  # Default to 1 hour from now
            
        job = await cleanup_old_data.defer_async(
            days_old=days_old,
            schedule_at=at
        )
        logger.info(f"Scheduled cleanup task: {job.id} for {at}")
        return str(job.id)
    
    async def schedule_health_check(self, at: datetime = None) -> str:
        """Schedule health check task"""
        if at is None:
            at = datetime.now() + timedelta(minutes=5)  # Default to 5 minutes from now
            
        job = await system_health_check.defer_async(schedule_at=at)
        logger.info(f"Scheduled health check task: {job.id} for {at}")
        return str(job.id)
    
    async def get_job_status(self, job_id: str) -> Dict[str, Any]:
        """Get job status and result"""
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
        """Get queue statistics"""
        try:
            # This would require custom SQL queries to the Procrastinate tables
            return {
                "total_jobs": "unknown",
                "pending_jobs": "unknown",
                "failed_jobs": "unknown",
                "message": "Queue statistics require custom implementation"
            }
        except Exception as e:
            logger.error(f"Error getting queue stats: {e}")
            return {"error": str(e)}


# Global manager instance
procrastinate_manager = ProcrastinateManager()


def get_procrastinate_app():
    """Get the procrastinate app instance"""
    return procrastinate_app


def register_plugin_blueprint(blueprint, namespace: str = None):
    """Register a plugin's Procrastinate blueprint with the main app"""
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
    """Initialize Procrastinate for the application startup"""
    procrastinate_manager._initialize_sync()


async def get_procrastinate_manager() -> ProcrastinateManager:
    """Dependency injection for Procrastinate manager"""
    if not procrastinate_manager.is_initialized:
        await procrastinate_manager.initialize()
    return procrastinate_manager 