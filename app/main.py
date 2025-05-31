"""
Main application entrypoint for FastAPI Modular Boilerplate.

This file initializes the FastAPI app, configures logging, middleware, exception handlers,
mounts the versioned API, manages startup/shutdown events, and provides a root health check endpoint.

Sections:
- Logging and settings initialization
- Middleware for request/response logging
- Centralized exception handlers
- API router mounting
- Startup/shutdown events (DB table creation, background tasks)
- Health check endpoint
- Uvicorn run block (for direct execution)
"""
import os
import sys
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from sqlalchemy.exc import SQLAlchemyError
import logging
from app.core.logging import setup_logging
from app.core.config import get_settings
from app.db.base import Base
from app.db.session import engine
from app.api.v1.api import api_router
from app.core.exception_handlers import (
    AppException,
    app_exception_handler,
    http_exception_handler,
    sqlalchemy_exception_handler,
    generic_exception_handler,
)

# Import production configurations if available
try:
    from production_configs.scripts.graceful_shutdown import (
        setup_graceful_shutdown,
        lifespan_with_graceful_shutdown,
        ConnectionTrackingMiddleware
    )
    from production_configs.scripts.health_checks import setup_health_checks
    PRODUCTION_FEATURES_AVAILABLE = True
except ImportError:
    PRODUCTION_FEATURES_AVAILABLE = False
    logging.warning("Production features not available - running in development mode")

# --- Logging and settings initialization ---
setup_logging()  # Configure loguru and std logging
settings = get_settings()  # Load environment variables and app config


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager for startup and shutdown events.
    """
    # Startup
    logging.info("FastAPI application starting up...")
    
    # Import task queue and managers
    from app.utils.task_queue import enhanced_task_queue
    from app.utils.procrastinate_manager import init_procrastinate
    
    # Start enhanced task queue
    enhanced_task_queue.start(num_workers=8)  # Start with 8 concurrent workers
    logging.info("Enhanced task queue started with concurrent processing.")
    
    # Initialize Procrastinate
    try:
        init_procrastinate()
        logging.info("Procrastinate PostgreSQL task queue initialized successfully.")
    except Exception as e:
        logging.error(f"Failed to initialize Procrastinate: {e}")
        # Don't raise - allow app to start even if Procrastinate fails
    
    logging.info("Startup complete. All task processing systems initialized.")
    
    yield
    
    # Shutdown
    logging.info("FastAPI application shutting down...")
    
    from app.utils.concurrent_utils import shutdown_concurrent_manager
    
    enhanced_task_queue.stop()
    await shutdown_concurrent_manager()
    logging.info("Shutdown complete. All concurrent processing stopped.")


# --- FastAPI app instance ---
app = FastAPI(
    title="FastAPI Modular Boilerplate",
    version="1.0.0",
    description="""
    A modular and scalable FastAPI boilerplate for rapid backend development.
    Features async SQLAlchemy, Alembic migrations, JWT authentication, role-based permissions, 
    concurrent processing, enhanced task queues, Procrastinate PostgreSQL-based task persistence,
    response compression (gzip), HTTP/2 support, API versioning, and advanced pagination.
    """,
    contact={
        "name": "Your Team or Name",
        "email": "your@email.com",
        "url": "https://yourprojectsite.com"
    },
    license_info={
        "name": "MIT License",
        "url": "https://opensource.org/licenses/MIT"
    },
    terms_of_service="https://yourprojectsite.com/terms/",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_tags=[
        {"name": "Users", "description": "Operations with users: CRUD, authentication, roles."},
        {"name": "Auth", "description": "Authentication endpoints: login, token, etc."},
        {"name": "Health", "description": "Health and readiness checks for orchestration."},
        {"name": "Bulk Operations", "description": "High-performance bulk operations with concurrent processing."},
        {"name": "Procrastinate Tasks", "description": "Persistent, distributed task queue using PostgreSQL."},
        {"name": "v1.0", "description": "API version 1.0 endpoints (current stable version)."},
        {"name": "v2.0", "description": "API version 2.0 endpoints (latest features)."},
        {"name": "Performance", "description": "Performance monitoring and optimization features."},
        {"name": "Compression", "description": "Response compression and optimization."},
    ],
    lifespan=lifespan
)

# --- Advanced middleware and performance features ---
try:
    from app.core.middleware import setup_middleware
    from app.core.versioning import version_manager, create_v1_router, create_v2_router
    ADVANCED_FEATURES_AVAILABLE = True
    
    # Setup comprehensive middleware (compression, security, performance monitoring)
    setup_middleware(app)
    logging.info("Advanced features configured: compression, security headers, performance monitoring, rate limiting")
except ImportError:
    ADVANCED_FEATURES_AVAILABLE = False
    logging.warning("Advanced middleware features not available")

# --- Production middleware and configurations ---
# Temporarily disabled due to weak reference issue with connection tracking
# if PRODUCTION_FEATURES_AVAILABLE:
#     # Add connection tracking middleware for graceful shutdown
#     app.add_middleware(ConnectionTrackingMiddleware)
#     
#     # Setup graceful shutdown with database engine
#     setup_graceful_shutdown(
#         app,
#         database_engine=engine,
#         shutdown_timeout=30,
#         cleanup_callbacks=[]
#     )
#     
#     # Setup comprehensive health checks
#     health_checker = setup_health_checks(
#         app,
#         database_engine=engine,
#         redis_url=os.getenv("REDIS_URL", "redis://localhost:6379"),
#         external_services=[
#             # Add any external services you depend on
#             # "https://api.example.com/health"
#         ]
#     )
#     
#     logging.info("Production features configured: graceful shutdown and health checks")

# --- Middleware for request/response logging ---
from loguru import logger
import time
from starlette.requests import Request

@app.middleware("http")
async def log_requests(request: Request, call_next):
    """
    Middleware to log each HTTP request and response with timing info.
    """
    start_time = time.time()
    response = await call_next(request)
    process_time = (time.time() - start_time) * 1000
    logger.info(
        f"{request.method} {request.url.path} - Status: {response.status_code} - Time: {process_time:.2f}ms"
    )
    return response

# --- Register centralized exception handlers ---
app.add_exception_handler(AppException, app_exception_handler)
app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(SQLAlchemyError, sqlalchemy_exception_handler)
app.add_exception_handler(Exception, generic_exception_handler)

# --- Mount versioned API router ---
app.include_router(api_router, prefix="/api/v1")

# --- Health check endpoints for orchestration and monitoring ---
@app.get("/", tags=["Health"], description="Welcome message and basic service status.")
def root():
    """
    Root endpoint for health checks and welcome message.
    """
    return {"status": "ok", "message": "Welcome to the FastAPI Modular Boilerplate with Production Features!"}

# Basic health endpoint (fallback if production health checks not available)
if not PRODUCTION_FEATURES_AVAILABLE:
    @app.get("/health", tags=["Health"], description="Basic liveness probe for orchestration.")
    def health():
        """
        Liveness probe endpoint for orchestration/monitoring (returns 200 if app is running).
        """
        return {"status": "healthy"}

    @app.get("/ready", tags=["Health"], description="Readiness probe for orchestration (checks DB connection).")
    async def ready():
        """
        Readiness probe endpoint for orchestration/monitoring.
        Attempts a simple DB connection to verify app is ready to serve traffic.
        """
        from app.db.session import get_db
        try:
            # Try to acquire and release a DB connection
            db_gen = get_db()
            if hasattr(db_gen, "__anext__"):  # async generator
                db = await db_gen.__anext__()
                if hasattr(db, "close"):
                    await db.close()
            else:
                db = next(db_gen)
                if hasattr(db, "close"):
                    db.close()
            return {"status": "ready"}
        except Exception as e:
            from fastapi import status
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={"status": "not ready", "detail": str(e)}
            )


# --- Uvicorn run block (for direct execution) ---
if __name__ == "__main__":
    import uvicorn
    
    # Configuration for development vs production
    if os.getenv("ENVIRONMENT", "development").lower() == "production":
        # Production configuration - should use Gunicorn instead
        logging.warning("Running in production mode with uvicorn directly is not recommended. Use Gunicorn + Uvicorn workers.")
        uvicorn.run(
            "app.main:app",
            host="0.0.0.0",
            port=8000,
            workers=1,
            access_log=True,
            use_colors=False,
            log_config=None
        )
    else:
        # Development configuration
        uvicorn.run(
            "app.main:app",
            host="127.0.0.1",
            port=8000,
            reload=True,
            reload_dirs=["app"],
            access_log=True
        )
