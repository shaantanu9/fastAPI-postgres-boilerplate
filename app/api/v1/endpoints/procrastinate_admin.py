"""Procrastinate Admin Dashboard Integration.

This module integrates the Procrastinate Admin dashboard into the FastAPI application,
providing a comprehensive task monitoring interface without reinventing the wheel.
"""

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from procrastinate.contrib.fastapi import ProcrastinateAdmin

from app.core.security.api_key import api_key_security
from app.utils.procrastinate_manager import procrastinate_app

# Initialize Procrastinate Admin
admin = ProcrastinateAdmin(procrastinate_app)

# Create router with API key security
router = APIRouter(
    prefix="/task-admin",
    tags=["task-monitoring"],
    dependencies=[Depends(api_key_security)],
)

# Mount the admin routes under /task-admin prefix
admin.mount_to_router(router)


# Add a welcome/landing page for the dashboard
@router.get("/", response_class=HTMLResponse)
async def task_admin_index(request: Request) -> str:
    """Task Administration Dashboard landing page.
    Provides links to the Procrastinate Admin UI components.
    """
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Task Administration Dashboard</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
        <style>
            body {
                padding: 2rem;
                font-family: system-ui, -apple-system, sans-serif;
            }
            .card {
                margin-bottom: 1rem;
                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            }
            .dashboard-header {
                margin-bottom: 2rem;
                border-bottom: 1px solid #dee2e6;
                padding-bottom: 1rem;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="dashboard-header">
                <h1>Task Administration Dashboard</h1>
                <p class="text-muted">Integrated Procrastinate Admin interface for task monitoring and management</p>
            </div>

            <div class="row">
                <div class="col-md-6">
                    <div class="card">
                        <div class="card-body">
                            <h5 class="card-title">Jobs Dashboard</h5>
                            <p class="card-text">View all pending, running, and completed jobs with filtering options.</p>
                            <a href="/api/v1/task-admin/jobs" class="btn btn-primary">View Jobs</a>
                        </div>
                    </div>
                </div>

                <div class="col-md-6">
                    <div class="card">
                        <div class="card-body">
                            <h5 class="card-title">Events Log</h5>
                            <p class="card-text">Monitor job events including successes, failures, and retries.</p>
                            <a href="/api/v1/task-admin/events" class="btn btn-primary">View Events</a>
                        </div>
                    </div>
                </div>
            </div>

            <div class="row mt-4">
                <div class="col-md-6">
                    <div class="card">
                        <div class="card-body">
                            <h5 class="card-title">Queue Status</h5>
                            <p class="card-text">Check the status of job queues and their contents.</p>
                            <a href="/api/v1/task-admin/queues" class="btn btn-primary">View Queues</a>
                        </div>
                    </div>
                </div>

                <div class="col-md-6">
                    <div class="card">
                        <div class="card-body">
                            <h5 class="card-title">Tasks Configuration</h5>
                            <p class="card-text">Configure task parameters and scheduling details.</p>
                            <a href="/api/v1/task-admin/tasks" class="btn btn-primary">Configure Tasks</a>
                        </div>
                    </div>
                </div>
            </div>

            <div class="mt-4">
                <p><strong>Note:</strong> This dashboard is secured with API key authentication. Ensure you have a valid API key.</p>
            </div>
        </div>
    </body>
    </html>
    """
