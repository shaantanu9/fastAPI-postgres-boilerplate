"""
Complete Example: Best Practices for Using Procrastinate Queue in FastAPI

This file demonstrates various ways to add tasks to the Procrastinate queue
following the established patterns in your codebase.
"""

from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

from app.utils.procrastinate_manager import (
    get_procrastinate_manager, 
    ProcrastinateManager,
    ProcrastinateTaskPriority
)
from app.services.enhanced_procrastinate_service import (
    EnhancedProcrastinateService, 
    ProcessingMode
)
from app.db.session import get_db

router = APIRouter()

# =============================================================================
# METHOD 1: Using ProcrastinateManager (Recommended for most cases)
# =============================================================================

@router.post("/users/{user_id}/process")
async def process_user_data_async(
    user_id: int,
    operation: str,
    priority: str = "normal",
    manager: ProcrastinateManager = Depends(get_procrastinate_manager)
):
    """
    BEST PRACTICE: Use ProcrastinateManager for user processing
    """
    # Convert priority string to enum
    priority_map = {
        "low": ProcrastinateTaskPriority.LOW,
        "normal": ProcrastinateTaskPriority.NORMAL,
        "high": ProcrastinateTaskPriority.HIGH,
        "critical": ProcrastinateTaskPriority.CRITICAL
    }
    
    try:
        job_id = await manager.defer_user_processing(
            user_id=user_id,
            operation=operation,
            priority=priority_map.get(priority, ProcrastinateTaskPriority.NORMAL),
            # Add any extra parameters
            timestamp=datetime.now().isoformat(),
            source="api_request"
        )
        
        return {
            "message": f"User {user_id} processing queued",
            "job_id": job_id,
            "operation": operation,
            "priority": priority,
            "status": "queued"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to queue task: {str(e)}")


@router.post("/bulk-process")
async def bulk_process_data(
    data_items: List[Dict[str, Any]],
    task_type: str = "parallel",
    priority: str = "normal",
    manager: ProcrastinateManager = Depends(get_procrastinate_manager)
):
    """
    BEST PRACTICE: Bulk processing with validation
    """
    # Validate input
    if len(data_items) > 10000:
        raise HTTPException(
            status_code=400, 
            detail="Maximum 10,000 items allowed per bulk operation"
        )
    
    if not data_items:
        raise HTTPException(status_code=400, detail="data_items cannot be empty")
    
    priority_enum = {
        "low": ProcrastinateTaskPriority.LOW,
        "normal": ProcrastinateTaskPriority.NORMAL,
        "high": ProcrastinateTaskPriority.HIGH,
        "critical": ProcrastinateTaskPriority.CRITICAL
    }.get(priority, ProcrastinateTaskPriority.NORMAL)
    
    try:
        job_id = await manager.defer_bulk_processing(
            data_items=data_items,
            task_type=task_type,
            priority=priority_enum
        )
        
        return {
            "message": f"Bulk processing queued for {len(data_items)} items",
            "job_id": job_id,
            "total_items": len(data_items),
            "task_type": task_type,
            "status": "queued"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to queue bulk task: {str(e)}")


@router.post("/notifications/send")
async def send_notification_async(
    notification_type: str,
    recipient: str,
    message: str,
    priority: str = "normal",
    metadata: Optional[Dict[str, Any]] = None,
    manager: ProcrastinateManager = Depends(get_procrastinate_manager)
):
    """
    BEST PRACTICE: Reliable notification delivery
    """
    priority_enum = {
        "low": ProcrastinateTaskPriority.LOW,
        "normal": ProcrastinateTaskPriority.NORMAL,
        "high": ProcrastinateTaskPriority.HIGH,
        "critical": ProcrastinateTaskPriority.CRITICAL
    }.get(priority, ProcrastinateTaskPriority.NORMAL)
    
    try:
        job_id = await manager.defer_notification(
            notification_type=notification_type,
            recipient=recipient,
            message=message,
            priority=priority_enum,
            **(metadata or {})
        )
        
        return {
            "message": f"Notification queued for {recipient}",
            "job_id": job_id,
            "notification_type": notification_type,
            "status": "queued"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to queue notification: {str(e)}")


# =============================================================================
# METHOD 2: Using Enhanced Service with Hybrid Processing
# =============================================================================

@router.post("/smart-process")
async def smart_bulk_processing(
    data_items: List[Dict[str, Any]],
    mode: str = "hybrid",
    immediate_threshold: int = 100,
    db: AsyncSession = Depends(get_db)
):
    """
    BEST PRACTICE: Smart processing with hybrid mode
    - Small datasets: immediate processing
    - Large datasets: persistent queue processing
    """
    from app.db.models.user import User  # Example model
    
    service = EnhancedProcrastinateService(User)
    
    # Define processing function
    async def process_item(item: Dict[str, Any]) -> Dict[str, Any]:
        # Your business logic here
        return {
            "id": item.get("id"),
            "processed": True,
            "processed_at": datetime.now().isoformat()
        }
    
    try:
        result = await service.process_bulk_data_hybrid(
            db=db,
            data_items=data_items,
            processing_func=process_item,
            mode=mode,
            immediate_threshold=immediate_threshold,
            priority=ProcrastinateTaskPriority.NORMAL
        )
        
        return {
            "message": f"Smart processing completed for {len(data_items)} items",
            "result": result
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Smart processing failed: {str(e)}")


# =============================================================================
# METHOD 3: Scheduled Tasks
# =============================================================================

@router.post("/schedule/cleanup")
async def schedule_cleanup(
    days_old: int = 30,
    schedule_at: Optional[datetime] = None,
    manager: ProcrastinateManager = Depends(get_procrastinate_manager)
):
    """
    BEST PRACTICE: Schedule maintenance tasks
    """
    try:
        job_id = await manager.schedule_cleanup(
            days_old=days_old,
            at=schedule_at
        )
        
        return {
            "message": f"Cleanup task scheduled for data older than {days_old} days",
            "job_id": job_id,
            "scheduled_at": schedule_at.isoformat() if schedule_at else "in 1 hour",
            "status": "scheduled"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to schedule cleanup: {str(e)}")


@router.post("/schedule/user-batch")
async def schedule_user_batch_processing(
    user_ids: List[int],
    operation: str,
    schedule_at: Optional[datetime] = None,
    priority: str = "normal"
):
    """
    BEST PRACTICE: Schedule batch user operations
    """
    from app.db.models.user import User
    
    service = EnhancedProcrastinateService(User)
    priority_enum = {
        "low": ProcrastinateTaskPriority.LOW,
        "normal": ProcrastinateTaskPriority.NORMAL,
        "high": ProcrastinateTaskPriority.HIGH,
        "critical": ProcrastinateTaskPriority.CRITICAL
    }.get(priority, ProcrastinateTaskPriority.NORMAL)
    
    try:
        result = await service.schedule_user_processing(
            user_ids=user_ids,
            operation=operation,
            schedule_at=schedule_at,
            priority=priority_enum
        )
        
        return {
            "message": f"Scheduled processing for {len(user_ids)} users",
            "result": result
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to schedule user processing: {str(e)}")


# =============================================================================
# METHOD 4: Direct Task Usage (Advanced)
# =============================================================================

@router.post("/direct-task")
async def create_direct_task():
    """
    ADVANCED: Direct task function usage
    Use this when you need full control over task parameters
    """
    from app.utils.procrastinate_manager import process_user_data, send_notification
    
    try:
        # Direct task deferral with full control
        user_job = await process_user_data.defer_async(
            user_id=123,
            operation="advanced_processing",
            priority=3,  # HIGH priority
            custom_field="custom_value",
            metadata={"source": "direct_api", "timestamp": datetime.now().isoformat()}
        )
        
        notification_job = await send_notification.defer_async(
            notification_type="email",
            recipient="admin@example.com",
            message="Advanced processing initiated",
            priority=4,  # CRITICAL priority
            tracking_id=str(user_job.id)
        )
        
        return {
            "message": "Direct tasks created",
            "user_processing_job": str(user_job.id),
            "notification_job": str(notification_job.id),
            "status": "queued"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Direct task creation failed: {str(e)}")


# =============================================================================
# METHOD 5: Task Status and Monitoring
# =============================================================================

@router.get("/jobs/{job_id}/status")
async def get_job_status(
    job_id: str,
    manager: ProcrastinateManager = Depends(get_procrastinate_manager)
):
    """
    BEST PRACTICE: Monitor job status
    """
    try:
        status_info = await manager.get_job_status(job_id)
        return status_info
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get job status: {str(e)}")


@router.get("/queue/health")
async def get_queue_health():
    """
    BEST PRACTICE: Monitor queue health
    """
    from app.db.models.user import User
    
    service = EnhancedProcrastinateService(User)
    
    try:
        health_info = await service.get_queue_health()
        return health_info
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get queue health: {str(e)}")


# =============================================================================
# Integration with Your Existing User Service
# =============================================================================

@router.post("/users/{user_id}/welcome-process")
async def welcome_user_process(
    user_id: int,
    include_email: bool = True,
    include_sms: bool = False,
    priority: str = "high",
    manager: ProcrastinateManager = Depends(get_procrastinate_manager)
):
    """
    REAL-WORLD EXAMPLE: Welcome user process with multiple tasks
    """
    priority_enum = {
        "low": ProcrastinateTaskPriority.LOW,
        "normal": ProcrastinateTaskPriority.NORMAL,
        "high": ProcrastinateTaskPriority.HIGH,
        "critical": ProcrastinateTaskPriority.CRITICAL
    }.get(priority, ProcrastinateTaskPriority.HIGH)
    
    try:
        tasks = []
        
        # Queue user data processing
        user_job_id = await manager.defer_user_processing(
            user_id=user_id,
            operation="welcome_setup",
            priority=priority_enum,
            setup_profile=True,
            create_workspace=True
        )
        tasks.append({"type": "user_processing", "job_id": user_job_id})
        
        # Queue welcome email
        if include_email:
            email_job_id = await manager.defer_notification(
                notification_type="email",
                recipient=f"user_{user_id}@example.com",  # You'd get this from the database
                message="Welcome to our platform!",
                priority=priority_enum,
                template="welcome_email",
                user_id=user_id
            )
            tasks.append({"type": "welcome_email", "job_id": email_job_id})
        
        # Queue welcome SMS
        if include_sms:
            sms_job_id = await manager.defer_notification(
                notification_type="sms",
                recipient=f"user_{user_id}_phone",  # You'd get this from the database
                message="Welcome! Your account is ready.",
                priority=priority_enum,
                user_id=user_id
            )
            tasks.append({"type": "welcome_sms", "job_id": sms_job_id})
        
        return {
            "message": f"Welcome process initiated for user {user_id}",
            "user_id": user_id,
            "tasks": tasks,
            "total_tasks": len(tasks),
            "status": "queued"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Welcome process failed: {str(e)}")


# =============================================================================
# Error Handling and Best Practices Summary
# =============================================================================

"""
BEST PRACTICES SUMMARY:

1. **Use ProcrastinateManager**: For most cases, use get_procrastinate_manager()
2. **Validate Input**: Always validate data before queuing tasks
3. **Set Priorities**: Use appropriate task priorities for business logic
4. **Handle Errors**: Wrap task creation in try-catch blocks
5. **Monitor Jobs**: Provide endpoints to check job status
6. **Use Hybrid Mode**: For flexible processing based on data size
7. **Schedule Wisely**: Use scheduled tasks for maintenance operations
8. **Resource Limits**: Set reasonable limits (max items, file sizes, etc.)
9. **Logging**: Log all task creation and status changes
10. **Health Checks**: Monitor queue health and worker status

TASK QUEUES AVAILABLE:
- user_processing: For user-related operations
- data_processing: For bulk data operations  
- notifications: For email, SMS, push notifications
- file_processing: For file analysis and processing
- analytics: For report generation (with locks)
- maintenance: For cleanup and health checks

PRIORITY LEVELS:
- LOW (1): Background, non-urgent tasks
- NORMAL (2): Standard priority tasks
- HIGH (3): Important tasks that should be processed quickly
- CRITICAL (4): Urgent tasks that need immediate attention
""" 