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
from sys import prefix
from fastapi_mcp import FastApiMCP
from fastapi import FastAPI, HTTPException
from sqlalchemy.exc import SQLAlchemyError
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

# --- Logging and settings initialization ---
setup_logging()  # Configure loguru and std logging
settings = get_settings()  # Load environment variables and app config

# --- FastAPI app instance ---

# --- FastAPI app instance ---
app = FastAPI(
    title="FastAPI Modular Boilerplate",
    version="1.0.0",
    description="""
    A modular and scalable FastAPI boilerplate for rapid backend development.
    Features async SQLAlchemy, Alembic migrations, JWT authentication, role-based permissions, 
    concurrent processing, enhanced task queues, and Procrastinate PostgreSQL-based task persistence.
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
        # Add more tags as you add more routers
    ]
)


# --- Mount API router ---
app.include_router(api_router, prefix="/api/v1")

@app.get("/health")
def health_check():
    return {"message": "OK"}


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

from app.utils.task_queue import enhanced_task_queue  # Enhanced async task queue for background jobs
from app.utils.concurrent_utils import shutdown_concurrent_manager
from app.utils.procrastinate_manager import init_procrastinate  # Procrastinate PostgreSQL task queue

# --- Startup event: start background workers and Procrastinate ---
@app.on_event("startup")
async def on_startup():
    """
    Startup event handler:
    - Starts the async task queue worker
    - Initializes Procrastinate PostgreSQL task queue
    - (Removed: table creation, handled by Alembic migrations)
    """
    import logging
    
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
    # ---
    # The following code is commented out to prevent conflicts with Alembic migrations:
    # from sqlalchemy.ext.asyncio import AsyncEngine
    # try:
    #     if isinstance(engine, AsyncEngine):
    #         async with engine.begin() as conn:
    #             await conn.run_sync(Base.metadata.create_all)
    #     else:
    #         with engine.begin() as conn:
    #             Base.metadata.create_all(bind=conn)
    #     logging.info("Database tables created/verified.")
    # except Exception as e:
    #     logging.error(f"[Startup Error] Could not create tables: {e}")
    #     raise

# --- Shutdown event: stop background workers ---
@app.on_event("shutdown")
async def on_shutdown():
    """
    Shutdown event handler: stops the enhanced task queue and concurrent managers.
    """
    enhanced_task_queue.stop()
    await shutdown_concurrent_manager()
    logging.info("Shutdown complete. All concurrent processing stopped.")

# --- Health check endpoints for orchestration and monitoring ---
@app.get("/", tags=["Health"], description="Welcome message and basic service status.")
def root():
    """
    Root endpoint for health checks and welcome message.
    """
    return {"status": "ok", "message": "Welcome to the FastAPI Modular Boilerplate with Procrastinate!"}

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
        # Try to acquire and release a DB connection (sync or async)
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
        return {"status": "not ready", "detail": str(e)}, status.HTTP_503_SERVICE_UNAVAILABLE

# mcp.mount("mcp", app)  # Mount the MCP server at /mcp (DISABLED: cannot mount FastAPI app as MCP subserver)
# mcp.mount()
try:
    from fastapi_mcp import FastApiMCP
    mcp = FastApiMCP(app,
    name="My API MCP",
    describe_all_responses=True,
    describe_full_response_schema=True,
    # prefix="/mcp"
    )
    mcp.mount()
    print("[INFO] FastAPI-MCP successfully mounted.")
except ImportError:
    print("[ERROR] fastapi_mcp is not installed. Install it with 'uv pip install fastapi_mcp' or 'poetry add fastapi_mcp'.")
except Exception as e:
    print(f"[ERROR] Failed to mount FastAPI-MCP: {e}")
# mcp.setup_server()
# --- Run with uvicorn if executed directly ---
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)
