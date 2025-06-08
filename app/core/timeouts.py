"""Request and operation timeout configurations.

This module provides timeout configurations and utilities for various operations
in the application, including HTTP requests, database queries, and other async operations.
"""

import asyncio
import logging
from collections.abc import AsyncGenerator, Awaitable, Callable
from contextlib import asynccontextmanager
from functools import wraps
from typing import Any, TypeVar

from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.exc import TimeoutError as SQLTimeoutError

logger = logging.getLogger(__name__)

# Type variable for generic function wrapping
T = TypeVar("T")

# Default timeout values (in seconds)
DEFAULT_TIMEOUT = 30.0  # 30 seconds default timeout
DATABASE_TIMEOUT = 10.0  # 10 seconds for database operations
EXTERNAL_API_TIMEOUT = 15.0  # 15 seconds for external API calls
HEAVY_COMPUTATION_TIMEOUT = 60.0  # 60 seconds for heavy computations


class TimeoutException(HTTPException):
    """Custom exception for timeout scenarios."""

    def __init__(
        self,
        detail: str = "Request timed out",
        status_code: int = status.HTTP_504_GATEWAY_TIMEOUT,
        headers: dict | None = None,
    ) -> None:
        super().__init__(
            status_code=status_code,
            detail=detail,
            headers=headers or {"Retry-After": "30"},
        )


async def timeout_middleware(request: Request, call_next):
    """Global request timeout middleware.

    This middleware enforces a maximum request processing time.
    If the request takes longer than the configured timeout,
    it will be aborted with a 504 Gateway Timeout response.
    """
    try:
        # Get the route-specific timeout or use default
        route_timeout = getattr(
            request.scope.get("endpoint"), "timeout_seconds", DEFAULT_TIMEOUT,
        )

        # Process the request with timeout
        return await asyncio.wait_for(call_next(request), timeout=route_timeout)

    except TimeoutError:
        logger.warning(
            f"Request timed out after {DEFAULT_TIMEOUT} seconds: {request.method} {request.url}",
            extra={"path": request.url.path, "method": request.method},
        )
        return JSONResponse(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            content={"detail": f"Request timed out after {DEFAULT_TIMEOUT} seconds"},
            headers={"Retry-After": "30"},
        )


def timeout(seconds: float = DEFAULT_TIMEOUT) -> Callable:
    """Decorator to set a custom timeout for a specific endpoint.

    Example:
        @router.get("/slow-endpoint")
        @timeout(60)  # 60 seconds timeout for this endpoint
        async def slow_endpoint():
            # Your code here
            pass

    """

    def decorator(func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            try:
                return await asyncio.wait_for(func(*args, **kwargs), timeout=seconds)
            except TimeoutError:
                logger.warning(
                    f"Operation timed out after {seconds} seconds: {func.__name__}",
                    extra={"function": func.__name__, "timeout_seconds": seconds},
                )
                raise TimeoutException(
                    detail=f"Operation timed out after {seconds} seconds",
                )

        # Store the timeout on the function for the middleware to access
        wrapper.timeout_seconds = seconds
        return wrapper

    return decorator


@asynccontextmanager
async def database_timeout_context(
    seconds: float = DATABASE_TIMEOUT,
) -> AsyncGenerator[None]:
    """Context manager for database operations with timeout.

    Example:
        async with database_timeout_context(5.0):  # 5 second timeout
            result = await db.execute(query)

    """
    try:
        yield
    except TimeoutError:
        logger.exception("Database operation timed out", extra={"timeout_seconds": seconds})
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Database operation timed out",
        )
    except SQLTimeoutError:
        logger.exception("Database query timed out", extra={"timeout_seconds": seconds})
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Database query timed out",
        )


def with_timeout(
    func: Callable[..., Awaitable[T]] | None = None,
    *,
    timeout_seconds: float = DEFAULT_TIMEOUT,
    exception_type: type[Exception] = TimeoutException,
    error_message: str = "Operation timed out",
) -> Callable[..., Awaitable[T]]:
    """Generic decorator to add timeout to any async function.

    Args:
        timeout_seconds: Maximum time to wait for the function to complete
        exception_type: Exception to raise on timeout
        error_message: Error message for the exception

    Returns:
        The result of the decorated function or raises an exception on timeout

    Example:
        @with_timeout(timeout_seconds=5.0)
        async def fetch_data():
            # Your code here
            pass

    """

    def decorator(f: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        @wraps(f)
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            try:
                return await asyncio.wait_for(
                    f(*args, **kwargs), timeout=timeout_seconds,
                )
            except TimeoutError:
                logger.warning(
                    f"{f.__name__} timed out after {timeout_seconds} seconds",
                    extra={
                        "function": f.__name__,
                        "timeout_seconds": timeout_seconds,
                        "args": str(args)[:200],
                        "kwargs": str(kwargs)[:200],
                    },
                )
                raise exception_type(detail=error_message) from None

        return wrapper

    if func is None:
        return decorator
    return decorator(func)


# Common timeout configurations
class Timeouts:
    """Predefined timeout configurations for common operations."""

    DATABASE = DATABASE_TIMEOUT
    EXTERNAL_API = EXTERNAL_API_TIMEOUT
    HEAVY_COMPUTATION = HEAVY_COMPUTATION_TIMEOUT
    DEFAULT = DEFAULT_TIMEOUT
