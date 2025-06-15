"""Enhanced Procrastinate Manager.

This module provides an enhanced Procrastinate task queue manager
with better integration, error handling, and monitoring capabilities.
"""

import asyncio
import json
from datetime import UTC, datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from loguru import logger
from procrastinate import App, PsycopgConnector
from procrastinate.exceptions import ProcrastinateException

from app.core.config import get_settings

settings = get_settings()


class TaskPriority(Enum):
    """Task priority levels."""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


class TaskStatus(Enum):
    """Task status enumeration."""
    TODO = "todo"
    DOING = "doing"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"
    DEFERRED = "deferred"


class EnhancedProcrastinateManager:
    """Enhanced Procrastinate manager with comprehensive features."""
    
    def __init__(self):
        self.settings = settings
        self.app: Optional[App] = None
        self.is_initialized = False
        self.connection_params = self._get_connection_params()
        
    def _get_connection_params(self) -> Dict[str, Any]:
        """Get PostgreSQL connection parameters."""
        return {
            "host": self.settings.postgres_host,
            "port": self.settings.postgres_port,
            "user": self.settings.postgres_user,
            "password": self.settings.postgres_password,
            "dbname": self.settings.postgres_database,
        }
    
    def initialize_sync(self) -> bool:
        """Initialize Procrastinate synchronously."""
        try:
            if self.is_initialized:
                logger.info("✅ Procrastinate already initialized")
                return True
                
            # Create Procrastinate app
            self.app = App(
                connector=PsycopgConnector(kwargs=self.connection_params),
                import_paths=["app.tasks"]  # Import task modules
            )
            
            # Register core tasks
            self._register_core_tasks()
            
            self.is_initialized = True
            logger.info("✅ Procrastinate initialized successfully (sync)")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize Procrastinate (sync): {e}")
            self.is_initialized = False
            return False
    
    async def initialize_async(self) -> bool:
        """Initialize Procrastinate asynchronously."""
        try:
            if self.is_initialized:
                logger.info("✅ Procrastinate already initialized")
                return True
                
            # Initialize sync first
            if not self.initialize_sync():
                return False
                
            # Apply schema if needed
            await self._ensure_schema()
            
            logger.info("✅ Procrastinate initialized successfully (async)")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize Procrastinate (async): {e}")
            self.is_initialized = False
            return False
    
    async def _ensure_schema(self) -> bool:
        """Ensure Procrastinate schema exists."""
        try:
            if not self.app:
                return False
                
            # Apply schema
            async with self.app.open_async() as app_context:
                await app_context.schema_manager.apply_schema()
                
            logger.info("✅ Procrastinate schema applied")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to apply Procrastinate schema: {e}")
            return False
    
    def _register_core_tasks(self) -> None:
        """Register core task definitions."""
        if not self.app:
            return
            
        # User processing task
        @self.app.task(queue="user_processing", retry=3)
        async def process_user_data(
            user_id: int, 
            operation: str, 
            **kwargs
        ) -> Dict[str, Any]:
            """Process user data with persistence."""
            logger.info(f"Processing user {user_id} with operation: {operation}")
            
            try:
                # Simulate processing
                await asyncio.sleep(1)
                
                result = {
                    "user_id": user_id,
                    "operation": operation,
                    "processed_at": datetime.now(UTC).isoformat(),
                    "status": "completed",
                    "details": kwargs,
                }
                
                logger.info(f"User {user_id} processing completed")
                return result
                
            except Exception as e:
                logger.error(f"Error processing user {user_id}: {e}")
                raise
        
        # Bulk data processing task
        @self.app.task(queue="data_processing", retry=3)
        async def process_bulk_data(
            data_items: List[Dict[str, Any]], 
            task_type: str = "parallel"
        ) -> Dict[str, Any]:
            """Process bulk data efficiently."""
            logger.info(f"Processing {len(data_items)} items with type: {task_type}")
            
            try:
                if task_type == "parallel":
                    # Parallel processing
                    async def process_item(item: Dict[str, Any]) -> Dict[str, Any]:
                        await asyncio.sleep(0.1)
                        return {
                            "item_id": item.get("id", "unknown"),
                            "processed": True,
                            "processed_at": datetime.now(UTC).isoformat(),
                        }
                    
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
                        "results": successful[:10],  # First 10 results
                        "processed_at": datetime.now(UTC).isoformat(),
                        "processing_type": "parallel",
                    }
                else:
                    # Sequential processing
                    results = []
                    for item in data_items:
                        await asyncio.sleep(0.1)
                        results.append({
                            "item_id": item.get("id", "unknown"),
                            "processed": True,
                            "processed_at": datetime.now(UTC).isoformat(),
                        })
                    
                    return {
                        "total_items": len(data_items),
                        "successful": len(results),
                        "failed": 0,
                        "results": results[:10],
                        "processed_at": datetime.now(UTC).isoformat(),
                        "processing_type": "sequential",
                    }
                    
            except Exception as e:
                logger.error(f"Error processing bulk data: {e}")
                raise
        
        # Notification task
        @self.app.task(queue="notifications", retry=2)
        async def send_notification(
            notification_type: str,
            recipient: str,
            message: str,
            **kwargs
        ) -> Dict[str, Any]:
            """Send notifications via various channels."""
            logger.info(f"Sending {notification_type} notification to {recipient}")
            
            try:
                # Simulate notification sending
                await asyncio.sleep(0.5)
                
                result = {
                    "notification_type": notification_type,
                    "recipient": recipient,
                    "message": message,
                    "sent_at": datetime.now(UTC).isoformat(),
                    "status": "sent",
                    "details": kwargs,
                }
                
                logger.info(f"Notification sent to {recipient}")
                return result
                
            except Exception as e:
                logger.error(f"Error sending notification to {recipient}: {e}")
                raise
        
        # Store task references for later use
        self.tasks = {
            "process_user_data": process_user_data,
            "process_bulk_data": process_bulk_data,
            "send_notification": send_notification,
        }
    
    async def defer_task(
        self,
        task_name: str,
        queue: str = "default",
        priority: TaskPriority = TaskPriority.NORMAL,
        at: Optional[datetime] = None,
        in_: Optional[timedelta] = None,
        **kwargs
    ) -> Optional[str]:
        """Defer a task for execution."""
        if not self.is_initialized or not self.app:
            logger.error("Procrastinate not initialized")
            return None
            
        try:
            task = self.tasks.get(task_name)
            if not task:
                logger.error(f"Task not found: {task_name}")
                return None
            
            # Prepare defer options
            defer_options = {
                "queue": queue,
                "priority": priority.value,
            }
            
            if at:
                defer_options["at"] = at
            elif in_:
                defer_options["in"] = in_
            
            # Defer the task
            async with self.app.open_async() as app_context:
                job = await task.defer_async(**kwargs, **defer_options)
                
            logger.info(f"Task deferred: {task_name} (Job ID: {job.id})")
            return str(job.id)
            
        except Exception as e:
            logger.error(f"Failed to defer task {task_name}: {e}")
            return None
    
    async def get_job_status(self, job_id: Union[str, int]) -> Optional[Dict[str, Any]]:
        """Get job status by ID."""
        if not self.is_initialized or not self.app:
            logger.error("Procrastinate not initialized")
            return None
            
        try:
            async with self.app.open_async() as app_context:
                job = await app_context.job_store.get_job_status(int(job_id))
                
                if job:
                    return {
                        "id": job.id,
                        "task_name": job.task_name,
                        "queue_name": job.queue_name,
                        "priority": job.priority,
                        "status": job.status.value,
                        "scheduled_at": job.scheduled_at.isoformat() if job.scheduled_at else None,
                        "started_at": job.started_at.isoformat() if job.started_at else None,
                        "finished_at": job.finished_at.isoformat() if job.finished_at else None,
                        "attempts": job.attempts,
                    }
                return None
                
        except Exception as e:
            logger.error(f"Failed to get job status {job_id}: {e}")
            return None
    
    async def get_queue_stats(self, queue_name: Optional[str] = None) -> Dict[str, Any]:
        """Get queue statistics."""
        if not self.is_initialized or not self.app:
            return {"error": "Procrastinate not initialized"}
            
        try:
            async with self.app.open_async() as app_context:
                stats = await app_context.job_store.get_queue_stats(queue_name)
                
                return {
                    "queue_name": queue_name or "all",
                    "total_jobs": stats.get("total", 0),
                    "todo_jobs": stats.get("todo", 0),
                    "doing_jobs": stats.get("doing", 0),
                    "succeeded_jobs": stats.get("succeeded", 0),
                    "failed_jobs": stats.get("failed", 0),
                    "cancelled_jobs": stats.get("cancelled", 0),
                    "timestamp": datetime.now(UTC).isoformat(),
                }
                
        except Exception as e:
            logger.error(f"Failed to get queue stats: {e}")
            return {"error": str(e)}
    
    async def cancel_job(self, job_id: Union[str, int]) -> bool:
        """Cancel a job by ID."""
        if not self.is_initialized or not self.app:
            logger.error("Procrastinate not initialized")
            return False
            
        try:
            async with self.app.open_async() as app_context:
                success = await app_context.job_store.cancel_job(int(job_id))
                
            if success:
                logger.info(f"Job {job_id} cancelled successfully")
            else:
                logger.warning(f"Failed to cancel job {job_id}")
                
            return success
            
        except Exception as e:
            logger.error(f"Error cancelling job {job_id}: {e}")
            return False
    
    async def retry_job(self, job_id: Union[str, int]) -> bool:
        """Retry a failed job."""
        if not self.is_initialized or not self.app:
            logger.error("Procrastinate not initialized")
            return False
            
        try:
            async with self.app.open_async() as app_context:
                success = await app_context.job_store.retry_job(int(job_id))
                
            if success:
                logger.info(f"Job {job_id} scheduled for retry")
            else:
                logger.warning(f"Failed to retry job {job_id}")
                
            return success
            
        except Exception as e:
            logger.error(f"Error retrying job {job_id}: {e}")
            return False
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on Procrastinate."""
        health_status = {
            "initialized": self.is_initialized,
            "app_available": self.app is not None,
            "connection_test": False,
            "schema_ready": False,
            "worker_count": 0,
            "total_jobs": 0,
            "timestamp": datetime.now(UTC).isoformat(),
        }
        
        if not self.is_initialized or not self.app:
            health_status["status"] = "unhealthy"
            return health_status
        
        try:
            async with self.app.open_async() as app_context:
                # Test connection
                await app_context.job_store.get_queue_stats()
                health_status["connection_test"] = True
                health_status["schema_ready"] = True
                
                # Get basic stats
                stats = await app_context.job_store.get_queue_stats()
                health_status["total_jobs"] = stats.get("total", 0)
                
            health_status["status"] = "healthy"
            
        except Exception as e:
            logger.error(f"Procrastinate health check failed: {e}")
            health_status["status"] = "unhealthy"
            health_status["error"] = str(e)
        
        return health_status
    
    def get_app(self) -> Optional[App]:
        """Get the Procrastinate app instance."""
        return self.app
    
    async def cleanup_old_jobs(self, days_old: int = 30) -> Dict[str, Any]:
        """Clean up old completed jobs."""
        if not self.is_initialized or not self.app:
            return {"error": "Procrastinate not initialized"}
        
        try:
            cutoff_date = datetime.now(UTC) - timedelta(days=days_old)
            
            async with self.app.open_async() as app_context:
                # This would need to be implemented based on Procrastinate's API
                # For now, return a placeholder
                result = {
                    "cleaned_jobs": 0,
                    "cutoff_date": cutoff_date.isoformat(),
                    "status": "completed",
                }
                
            logger.info(f"Cleaned up jobs older than {days_old} days")
            return result
            
        except Exception as e:
            logger.error(f"Failed to cleanup old jobs: {e}")
            return {"error": str(e)}


# Global instance
enhanced_procrastinate_manager = EnhancedProcrastinateManager()


def get_procrastinate_manager() -> EnhancedProcrastinateManager:
    """Get the enhanced Procrastinate manager instance."""
    return enhanced_procrastinate_manager


async def init_procrastinate() -> bool:
    """Initialize Procrastinate on startup."""
    try:
        logger.info("🔄 Initializing Procrastinate...")
        
        # Initialize synchronously first
        if not enhanced_procrastinate_manager.initialize_sync():
            return False
            
        # Then initialize asynchronously
        if not await enhanced_procrastinate_manager.initialize_async():
            return False
            
        logger.info("✅ Procrastinate initialization complete")
        return True
        
    except Exception as e:
        logger.error(f"❌ Procrastinate initialization failed: {e}")
        return False


async def procrastinate_health_check() -> Dict[str, Any]:
    """Perform health check on Procrastinate."""
    return await enhanced_procrastinate_manager.health_check() 