"""
Procrastinate Task Management API Endpoints

This module provides REST API endpoints for managing persistent, distributed tasks
using Procrastinate. These endpoints complement the existing bulk operations and
concurrent processing with PostgreSQL-backed persistence and distributed execution.

Features:
- Task scheduling and queuing
- Job status monitoring
- Bulk task operations with persistence
- Scheduled and periodic task management
- Integration with existing concurrent processing
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, status
from pydantic import BaseModel, Field
from loguru import logger

from app.utils.procrastinate_manager import (
    get_procrastinate_manager, 
    ProcrastinateManager,
    ProcrastinateTaskPriority,
    ProcrastinateTaskType
)
from app.db.session import get_db

router = APIRouter()

# Request/Response Models
class TaskRequest(BaseModel):
    """Base task request model"""
    priority: str = Field(default="normal", description="Task priority: low, normal, high, critical")
    
    def get_priority(self) -> ProcrastinateTaskPriority:
        priority_map = {
            "low": ProcrastinateTaskPriority.LOW,
            "normal": ProcrastinateTaskPriority.NORMAL,
            "high": ProcrastinateTaskPriority.HIGH,
            "critical": ProcrastinateTaskPriority.CRITICAL
        }
        return priority_map.get(self.priority.lower(), ProcrastinateTaskPriority.NORMAL)


class UserProcessingRequest(TaskRequest):
    """User processing task request"""
    user_id: int = Field(..., description="User ID to process")
    operation: str = Field(..., description="Operation to perform")
    additional_data: Dict[str, Any] = Field(default_factory=dict, description="Additional operation data")


class BulkProcessingRequest(TaskRequest):
    """Bulk processing task request"""
    data_items: List[Dict[str, Any]] = Field(..., description="List of items to process")
    task_type: str = Field(default="parallel", description="Processing type: parallel or sequential")
    batch_size: Optional[int] = Field(default=100, description="Batch size for processing")


class NotificationRequest(TaskRequest):
    """Notification task request"""
    notification_type: str = Field(..., description="Type of notification: email, sms, push")
    recipient: str = Field(..., description="Recipient identifier")
    message: str = Field(..., description="Notification message")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional notification metadata")


class FileProcessingRequest(TaskRequest):
    """File processing task request"""
    file_path: str = Field(..., description="Path to file to process")
    operation: str = Field(default="analyze", description="Operation to perform on file")
    file_size: Optional[int] = Field(default=None, description="File size in bytes")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional file metadata")


class AnalyticsReportRequest(TaskRequest):
    """Analytics report generation request"""
    report_type: str = Field(..., description="Type of report to generate")
    date_range: Dict[str, str] = Field(..., description="Date range for report")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Report parameters")


class ScheduledTaskRequest(BaseModel):
    """Scheduled task request"""
    task_type: str = Field(..., description="Type of scheduled task")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Task parameters")
    schedule_at: Optional[datetime] = Field(default=None, description="When to execute the task")
    

class TaskResponse(BaseModel):
    """Task response model"""
    job_id: str = Field(..., description="Unique job identifier")
    status: str = Field(..., description="Task status")
    message: str = Field(..., description="Status message")
    created_at: datetime = Field(default_factory=datetime.now, description="Task creation time")


class JobStatusResponse(BaseModel):
    """Job status response model"""
    job_id: str
    status: str
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    created_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


# API Endpoints

@router.post("/user-processing", 
             response_model=TaskResponse,
             status_code=status.HTTP_201_CREATED,
             summary="Process User Data",
             description="Queue a user data processing task with persistence and retry capabilities")
async def create_user_processing_task(
    request: UserProcessingRequest,
    manager: ProcrastinateManager = Depends(get_procrastinate_manager)
) -> TaskResponse:
    """
    Create a persistent user processing task
    
    This endpoint queues a user processing task that will be executed by Procrastinate workers.
    The task is stored in PostgreSQL and provides durability, retries, and distributed execution.
    """
    try:
        job_id = await manager.defer_user_processing(
            user_id=request.user_id,
            operation=request.operation,
            priority=request.get_priority(),
            **request.additional_data
        )
        
        return TaskResponse(
            job_id=job_id,
            status="queued",
            message=f"User processing task created for user {request.user_id}"
        )
        
    except Exception as e:
        logger.error(f"Error creating user processing task: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create user processing task: {str(e)}"
        )


@router.post("/bulk-processing",
             response_model=TaskResponse,
             status_code=status.HTTP_201_CREATED,
             summary="Bulk Data Processing",
             description="Queue a bulk data processing task with concurrent execution")
async def create_bulk_processing_task(
    request: BulkProcessingRequest,
    manager: ProcrastinateManager = Depends(get_procrastinate_manager)
) -> TaskResponse:
    """
    Create a persistent bulk data processing task
    
    This endpoint queues a bulk processing task that combines Procrastinate persistence
    with the existing concurrent.futures parallel processing capabilities.
    """
    try:
        # Validate data items
        if not request.data_items:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="data_items cannot be empty"
            )
        
        if len(request.data_items) > 10000:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Maximum 10,000 items allowed per bulk processing task"
            )
        
        job_id = await manager.defer_bulk_processing(
            data_items=request.data_items,
            task_type=request.task_type,
            priority=request.get_priority()
        )
        
        return TaskResponse(
            job_id=job_id,
            status="queued",
            message=f"Bulk processing task created for {len(request.data_items)} items"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating bulk processing task: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create bulk processing task: {str(e)}"
        )


@router.post("/notifications",
             response_model=TaskResponse,
             status_code=status.HTTP_201_CREATED,
             summary="Send Notification",
             description="Queue a notification task for reliable delivery")
async def create_notification_task(
    request: NotificationRequest,
    manager: ProcrastinateManager = Depends(get_procrastinate_manager)
) -> TaskResponse:
    """
    Create a persistent notification task
    
    This endpoint queues a notification task with retry capabilities for reliable delivery.
    """
    try:
        job_id = await manager.defer_notification(
            notification_type=request.notification_type,
            recipient=request.recipient,
            message=request.message,
            priority=request.get_priority(),
            **request.metadata
        )
        
        return TaskResponse(
            job_id=job_id,
            status="queued",
            message=f"Notification task created for {request.recipient}"
        )
        
    except Exception as e:
        logger.error(f"Error creating notification task: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create notification task: {str(e)}"
        )


@router.post("/file-processing",
             response_model=TaskResponse,
             status_code=status.HTTP_201_CREATED,
             summary="Process File",
             description="Queue a file processing task with configurable operations")
async def create_file_processing_task(
    request: FileProcessingRequest,
    manager: ProcrastinateManager = Depends(get_procrastinate_manager)
) -> TaskResponse:
    """
    Create a persistent file processing task
    
    This endpoint queues a file processing task for various operations like analysis,
    transformation, or validation.
    """
    try:
        job_id = await manager.defer_file_processing(
            file_path=request.file_path,
            operation=request.operation,
            priority=request.get_priority(),
            file_size=request.file_size,
            **request.metadata
        )
        
        return TaskResponse(
            job_id=job_id,
            status="queued",
            message=f"File processing task created for {request.file_path}"
        )
        
    except Exception as e:
        logger.error(f"Error creating file processing task: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create file processing task: {str(e)}"
        )


@router.post("/analytics-reports",
             response_model=TaskResponse,
             status_code=status.HTTP_201_CREATED,
             summary="Generate Analytics Report",
             description="Queue an analytics report generation task (locked to prevent concurrent execution)")
async def create_analytics_report_task(
    request: AnalyticsReportRequest,
    manager: ProcrastinateManager = Depends(get_procrastinate_manager)
) -> TaskResponse:
    """
    Create a persistent analytics report generation task
    
    This endpoint queues an analytics report task with locking to prevent concurrent
    execution of the same report type.
    """
    try:
        job_id = await manager.defer_analytics_report(
            report_type=request.report_type,
            date_range=request.date_range,
            priority=request.get_priority(),
            **request.parameters
        )
        
        return TaskResponse(
            job_id=job_id,
            status="queued",
            message=f"Analytics report task created: {request.report_type}"
        )
        
    except Exception as e:
        logger.error(f"Error creating analytics report task: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create analytics report task: {str(e)}"
        )


@router.post("/scheduled/cleanup",
             response_model=TaskResponse,
             status_code=status.HTTP_201_CREATED,
             summary="Schedule Cleanup Task",
             description="Schedule a data cleanup task for future execution")
async def schedule_cleanup_task(
    request: ScheduledTaskRequest,
    manager: ProcrastinateManager = Depends(get_procrastinate_manager)
) -> TaskResponse:
    """
    Schedule a cleanup task for future execution
    
    This endpoint schedules a cleanup task to run at a specified time or with default timing.
    """
    try:
        days_old = request.parameters.get("days_old", 30)
        
        job_id = await manager.schedule_cleanup(
            days_old=days_old,
            at=request.schedule_at
        )
        
        schedule_time = request.schedule_at or (datetime.now() + timedelta(hours=1))
        
        return TaskResponse(
            job_id=job_id,
            status="scheduled",
            message=f"Cleanup task scheduled for {schedule_time}"
        )
        
    except Exception as e:
        logger.error(f"Error scheduling cleanup task: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to schedule cleanup task: {str(e)}"
        )


@router.post("/scheduled/health-check",
             response_model=TaskResponse,
             status_code=status.HTTP_201_CREATED,
             summary="Schedule Health Check",
             description="Schedule a system health check for future execution")
async def schedule_health_check_task(
    request: ScheduledTaskRequest,
    manager: ProcrastinateManager = Depends(get_procrastinate_manager)
) -> TaskResponse:
    """
    Schedule a health check task for future execution
    """
    try:
        job_id = await manager.schedule_health_check(at=request.schedule_at)
        
        schedule_time = request.schedule_at or (datetime.now() + timedelta(minutes=5))
        
        return TaskResponse(
            job_id=job_id,
            status="scheduled",
            message=f"Health check scheduled for {schedule_time}"
        )
        
    except Exception as e:
        logger.error(f"Error scheduling health check: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to schedule health check: {str(e)}"
        )


@router.get("/jobs/{job_id}/status",
            response_model=JobStatusResponse,
            summary="Get Job Status",
            description="Get the status and result of a specific job")
async def get_job_status(
    job_id: str,
    manager: ProcrastinateManager = Depends(get_procrastinate_manager)
) -> JobStatusResponse:
    """
    Get the status and result of a specific job
    
    Note: This is a basic implementation. For production use, you should implement
    proper job status tracking using Procrastinate's database tables.
    """
    try:
        status_info = await manager.get_job_status(job_id)
        
        return JobStatusResponse(
            job_id=job_id,
            status=status_info.get("status", "unknown"),
            result=status_info.get("result"),
            error=status_info.get("error")
        )
        
    except Exception as e:
        logger.error(f"Error getting job status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get job status: {str(e)}"
        )


@router.get("/queue/stats",
            summary="Get Queue Statistics",
            description="Get statistics about the Procrastinate task queues")
async def get_queue_statistics(
    manager: ProcrastinateManager = Depends(get_procrastinate_manager)
) -> Dict[str, Any]:
    """
    Get statistics about the Procrastinate task queues
    
    Note: This requires custom implementation to query Procrastinate tables.
    """
    try:
        stats = await manager.get_queue_stats()
        return stats
        
    except Exception as e:
        logger.error(f"Error getting queue statistics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get queue statistics: {str(e)}"
        )


@router.get("/health",
            summary="Procrastinate Health Check",
            description="Check the health of the Procrastinate system")
async def procrastinate_health_check(
    manager: ProcrastinateManager = Depends(get_procrastinate_manager)
) -> Dict[str, Any]:
    """
    Health check endpoint for Procrastinate system
    """
    try:
        return {
            "status": "healthy" if manager.is_initialized else "unhealthy",
            "initialized": manager.is_initialized,
            "timestamp": datetime.now().isoformat(),
            "component": "procrastinate"
        }
        
    except Exception as e:
        logger.error(f"Procrastinate health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
            "component": "procrastinate"
        } 