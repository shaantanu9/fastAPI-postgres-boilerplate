"""
Bulk Operations API Endpoints with Parallel Processing.

This module provides high-performance bulk operations for large datasets
using concurrent.futures and enhanced services.
"""

from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, status, UploadFile, File
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
import json
import csv
import io
import time
from datetime import datetime
from loguru import logger

from app.db.session import get_db
from app.services.user_service import UserService
from app.db.schemas.user import UserRead, UserCreate
from app.utils.task_queue import enhanced_task_queue, TaskPriority
from app.utils.concurrent_utils import TaskType
from app.utils.concurrent_utils import parallel_io, parallel_cpu, execute_parallel
from app.core.exception_handlers import AppException


router = APIRouter(prefix="/bulk", tags=["Bulk Operations"])


# Pydantic models for bulk operations
class BulkCreateRequest(BaseModel):
    """Request model for bulk create operations"""
    data: List[Dict[str, Any]] = Field(..., description="List of items to create")
    batch_size: Optional[int] = Field(50, description="Batch size for processing", ge=1, le=1000)
    validate_parallel: Optional[bool] = Field(True, description="Enable parallel validation")


class BulkUpdateRequest(BaseModel):
    """Request model for bulk update operations"""
    updates: List[Dict[str, Any]] = Field(..., description="List of update data with IDs")
    batch_size: Optional[int] = Field(50, description="Batch size for processing", ge=1, le=1000)


class BulkDeleteRequest(BaseModel):
    """Request model for bulk delete operations"""
    ids: List[int] = Field(..., description="List of IDs to delete")
    batch_size: Optional[int] = Field(100, description="Batch size for processing", ge=1, le=1000)


class BulkOperationResponse(BaseModel):
    """Response model for bulk operations"""
    success: bool
    processed: int
    failed: int
    task_id: Optional[str] = None
    results: Optional[List[Any]] = None
    errors: Optional[List[str]] = None
    execution_time: Optional[float] = None


class BulkSearchRequest(BaseModel):
    """Request model for bulk search operations"""
    queries: List[Dict[str, Any]] = Field(..., description="List of search queries")
    max_results_per_query: Optional[int] = Field(100, description="Max results per query")


class NotificationRequest(BaseModel):
    """Request model for bulk notifications"""
    user_ids: List[int] = Field(..., description="List of user IDs")
    message: str = Field(..., description="Notification message")
    notification_type: str = Field("email", description="Type of notification")
    priority: str = Field("normal", description="Notification priority")


# User Bulk Operations
@router.post("/users/create", response_model=BulkOperationResponse)
async def bulk_create_users(
    request: BulkCreateRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    user_service: UserService = Depends(lambda: UserService())
):
    """
    Create multiple users in parallel with validation.
    
    - **Parallel validation**: Validates user data using CPU-bound processing
    - **Batch processing**: Creates users in optimized batches
    - **Error handling**: Reports individual validation and creation errors
    """
    try:
        start_time = time.time()
        
        # Validate required fields in parallel if enabled
        if request.validate_parallel:
            validation_errors = []
            
            def validate_user_data(user_data: Dict[str, Any]) -> Dict[str, Any]:
                required_fields = ['username', 'name', 'email', 'password']
                for field in required_fields:
                    if not user_data.get(field):
                        raise ValueError(f"Missing required field: {field}")
                return user_data
            
            # Validate all user data in parallel
            validated_data = await execute_parallel(
                validate_user_data, request.data, TaskType.CPU_BOUND, max_workers=4
            )
            
            # Filter out validation errors
            valid_data = []
            for i, result in enumerate(validated_data):
                if isinstance(result, Exception):
                    validation_errors.append(f"Row {i+1}: {str(result)}")
                else:
                    valid_data.append(result)
            
            if validation_errors and not valid_data:
                raise HTTPException(
                    status_code=400, 
                    detail={"message": "All data failed validation", "errors": validation_errors}
                )
        else:
            valid_data = request.data
            validation_errors = []
        
        # Create users in parallel
        created_users = await user_service.bulk_create_users_parallel(
            db, valid_data, request.batch_size
        )
        
        execution_time = time.time() - start_time
        
        return BulkOperationResponse(
            success=True,
            processed=len(created_users),
            failed=len(request.data) - len(created_users),
            results=created_users,
            errors=validation_errors if validation_errors else None,
            execution_time=execution_time
        )
        
    except Exception as e:
        logger.error(f"Bulk create users error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/users/update", response_model=BulkOperationResponse)
async def bulk_update_users(
    request: BulkUpdateRequest,
    db: AsyncSession = Depends(get_db),
    user_service: UserService = Depends(lambda: UserService())
):
    """
    Update multiple users in parallel.
    
    - **Parallel processing**: Updates users concurrently
    - **Password hashing**: Automatically hashes passwords if provided
    - **Error tracking**: Reports individual update failures
    """
    try:
        import time
        start_time = time.time()
        
        # Update users in parallel
        updated_users = await user_service.bulk_update_users_parallel(db, request.updates)
        
        execution_time = time.time() - start_time
        
        return BulkOperationResponse(
            success=True,
            processed=len(updated_users),
            failed=len(request.updates) - len(updated_users),
            results=updated_users,
            execution_time=execution_time
        )
        
    except Exception as e:
        logger.error(f"Bulk update users error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/users/delete", response_model=BulkOperationResponse)
async def bulk_delete_users(
    request: BulkDeleteRequest,
    db: AsyncSession = Depends(get_db),
    user_service: UserService = Depends(lambda: UserService())
):
    """
    Delete multiple users in parallel.
    
    - **Parallel deletion**: Deletes users concurrently
    - **Batch processing**: Processes deletions in optimized batches
    - **Success tracking**: Reports number of successful deletions
    """
    try:
        import time
        start_time = time.time()
        
        # Delete users in parallel
        deleted_count = await user_service.bulk_delete_parallel(db, request.ids)
        
        execution_time = time.time() - start_time
        
        return BulkOperationResponse(
            success=True,
            processed=deleted_count,
            failed=len(request.ids) - deleted_count,
            execution_time=execution_time
        )
        
    except Exception as e:
        logger.error(f"Bulk delete users error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/users/search", response_model=BulkOperationResponse)
async def bulk_search_users(
    request: BulkSearchRequest,
    db: AsyncSession = Depends(get_db),
    user_service: UserService = Depends(lambda: UserService())
):
    """
    Execute multiple search queries in parallel.
    
    - **Parallel queries**: Executes multiple searches concurrently
    - **Optimized performance**: Leverages database connection pooling
    - **Flexible queries**: Supports various search conditions
    """
    try:
        import time
        start_time = time.time()
        
        # Execute searches in parallel
        search_results = await user_service.search_users_parallel(db, request.queries)
        
        execution_time = time.time() - start_time
        total_results = sum(len(results) for results in search_results)
        
        return BulkOperationResponse(
            success=True,
            processed=len(search_results),
            failed=0,
            results=search_results,
            execution_time=execution_time
        )
        
    except Exception as e:
        logger.error(f"Bulk search users error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# File Import/Export Operations
@router.post("/users/import-csv")
async def import_users_from_csv(
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = None,
    batch_size: int = 50,
    db: AsyncSession = Depends(get_db),
    user_service: UserService = Depends(lambda: UserService())
):
    """
    Import users from CSV file with parallel processing.
    
    - **File validation**: Validates CSV format and headers
    - **Parallel processing**: Processes CSV rows concurrently
    - **Background import**: For large files, processes in background
    """
    try:
        # Validate file type
        if not file.filename.endswith('.csv'):
            raise HTTPException(status_code=400, detail="File must be a CSV")
        
        # Read and parse CSV
        content = await file.read()
        csv_data = content.decode('utf-8')
        
        def parse_csv_parallel(csv_content: str) -> List[Dict[str, Any]]:
            """Parse CSV content (CPU-bound)"""
            reader = csv.DictReader(io.StringIO(csv_content))
            required_columns = ['username', 'name', 'email', 'password']
            
            # Validate headers
            if not all(col in reader.fieldnames for col in required_columns):
                raise ValueError(f"CSV must contain columns: {required_columns}")
            
            return [dict(row) for row in reader]
        
        # Parse CSV in parallel
        users_data = await execute_parallel(
            lambda: parse_csv_parallel(csv_data), 
            [None], 
            TaskType.CPU_BOUND
        )
        
        if not users_data or isinstance(users_data[0], Exception):
            raise HTTPException(status_code=400, detail="Failed to parse CSV file")
        
        users_data = users_data[0]
        
        # For large files, process in background
        if len(users_data) > 1000:
            # Add to background task queue
            task_id = await enhanced_task_queue.add_task(
                user_service.bulk_create_users_parallel,
                db, users_data, batch_size,
                priority=TaskPriority.HIGH,
                task_type=TaskType.IO_BOUND
            )
            
            return {
                "message": f"Import queued for {len(users_data)} users",
                "task_id": task_id,
                "status": "processing"
            }
        else:
            # Process immediately for smaller files
            created_users = await user_service.bulk_create_users_parallel(
                db, users_data, batch_size
            )
            
            return {
                "message": f"Successfully imported {len(created_users)} users",
                "processed": len(created_users),
                "failed": len(users_data) - len(created_users)
            }
            
    except Exception as e:
        logger.error(f"CSV import error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/users/export")
async def export_users_parallel(
    format: str = "json",
    filters: Optional[str] = None,
    background_tasks: BackgroundTasks = None,
    db: AsyncSession = Depends(get_db),
    user_service: UserService = Depends(lambda: UserService())
):
    """
    Export users data with parallel processing.
    
    - **Parallel export**: Processes user data concurrently
    - **Multiple formats**: Supports JSON, CSV export
    - **Filtered export**: Supports query filters
    """
    try:
        # Parse filters if provided
        filter_dict = json.loads(filters) if filters else None
        
        # Export users in parallel
        export_data = await user_service.export_users_parallel(
            db, filter_dict, format
        )
        
        if format.lower() == "csv":
            # Convert to CSV format
            def convert_to_csv(data: List[Dict[str, Any]]) -> str:
                if not data:
                    return ""
                
                output = io.StringIO()
                writer = csv.DictWriter(output, fieldnames=data[0].keys())
                writer.writeheader()
                writer.writerows(data)
                return output.getvalue()
            
            csv_content = await execute_parallel(
                convert_to_csv, [export_data], TaskType.CPU_BOUND
            )
            
            from fastapi.responses import Response
            return Response(
                content=csv_content[0],
                media_type="text/csv",
                headers={"Content-Disposition": "attachment; filename=users_export.csv"}
            )
        else:
            return {
                "format": format,
                "count": len(export_data),
                "data": export_data
            }
            
    except Exception as e:
        logger.error(f"Export error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Notification Operations
@router.post("/notifications/send", response_model=BulkOperationResponse)
async def send_bulk_notifications(
    request: NotificationRequest,
    background_tasks: BackgroundTasks,
    user_service: UserService = Depends(lambda: UserService())
):
    """
    Send notifications to multiple users in parallel.
    
    - **Parallel delivery**: Sends notifications concurrently
    - **Priority handling**: Supports different notification priorities
    - **Background processing**: Prevents API timeout for large batches
    """
    try:
        import time
        start_time = time.time()
        
        # Define notification function
        def send_notification(user_id: int) -> Dict[str, Any]:
            """Send notification to a single user (I/O-bound)"""
            # Simulate notification sending
            logger.info(f"Sending {request.notification_type} to user {user_id}: {request.message}")
            return {
                "user_id": user_id,
                "status": "sent",
                "type": request.notification_type,
                "message": request.message,
                "priority": request.priority
            }
        
        # Send notifications in parallel
        notification_results = await user_service.send_user_notifications_parallel(
            request.user_ids, 
            {"message": request.message, "type": request.notification_type},
            send_notification
        )
        
        execution_time = time.time() - start_time
        successful_sends = len([r for r in notification_results if not isinstance(r, Exception)])
        
        return BulkOperationResponse(
            success=True,
            processed=successful_sends,
            failed=len(request.user_ids) - successful_sends,
            results=notification_results,
            execution_time=execution_time
        )
        
    except Exception as e:
        logger.error(f"Bulk notification error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Analytics and Statistics
@router.get("/users/statistics")
async def get_user_statistics_parallel(
    db: AsyncSession = Depends(get_db),
    user_service: UserService = Depends(lambda: UserService())
):
    """
    Generate comprehensive user statistics in parallel.
    
    - **Parallel queries**: Executes multiple analytics queries concurrently
    - **Real-time data**: Provides up-to-date statistics
    - **Performance optimized**: Uses database connection pooling
    """
    try:
        import time
        start_time = time.time()
        
        # Generate statistics in parallel
        statistics = await user_service.generate_user_statistics_parallel(db)
        
        execution_time = time.time() - start_time
        
        return {
            "statistics": statistics,
            "generated_at": datetime.now().isoformat(),
            "execution_time": execution_time
        }
        
    except Exception as e:
        logger.error(f"Statistics generation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Task Queue Monitoring
@router.get("/tasks/status/{task_id}")
async def get_task_status(task_id: str):
    """Get the status of a background task"""
    result = enhanced_task_queue.get_task_result(task_id)
    
    if not result:
        raise HTTPException(status_code=404, detail="Task not found")
    
    return {
        "task_id": task_id,
        "status": result.status,
        "result": result.result,
        "error": result.error,
        "execution_time": result.execution_time,
        "start_time": result.start_time.isoformat() if result.start_time else None,
        "end_time": result.end_time.isoformat() if result.end_time else None
    }


@router.get("/tasks/queue-stats")
async def get_queue_statistics():
    """Get task queue statistics and health"""
    stats = enhanced_task_queue.get_queue_stats()
    health = await enhanced_task_queue.health_check()
    
    return {
        "queue_stats": stats,
        "health_check": health
    }


# Validation Endpoints
@router.post("/users/validate", response_model=BulkOperationResponse)
async def validate_users_parallel(
    request: BulkCreateRequest,
    user_service: UserService = Depends(lambda: UserService())
):
    """
    Validate user data in parallel without creating records.
    
    - **Parallel validation**: Validates data using CPU-bound processing
    - **Comprehensive checks**: Email format, username rules, required fields
    - **Error reporting**: Detailed validation error messages
    """
    try:
        import time
        start_time = time.time()
        
        # Validate users in parallel
        validated_data = await user_service.validate_users_parallel(request.data)
        
        execution_time = time.time() - start_time
        
        return BulkOperationResponse(
            success=True,
            processed=len(validated_data),
            failed=len(request.data) - len(validated_data),
            results=validated_data,
            execution_time=execution_time
        )
        
    except Exception as e:
        logger.error(f"Bulk validation error: {e}")
        raise HTTPException(status_code=500, detail=str(e)) 