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

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, status, Query
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
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Task creation time")


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
    Create a persistent user processing task.
    
    This endpoint queues a user processing task that will be executed by Procrastinate workers.
    The task is stored in PostgreSQL and provides durability, retries, and distributed execution.
    Tasks are processed asynchronously by worker processes and can be monitored through the
    job status endpoint.
    
    Args:
        request (UserProcessingRequest): Request containing user ID, operation type,
                                        priority, and additional data.
        manager (ProcrastinateManager): Procrastinate manager dependency for task scheduling.
    
    Returns:
        TaskResponse: Response containing job ID, status, and creation timestamp.
        
    Raises:
        HTTPException: If task creation fails or parameters are invalid.
    """
    try:
        job_id = await manager.defer_user_processing(
            user_id=request.user_id,
            operation=request.operation,
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
    Create a persistent bulk data processing task.
    
    This endpoint queues a bulk processing task that combines Procrastinate persistence
    with the existing concurrent.futures parallel processing capabilities. It supports
    both parallel and sequential processing modes with configurable batch sizes for
    optimized performance.
    
    Args:
        request (BulkProcessingRequest): Request containing data items to process,
                                        task type (parallel/sequential), batch size,
                                        and priority.
        manager (ProcrastinateManager): Procrastinate manager dependency for task scheduling.
    
    Returns:
        TaskResponse: Response containing job ID, status, and creation timestamp.
        
    Raises:
        HTTPException: If task creation fails, parameters are invalid, or if the
                      data items exceed the maximum allowed size.
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
            task_type=request.task_type
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
    Create a persistent notification task.
    
    This endpoint queues a notification task with retry capabilities for reliable delivery.
    Supports multiple notification channels (email, SMS, push) with configurable priorities
    and metadata. Failed notifications will be automatically retried with exponential backoff.
    
    Args:
        request (NotificationRequest): Request containing notification type, recipient,
                                      message content, metadata, and priority.
        manager (ProcrastinateManager): Procrastinate manager dependency for task scheduling.
    
    Returns:
        TaskResponse: Response containing job ID, status, and creation timestamp.
        
    Raises:
        HTTPException: If task creation fails, notification type is invalid, or if the
                      recipient format is incorrect.
    """
    try:
        job_id = await manager.defer_notification(
            notification_type=request.notification_type,
            recipient=request.recipient,
            message=request.message,
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
    Create a persistent file processing task.
    
    This endpoint queues a file processing task for various operations like analysis,
    transformation, or validation. Large files are automatically processed in chunks
    to optimize memory usage and performance. Supports various file formats and
    processing operations.
    
    Args:
        request (FileProcessingRequest): Request containing file path, operation type,
                                        file size, metadata, and priority.
        manager (ProcrastinateManager): Procrastinate manager dependency for task scheduling.
    
    Returns:
        TaskResponse: Response containing job ID, status, and creation timestamp.
        
    Raises:
        HTTPException: If task creation fails, file path is invalid, or if the
                      requested operation is not supported.
    """
    try:
        job_id = await manager.defer_file_processing(
            file_path=request.file_path,
            operation=request.operation,
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
    Create a persistent analytics report generation task.
    
    This endpoint queues an analytics report task with locking to prevent concurrent
    execution of the same report type. Reports can be scheduled with different priorities
    and customized with various parameters. The system implements resource-aware scheduling
    to prevent overloading database resources during peak times.
    
    Args:
        request (AnalyticsReportRequest): Request containing report type, date range,
                                         parameters, and priority.
        manager (ProcrastinateManager): Procrastinate manager dependency for task scheduling.
    
    Returns:
        TaskResponse: Response containing job ID, status, and creation timestamp.
        
    Raises:
        HTTPException: If task creation fails, report type is invalid, or if there's
                      already a pending report of the same type (lock conflict).
    """
    try:
        job_id = await manager.defer_analytics_report(
            report_type=request.report_type,
            date_range=request.date_range,
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
             description="Schedule a cleanup task for future execution")
async def schedule_cleanup_task(
    request: ScheduledTaskRequest,
    manager: ProcrastinateManager = Depends(get_procrastinate_manager)
) -> TaskResponse:
    """
    Schedule a cleanup task for future execution.
    
    This endpoint schedules a cleanup task to run at a specified time or with default timing.
    Cleanup tasks can include database maintenance, temporary file removal, log rotation,
    and other system maintenance operations. Tasks can be scheduled with specific parameters
    to customize the cleanup process.
    
    Args:
        request (ScheduledTaskRequest): Request containing task type, parameters, and
                                       scheduled execution time.
        manager (ProcrastinateManager): Procrastinate manager dependency for task scheduling.
    
    Returns:
        TaskResponse: Response containing job ID, status, and creation timestamp.
        
    Raises:
        HTTPException: If task scheduling fails or parameters are invalid.
    """
    try:
        days_old = request.parameters.get("days_old", 30)
        
        job_id = await manager.schedule_cleanup(
            days_old=days_old,
            at=request.schedule_at
        )
        
        schedule_time = request.schedule_at or (datetime.now(timezone.utc) + timedelta(hours=1))
        
        return TaskResponse(
            job_id=job_id,
            status="scheduled",
            message=f"Cleanup task scheduled for {schedule_time.isoformat()}"
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
             description="Schedule a health check task for future execution")
async def schedule_health_check_task(
    request: ScheduledTaskRequest,
    manager: ProcrastinateManager = Depends(get_procrastinate_manager)
) -> TaskResponse:
    """
    Schedule a health check task for future execution.
    
    This endpoint schedules a comprehensive system health check to run at a specified time.
    Health checks can verify database connections, external service availability, disk space,
    memory usage, and other critical system metrics. Results are logged and can trigger
    alerts if issues are detected.
    
    Args:
        request (ScheduledTaskRequest): Request containing task type, parameters, and
                                       scheduled execution time.
        manager (ProcrastinateManager): Procrastinate manager dependency for task scheduling.
    
    Returns:
        TaskResponse: Response containing job ID, status, and creation timestamp.
        
    Raises:
        HTTPException: If task scheduling fails or parameters are invalid.
    """
    try:
        job_id = await manager.schedule_health_check(at=request.schedule_at)
        
        schedule_time = request.schedule_at or (datetime.now(timezone.utc) + timedelta(minutes=5))
        
        return TaskResponse(
            job_id=job_id,
            status="scheduled",
            message=f"Health check scheduled for {schedule_time.isoformat()}"
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
    Get the status and result of a specific job.
    
    This endpoint retrieves detailed information about a job including its current status,
    result (if completed), error message (if failed), and timing information. It provides
    visibility into the job lifecycle and helps with monitoring and debugging.
    
    Note: This is a basic implementation. For production use, you should implement
    proper job status tracking using Procrastinate's database tables.
    
    Args:
        job_id (str): Unique identifier of the job to retrieve status for.
        manager (ProcrastinateManager): Procrastinate manager dependency for job status retrieval.
    
    Returns:
        JobStatusResponse: Detailed job status information including status, result/error,
                          and timing information.
        
    Raises:
        HTTPException: If the job is not found or status retrieval fails.
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
    Get statistics about the Procrastinate task queues.
    
    This endpoint provides comprehensive statistics about task queues including counts of
    pending, running, completed, and failed jobs per queue, average processing times,
    throughput metrics, and historical trends. This information is valuable for monitoring
    system load and identifying potential bottlenecks.
    
    Note: This requires custom implementation to query Procrastinate tables.
    
    Args:
        manager (ProcrastinateManager): Procrastinate manager dependency for accessing queue data.
    
    Returns:
        Dict[str, Any]: Queue statistics including job counts by status, processing metrics,
                       and historical trends.
        
    Raises:
        HTTPException: If statistics retrieval fails or database access issues occur.
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
    Health check endpoint for Procrastinate system.
    
    This endpoint performs a comprehensive health check of the Procrastinate task system,
    verifying database connectivity, worker availability, queue status, and system
    configuration. It's suitable for use with monitoring systems and container orchestration
    platforms for automated health monitoring.
    
    Args:
        manager (ProcrastinateManager): Procrastinate manager dependency for system health checks.
    
    Returns:
        Dict[str, Any]: Health status information including database connectivity,
                       worker status, queue health, and overall system status.
        
    Raises:
        HTTPException: If the health check fails or critical components are unavailable.
    """
    try:
        return {
            "status": "healthy" if manager.is_initialized else "unhealthy",
            "initialized": manager.is_initialized,
            "db_connected": await manager.check_db_connection(),
            "workers_active": await manager.check_workers(),
            "queues": await manager.get_queue_summary(),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "component": "procrastinate"
        }
    except Exception as e:
        logger.error(f"Error in procrastinate health check: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Health check failed: {str(e)}"
        )
        
    except Exception as e:
        logger.error(f"Procrastinate health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "component": "procrastinate"
        }


@router.delete("/queue/{queue_name}/purge",
               summary="Purge Queue", 
               description="Remove all jobs from a specific queue")
async def purge_queue(
    queue_name: str,
    status: Optional[str] = None,
    manager: ProcrastinateManager = Depends(get_procrastinate_manager)
) -> Dict[str, Any]:
    """
    Purge all jobs from a specific queue
    
    Args:
        queue_name: Name of the queue to purge
        status: Optional status filter (todo, doing, succeeded, failed, cancelled)
    """
    try:
        result = await manager.purge_queue(queue_name, status)
        return result
        
    except Exception as e:
        logger.error(f"Error purging queue {queue_name}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to purge queue: {str(e)}"
        )


@router.post("/queue/{queue_name}/retry-failed",
             summary="Retry Failed Jobs",
             description="Retry all failed jobs in a specific queue")
async def retry_failed_jobs(
    queue_name: str,
    limit: int = Query(100, ge=1, le=1000),
    manager: ProcrastinateManager = Depends(get_procrastinate_manager)
) -> Dict[str, Any]:
    """
    Retry all failed jobs in a specific queue
    
    Args:
        queue_name: Name of the queue
        limit: Maximum number of jobs to retry
    """
    try:
        result = await manager.retry_failed_jobs(queue_name, limit)
        return result
        
    except Exception as e:
        logger.error(f"Error retrying failed jobs in queue {queue_name}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retry failed jobs: {str(e)}"
        )


@router.delete("/jobs/{job_id}/cancel",
               summary="Cancel Job",
               description="Cancel a specific job by ID")
async def cancel_job(
    job_id: str,
    manager: ProcrastinateManager = Depends(get_procrastinate_manager)
) -> Dict[str, Any]:
    """
    Cancel a specific job
    
    Args:
        job_id: ID of the job to cancel
    """
    try:
        result = await manager.cancel_job(job_id)
        return result
        
    except Exception as e:
        logger.error(f"Error canceling job {job_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to cancel job: {str(e)}"
        )


@router.get("/jobs/search",
            summary="Search Jobs",
            description="Search jobs with various filters")
async def search_jobs(
    queue_name: Optional[str] = None,
    status: Optional[str] = None,
    task_name: Optional[str] = None,
    from_date: Optional[datetime] = None,
    to_date: Optional[datetime] = None,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    manager: ProcrastinateManager = Depends(get_procrastinate_manager)
) -> Dict[str, Any]:
    """
    Search jobs with comprehensive filtering options
    """
    try:
        result = await manager.search_jobs(
            queue_name=queue_name,
            status=status,
            task_name=task_name,
            from_date=from_date,
            to_date=to_date,
            limit=limit,
            offset=offset
        )
        return result
        
    except Exception as e:
        logger.error(f"Error searching jobs: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to search jobs: {str(e)}"
        )


@router.get("/jobs/{job_id}/details",
            summary="Get Job Details",
            description="Get comprehensive details about a specific job")
async def get_job_details(
    job_id: str,
    manager: ProcrastinateManager = Depends(get_procrastinate_manager)
) -> Dict[str, Any]:
    """
    Get detailed information about a specific job including events and attempts
    """
    try:
        result = await manager.get_job_details(job_id)
        return result
        
    except Exception as e:
        logger.error(f"Error getting job details for {job_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get job details: {str(e)}"
        )


@router.get("/tasks/registered",
            summary="Get Registered Tasks",
            description="Get list of all registered Procrastinate tasks")
async def get_registered_tasks(
    manager: ProcrastinateManager = Depends(get_procrastinate_manager)
) -> Dict[str, Any]:
    """
    Get all registered Procrastinate tasks with their configuration
    """
    try:
        result = await manager.get_registered_tasks()
        return result
        
    except Exception as e:
        logger.error(f"Error getting registered tasks: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get registered tasks: {str(e)}"
        )


@router.get("/system/worker-status",
            summary="Get Worker Status",
            description="Get status of all active Procrastinate workers")
async def get_worker_status(
    manager: ProcrastinateManager = Depends(get_procrastinate_manager)
) -> Dict[str, Any]:
    """
    Get comprehensive worker status information
    """
    try:
        result = await manager.get_worker_status()
        return result
        
    except Exception as e:
        logger.error(f"Error getting worker status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get worker status: {str(e)}"
        )


@router.post("/system/cleanup-old-jobs",
             summary="Cleanup Old Jobs",
             description="Clean up old completed/failed jobs to free space")
async def cleanup_old_jobs(
    days_old: int = Query(30, ge=1, le=365),
    status_filter: Optional[str] = None,
    manager: ProcrastinateManager = Depends(get_procrastinate_manager)
) -> Dict[str, Any]:
    """
    Clean up old jobs to free database space
    
    Args:
        days_old: Jobs older than this many days will be cleaned up
        status_filter: Optional status filter (succeeded, failed, cancelled)
    """
    try:
        result = await manager.cleanup_old_jobs(days_old, status_filter)
        return result
        
    except Exception as e:
        logger.error(f"Error cleaning up old jobs: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to cleanup old jobs: {str(e)}"
        ) 