"""Test endpoints for rate limiting functionality.

This module provides endpoints to test different rate limiting scenarios.
"""

import logging
import time
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.rate_limiting import (
    get_endpoint_rate_limit,
    get_rate_limit_key,
    get_rate_limiter_dependency,
    rate_limit,
)

# Set up logger
logger = logging.getLogger(__name__)

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)


@router.get(
    "/test/rate-limit",
    summary="Test rate limiting",
    description="Endpoint to test rate limiting functionality.",
    response_model=dict[str, Any],
    responses={
        200: {"description": "Rate limit test successful"},
        429: {"description": "Rate limit exceeded"},
        500: {"description": "Internal server error"},
    },
)
@limiter.limit("5/minute")  # Strict rate limit for testing
async def test_rate_limit(request: Request):
    """Test endpoint for rate limiting.

    This endpoint has a strict rate limit of 5 requests per minute for testing purposes.
    """
    try:
        # Simple response to test if the endpoint works at all
        return {
            "message": "Rate limit test successful. This endpoint is rate limited to 5 requests per minute.",
            "status": "success",
            "client_ip": request.client.host if request.client else "unknown",
        }
    except Exception as e:
        logger.error(f"Error in rate limit test endpoint: {e!s}", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "detail": "An error occurred while processing your request.",
                "error": str(e),
            },
        )


@router.get(
    "/test/no-rate-limit",
    summary="Test without rate limiting",
    description="Endpoint without rate limiting for comparison.",
    response_model=dict[str, str],
    responses={
        200: {"description": "Request successful"},
        500: {"description": "Internal server error"},
    },
)
async def test_no_rate_limit(request: Request):
    """Test endpoint without rate limiting.

    This endpoint has no rate limiting applied for comparison testing.
    """
    try:
        client_ip = request.client.host if request.client else "unknown"
        logger.info(f"No rate limit test request from {client_ip}")

        return {
            "message": "This endpoint has no rate limiting applied.",
            "status": "success",
            "client_ip": client_ip,
            "note": "This endpoint is not rate limited for testing purposes",
        }
    except Exception as e:
        logger.error(f"Error in no-rate-limit test endpoint: {e!s}", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "detail": "An error occurred while processing your request.",
                "error": str(e),
            },
        )


@router.get("/basic-test")
@limiter.limit("5/minute")  # 5 requests per minute
async def basic_rate_limit_test(request: Request):
    """Basic rate limiting test endpoint.
    Limited to 5 requests per minute per IP.
    """
    return {
        "message": "Rate limiting test successful!",
        "timestamp": time.time(),
        "endpoint": "/test/rate-limit/basic-test",
        "limit": "5/minute",
    }


@router.get("/enhanced-test")
async def enhanced_rate_limit_test(
    request: Request, rate_limiter=Depends(get_rate_limiter_dependency),
):
    """Enhanced rate limiting test using our custom rate limiter.
    Tests the EnhancedRateLimiter directly.
    """
    if not rate_limiter:
        return {
            "message": "Rate limiter not available",
            "status": "error",
            "fallback": "allowing request",
        }

    # Get rate limit for this endpoint
    limit, window = get_endpoint_rate_limit(request)
    key = get_rate_limit_key(request)

    # Check rate limit
    result = await rate_limiter.check_rate_limit(key, limit, window)

    if not result.allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "error": "Rate limit exceeded",
                "limit": result.limit,
                "remaining": result.remaining,
                "retry_after": result.retry_after,
                "reset_time": result.reset_time,
                "status": result.status.value,
            },
        )

    return {
        "message": "Enhanced rate limiting test successful!",
        "timestamp": time.time(),
        "endpoint": "/test/rate-limit/enhanced-test",
        "rate_limit_info": {
            "limit": result.limit,
            "remaining": result.remaining,
            "reset_time": result.reset_time,
            "status": result.status.value,
            "window": window,
        },
        "key": key,
    }


@router.get("/strict-test")
@limiter.limit("2/minute")  # Very strict limit for testing
async def strict_rate_limit_test(request: Request):
    """Strict rate limiting test endpoint.
    Limited to 2 requests per minute per IP for easy testing.
    """
    return {
        "message": "Strict rate limiting test successful!",
        "timestamp": time.time(),
        "endpoint": "/test/rate-limit/strict-test",
        "limit": "2/minute",
        "warning": "This endpoint has a very strict rate limit for testing purposes",
    }


@router.get("/status")
async def rate_limiting_status(
    request: Request, rate_limiter=Depends(get_rate_limiter_dependency),
):
    """Get rate limiting system status and metrics."""
    if not rate_limiter:
        return {
            "status": "Rate limiter not available",
            "message": "Enhanced rate limiter is not initialized",
        }

    metrics = rate_limiter.get_metrics()
    config = rate_limiter.config

    return {
        "status": "operational",
        "metrics": metrics,
        "config": {
            "redis_url": config.redis_url.replace(
                config.redis_url.split("@")[0].split("://")[1] + "@", "***:***@",
            )
            if "@" in config.redis_url
            else config.redis_url,
            "default_limit": config.default_limit,
            "enable_fallback": config.enable_fallback,
            "fallback_limit": config.fallback_limit,
            "redis_timeout": config.redis_timeout,
            "enable_metrics": config.enable_metrics,
        },
        "timestamp": time.time(),
    }


@router.get("/health")
async def rate_limiting_health(rate_limiter=Depends(get_rate_limiter_dependency)):
    """Health check for rate limiting system."""
    if not rate_limiter:
        return JSONResponse(
            status_code=503,
            content={"status": "unhealthy", "message": "Rate limiter not initialized"},
        )

    metrics = rate_limiter.get_metrics()
    redis_healthy = metrics.get("redis_healthy", False)
    fallback_enabled = metrics.get("fallback_enabled", False)

    if redis_healthy:
        status_code = 200
        status_message = "healthy"
        details = "Redis connection is healthy"
    elif fallback_enabled:
        status_code = 200
        status_message = "degraded"
        details = "Redis unavailable, using fallback"
    else:
        status_code = 503
        status_message = "unhealthy"
        details = "Redis unavailable and no fallback"

    return JSONResponse(
        status_code=status_code,
        content={
            "status": status_message,
            "details": details,
            "redis_healthy": redis_healthy,
            "fallback_enabled": fallback_enabled,
            "timestamp": time.time(),
        },
    )


@router.post("/reset")
async def reset_rate_limits(
    request: Request, rate_limiter=Depends(get_rate_limiter_dependency),
):
    """Reset rate limits for the current IP (for testing purposes).
    In production, this should be protected with authentication.
    """
    if not rate_limiter or not rate_limiter.redis_client:
        return {"message": "Cannot reset - Redis not available", "status": "error"}

    try:
        # Get the current IP's rate limit keys
        client_ip = request.headers.get("x-forwarded-for", get_remote_address(request))

        # Pattern to match all keys for this IP
        pattern = f"rate_limit:{client_ip}:*"

        # Get all matching keys
        keys = await rate_limiter.redis_client.keys(pattern)

        if keys:
            # Delete all rate limit keys for this IP
            await rate_limiter.redis_client.delete(*keys)

        return {
            "message": f"Reset rate limits for IP {client_ip}",
            "keys_deleted": len(keys),
            "status": "success",
        }

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "message": f"Error resetting rate limits: {e!s}",
                "status": "error",
            },
        )


# Rate limited endpoint using decorator
@router.get("/decorator-test")
@rate_limit("3/minute")
async def decorator_rate_limit_test(request: Request):
    """Test rate limiting using the @rate_limit decorator.
    Limited to 3 requests per minute.
    """
    return {
        "message": "Decorator rate limiting test successful!",
        "timestamp": time.time(),
        "endpoint": "/test/rate-limit/decorator-test",
        "limit": "3/minute (via decorator)",
    }


# Include these test endpoints in the API router
def include_router(api_router) -> None:
    """Include the rate limit test routes in the main API router."""
    api_router.include_router(router, tags=["Rate Limit Tests"])
