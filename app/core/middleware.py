"""Core middleware for FastAPI application.

This module provides comprehensive middleware for:
- Response compression (gzip)
- CORS handling
- Security headers
- Request/response logging
- Performance monitoring
"""

import gzip
import json
import time
import uuid
from collections.abc import Callable

from fastapi import Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from loguru import logger
from starlette.middleware.base import BaseHTTPMiddleware

# Import tenant middleware for multi-tenancy support
from app.middleware.tenant_middleware import TenantIsolationMiddleware, TenantMiddleware


class ResponseCompressionMiddleware(BaseHTTPMiddleware):
    """Advanced response compression middleware with configurable compression levels."""

    def __init__(
        self, app, minimum_size: int = 500, compressible_media_types: list | None = None,
    ) -> None:
        super().__init__(app)
        self.minimum_size = minimum_size
        self.compressible_media_types = compressible_media_types or [
            "application/json",
            "application/javascript",
            "text/css",
            "text/html",
            "text/plain",
            "text/xml",
            "application/xml",
            "application/x-javascript",
        ]

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)

        # Check if compression should be applied
        if not self._should_compress(request, response):
            return response

        # Get response body
        response_body = b""
        async for chunk in response.body_iterator:
            response_body += chunk

        # Apply compression if body is large enough
        if len(response_body) >= self.minimum_size:
            compressed_body = gzip.compress(response_body, compresslevel=6)

            # Only use compressed version if it's actually smaller
            if len(compressed_body) < len(response_body):
                response.headers["content-encoding"] = "gzip"
                response.headers["content-length"] = str(len(compressed_body))
                response.body = compressed_body
            else:
                response.body = response_body
        else:
            response.body = response_body

        return response

    def _should_compress(self, request: Request, response: Response) -> bool:
        """Check if response should be compressed."""
        # Check if client accepts gzip
        accept_encoding = request.headers.get("accept-encoding", "")
        if "gzip" not in accept_encoding:
            return False

        # Check content type
        content_type = response.headers.get("content-type", "")
        if not any(ct in content_type for ct in self.compressible_media_types):
            return False

        # Don't compress if already compressed
        return not response.headers.get("content-encoding")


class PerformanceMonitoringMiddleware(BaseHTTPMiddleware):
    """Middleware for monitoring request performance and adding performance headers."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Generate request ID
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id

        # Start timing
        start_time = time.time()

        # Process request
        response = await call_next(request)

        # Calculate processing time
        process_time = time.time() - start_time

        # Add performance headers
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Process-Time"] = f"{process_time:.4f}"
        response.headers["X-Timestamp"] = str(int(time.time()))

        # Log performance metrics
        logger.info(
            "Request processed",
            extra={
                "request_id": request_id,
                "method": request.method,
                "url": str(request.url),
                "status_code": response.status_code,
                "process_time": f"{process_time:.4f}s",
                "user_agent": request.headers.get("user-agent", "unknown"),
            },
        )

        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware for adding security headers to responses."""

    def __init__(self, app, enable_hsts: bool = True) -> None:
        super().__init__(app)
        self.enable_hsts = enable_hsts

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)

        # Security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = (
            "geolocation=(), microphone=(), camera=()"
        )

        # HSTS (only for HTTPS)
        if self.enable_hsts and request.url.scheme == "https":
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains"
            )

        # Content Security Policy - Updated to allow Swagger UI CDN resources
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net; "
            "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
            "img-src 'self' data: https:; "
            "font-src 'self' data: https://cdn.jsdelivr.net; "
            "connect-src 'self'"
        )

        return response


class RateLimitingMiddleware(BaseHTTPMiddleware):
    """Simple in-memory rate limiting middleware.
    For production, consider using Redis-based rate limiting.
    """

    def __init__(self, app, calls: int = 100, period: int = 60) -> None:
        super().__init__(app)
        self.calls = calls
        self.period = period
        self.clients = {}

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        client_ip = self._get_client_ip(request)
        current_time = time.time()

        # Clean old entries
        self._cleanup_old_entries(current_time)

        # Check rate limit
        if self._is_rate_limited(client_ip, current_time):
            return Response(
                content=json.dumps({"error": "Rate limit exceeded"}),
                status_code=429,
                headers={"Content-Type": "application/json"},
            )

        # Record request
        self._record_request(client_ip, current_time)

        return await call_next(request)

    def _get_client_ip(self, request: Request) -> str:
        """Get client IP address."""
        # Check for forwarded IP first (when behind reverse proxy)
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()

        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip

        return request.client.host if request.client else "unknown"

    def _cleanup_old_entries(self, current_time: float) -> None:
        """Remove old entries beyond the time window."""
        cutoff_time = current_time - self.period
        for client_ip in list(self.clients.keys()):
            self.clients[client_ip] = [
                timestamp
                for timestamp in self.clients[client_ip]
                if timestamp > cutoff_time
            ]
            if not self.clients[client_ip]:
                del self.clients[client_ip]

    def _is_rate_limited(self, client_ip: str, current_time: float) -> bool:
        """Check if client has exceeded rate limit."""
        if client_ip not in self.clients:
            return False

        return len(self.clients[client_ip]) >= self.calls

    def _record_request(self, client_ip: str, current_time: float) -> None:
        """Record request timestamp for client."""
        if client_ip not in self.clients:
            self.clients[client_ip] = []

        self.clients[client_ip].append(current_time)


def setup_middleware(app) -> None:
    """Set up all middleware for the FastAPI application."""
    # Multi-tenancy middleware (should be early in the chain)
    app.add_middleware(TenantIsolationMiddleware)
    app.add_middleware(TenantMiddleware)

    # CORS middleware (should be first after tenant middleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure appropriately for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID", "X-Process-Time"],
    )

    # Security headers middleware
    app.add_middleware(SecurityHeadersMiddleware, enable_hsts=True)

    # Rate limiting middleware (configure limits as needed)
    app.add_middleware(RateLimitingMiddleware, calls=1000, period=60)

    # Performance monitoring middleware
    app.add_middleware(PerformanceMonitoringMiddleware)

    # Response compression middleware
    # Note: Using FastAPI's built-in GZipMiddleware for simplicity
    # For more control, use custom ResponseCompressionMiddleware above
    app.add_middleware(GZipMiddleware, minimum_size=1000)

    logger.info(
        "Middleware setup completed: CORS, Security, Rate Limiting, Performance, Compression",
    )
