"""
Request timeout middleware for FastAPI.

This module provides middleware for enforcing request timeouts at the application level.
It works in conjunction with the timeout utilities in app.core.timeouts.
"""
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.types import ASGIApp
import asyncio
import logging
import time
from typing import Optional, Dict, Any

from app.core.timeouts import DEFAULT_TIMEOUT, TimeoutException

logger = logging.getLogger(__name__)

class TimeoutMiddleware(BaseHTTPMiddleware):
    """
    Enhanced middleware that enforces request timeouts with metrics and escalation.
    
    Features:
    - Global and per-endpoint timeout configuration
    - Timeout escalation warnings
    - Metrics collection
    - Detailed error responses
    - Performance monitoring
    """
    
    def __init__(
        self,
        app: ASGIApp,
        timeout_seconds: float = DEFAULT_TIMEOUT,
        timeout_response: Optional[Dict[str, Any]] = None,
        warning_threshold: float = 0.8,
        enable_metrics: bool = True,
    ) -> None:
        """Initialize the enhanced timeout middleware.
        
        Args:
            app: The ASGI application
            timeout_seconds: Global timeout in seconds (default: 30s)
            timeout_response: Custom response for timeout errors
            warning_threshold: Fraction of timeout to trigger warning (default: 0.8 = 80%)
            enable_metrics: Whether to collect timeout metrics
        """
        super().__init__(app)
        self.timeout_seconds = timeout_seconds
        self.warning_threshold = warning_threshold
        self.enable_metrics = enable_metrics
        self.timeout_response = timeout_response or {
            "detail": f"Request timed out after {timeout_seconds} seconds",
            "error_code": "REQUEST_TIMEOUT",
            "timeout_seconds": timeout_seconds
        }
        
        # Metrics collection
        self.metrics = {
            "total_requests": 0,
            "timeout_count": 0,
            "warning_count": 0,
            "avg_response_time": 0.0,
            "max_response_time": 0.0,
        } if enable_metrics else None
    
    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        """
        Process the request with enhanced timeout enforcement and monitoring.
        
        Args:
            request: The incoming request
            call_next: The next middleware or endpoint to call
            
        Returns:
            Response: The response from the next handler or timeout error
        """
        start_time = time.monotonic()
        
        # Get endpoint-specific timeout if configured
        endpoint_timeout = self._get_endpoint_timeout(request)
        
        try:
            if self.enable_metrics:
                self.metrics["total_requests"] += 1
            
            # Create timeout task with warning
            warning_time = endpoint_timeout * self.warning_threshold
            
            # Execute request with timeout
            response = await self._execute_with_timeout(
                request, call_next, endpoint_timeout, warning_time
            )
            
            # Update metrics
            duration = time.monotonic() - start_time
            if self.enable_metrics:
                self._update_metrics(duration)
            
            # Add timeout headers
            response.headers["X-Request-Duration"] = f"{duration:.3f}"
            response.headers["X-Timeout-Limit"] = str(endpoint_timeout)
            
            return response
            
        except asyncio.TimeoutError:
            duration = time.monotonic() - start_time
            if self.enable_metrics:
                self.metrics["timeout_count"] += 1
            
            logger.warning(
                f"Request to {request.method} {request.url.path} timed out after {duration:.2f}s "
                f"(limit: {endpoint_timeout}s)"
            )
            
            return JSONResponse(
                status_code=504,
                content={
                    **self.timeout_response,
                    "actual_duration": round(duration, 2),
                    "method": request.method,
                    "path": str(request.url.path),
                    "timestamp": time.time()
                },
                headers={
                    "X-Request-Duration": f"{duration:.3f}",
                    "X-Timeout-Limit": str(endpoint_timeout),
                    "Retry-After": "60"  # Suggest retry after 60 seconds
                }
            )
            
        except Exception as exc:
            duration = time.monotonic() - start_time
            logger.error(f"Error in timeout middleware for {request.url}: {exc}")
            
            return JSONResponse(
                status_code=500,
                content={
                    "detail": "Internal server error during timeout handling",
                    "error_code": "TIMEOUT_MIDDLEWARE_ERROR",
                    "duration": round(duration, 2)
                }
            )

    def _get_endpoint_timeout(self, request: Request) -> float:
        """
        Get the timeout for a specific endpoint.
        
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
            "/api/v1/auth/": 10.0,  # Auth endpoints - shorter timeout
            "/api/v1/users/": 15.0,  # User operations
            "/api/v1/data/": 60.0,   # Data processing - longer timeout
            "/health": 5.0,          # Health checks - very short
            "/metrics": 5.0,         # Metrics - very short
        }
        
        # Find matching timeout
        for path_prefix, timeout in endpoint_timeouts.items():
            if path.startswith(path_prefix):
                return timeout
        
        # Default timeout
        return self.timeout_seconds
    
    async def _execute_with_timeout(
        self, 
        request: Request, 
        call_next: RequestResponseEndpoint, 
        timeout: float, 
        warning_time: float
    ) -> Response:
        """
        Execute the request with timeout and warning monitoring.
        
        Args:
            request: The incoming request
            call_next: The next middleware or endpoint to call
            timeout: Timeout in seconds
            warning_time: Time in seconds to trigger warning
            
        Returns:
            Response: The response from the next handler
        """
        # Create the main request task
        request_task = asyncio.create_task(call_next(request))
        
        # Create warning task
        warning_task = asyncio.create_task(asyncio.sleep(warning_time))
        
        try:
            # Wait for either completion or warning
            done, pending = await asyncio.wait(
                [request_task, warning_task],
                return_when=asyncio.FIRST_COMPLETED,
                timeout=timeout
            )
            
            # Cancel pending tasks
            for task in pending:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
            
            # Check if warning triggered
            if warning_task in done and request_task not in done:
                if self.enable_metrics:
                    self.metrics["warning_count"] += 1
                
                logger.warning(
                    f"Request to {request.method} {request.url.path} is taking longer than expected "
                    f"({warning_time:.1f}s warning threshold, {timeout:.1f}s timeout)"
                )
                
                # Continue waiting for the actual request
                return await asyncio.wait_for(request_task, timeout=timeout - warning_time)
            
            # Request completed normally
            if request_task in done:
                return await request_task
            
            # This shouldn't happen, but handle it
            raise asyncio.TimeoutError()
            
        except asyncio.TimeoutError:
            # Cancel the request task
            request_task.cancel()
            try:
                await request_task
            except asyncio.CancelledError:
                pass
            raise
    
    def _update_metrics(self, duration: float) -> None:
        """
        Update performance metrics.
        
        Args:
            duration: Request duration in seconds
        """
        if not self.enable_metrics or not self.metrics:
            return
        
        # Update average response time
        total_requests = self.metrics["total_requests"]
        current_avg = self.metrics["avg_response_time"]
        self.metrics["avg_response_time"] = (
            (current_avg * (total_requests - 1) + duration) / total_requests
        )
        
        # Update max response time
        if duration > self.metrics["max_response_time"]:
            self.metrics["max_response_time"] = duration
    
    def get_metrics(self) -> Optional[Dict[str, Any]]:
        """
        Get current timeout metrics.
        
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
            )
        }
    
    def reset_metrics(self) -> None:
        """Reset all metrics to zero."""
        if self.enable_metrics and self.metrics:
            self.metrics.update({
                "total_requests": 0,
                "timeout_count": 0,
                "warning_count": 0,
                "avg_response_time": 0.0,
                "max_response_time": 0.0,
            })
