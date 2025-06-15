"""Main application entrypoint for FastAPI Modular Boilerplate.

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

import asyncio
import logging
import os
import sys
import time
from contextlib import asynccontextmanager
from typing import Any, Dict, Optional

from fastapi import Depends, FastAPI, Request, status
from fastapi.exceptions import HTTPException, RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded
from starlette.exceptions import HTTPException as StarletteHTTPException

# Import API router
from app.api.v1.api import api_router

# Import rate limiting components
from app.core.rate_limiting import (
    RateLimitConfig,
    enhanced_rate_limit_exceeded_handler,
    get_rate_limit_config,
    get_rate_limiter,
    get_rate_limiter_dependency,
    setup_rate_limiting,
)

# Import timeout components
from app.core.timeouts import (
    TimeoutException,
    Timeouts,
    database_timeout_context,
    with_timeout,
)
from app.middleware.timeout_middleware import TimeoutMiddleware

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global timeout configuration (in seconds)
GLOBAL_REQUEST_TIMEOUT = 30.0

# Import tenant middleware for multi-tenancy support
from app.middleware.tenant_middleware import TenantIsolationMiddleware, TenantMiddleware

# Import production configurations if available
try:
    from production_configs.scripts.graceful_shutdown import (
        ConnectionTrackingMiddleware,
        lifespan_with_graceful_shutdown,
        setup_graceful_shutdown,
    )
    from production_configs.scripts.health_checks import setup_health_checks

    PRODUCTION_FEATURES_AVAILABLE = True
except ImportError:
    PRODUCTION_FEATURES_AVAILABLE = False
    logging.warning("Production features not available - running in development mode")

# Observability imports
from app.api.v1.endpoints.production_health import router as health_router
from app.core.metrics import metrics
from app.middleware.logging_middleware import (
    LoggingMiddleware,
    SecurityLoggingMiddleware,
)

# Production middleware imports
try:
    from app.middleware.simple_error_tracker import SimpleErrorTracker
    from app.middleware.security_headers import SecurityHeadersMiddleware
    PRODUCTION_MIDDLEWARE_AVAILABLE = True
except ImportError:
    PRODUCTION_MIDDLEWARE_AVAILABLE = False

# --- Import core functions ---
try:
    from app.api.v1.api import api_router
    from app.core.config import get_settings
    from app.core.logging import setup_logging
    from app.core.security import EnterpriseSecurityService, security_service

    CORE_IMPORTS_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Core imports not available: {e}")
    CORE_IMPORTS_AVAILABLE = False

    # Provide minimal fallbacks
    def setup_logging(**kwargs) -> None:
        pass

    def get_settings():
        class Settings:
            PROJECT_NAME = "FastAPI App"
            VERSION = "1.0.0"
            API_V1_STR = "/api/v1"
            LOG_LEVEL = "INFO"
            ENVIRONMENT = "development"

        return Settings()


# --- Logging and settings initialization ---
if CORE_IMPORTS_AVAILABLE:
    setup_logging()  # Configure loguru and std logging

# Error aggregation setup
try:
    from app.core.error_aggregator import setup_error_aggregation

    setup_error_aggregation()
    logger.info("✅ Error aggregation system initialized")
except ImportError as e:
    logger.warning(f"⚠️ Error aggregation not available: {e}")

    settings = get_settings()  # Load environment variables and app config
else:
    logging.basicConfig(level=logging.INFO)
    settings = get_settings()

# Global plugin manager reference
_plugin_manager = None

from app.websocket.manager import WebSocketManager, get_websocket_manager
from app.websocket.redis_pubsub import RedisPubSub
from app.websocket.presence import Presence
from app.websocket.history import MessageHistory


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup and shutdown events."""
    global _plugin_manager

    # --- WebSocket system setup ---
    ws_manager = WebSocketManager()
    ws_manager.redis_pubsub = RedisPubSub()
    ws_manager.presence = Presence()
    ws_manager.history = MessageHistory()
    app.state.websocket_manager = ws_manager

    # Start heartbeat and Redis listener
    ws_manager.start_heartbeat()
    await ws_manager.redis_pubsub.connect()
    # Optionally, subscribe to all rooms (for demo, subscribe to 'global')
    async def redis_callback(msg):
        # Broadcast to all local connections
        await ws_manager.broadcast(msg)
    await ws_manager.redis_pubsub.subscribe('global', redis_callback)

    # Startup
    logging.info("🚀 FastAPI application starting up...")

    # Import task queue and managers
    from app.core.plugin_system import PluginManager
    from app.utils.procrastinate_manager import init_procrastinate
    from app.utils.task_queue import enhanced_task_queue

    # Import error aggregation
    try:
        from app.core.error_aggregator import (
            start_error_aggregation,
            stop_error_aggregation,
        )

        ERROR_AGGREGATION_AVAILABLE = True
    except ImportError:
        ERROR_AGGREGATION_AVAILABLE = False

    # Start enhanced task queue
    enhanced_task_queue.start(num_workers=8)  # Start with 8 concurrent workers
    logging.info("✅ Enhanced task queue started with concurrent processing.")

    # Initialize Procrastinate
    try:
        init_procrastinate()
        logging.info("✅ Procrastinate PostgreSQL task queue initialized successfully.")
    except Exception as e:
        logging.exception(f"❌ Failed to initialize Procrastinate: {e}")
        # Don't raise - allow app to start even if Procrastinate fails

    # Initialize enterprise plugin system EARLY in startup
    try:
        logging.info("🔌 Initializing enterprise plugin system...")
        _plugin_manager = PluginManager(app, app_version="1.0.0")

        # Discover and load plugins
        plugin_search_paths = [
            "app/plugins",  # Built-in plugins
            "plugins",  # External plugins directory (if it exists)
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
        logging.exception(f"❌ Failed to initialize plugin system: {e}")
        import traceback

        logging.exception(traceback.format_exc())
        # Don't raise - allow app to start even if plugins fail

    # Start error aggregation background tasks
    if ERROR_AGGREGATION_AVAILABLE:
        try:
            await start_error_aggregation()
            logging.info("✅ Error aggregation background tasks started")
        except Exception as e:
            logging.exception(f"❌ Failed to start error aggregation: {e}")

    logging.info("🎉 Startup complete. All systems initialized.")

    yield

    # Shutdown
    logging.info("🛑 FastAPI application shutting down...")

    from app.utils.concurrent_utils import shutdown_concurrent_manager

    # Stop error aggregation background tasks
    if ERROR_AGGREGATION_AVAILABLE:
        try:
            await stop_error_aggregation()
            logging.info("✅ Error aggregation background tasks stopped")
        except Exception as e:
            logging.exception(f"❌ Error stopping error aggregation: {e}")

    # Shutdown plugins
    try:
        if _plugin_manager:
            await _plugin_manager.shutdown_plugins()
            logging.info("🔌 Plugin system shutdown complete.")
    except Exception as e:
        logging.exception(f"❌ Error shutting down plugin system: {e}")

    await enhanced_task_queue.stop()
    await shutdown_concurrent_manager()
    logging.info("✅ Shutdown complete. All concurrent processing stopped.")

    # --- WebSocket system cleanup ---
    ws_manager.stop_heartbeat()
    await ws_manager.redis_pubsub.close()


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()

    # Setup structured logging
    setup_logging(
        log_level=settings.LOG_LEVEL,
        log_file="logs/app.log",
        enable_console=True,
        enable_file=True,
    )

    app = FastAPI(
        title=settings.PROJECT_NAME,
        version=settings.VERSION,
        openapi_url=f"{settings.API_V1_STR}/openapi.json",
        lifespan=lifespan,
    )

    # FORCE plugin initialization during app creation as fallback
    # This ensures plugins work even if lifespan doesn't execute in dev mode
    try:
        global _plugin_manager
        if not _plugin_manager:
            logger.info("🔧 Initializing plugins during app creation (fallback)")
            
            # Import here to avoid circular imports
            from app.core.plugin_system import PluginManager
            
            # Create plugin manager
            manager = PluginManager(app, "1.0.0")
            
            # Import asyncio for running async functions
            import asyncio
            
            # Run plugin initialization
            async def init_plugins_sync():
                await manager.discover_and_load_plugins(["app/plugins"])
                await manager.initialize_plugins()
                await manager.startup_plugins()
                return manager
            
            # Run the initialization
            try:
                _plugin_manager = asyncio.get_event_loop().run_until_complete(init_plugins_sync())
                logger.info("✅ Plugins initialized successfully during app creation")
            except RuntimeError:
                # If no event loop, create one
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                _plugin_manager = loop.run_until_complete(init_plugins_sync())
                logger.info("✅ Plugins initialized successfully with new event loop")
                
    except Exception as e:
        logger.warning(f"⚠️ Plugin initialization fallback failed: {e}")
        # Don't crash the app if plugin initialization fails

    # Add production middleware (minimal overhead)
    if PRODUCTION_MIDDLEWARE_AVAILABLE:
        app.add_middleware(SecurityHeadersMiddleware)
        app.add_middleware(SimpleErrorTracker)
        logger.info("✅ Production middleware enabled")
    
    # Add observability middleware
    app.add_middleware(SecurityLoggingMiddleware)
    app.add_middleware(
        LoggingMiddleware, skip_paths=["/health", "/metrics", "/docs", "/openapi.json"],
    )

    # Add timeout middleware with enhanced features
    app.add_middleware(
        TimeoutMiddleware,
        timeout_seconds=GLOBAL_REQUEST_TIMEOUT,
        warning_threshold=0.8,  # Warn at 80% of timeout
        enable_metrics=True,
    )

    # Set application info for metrics
    metrics.set_app_info(
        version=settings.VERSION,
        environment=settings.ENVIRONMENT,
        build_time="2024-12-22T00:00:00Z",  # Would be actual build time
    )

    # Include routers
    app.include_router(api_router, prefix=settings.API_V1_STR)
    app.include_router(health_router, prefix="/health", tags=["health"])
    
    # --- WebSocket router integration ---
    from app.websocket.routes import router as websocket_router
    app.include_router(websocket_router)  # WebSocket endpoints (e.g., /ws/{room})

    # Add root endpoint
    @app.get("/")
    async def root():
        return {
            "message": "FastAPI Application with Observability",
            "version": settings.VERSION,
            "environment": settings.ENVIRONMENT,
            "health_check": "/health",
            "metrics": "/metrics",
        }

    # --- Advanced middleware and performance features ---
    try:
        from app.core.middleware import setup_middleware
        from app.core.versioning import (
            create_v1_router,
            create_v2_router,
            version_manager,
        )

        ADVANCED_FEATURES_AVAILABLE = True

        # Setup comprehensive middleware (compression, security, performance monitoring)
        setup_middleware(app)
        logging.info(
            "✅ Advanced features configured: compression, security headers, performance monitoring, rate limiting",
        )
    except ImportError:
        ADVANCED_FEATURES_AVAILABLE = False
        logging.warning("⚠️ Advanced middleware features not available")

    # --- Exception handlers ---
    try:
        from sqlalchemy.exc import SQLAlchemyError

        from app.core.exception_handlers import (
            AppException,
            app_exception_handler,
            generic_exception_handler,
            http_exception_handler,
            sqlalchemy_exception_handler,
        )

        app.add_exception_handler(AppException, app_exception_handler)
        app.add_exception_handler(HTTPException, http_exception_handler)
        app.add_exception_handler(SQLAlchemyError, sqlalchemy_exception_handler)
        app.add_exception_handler(
            RateLimitExceeded, enhanced_rate_limit_exceeded_handler,
        )
        app.add_exception_handler(Exception, generic_exception_handler)

    except ImportError as e:
        logger.warning(f"Some exception handlers not available: {e}")
        # Add basic exception handlers
        app.add_exception_handler(
            RateLimitExceeded, enhanced_rate_limit_exceeded_handler,
        )

    # Setup rate limiting middleware during app creation (not during startup)
    try:
        from slowapi import Limiter, _rate_limit_exceeded_handler
        from slowapi.middleware import SlowAPIMiddleware
        from slowapi.util import get_remote_address

        # Get rate limit configuration
        config = get_rate_limit_config()

        # Import the correct key function
        from app.core.rate_limiting import get_rate_limit_key

        # Create traditional slowapi limiter for middleware compatibility
        limiter = Limiter(
            key_func=get_rate_limit_key,
            default_limits=[config.default_limit],
            headers_enabled=True,
            storage_uri=config.redis_url,
        )

        # Override the default handler
        limiter._rate_limit_exceeded_handler = enhanced_rate_limit_exceeded_handler
        app.state.limiter = limiter

        # Add middleware DURING app creation
        app.add_middleware(SlowAPIMiddleware)

        # Setup enhanced rate limiting initialization for startup
        @app.on_event("startup")
        async def startup_rate_limiting() -> None:
            from app.core.rate_limiting import initialize_enhanced_rate_limiter

            try:
                # Initialize enhanced rate limiter
                rate_limiter = await initialize_enhanced_rate_limiter(config)

                # Store in app state for access in endpoints
                app.state.rate_limiter = rate_limiter

            except Exception as e:
                logger.exception(f"Failed to initialize enhanced rate limiting: {e}")
                if not config.enable_fallback:
                    raise
                logger.warning("Continuing with basic rate limiting only")

        # Add cleanup on shutdown
        @app.on_event("shutdown")
        async def shutdown_rate_limiting() -> None:
            try:
                from app.core.rate_limiting import _rate_limiter

                if _rate_limiter:
                    await _rate_limiter.cleanup()
                logger.info("Rate limiting cleanup completed")
            except Exception as e:
                logger.exception(f"Error during rate limiting cleanup: {e}")

        logger.info("Rate limiting middleware setup completed successfully")

    except ImportError as e:
        logger.warning(f"Rate limiting not available: {e}")
    except Exception as e:
        logger.exception(f"Failed to setup rate limiting middleware: {e}")
        # Don't crash the app if rate limiting fails

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
            f"Time: {process_time:.4f}s",
        )

        return response

    if ADVANCED_FEATURES_AVAILABLE:
        import time

        @app.get(
            "/health",
            tags=["System"],
            summary="💓 Health Check",
            description="Liveness probe for orchestration",
        )
        def health():
            """💓 **System Health Check**.

            Basic liveness probe for container orchestration and load balancers.
            Returns 200 if the application is running.
            """
            return {"status": "healthy", "timestamp": time.time()}

        @app.get(
            "/ready",
            tags=["System"],
            summary="✅ Readiness Check",
            description="Readiness probe with dependency checks",
        )
        async def ready():
            """✅ **System Readiness Check**.

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
                        "plugins": "✅ loaded" if plugin_ready else "⚠️ not loaded",
                    },
                }
            except Exception as e:
                logging.exception(f"Readiness check failed: {e}")
                raise HTTPException(status_code=503, detail="Service not ready")

    # --- Additional plugin status endpoint ---
    @app.get(
        "/plugins/status",
        tags=["Plugins"],
        summary="🔌 Plugin Status",
        description="Get status of all plugins",
    )
    async def get_plugin_status():
        """🔌 **Plugin Status Overview**.

        Returns the current status of all discovered and loaded plugins.
        """
        if not _plugin_manager:
            return {"message": "Plugin system not initialized", "plugins": {}}

        status = _plugin_manager.get_plugin_status()
        return {
            "message": "Plugin system operational",
            "total_plugins": len(status),
            "plugins": status,
        }

    # Initialize security_service
    from app.core.security import security_service

    security_service.init_app(app)

    return app


# Create the app instance
app = create_app()

# --- Development server (optional, for direct execution) ---
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app", host="0.0.0.0", port=8000, reload=True, log_level="info",
    )
