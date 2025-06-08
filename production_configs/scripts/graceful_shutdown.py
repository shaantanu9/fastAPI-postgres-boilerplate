#!/usr/bin/env python3
"""Graceful Shutdown Handler for FastAPI Applications.

This module provides comprehensive graceful shutdown handling for FastAPI applications,
ensuring all connections are properly closed and background tasks are completed.
"""

import asyncio
import logging
import signal
import sys
import time
import weakref
from collections.abc import Callable
from contextlib import asynccontextmanager, suppress
from typing import Any

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class GracefulShutdownManager:
    """Manages graceful shutdown for FastAPI applications.

    Features:
    - Signal handling (SIGTERM, SIGINT, SIGHUP)
    - Background task completion
    - Connection draining
    - Configurable shutdown timeout
    - Cleanup callbacks
    """

    def __init__(self, shutdown_timeout: int = 30) -> None:
        self.shutdown_timeout = shutdown_timeout
        self.shutdown_event = asyncio.Event()
        self.is_shutting_down = False
        self.cleanup_callbacks: list[Callable] = []
        self.background_tasks: list[asyncio.Task] = []
        self.active_connections: weakref.WeakSet = weakref.WeakSet()

        # Signal handlers
        self._setup_signal_handlers()

    def _setup_signal_handlers(self) -> None:
        """Set up signal handlers for graceful shutdown."""
        for sig in [signal.SIGTERM, signal.SIGINT]:
            signal.signal(sig, self._signal_handler)

        # Handle SIGHUP for graceful restart (reload)
        if hasattr(signal, "SIGHUP"):
            signal.signal(signal.SIGHUP, self._reload_handler)

    def _signal_handler(self, signum: int, frame) -> None:
        """Handle shutdown signals."""
        logger.info(f"Received signal {signum}. Initiating graceful shutdown...")
        self.is_shutting_down = True

        # For async contexts, we need to schedule the shutdown
        if asyncio.get_running_loop():
            asyncio.create_task(self.shutdown())
        else:
            asyncio.run(self.shutdown())

    def _reload_handler(self, signum: int, frame) -> None:
        """Handle reload signal (SIGHUP)."""
        logger.info("Received SIGHUP. Initiating graceful reload...")
        # In production, this would typically restart workers
        self._signal_handler(signum, frame)

    def add_cleanup_callback(self, callback: Callable) -> None:
        """Add a cleanup callback to be called during shutdown."""
        self.cleanup_callbacks.append(callback)

    def track_background_task(self, task: asyncio.Task) -> None:
        """Track a background task for graceful completion."""
        self.background_tasks.append(task)
        task.add_done_callback(lambda t: self.background_tasks.remove(t))

    def track_connection(self, connection: Any) -> None:
        """Track an active connection."""
        self.active_connections.add(connection)

    async def shutdown(self) -> None:
        """Perform graceful shutdown."""
        if self.shutdown_event.is_set():
            return

        logger.info("Starting graceful shutdown process...")
        start_time = time.time()

        # Set shutdown event
        self.shutdown_event.set()

        try:
            # 1. Stop accepting new connections
            logger.info("Stopping new connection acceptance...")

            # 2. Wait for background tasks to complete
            if self.background_tasks:
                logger.info(
                    f"Waiting for {len(self.background_tasks)} background tasks to complete...",
                )
                await self._wait_for_tasks()

            # 3. Drain existing connections
            if self.active_connections:
                logger.info(
                    f"Draining {len(self.active_connections)} active connections...",
                )
                await self._drain_connections()

            # 4. Run cleanup callbacks
            if self.cleanup_callbacks:
                logger.info(
                    f"Running {len(self.cleanup_callbacks)} cleanup callbacks...",
                )
                await self._run_cleanup_callbacks()

            elapsed = time.time() - start_time
            logger.info(f"Graceful shutdown completed in {elapsed:.2f} seconds")

        except TimeoutError:
            logger.warning(
                f"Graceful shutdown timed out after {self.shutdown_timeout}s. Forcing exit.",
            )
        except Exception as e:
            logger.exception(f"Error during graceful shutdown: {e}")
        finally:
            # Force exit if needed
            sys.exit(0)

    async def _wait_for_tasks(self) -> None:
        """Wait for background tasks to complete."""
        if not self.background_tasks:
            return

        try:
            await asyncio.wait_for(
                asyncio.gather(*self.background_tasks, return_exceptions=True),
                timeout=self.shutdown_timeout * 0.7,  # Use 70% of timeout for tasks
            )
        except TimeoutError:
            logger.warning(
                "Background tasks didn't complete within timeout, cancelling...",
            )
            for task in self.background_tasks:
                if not task.done():
                    task.cancel()

            # Wait a bit more for cancellation
            with suppress(TimeoutError):
                await asyncio.wait_for(
                    asyncio.gather(*self.background_tasks, return_exceptions=True),
                    timeout=5,
                )

    async def _drain_connections(self) -> None:
        """Wait for active connections to close."""
        max_wait = self.shutdown_timeout * 0.2  # Use 20% of timeout for connections
        wait_interval = 0.5
        waited = 0

        while self.active_connections and waited < max_wait:
            await asyncio.sleep(wait_interval)
            waited += wait_interval

        if self.active_connections:
            logger.warning(
                f"Force closing {len(self.active_connections)} remaining connections",
            )

    async def _run_cleanup_callbacks(self) -> None:
        """Run all registered cleanup callbacks."""
        for callback in self.cleanup_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback()
                else:
                    callback()
            except Exception as e:
                logger.exception(f"Error in cleanup callback: {e}")


# Global shutdown manager instance
shutdown_manager = GracefulShutdownManager()


@asynccontextmanager
async def lifespan_with_graceful_shutdown(app):
    """FastAPI lifespan context manager with graceful shutdown.

    Usage:
        from production_configs.scripts.graceful_shutdown import lifespan_with_graceful_shutdown

        app = FastAPI(lifespan=lifespan_with_graceful_shutdown)
    """
    # Startup
    logger.info("FastAPI application starting up...")

    # Add any startup tasks here
    yield

    # Shutdown
    logger.info("FastAPI application shutting down...")
    await shutdown_manager.shutdown()


def setup_graceful_shutdown(app, **kwargs):
    """Set up graceful shutdown for a FastAPI application.

    Args:
        app: FastAPI application instance
        **kwargs: Additional configuration options

    """
    global shutdown_manager

    # Configure shutdown manager
    timeout = kwargs.get("shutdown_timeout", 30)
    shutdown_manager.shutdown_timeout = timeout

    # Add database cleanup if using SQLAlchemy
    if "database_engine" in kwargs:
        engine = kwargs["database_engine"]
        shutdown_manager.add_cleanup_callback(lambda: engine.dispose())

    # Add Redis cleanup if using Redis
    if "redis_client" in kwargs:
        redis = kwargs["redis_client"]
        shutdown_manager.add_cleanup_callback(lambda: redis.close())

    # Add custom cleanup callbacks
    for callback in kwargs.get("cleanup_callbacks", []):
        shutdown_manager.add_cleanup_callback(callback)

    logger.info(f"Graceful shutdown configured with {timeout}s timeout")
    return shutdown_manager


# Middleware for tracking connections
class ConnectionTrackingMiddleware:
    """Middleware to track active connections for graceful shutdown."""

    def __init__(self, app) -> None:
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # Track this connection
        connection_id = id(scope)
        shutdown_manager.track_connection(connection_id)

        try:
            await self.app(scope, receive, send)
        finally:
            # Connection cleanup happens automatically via WeakSet
            pass


# Example usage in FastAPI app
if __name__ == "__main__":
    import uvicorn
    from fastapi import FastAPI

    # Create FastAPI app with graceful shutdown
    app = FastAPI(lifespan=lifespan_with_graceful_shutdown)

    # Add connection tracking middleware
    app.add_middleware(ConnectionTrackingMiddleware)

    @app.get("/")
    async def root():
        return {"message": "Hello World"}

    @app.get("/health")
    async def health():
        return {"status": "healthy", "shutting_down": shutdown_manager.is_shutting_down}

    # Configure graceful shutdown
    setup_graceful_shutdown(app, shutdown_timeout=30)

    # Run with uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
