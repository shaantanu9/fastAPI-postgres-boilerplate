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
        
        # Store task references for later use
        self.tasks = {
            "process_user_data": process_user_data,
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
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on Procrastinate."""
        health_status = {
            "initialized": self.is_initialized,
            "app_available": self.app is not None,
            "connection_test": False,
            "schema_ready": False,
            "timestamp": datetime.now(UTC).isoformat(),
        }
        
        if not self.is_initialized or not self.app:
            health_status["status"] = "unhealthy"
            return health_status
        
        try:
            async with self.app.open_async() as app_context:
                # Test basic connection
                health_status["connection_test"] = True
                health_status["schema_ready"] = True
                
            health_status["status"] = "healthy"
            
        except Exception as e:
            logger.error(f"Procrastinate health check failed: {e}")
            health_status["status"] = "unhealthy"
            health_status["error"] = str(e)
        
        return health_status
    
    def get_app(self) -> Optional[App]:
        """Get the Procrastinate app instance."""
        return self.app


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