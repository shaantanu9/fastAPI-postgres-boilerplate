# app/api/v1/endpoints/jobs.py

from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from sqlalchemy import text, desc, asc
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db


router = APIRouter()


class JobStatus(BaseModel):
    id: str
    task_name: str
    status: str
    queue_name: str
    scheduled_at: Optional[datetime]
    started_at: Optional[datetime]
    finished_at: Optional[datetime]
    attempts: int
    args: Dict[str, Any]
    kwargs: Dict[str, Any]
    result: Optional[Any] = None
    exception: Optional[str] = None


class JobStats(BaseModel):
    total_jobs: int
    todo_jobs: int
    doing_jobs: int
    succeeded_jobs: int
    failed_jobs: int
    cancelled_jobs: int
    retry_jobs: int
    jobs_last_24h: int
    average_execution_time: Optional[float] = None


class QueueStats(BaseModel):
    queue_name: str
    pending_jobs: int
    running_jobs: int
    failed_jobs: int
    succeeded_jobs_today: int


@router.get("/stats", response_model=JobStats)
async def get_job_stats(
    session: AsyncSession = Depends(get_db)
) -> JobStats:
    """Get overall job statistics"""
    
    try:
        # Check if procrastinate_jobs table exists
        table_check = text("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'procrastinate_jobs'
            );
        """)
        table_exists = await session.execute(table_check)
        if not table_exists.scalar():
            # Return empty stats if table doesn't exist
            return JobStats(
                total_jobs=0,
                todo_jobs=0,
                doing_jobs=0,
                succeeded_jobs=0,
                failed_jobs=0,
                cancelled_jobs=0,
                retry_jobs=0,
                jobs_last_24h=0,
                average_execution_time=None
            )
        
        # Get total counts by status
        status_query = text("""
            SELECT status, COUNT(*) as count
            FROM procrastinate_jobs 
            GROUP BY status
        """)
        status_result = await session.execute(status_query)
        status_counts = {row.status: row.count for row in status_result}
        
        # Get jobs from last 24 hours
        last_24h_query = text("""
            SELECT COUNT(*) as count
            FROM procrastinate_jobs 
            WHERE scheduled_at >= NOW() - INTERVAL '24 HOURS'
        """)
        last_24h_result = await session.execute(last_24h_query)
        jobs_last_24h = last_24h_result.scalar() or 0
        
        # Get average execution time for succeeded jobs
        avg_time_query = text("""
            SELECT AVG(EXTRACT(EPOCH FROM (finished_at - started_at))) as avg_time
            FROM procrastinate_jobs 
            WHERE status = 'succeeded' 
            AND started_at IS NOT NULL 
            AND finished_at IS NOT NULL
            AND finished_at >= NOW() - INTERVAL '7 DAYS'
        """)
        avg_time_result = await session.execute(avg_time_query)
        avg_execution_time = avg_time_result.scalar()
        
        return JobStats(
            total_jobs=sum(status_counts.values()),
            todo_jobs=status_counts.get('todo', 0),
            doing_jobs=status_counts.get('doing', 0),
            succeeded_jobs=status_counts.get('succeeded', 0),
            failed_jobs=status_counts.get('failed', 0),
            cancelled_jobs=status_counts.get('cancelled', 0),
            retry_jobs=status_counts.get('retry', 0),
            jobs_last_24h=jobs_last_24h,
            average_execution_time=avg_execution_time
        )
    except Exception as e:
        # Return empty stats on any error
        return JobStats(
            total_jobs=0,
            todo_jobs=0,
            doing_jobs=0,
            succeeded_jobs=0,
            failed_jobs=0,
            cancelled_jobs=0,
            retry_jobs=0,
            jobs_last_24h=0,
            average_execution_time=None
        )


@router.get("/queues", response_model=List[QueueStats])
async def get_queue_stats(
    session: AsyncSession = Depends(get_db)
) -> List[QueueStats]:
    """Get statistics by queue"""
    
    try:
        # Check if procrastinate_jobs table exists
        table_check = text("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'procrastinate_jobs'
            );
        """)
        table_exists = await session.execute(table_check)
        if not table_exists.scalar():
            # Return empty list if table doesn't exist
            return []
        
        queue_query = text("""
            SELECT 
                queue_name,
                SUM(CASE WHEN status = 'todo' THEN 1 ELSE 0 END) as pending_jobs,
                SUM(CASE WHEN status = 'doing' THEN 1 ELSE 0 END) as running_jobs,
                SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed_jobs,
                SUM(CASE WHEN status = 'succeeded' AND finished_at >= CURRENT_DATE THEN 1 ELSE 0 END) as succeeded_jobs_today
            FROM procrastinate_jobs 
            GROUP BY queue_name
            ORDER BY queue_name
        """)
        
        result = await session.execute(queue_query)
        return [
            QueueStats(
                queue_name=row.queue_name,
                pending_jobs=row.pending_jobs,
                running_jobs=row.running_jobs,
                failed_jobs=row.failed_jobs,
                succeeded_jobs_today=row.succeeded_jobs_today
            )
            for row in result
        ]
    except Exception as e:
        # Return empty list on any error
        return []


@router.get("/", response_model=List[JobStatus])
async def list_jobs(
    status: Optional[str] = Query(None, description="Filter by job status"),
    queue: Optional[str] = Query(None, description="Filter by queue name"),
    task_name: Optional[str] = Query(None, description="Filter by task name"),
    limit: int = Query(50, ge=1, le=500, description="Number of jobs to return"),
    offset: int = Query(0, ge=0, description="Number of jobs to skip"),
    session: AsyncSession = Depends(get_db)
) -> List[JobStatus]:
    """List jobs with optional filtering"""
    
    try:
        # Check if procrastinate_jobs table exists
        table_check = text("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'procrastinate_jobs'
            );
        """)
        table_exists = await session.execute(table_check)
        if not table_exists.scalar():
            # Return empty list if table doesn't exist
            return []
        
        # Build dynamic query
        where_conditions = []
        params = {}
        
        if status:
            where_conditions.append("status = :status")
            params["status"] = status
        
        if queue:
            where_conditions.append("queue_name = :queue")
            params["queue"] = queue
        
        if task_name:
            where_conditions.append("task_name ILIKE :task_name")
            params["task_name"] = f"%{task_name}%"
        
        where_clause = "WHERE " + " AND ".join(where_conditions) if where_conditions else ""
        
        query = text(f"""
            SELECT 
                id,
                task_name,
                status,
                queue_name,
                scheduled_at,
                started_at,
                finished_at,
                attempts,
                args,
                kwargs
            FROM procrastinate_jobs 
            {where_clause}
            ORDER BY scheduled_at DESC
            LIMIT :limit OFFSET :offset
        """)
        
        params.update({"limit": limit, "offset": offset})
        result = await session.execute(query, params)
        
        jobs = []
        for row in result:
            jobs.append(JobStatus(
                id=str(row.id),
                task_name=row.task_name,
                status=row.status,
                queue_name=row.queue_name,
                scheduled_at=row.scheduled_at,
                started_at=row.started_at,
                finished_at=row.finished_at,
                attempts=row.attempts,
                args=row.args or {},
                kwargs=row.kwargs or {}
            ))
        
        return jobs
    except Exception as e:
        # Return empty list on any error
        return []


@router.get("/job/{job_id}", response_model=JobStatus)
async def get_job(
    job_id: str,
    session: AsyncSession = Depends(get_db)
) -> JobStatus:
    """Get detailed information about a specific job"""
    
    try:
        # Check if procrastinate_jobs table exists
        table_check = text("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'procrastinate_jobs'
            );
        """)
        table_exists = await session.execute(table_check)
        if not table_exists.scalar():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Job system not initialized"
            )
        
        query = text("""
            SELECT 
                id,
                task_name,
                status,
                queue_name,
                scheduled_at,
                started_at,
                finished_at,
                attempts,
                args,
                kwargs
            FROM procrastinate_jobs 
            WHERE id = :job_id
        """)
        
        result = await session.execute(query, {"job_id": job_id})
        row = result.first()
        
        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Job not found"
            )
        
        return JobStatus(
            id=str(row.id),
            task_name=row.task_name,
            status=row.status,
            queue_name=row.queue_name,
            scheduled_at=row.scheduled_at,
            started_at=row.started_at,
            finished_at=row.finished_at,
            attempts=row.attempts,
            args=row.args or {},
            kwargs=row.kwargs or {}
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Job system error"
        )


@router.post("/job/{job_id}/retry")
async def retry_job(
    job_id: str,
    session: AsyncSession = Depends(get_db)
) -> Dict[str, str]:
    """Retry a failed job"""
    
    # Update job status to retry
    query = text("""
        UPDATE procrastinate_jobs 
        SET status = 'todo', 
            attempts = attempts + 1,
            scheduled_at = NOW()
        WHERE id = :job_id 
        AND status IN ('failed', 'cancelled')
    """)
    
    result = await session.execute(query, {"job_id": job_id})
    await session.commit()
    
    if result.rowcount == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found or cannot be retried"
        )
    
    return {"message": "Job queued for retry"}


@router.delete("/job/{job_id}")
async def cancel_job(
    job_id: str,
    session: AsyncSession = Depends(get_db)
) -> Dict[str, str]:
    """Cancel a pending job"""
    
    query = text("""
        UPDATE procrastinate_jobs 
        SET status = 'cancelled'
        WHERE id = :job_id 
        AND status = 'todo'
    """)
    
    result = await session.execute(query, {"job_id": job_id})
    await session.commit()
    
    if result.rowcount == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found or cannot be cancelled"
        )
    
    return {"message": "Job cancelled"}


@router.post("/cleanup")
async def cleanup_old_jobs(
    days: int = Query(7, ge=1, le=365, description="Delete jobs older than this many days"),
    status_filter: Optional[str] = Query("succeeded", description="Only delete jobs with this status"),
    session: AsyncSession = Depends(get_db)
) -> Dict[str, int]:
    """Cleanup old completed jobs"""
    
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    
    where_clause = "WHERE finished_at < :cutoff_date"
    params = {"cutoff_date": cutoff_date}
    
    if status_filter:
        where_clause += " AND status = :status"
        params["status"] = status_filter
    
    query = text(f"""
        DELETE FROM procrastinate_jobs 
        {where_clause}
    """)
    
    result = await session.execute(query, params)
    await session.commit()
    
    return {"deleted_count": result.rowcount}


@router.get("/ui", response_class=HTMLResponse)
async def job_monitoring_ui():
    """Simple HTML UI for job monitoring"""
    
    html_content = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Job Monitoring Dashboard</title>
        <style>
            body {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                margin: 0;
                padding: 20px;
                background-color: #f5f5f5;
            }
            .container {
                max-width: 1200px;
                margin: 0 auto;
            }
            .header {
                background: #2c3e50;
                color: white;
                padding: 20px;
                border-radius: 8px;
                margin-bottom: 20px;
            }
            .stats-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 20px;
                margin-bottom: 30px;
            }
            .stat-card {
                background: white;
                padding: 20px;
                border-radius: 8px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                text-align: center;
            }
            .stat-number {
                font-size: 2em;
                font-weight: bold;
                color: #3498db;
            }
            .stat-label {
                color: #7f8c8d;
                margin-top: 5px;
            }
            .jobs-table {
                background: white;
                border-radius: 8px;
                overflow: hidden;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }
            .table-header {
                background: #34495e;
                color: white;
                padding: 15px 20px;
                font-weight: bold;
            }
            .job-row {
                padding: 15px 20px;
                border-bottom: 1px solid #ecf0f1;
                display: flex;
                justify-content: space-between;
                align-items: center;
            }
            .job-row:hover {
                background: #f8f9fa;
            }
            .job-status {
                padding: 4px 12px;
                border-radius: 20px;
                font-size: 0.85em;
                font-weight: bold;
            }
            .status-todo { background: #f39c12; color: white; }
            .status-doing { background: #3498db; color: white; }
            .status-succeeded { background: #27ae60; color: white; }
            .status-failed { background: #e74c3c; color: white; }
            .status-cancelled { background: #95a5a6; color: white; }
            .controls {
                margin-bottom: 20px;
                display: flex;
                gap: 10px;
                align-items: center;
            }
            .btn {
                padding: 8px 16px;
                border: none;
                border-radius: 4px;
                cursor: pointer;
                font-size: 14px;
            }
            .btn-primary {
                background: #3498db;
                color: white;
            }
            .btn-primary:hover {
                background: #2980b9;
            }
            select, input {
                padding: 8px;
                border: 1px solid #ddd;
                border-radius: 4px;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🔧 Background Job Monitoring Dashboard</h1>
                <p>Monitor and manage background jobs in real-time</p>
            </div>

            <div class="stats-grid" id="stats-grid">
                <!-- Stats will be loaded here -->
            </div>

            <div class="controls">
                <select id="statusFilter">
                    <option value="">All Statuses</option>
                    <option value="todo">Todo</option>
                    <option value="doing">Doing</option>
                    <option value="succeeded">Succeeded</option>
                    <option value="failed">Failed</option>
                    <option value="cancelled">Cancelled</option>
                </select>
                <input type="text" id="taskFilter" placeholder="Filter by task name...">
                <button class="btn btn-primary" onclick="refreshData()">Refresh</button>
                <button class="btn btn-primary" onclick="autoRefresh()">Auto Refresh (5s)</button>
            </div>

            <div class="jobs-table">
                <div class="table-header">Recent Jobs</div>
                <div id="jobs-list">
                    <!-- Jobs will be loaded here -->
                </div>
            </div>
        </div>

        <script>
            let autoRefreshInterval = null;

            async function loadStats() {
                try {
                    const response = await fetch('/api/v1/jobs/stats');
                    const stats = await response.json();
                    
                    const statsGrid = document.getElementById('stats-grid');
                    statsGrid.innerHTML = `
                        <div class="stat-card">
                            <div class="stat-number">${stats.total_jobs}</div>
                            <div class="stat-label">Total Jobs</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-number">${stats.todo_jobs}</div>
                            <div class="stat-label">Pending</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-number">${stats.doing_jobs}</div>
                            <div class="stat-label">Running</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-number">${stats.succeeded_jobs}</div>
                            <div class="stat-label">Succeeded</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-number">${stats.failed_jobs}</div>
                            <div class="stat-label">Failed</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-number">${stats.jobs_last_24h}</div>
                            <div class="stat-label">Last 24h</div>
                        </div>
                    `;
                } catch (error) {
                    console.error('Failed to load stats:', error);
                }
            }

            async function loadJobs() {
                try {
                    const statusFilter = document.getElementById('statusFilter').value;
                    const taskFilter = document.getElementById('taskFilter').value;
                    
                    let url = '/api/v1/jobs/?limit=20';
                    if (statusFilter) url += `&status=${statusFilter}`;
                    if (taskFilter) url += `&task_name=${taskFilter}`;
                    
                    const response = await fetch(url);
                    const jobs = await response.json();
                    
                    const jobsList = document.getElementById('jobs-list');
                    jobsList.innerHTML = jobs.map(job => `
                        <div class="job-row">
                            <div>
                                <strong>${job.task_name}</strong><br>
                                <small>ID: ${job.id}</small>
                            </div>
                            <div>
                                <span class="job-status status-${job.status}">${job.status}</span>
                            </div>
                            <div>
                                <small>${new Date(job.scheduled_at).toLocaleString()}</small>
                            </div>
                            <div>
                                Queue: ${job.queue_name}
                            </div>
                        </div>
                    `).join('');
                } catch (error) {
                    console.error('Failed to load jobs:', error);
                }
            }

            function refreshData() {
                loadStats();
                loadJobs();
            }

            function autoRefresh() {
                if (autoRefreshInterval) {
                    clearInterval(autoRefreshInterval);
                    autoRefreshInterval = null;
                    document.querySelector('[onclick="autoRefresh()"]').textContent = 'Auto Refresh (5s)';
                } else {
                    autoRefreshInterval = setInterval(refreshData, 5000);
                    document.querySelector('[onclick="autoRefresh()"]').textContent = 'Stop Auto Refresh';
                }
            }

            // Event listeners
            document.getElementById('statusFilter').addEventListener('change', loadJobs);
            document.getElementById('taskFilter').addEventListener('input', 
                debounce(loadJobs, 500)
            );

            function debounce(func, wait) {
                let timeout;
                return function executedFunction(...args) {
                    const later = () => {
                        clearTimeout(timeout);
                        func(...args);
                    };
                    clearTimeout(timeout);
                    timeout = setTimeout(later, wait);
                };
            }

            // Initial load
            refreshData();
        </script>
    </body>
    </html>
    """
    
    return HTMLResponse(content=html_content) 