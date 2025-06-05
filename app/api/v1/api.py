from fastapi import APIRouter
from app.api.v1.endpoints import user
from app.api.v1.endpoints import task 
from app.api.v1.endpoints import auth
from app.api.v1.endpoints import user_management
from app.api.v1.endpoints import bulk_operations
from app.api.v1.endpoints import procrastinate_tasks
from app.api.v1.endpoints import examples
from app.api.v1.endpoints import plugins
from app.api.v1.endpoints import health
from app.api.v1.endpoints import files
from app.api.v1.endpoints import listing
from app.api.v1.endpoints import jobs
from app.api.v1.endpoints import organizations
from app.api.v1.endpoints import email_integration
from app.api.v1.endpoints import rate_limit_test
from app.api.v1.endpoints.timeout_test import router as timeout_test_router

api_router = APIRouter()

# Core authentication and user management
api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])
api_router.include_router(user.router, prefix="/users", tags=["users"])
api_router.include_router(user_management.router, prefix="/user-management", tags=["user-management"])
api_router.include_router(organizations.router, prefix="/organizations", tags=["organizations"])

# Email service
api_router.include_router(email_integration.router, prefix="/email", tags=["email-service"])

# Enterprise features
api_router.include_router(health.router, prefix="/health", tags=["health-monitoring"])
api_router.include_router(files.router, prefix="/files", tags=["file-management"])
api_router.include_router(listing.router, prefix="/listing", tags=["advanced-listing"])
api_router.include_router(jobs.router, prefix="/jobs", tags=["job-monitoring"])

# Legacy endpoints
api_router.include_router(task.router, prefix="/tasks", tags=["tasks"])
api_router.include_router(bulk_operations.router, tags=["bulk-operations"])
api_router.include_router(procrastinate_tasks.router, prefix="/procrastinate", tags=["procrastinate-tasks"])
api_router.include_router(examples.router, prefix="/examples", tags=["examples"])
api_router.include_router(plugins.router, prefix="/system", tags=["plugin-management"])

# Include test endpoints with proper prefixes
api_router.include_router(rate_limit_test.router, prefix="/test/rate-limit", tags=["rate-limit-tests"])
api_router.include_router(timeout_test_router, prefix="/test/timeout", tags=["timeout-tests"])
