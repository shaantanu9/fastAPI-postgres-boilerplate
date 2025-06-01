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
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
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

# Import tenant middleware for multi-tenancy support
from app.middleware.tenant_middleware import TenantMiddleware, TenantIsolationMiddleware

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

# Global plugin manager reference
_plugin_manager = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager for startup and shutdown events.
    """
    global _plugin_manager
    
    # Startup
    logging.info("🚀 FastAPI application starting up...")
    
    # Import task queue and managers
    from app.utils.task_queue import enhanced_task_queue
    from app.utils.procrastinate_manager import init_procrastinate
    from app.core.plugin_system import PluginManager
    
    # Start enhanced task queue
    enhanced_task_queue.start(num_workers=8)  # Start with 8 concurrent workers
    logging.info("✅ Enhanced task queue started with concurrent processing.")
    
    # Initialize Procrastinate
    try:
        init_procrastinate()
        logging.info("✅ Procrastinate PostgreSQL task queue initialized successfully.")
    except Exception as e:
        logging.error(f"❌ Failed to initialize Procrastinate: {e}")
        # Don't raise - allow app to start even if Procrastinate fails
    
    # Initialize enterprise plugin system EARLY in startup
    try:
        logging.info("🔌 Initializing enterprise plugin system...")
        _plugin_manager = PluginManager(app, app_version="1.0.0")
        
        # Discover and load plugins
        plugin_search_paths = [
            "app/plugins",  # Built-in plugins
            "plugins",      # External plugins directory (if it exists)
        ]
        
        # Step 1: Discover and load plugins
        await _plugin_manager.discover_and_load_plugins(plugin_search_paths)
        logging.info(f"📂 Discovered plugins from paths: {plugin_search_paths}")
        
        # Step 2: Initialize plugins (this registers routes and middleware)
        await _plugin_manager.initialize_plugins()
        logging.info("🔧 Plugins initialized and routes registered")
        
        # Step 3: Start plugins
        await _plugin_manager.startup_plugins()
        logging.info("🟢 Plugins started successfully")
        
        # Emit application startup event
        _plugin_manager.context.event_bus.emit("application_startup")
        
        # Log plugin status for debugging
        plugin_status = _plugin_manager.get_plugin_status()
        for name, status in plugin_status.items():
            logging.info(f"📊 Plugin {name}: {status['status']}")
        
        logging.info("✅ Enterprise plugin system initialized successfully.")
        
    except Exception as e:
        logging.error(f"❌ Failed to initialize plugin system: {e}")
        import traceback
        logging.error(traceback.format_exc())
        # Don't raise - allow app to start even if plugins fail
    
    logging.info("🎉 Startup complete. All systems initialized.")
    
    yield
    
    # Shutdown
    logging.info("🛑 FastAPI application shutting down...")
    
    from app.utils.concurrent_utils import shutdown_concurrent_manager
    
    # Shutdown plugins
    try:
        if _plugin_manager:
            await _plugin_manager.shutdown_plugins()
            logging.info("🔌 Plugin system shutdown complete.")
    except Exception as e:
        logging.error(f"❌ Error shutting down plugin system: {e}")
    
    enhanced_task_queue.stop()
    await shutdown_concurrent_manager()
    logging.info("✅ Shutdown complete. All concurrent processing stopped.")


# --- FastAPI app instance ---
app = FastAPI(
    title="FastAPI Enterprise Plugin System",
    version="1.0.0",
    description="""
    🚀 **FastAPI Enterprise Plugin System with Dynamic Route Discovery**
    
    A modular and scalable FastAPI application featuring:
    - 🔌 **Dynamic Plugin System** - Hot-pluggable modules with automatic discovery
    - 🏗️ **Enterprise Architecture** - Scalable, maintainable, and production-ready
    - 📊 **Monitoring & Analytics** - Built-in performance monitoring and health checks
    - 🔄 **Background Tasks** - Procrastinate-powered task queue with PostgreSQL persistence
    - 🛡️ **Security** - JWT authentication, role-based permissions, security middleware
    - 📱 **Auto-Generated APIs** - Complete CRUD operations with validation
    - 🚄 **High Performance** - Async SQLAlchemy, connection pooling, response compression
    - 📖 **Interactive Documentation** - Swagger UI with comprehensive API docs
    
    **Plugin Features:**
    - ✅ Automatic route registration and Swagger integration
    - ✅ Database models with migrations
    - ✅ Pydantic schemas with validation
    - ✅ Service layer with repository pattern
    - ✅ Event-driven architecture
    - ✅ Background task integration
    - ✅ Bulk operations support
    - ✅ Health monitoring
    
    **Generated Endpoints:**
    All plugins automatically generate REST endpoints that appear in this documentation.
    Navigate through the sections below to explore the available APIs.
    """,
    contact={
        "name": "FastAPI Enterprise Team",
        "email": "enterprise@fastapi.dev",
        "url": "https://fastapi-enterprise.dev"
    },
    license_info={
        "name": "MIT License",
        "url": "https://opensource.org/licenses/MIT"
    },
    terms_of_service="https://fastapi-enterprise.dev/terms/",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_tags=[
        {"name": "System", "description": "🔧 System health, status, and monitoring endpoints"},
        {"name": "Authentication", "description": "🔐 User authentication and authorization"},
        {"name": "Users", "description": "👥 User management operations"},
        {"name": "Plugins", "description": "🔌 Plugin management and status"},
        {"name": "Tasks", "description": "⚙️ Background task management"},
        {"name": "Monitoring", "description": "📊 Application monitoring and metrics"},
        {"name": "Cache", "description": "🗄️ Caching operations and management"},
        {"name": "Products", "description": "🛍️ Product management (demo plugin)"},
        {"name": "Bulk Operations", "description": "📦 High-performance bulk operations"},
        {"name": "v1.0", "description": "📋 API version 1.0 endpoints"},
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
    logging.info("✅ Advanced features configured: compression, security headers, performance monitoring, rate limiting")
except ImportError:
    ADVANCED_FEATURES_AVAILABLE = False
    logging.warning("⚠️ Advanced middleware features not available")

# --- Exception handlers ---
app.add_exception_handler(AppException, app_exception_handler)
app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(SQLAlchemyError, sqlalchemy_exception_handler)
app.add_exception_handler(Exception, generic_exception_handler)

# --- API router mounting ---
app.include_router(api_router, prefix="/api/v1")

# --- Request logging middleware ---
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all requests for debugging and monitoring."""
    start_time = time.time()
    
    # Process request
    response = await call_next(request)
    
    # Calculate processing time
    process_time = time.time() - start_time
    
    # Log the request
    logging.info(
        f"{request.method} {request.url.path} - "
        f"Status: {response.status_code} - "
        f"Time: {process_time:.4f}s"
    )
    
    return response

# --- Root endpoints ---
@app.get("/", tags=["System"], summary="🏠 Welcome", description="Welcome message and system overview")
def root():
    """
    🏠 **Welcome to FastAPI Enterprise Plugin System**
    
    This endpoint provides basic system information and navigation.
    """
    return {
        "message": "🚀 Welcome to FastAPI Enterprise Plugin System!",
        "version": "1.0.0",
        "status": "running",
        "features": [
            "🔌 Dynamic Plugin System",
            "📊 Real-time Monitoring", 
            "🛡️ Enterprise Security",
            "⚡ High Performance",
            "📖 Auto-generated APIs"
        ],
        "endpoints": {
            "docs": "/docs",
            "redoc": "/redoc", 
            "health": "/health",
            "ready": "/ready",
            "plugins": "/api/v1/plugins/status"
        }
    }

if ADVANCED_FEATURES_AVAILABLE:
    import time
    
    @app.get("/health", tags=["System"], summary="💓 Health Check", description="Liveness probe for orchestration")
    def health():
        """
        💓 **System Health Check**
        
        Basic liveness probe for container orchestration and load balancers.
        Returns 200 if the application is running.
        """
        return {"status": "healthy", "timestamp": time.time()}

    @app.get("/ready", tags=["System"], summary="✅ Readiness Check", description="Readiness probe with dependency checks")
    async def ready():
        """
        ✅ **System Readiness Check**
        
        Readiness probe that checks if the application is ready to serve traffic.
        Validates database connectivity and essential services.
        """
        try:
            # Test database connection
            from sqlalchemy import text
            from app.db.session import get_db
            
            async for db in get_db():
                await db.execute(text("SELECT 1"))
                break
            
            # Check plugin system
            plugin_ready = _plugin_manager is not None if _plugin_manager else False
            
            return {
                "status": "ready",
                "timestamp": time.time(),
                "checks": {
                    "database": "✅ connected",
                    "plugins": "✅ loaded" if plugin_ready else "⚠️ not loaded"
                }
            }
        except Exception as e:
            logging.error(f"Readiness check failed: {e}")
            raise HTTPException(status_code=503, detail="Service not ready")

# --- Additional plugin status endpoint ---
@app.get("/plugins/status", tags=["Plugins"], summary="🔌 Plugin Status", description="Get status of all plugins")
async def get_plugin_status():
    """
    🔌 **Plugin Status Overview**
    
    Returns the current status of all discovered and loaded plugins.
    """
    if not _plugin_manager:
        return {"message": "Plugin system not initialized", "plugins": {}}
    
    status = _plugin_manager.get_plugin_status()
    return {
        "message": "Plugin system operational",
        "total_plugins": len(status),
        "plugins": status
    }

# --- Development server (optional, for direct execution) ---
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
