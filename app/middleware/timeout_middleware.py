"""
Timeout middleware with enhanced error handling and debugging.
"""
import asyncio
import contextlib
import time
from typing import Any

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from loguru import logger
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.types import ASGIApp

# Default timeout in seconds
DEFAULT_TIMEOUT = 30.0


class TimeoutMiddleware(BaseHTTPMiddleware):
    """Middleware to handle request timeouts with enhanced error handling."""

    def __init__(
        self,
        app: ASGIApp,
        timeout_seconds: float = DEFAULT_TIMEOUT,
        timeout_response: dict[str, Any] | None = None,
        warning_threshold: float = 0.8,
        enable_metrics: bool = True,
    ) -> None:
        """Initialize timeout middleware.

        Args:
            app: ASGI application
            timeout_seconds: Default timeout in seconds
            timeout_response: Custom timeout response
            warning_threshold: Warning threshold as fraction of timeout
            enable_metrics: Whether to collect metrics

        """
        super().__init__(app)
        self.timeout_seconds = timeout_seconds
        self.timeout_response = timeout_response or {
            "detail": "Request timeout",
            "error_code": "REQUEST_TIMEOUT",
        }
        self.warning_threshold = warning_threshold
        self.enable_metrics = enable_metrics

        # Initialize metrics
        if self.enable_metrics:
            self.metrics = {
                "total_requests": 0,
                "timeout_count": 0,
                "warning_count": 0,
                "avg_response_time": 0.0,
                "max_response_time": 0.0,
            }

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint,
    ) -> Response:
        """Process request with timeout handling.

        Args:
            request: The incoming request
            call_next: The next middleware or endpoint to call

        Returns:
            Response: The response from the next handler or timeout response

        """
        start_time = time.monotonic()

        # Get endpoint-specific timeout
        endpoint_timeout = self._get_endpoint_timeout(request)
        warning_time = endpoint_timeout * self.warning_threshold

        # Update metrics
        if self.enable_metrics:
            self.metrics["total_requests"] += 1

        try:
            # ENHANCED ERROR HANDLING: Check if this is an auth endpoint
            is_auth_endpoint = "/api/v1/auth/" in request.url.path
            
            if is_auth_endpoint:
                logger.debug(f"Processing auth endpoint: {request.method} {request.url.path}")
            
            # Execute request with timeout
            response = await self._execute_with_timeout_enhanced(
                request, call_next, endpoint_timeout, warning_time, is_auth_endpoint
            )

            # Calculate duration and update metrics
            duration = time.monotonic() - start_time
            self._update_metrics(duration)

            # Add timeout headers
            response.headers["X-Request-Duration"] = f"{duration:.3f}"
            response.headers["X-Timeout-Limit"] = str(endpoint_timeout)

            return response

        except TimeoutError:
            duration = time.monotonic() - start_time
            if self.enable_metrics:
                self.metrics["timeout_count"] += 1

            logger.warning(
                f"Request to {request.method} {request.url.path} timed out after {duration:.2f}s "
                f"(limit: {endpoint_timeout}s)",
            )

            return JSONResponse(
                status_code=504,
                content={
                    **self.timeout_response,
                    "actual_duration": round(duration, 2),
                    "method": request.method,
                    "path": str(request.url.path),
                    "timestamp": time.time(),
                },
                headers={
                    "X-Request-Duration": f"{duration:.3f}",
                    "X-Timeout-Limit": str(endpoint_timeout),
                    "Retry-After": "60",  # Suggest retry after 60 seconds
                },
            )

        except Exception as exc:
            duration = time.monotonic() - start_time
            
            # ENHANCED ERROR LOGGING
            logger.error(f"Error in timeout middleware for {request.method} {request.url.path}: {exc}")
            logger.error(f"Exception type: {type(exc)}")
            logger.error(f"Exception args: {exc.args}")
            
            # Log the full traceback for debugging
            import traceback
            logger.error(f"Full traceback: {traceback.format_exc()}")

            return JSONResponse(
                status_code=500,
                content={
                    "detail": "Internal server error during timeout handling",
                    "error_code": "TIMEOUT_MIDDLEWARE_ERROR",
                    "duration": round(duration, 2),
                    "debug_info": {
                        "exception_type": str(type(exc)),
                        "exception_message": str(exc),
                        "endpoint": str(request.url.path),
                        "method": request.method
                    }
                },
            )

    def _get_endpoint_timeout(self, request: Request) -> float:
        """Get the timeout for a specific endpoint.

        Args:
            request: The incoming request

        Returns:
            float: Timeout in seconds for this endpoint

        """
        # Check for route-specific timeout
        endpoint = request.scope.get("endpoint")
        if endpoint and hasattr(endpoint, "timeout_seconds"):
            return endpoint.timeout_seconds

        # Check for path-based timeout configuration
        path = request.url.path

        # Define endpoint-specific timeouts
        endpoint_timeouts = {
            "/api/v1/auth/": 15.0,  # Auth endpoints - increased timeout
            "/api/v1/users/": 15.0,  # User operations
            "/api/v1/data/": 60.0,  # Data processing - longer timeout
            "/health": 5.0,  # Health checks - very short
            "/metrics": 5.0,  # Metrics - very short
        }

        # Find matching timeout
        for path_prefix, timeout in endpoint_timeouts.items():
            if path.startswith(path_prefix):
                return timeout

        # Default timeout
        return self.timeout_seconds

    async def _execute_with_timeout_enhanced(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
        timeout: float,
        warning_time: float,
        is_auth_endpoint: bool = False,
    ) -> Response:
        """Execute the request with enhanced timeout and error handling.

        Args:
            request: The incoming request
            call_next: The next middleware or endpoint to call
            timeout: Timeout in seconds
            warning_time: Time in seconds to trigger warning
            is_auth_endpoint: Whether this is an auth endpoint

        Returns:
            Response: The response from the next handler

        """
        try:
            # For auth endpoints, add extra debugging
            if is_auth_endpoint:
                logger.debug(f"Creating task for auth endpoint: {request.url.path}")
            
            # Create the main request task
            request_task = asyncio.create_task(call_next(request))
            
            if is_auth_endpoint:
                logger.debug(f"Request task created successfully for: {request.url.path}")

            # Create warning task
            warning_task = asyncio.create_task(asyncio.sleep(warning_time))

            # Wait for either completion or warning
            done, pending = await asyncio.wait(
                [request_task, warning_task],
                return_when=asyncio.FIRST_COMPLETED,
                timeout=timeout,
            )

            # Cancel pending tasks
            for task in pending:
                task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await task

            # Check if warning triggered
            if warning_task in done and request_task not in done:
                if self.enable_metrics:
                    self.metrics["warning_count"] += 1

                logger.warning(
                    f"Request to {request.method} {request.url.path} is taking longer than expected "
                    f"({warning_time:.1f}s warning threshold, {timeout:.1f}s timeout)",
                )

                # Continue waiting for the actual request
                return await asyncio.wait_for(
                    request_task, timeout=timeout - warning_time,
                )

            # Request completed normally
            if request_task in done:
                if is_auth_endpoint:
                    logger.debug(f"Auth endpoint completed successfully: {request.url.path}")
                return await request_task

            # This shouldn't happen, but handle it
            logger.error(f"Unexpected state in timeout middleware for {request.url.path}")
            raise TimeoutError("Request did not complete within timeout")

        except asyncio.CancelledError:
            logger.error(f"Request was cancelled for {request.url.path}")
            raise
        except Exception as e:
            logger.error(f"Exception in _execute_with_timeout_enhanced for {request.url.path}: {e}")
            logger.error(f"Exception type: {type(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            raise

    def _update_metrics(self, duration: float) -> None:
        """Update performance metrics.

        Args:
            duration: Request duration in seconds

        """
        if not self.enable_metrics or not self.metrics:
            return

        # Update average response time
        total_requests = self.metrics["total_requests"]
        current_avg = self.metrics["avg_response_time"]
        self.metrics["avg_response_time"] = (
            current_avg * (total_requests - 1) + duration
        ) / total_requests

        # Update max response time
        self.metrics["max_response_time"] = max(self.metrics["max_response_time"], duration)

    def get_metrics(self) -> dict[str, Any] | None:
        """Get current timeout metrics.

        Returns:
            Dict with metrics or None if metrics disabled

        """
        if not self.enable_metrics:
            return None

        return {
            **self.metrics,
            "timeout_rate": (
                self.metrics["timeout_count"] / max(self.metrics["total_requests"], 1)
            ),
            "warning_rate": (
                self.metrics["warning_count"] / max(self.metrics["total_requests"], 1)
            ),
        }

    def reset_metrics(self) -> None:
        """Reset all metrics to zero."""
        if self.enable_metrics and self.metrics:
            self.metrics.update(
                {
                    "total_requests": 0,
                    "timeout_count": 0,
                    "warning_count": 0,
                    "avg_response_time": 0.0,
                    "max_response_time": 0.0,
                },
            )
