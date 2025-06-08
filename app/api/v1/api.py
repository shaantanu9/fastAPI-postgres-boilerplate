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

# Conditionally import procrastinate admin router if the module is available
try:
    from app.api.v1.endpoints.procrastinate_admin import router as procrastinate_admin_router
    PROCRASTINATE_ADMIN_AVAILABLE = True
except ImportError:
    PROCRASTINATE_ADMIN_AVAILABLE = False
    print("Warning: procrastinate.contrib.fastapi module not found. Procrastinate admin dashboard will not be available.")

from app.api.v1.endpoints.feature_flags import router as feature_flags_router
from app.api.v1.endpoints import notification_preferences

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

# Task monitoring dashboard
if PROCRASTINATE_ADMIN_AVAILABLE:
    api_router.include_router(procrastinate_admin_router)

# Feature flag management
api_router.include_router(feature_flags_router, prefix="/features", tags=["feature-flags"])

# Notification preferences
api_router.include_router(notification_preferences.router, prefix="/notifications", tags=["notifications"])

# Procrastinate test endpoint
from app.api.v1.endpoints import procrastinate_test
api_router.include_router(procrastinate_test.router, prefix="/test-procrastinate", tags=["procrastinate-test"])
