"""Enhanced Rate limiting implementation using slowapi and Redis.

This module provides robust rate limiting functionality using the slowapi library
with Redis as the backend for distributed rate limiting, including fallback mechanisms
and comprehensive error handling.
"""

import asyncio
import logging
import os
import time
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any

import redis.asyncio as redis
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

# Configure logging
logger = logging.getLogger(__name__)


# Rate limiting configuration
@dataclass
class RateLimitConfig:
    """Configuration for rate limiting."""

    redis_url: str = "redis://localhost:6379/0"
    default_limit: str = "100/minute"
    enable_fallback: bool = True
    fallback_limit: int = 50  # Per minute when Redis is down
    redis_timeout: int = 5
    redis_retry_attempts: int = 3
    redis_retry_delay: float = 0.5
    enable_metrics: bool = True
    key_prefix: str = "rate_limit"
    cleanup_interval: int = 3600  # Clean up old entries every hour


class RateLimitStatus(Enum):
    """Rate limit check status."""

    ALLOWED = "allowed"
    EXCEEDED = "exceeded"
    ERROR = "error"
    FALLBACK = "fallback"


@dataclass
class RateLimitResult:
    """Result of rate limit check."""

    status: RateLimitStatus
    allowed: bool
    limit: int
    remaining: int
    reset_time: int
    retry_after: int
    error_message: str | None = None


class InMemoryFallback:
    """In-memory fallback for rate limiting when Redis is unavailable."""

    def __init__(self, cleanup_interval: int = 3600) -> None:
        self._storage: dict[str, list[float]] = {}
        self._cleanup_interval = cleanup_interval
        self._last_cleanup = time.time()
        self._lock = asyncio.Lock()

    async def check_rate_limit(
        self, key: str, limit: int, window: int,
    ) -> RateLimitResult:
        """Check rate limit using in-memory storage."""
        async with self._lock:
            current_time = time.time()

            # Cleanup old entries periodically
            if current_time - self._last_cleanup > self._cleanup_interval:
                await self._cleanup_old_entries(current_time)
                self._last_cleanup = current_time

            # Get or create entry
            if key not in self._storage:
                self._storage[key] = []

            timestamps = self._storage[key]

            # Remove old timestamps outside the window
            cutoff_time = current_time - window
            timestamps[:] = [ts for ts in timestamps if ts > cutoff_time]

            # Check if limit is exceeded
            if len(timestamps) >= limit:
                # Find the oldest timestamp to calculate retry_after
                oldest_timestamp = min(timestamps) if timestamps else current_time
                retry_after = int(oldest_timestamp + window - current_time)
                retry_after = max(retry_after, 1)  # At least 1 second

                return RateLimitResult(
                    status=RateLimitStatus.FALLBACK,
                    allowed=False,
                    limit=limit,
                    remaining=0,
                    reset_time=int(oldest_timestamp + window),
                    retry_after=retry_after,
                )

            # Add current timestamp
            timestamps.append(current_time)
            remaining = limit - len(timestamps)

            return RateLimitResult(
                status=RateLimitStatus.FALLBACK,
                allowed=True,
                limit=limit,
                remaining=remaining,
                reset_time=int(current_time + window),
                retry_after=0,
            )

    async def _cleanup_old_entries(self, current_time: float) -> None:
        """Clean up old entries to prevent memory leaks."""
        try:
            # Remove entries older than 1 hour
            cutoff_time = current_time - 3600
            keys_to_remove = []

            for key, timestamps in self._storage.items():
                # Filter out old timestamps
                self._storage[key] = [ts for ts in timestamps if ts > cutoff_time]

                # Remove empty entries
                if not self._storage[key]:
                    keys_to_remove.append(key)

            for key in keys_to_remove:
                del self._storage[key]

            logger.debug(f"Cleaned up {len(keys_to_remove)} empty rate limit entries")

        except Exception as e:
            logger.exception(f"Error during rate limit cleanup: {e}")


class EnhancedRateLimiter:
    """Enhanced rate limiter with robust error handling and fallback mechanisms."""

    def __init__(self, config: RateLimitConfig) -> None:
        self.config = config
        self.redis_client: redis.Redis | None = None
        self.fallback = (
            InMemoryFallback(config.cleanup_interval)
            if config.enable_fallback
            else None
        )
        self._redis_healthy = False
        self._last_health_check = 0
        self._health_check_interval = 30  # Check Redis health every 30 seconds
        self._metrics = {
            "total_requests": 0,
            "redis_requests": 0,
            "fallback_requests": 0,
            "errors": 0,
            "rate_limited": 0,
        }

    async def initialize(self) -> bool:
        """Initialize Redis connection with retry logic."""
        for attempt in range(self.config.redis_retry_attempts):
            try:
                self.redis_client = redis.Redis.from_url(
                    self.config.redis_url,
                    encoding="utf-8",
                    decode_responses=True,
                    socket_connect_timeout=self.config.redis_timeout,
                    socket_keepalive=True,
                    retry_on_timeout=True,
                    health_check_interval=30,
                )

                # Test the connection
                await asyncio.wait_for(
                    self.redis_client.ping(), timeout=self.config.redis_timeout,
                )

                self._redis_healthy = True
                logger.info("Successfully connected to Redis for rate limiting")
                return True

            except Exception as e:
                logger.warning(
                    f"Failed to connect to Redis (attempt {attempt + 1}/{self.config.redis_retry_attempts}): {e}",
                )
                if attempt < self.config.redis_retry_attempts - 1:
                    await asyncio.sleep(
                        self.config.redis_retry_delay * (2**attempt),
                    )  # Exponential backoff

        self._redis_healthy = False
        logger.error("Failed to connect to Redis after all attempts")

        if not self.config.enable_fallback:
            msg = "Redis connection failed and fallback is disabled"
            raise ConnectionError(msg)

        logger.warning("Using in-memory fallback for rate limiting")
        return False

    async def _check_redis_health(self) -> bool:
        """Check Redis health with caching to avoid frequent health checks."""
        current_time = time.time()

        # Use cached health status if within interval
        if current_time - self._last_health_check < self._health_check_interval:
            return self._redis_healthy

        if not self.redis_client:
            self._redis_healthy = False
            self._last_health_check = current_time
            return False

        try:
            await asyncio.wait_for(
                self.redis_client.ping(),
                timeout=2.0,  # Quick health check
            )
            self._redis_healthy = True

        except Exception as e:
            logger.warning(f"Redis health check failed: {e}")
            self._redis_healthy = False

        self._last_health_check = current_time
        return self._redis_healthy

    async def check_rate_limit(
        self, key: str, limit: int, window: int,
    ) -> RateLimitResult:
        """Check rate limit with Redis or fallback to in-memory."""
        self._metrics["total_requests"] += 1

        # Try Redis first if healthy
        if await self._check_redis_health():
            try:
                result = await self._check_redis_rate_limit(key, limit, window)
                self._metrics["redis_requests"] += 1
                return result

            except Exception as e:
                logger.exception(f"Redis rate limit check failed: {e}")
                self._metrics["errors"] += 1
                self._redis_healthy = False  # Mark as unhealthy for faster fallback

        # Use fallback if Redis failed or is unhealthy
        if self.fallback:
            logger.debug(f"Using fallback rate limiting for key: {key}")
            result = await self.fallback.check_rate_limit(key, limit, window)
            self._metrics["fallback_requests"] += 1
            return result

        # No fallback available - allow the request but log the issue
        logger.error("Rate limiting unavailable - allowing request")
        return RateLimitResult(
            status=RateLimitStatus.ERROR,
            allowed=True,  # Fail open for better user experience
            limit=limit,
            remaining=limit,
            reset_time=int(time.time() + window),
            retry_after=0,
            error_message="Rate limiting service unavailable",
        )

    async def _check_redis_rate_limit(
        self, key: str, limit: int, window: int,
    ) -> RateLimitResult:
        """Check rate limit using Redis with sliding window."""
        if not self.redis_client:
            msg = "Redis client not initialized"
            raise ConnectionError(msg)

        current_time = time.time()
        window_start = current_time - window

        # Use Redis pipeline for atomic operations
        pipe = self.redis_client.pipeline()

        try:
            # Remove expired entries
            pipe.zremrangebyscore(key, 0, window_start)

            # Count current entries
            pipe.zcard(key)

            # Add current timestamp
            pipe.zadd(key, {str(current_time): current_time})

            # Set expiration for cleanup
            pipe.expire(key, window + 60)  # Extra buffer for cleanup

            # Execute pipeline
            results = await pipe.execute()
            current_count = results[1]  # Count after removing expired entries

            if current_count >= limit:
                # Get oldest entry to calculate retry_after
                oldest_entries = await self.redis_client.zrange(
                    key, 0, 0, withscores=True,
                )
                if oldest_entries:
                    oldest_time = oldest_entries[0][1]
                    retry_after = int(oldest_time + window - current_time)
                    retry_after = max(retry_after, 1)
                else:
                    retry_after = window

                # Remove the entry we just added since we're rejecting
                await self.redis_client.zrem(key, str(current_time))

                self._metrics["rate_limited"] += 1

                return RateLimitResult(
                    status=RateLimitStatus.EXCEEDED,
                    allowed=False,
                    limit=limit,
                    remaining=0,
                    reset_time=int(oldest_time + window)
                    if oldest_entries
                    else int(current_time + window),
                    retry_after=retry_after,
                )

            remaining = limit - (current_count + 1)  # +1 for the current request

            return RateLimitResult(
                status=RateLimitStatus.ALLOWED,
                allowed=True,
                limit=limit,
                remaining=remaining,
                reset_time=int(current_time + window),
                retry_after=0,
            )

        except redis.RedisError as e:
            # If Redis fails, don't add the entry and re-raise
            logger.exception(f"Redis pipeline failed: {e}")
            raise

    async def cleanup(self) -> None:
        """Cleanup resources."""
        try:
            if self.redis_client:
                await self.redis_client.close()
                logger.info("Redis connection closed")
        except Exception as e:
            logger.exception(f"Error closing Redis connection: {e}")

    def get_metrics(self) -> dict[str, Any]:
        """Get rate limiting metrics."""
        return {
            **self._metrics,
            "redis_healthy": self._redis_healthy,
            "fallback_enabled": self.config.enable_fallback,
            "timestamp": time.time(),
        }


# Global rate limiter instance
_rate_limiter: EnhancedRateLimiter | None = None


def get_rate_limit_key(request: Request) -> str:
    """Generate a rate limit key based on the client's IP and the endpoint being accessed.

    Args:
        request: The incoming request

    Returns:
        str: A string key for rate limiting

    """
    try:
        # Get client IP (handle proxies)
        client_ip = request.headers.get("x-forwarded-for")
        if client_ip:
            # Take the first IP in case of multiple proxies
            client_ip = client_ip.split(",")[0].strip()
        else:
            client_ip = get_remote_address(request)

        # Get the endpoint path
        endpoint = request.url.path

        # Include method for different rate limits per method if needed
        method = request.method

        # Generate a key with prefix for namespacing
        config = get_rate_limit_config()
        return f"{config.key_prefix}:{client_ip}:{method}:{endpoint}"

    except Exception as e:
        logger.exception(f"Error generating rate limit key: {e!s}")
        # Fallback to a simple key if there's an error
        return f"{get_rate_limit_config().key_prefix}:error:{id(request)}"


def get_rate_limit_config() -> RateLimitConfig:
    """Get rate limiting configuration from environment variables."""
    try:
        from app.core.config import get_settings

        settings = get_settings()

        return RateLimitConfig(
            redis_url=getattr(settings, "REDIS_URL", "redis://localhost:6379/0"),
            default_limit=os.getenv("RATE_LIMIT_DEFAULT", "100/minute"),
            enable_fallback=os.getenv("RATE_LIMIT_ENABLE_FALLBACK", "true").lower()
            == "true",
            fallback_limit=int(os.getenv("RATE_LIMIT_FALLBACK_LIMIT", "50")),
            redis_timeout=int(os.getenv("RATE_LIMIT_REDIS_TIMEOUT", "5")),
            redis_retry_attempts=int(os.getenv("RATE_LIMIT_REDIS_RETRY_ATTEMPTS", "3")),
            redis_retry_delay=float(os.getenv("RATE_LIMIT_REDIS_RETRY_DELAY", "0.5")),
            enable_metrics=os.getenv("RATE_LIMIT_ENABLE_METRICS", "true").lower()
            == "true",
            key_prefix=os.getenv("RATE_LIMIT_KEY_PREFIX", "rate_limit"),
            cleanup_interval=int(os.getenv("RATE_LIMIT_CLEANUP_INTERVAL", "3600")),
        )
    except Exception as e:
        logger.warning(f"Error loading rate limit config, using defaults: {e}")
        return RateLimitConfig()


def get_rate_limits() -> dict[str, str]:
    """Get the default rate limits for different endpoints.

    Returns:
        Dict[str, str]: A dictionary mapping endpoint patterns to rate limits

    """
    return {
        # Default rate limit
        "default": os.getenv("RATE_LIMIT_DEFAULT", "100/minute"),
        # Authentication endpoints (stricter limits)
        "/api/v1/auth/login": os.getenv("RATE_LIMIT_AUTH_LOGIN", "10/minute"),
        "/api/v1/auth/register": os.getenv("RATE_LIMIT_AUTH_REGISTER", "5/minute"),
        "/api/v1/auth/forgot-password": os.getenv("RATE_LIMIT_AUTH_FORGOT", "3/minute"),
        "/api/v1/auth/reset-password": os.getenv("RATE_LIMIT_AUTH_RESET", "3/minute"),
        "/api/v1/auth/refresh": os.getenv("RATE_LIMIT_AUTH_REFRESH", "20/minute"),
        # API endpoints
        "/api/v1/users": os.getenv("RATE_LIMIT_USERS", "50/minute"),
        "/api/v1/organizations": os.getenv("RATE_LIMIT_ORGS", "30/minute"),
        # Public endpoints (more generous limits)
        "/api/v1/public": os.getenv("RATE_LIMIT_PUBLIC", "200/minute"),
        # Health checks (very generous)
        "/health": "1000/minute",
        "/metrics": "100/minute",
        # Test endpoints (stricter limits)
        "/api/v1/test/rate-limit": "5/minute",
    }


def parse_rate_limit(rate_limit_str: str) -> tuple[int, int]:
    """Parse a rate limit string like '100/minute' into (limit, window_seconds).

    Args:
        rate_limit_str: Rate limit string (e.g., "100/minute", "10/second")

    Returns:
        tuple: (limit, window_in_seconds)

    """
    try:
        parts = rate_limit_str.split("/")
        if len(parts) != 2:
            msg = f"Invalid rate limit format: {rate_limit_str}"
            raise ValueError(msg)

        limit = int(parts[0])
        period = parts[1].lower()

        period_map = {"second": 1, "minute": 60, "hour": 3600, "day": 86400}

        if period not in period_map:
            msg = f"Invalid period: {period}"
            raise ValueError(msg)

        return limit, period_map[period]

    except Exception as e:
        logger.exception(f"Error parsing rate limit '{rate_limit_str}': {e}")
        # Return a safe default
        return 100, 60  # 100 per minute


def get_endpoint_rate_limit(request: Request) -> tuple[int, int]:
    """Determine the rate limit for the current endpoint.

    Args:
        request: The incoming request

    Returns:
        tuple: (limit, window_in_seconds)

    """
    # Get the endpoint path
    path = request.url.path

    # Get the rate limits configuration
    rate_limits = get_rate_limits()

    # Check for exact matches first
    if path in rate_limits:
        return parse_rate_limit(rate_limits[path])

    # Check for path prefixes
    for endpoint, limit_str in rate_limits.items():
        if path.startswith(endpoint):
            return parse_rate_limit(limit_str)

    # Return default rate limit
    return parse_rate_limit(rate_limits["default"])


async def enhanced_rate_limit_exceeded_handler(
    request: Request, exc: RateLimitExceeded,
) -> JSONResponse:
    """Enhanced handler for rate limit exceeded errors with detailed information.

    Args:
        request: The incoming request
        exc: The rate limit exception

    Returns:
        JSONResponse: A 429 response with comprehensive rate limit information

    """
    try:
        # Get rate limit details if available
        retry_after = getattr(exc, "retry_after", 60)
        detail = getattr(exc, "detail", "Rate limit exceeded")

        # Get additional context
        endpoint = request.url.path
        method = request.method
        client_ip = request.headers.get("x-forwarded-for", get_remote_address(request))

        # Log the rate limit event
        logger.warning(
            f"Rate limit exceeded - IP: {client_ip}, Endpoint: {method} {endpoint}, "
            f"Retry after: {retry_after}s",
        )

        # Get current rate limit for this endpoint
        limit, window = get_endpoint_rate_limit(request)

        response_data = {
            "detail": str(detail),
            "error": "rate_limit_exceeded",
            "error_code": "RATE_LIMIT_EXCEEDED",
            "retry_after": retry_after,
            "limit": limit,
            "window": window,
            "endpoint": endpoint,
            "timestamp": datetime.utcnow().isoformat(),
            "suggestion": f"Please wait {retry_after} seconds before making another request to this endpoint",
        }

        headers = {
            "Retry-After": str(retry_after),
            "X-RateLimit-Limit": str(limit),
            "X-RateLimit-Remaining": "0",
            "X-RateLimit-Reset": str(int(time.time() + retry_after)),
            "X-RateLimit-Window": str(window),
        }

        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content=response_data,
            headers=headers,
        )

    except Exception as e:
        logger.error(f"Error in enhanced rate limit handler: {e!s}", exc_info=True)
        # Fallback response if something goes wrong
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={
                "detail": "Rate limit exceeded",
                "error": "rate_limit_exceeded",
                "retry_after": 60,
                "timestamp": datetime.utcnow().isoformat(),
            },
            headers={"Retry-After": "60"},
        )


async def setup_rate_limiting(app: FastAPI) -> None:
    """Set up enhanced rate limiting for the FastAPI application.

    DEPRECATED: This function tries to add middleware during startup which causes warnings.
    Use initialize_enhanced_rate_limiter() instead for startup initialization.

    This function:
    1. Initializes the enhanced rate limiter with Redis/fallback
    2. Adds rate limiting middleware (CAUSES WARNING - should be done during app creation)
    3. Adds exception handlers for rate limiting
    4. Sets up cleanup on shutdown

    Args:
        app: The FastAPI application instance

    """
    global _rate_limiter

    try:
        # Get configuration
        config = get_rate_limit_config()
        logger.info(
            f"Setting up rate limiting with config: Redis={config.redis_url}, Fallback={config.enable_fallback}",
        )

        # Initialize enhanced rate limiter
        _rate_limiter = EnhancedRateLimiter(config)

        # Initialize on startup
        @app.on_event("startup")
        async def startup_rate_limiting() -> None:
            try:
                await _rate_limiter.initialize()
                logger.info("Enhanced rate limiting initialized successfully")

                # Store in app state for access in endpoints
                app.state.rate_limiter = _rate_limiter

            except Exception as e:
                logger.exception(f"Failed to initialize rate limiting: {e}")
                if not config.enable_fallback:
                    raise
                logger.warning("Continuing with fallback rate limiting only")

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

        # Add middleware - THIS CAUSES THE WARNING when called during startup
        from slowapi.middleware import SlowAPIMiddleware

        app.add_middleware(SlowAPIMiddleware)

        # Add cleanup on shutdown
        @app.on_event("shutdown")
        async def shutdown_rate_limiting() -> None:
            try:
                if _rate_limiter:
                    await _rate_limiter.cleanup()
                logger.info("Rate limiting cleanup completed")
            except Exception as e:
                logger.exception(f"Error during rate limiting cleanup: {e}")

        logger.info("Rate limiting setup completed successfully")

    except Exception as e:
        logger.exception(f"Failed to setup rate limiting: {e}")
        if not get_rate_limit_config().enable_fallback:
            raise
        logger.warning("Rate limiting setup failed but fallback is enabled")


async def initialize_enhanced_rate_limiter(
    config: RateLimitConfig | None = None,
) -> EnhancedRateLimiter:
    """Initialize only the enhanced rate limiter (without middleware setup).

    This function should be called during startup events, while middleware
    should be added during app creation.

    Args:
        config: Rate limiting configuration, uses default if None

    Returns:
        The initialized enhanced rate limiter

    Raises:
        Exception if initialization fails and fallback is disabled

    """
    global _rate_limiter

    if config is None:
        config = get_rate_limit_config()

    try:
        logger.info(
            f"Initializing enhanced rate limiter with config: Redis={config.redis_url}, Fallback={config.enable_fallback}",
        )

        # Initialize enhanced rate limiter
        _rate_limiter = EnhancedRateLimiter(config)
        await _rate_limiter.initialize()

        logger.info("Enhanced rate limiting initialized successfully")
        return _rate_limiter

    except Exception as e:
        logger.exception(f"Failed to initialize enhanced rate limiting: {e}")
        if not config.enable_fallback:
            raise
        logger.warning("Enhanced rate limiting failed, fallback available")
        raise


def get_rate_limiter() -> EnhancedRateLimiter | None:
    """Get the enhanced rate limiter instance for use in dependencies.

    Returns:
        The enhanced rate limiter instance or None if not initialized

    """
    return _rate_limiter


# Dependency for getting rate limiter in endpoints
async def get_rate_limiter_dependency() -> EnhancedRateLimiter | None:
    """FastAPI dependency for getting the rate limiter."""
    return get_rate_limiter()


# Export rate limit decorator for specific endpoints
def rate_limit(limit_str: str):
    """Decorator for applying specific rate limits to endpoints.

    Args:
        limit_str: Rate limit string (e.g., "10/minute")

    Returns:
        Decorated function

    """

    def decorator(func):
        func.__rate_limit__ = limit_str
        return func

    return decorator
