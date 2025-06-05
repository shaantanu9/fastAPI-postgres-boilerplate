"""
Test endpoints for demonstrating and testing timeout functionality.
"""
from fastapi import APIRouter, Request, HTTPException, status
from fastapi.responses import JSONResponse
from app.core.timeouts import with_timeout, database_timeout_context, TimeoutException
import asyncio
import logging
import time
from typing import Dict, Any, Optional

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/health")
async def timeout_health() -> Dict[str, Any]:
    """
    Health check for timeout functionality.
    """
    return {
        "status": "healthy",
        "message": "Timeout system operational",
        "timestamp": time.time(),
        "available_tests": [
            "/test/timeout/quick",
            "/test/timeout/slow", 
            "/test/timeout/database",
            "/test/timeout/heavy-computation",
            "/test/timeout/middleware-test",
            "/test/timeout/custom-timeout"
        ]
    }

@router.get("/quick")
async def test_quick_operation(delay: float = 1.0) -> Dict[str, Any]:
    """
    Test a quick operation that should complete within timeout.
    
    Args:
        delay: Delay in seconds (default: 1.0)
    """
    start_time = time.time()
    
    try:
        await asyncio.sleep(delay)
        duration = time.time() - start_time
        
        return {
            "status": "success",
            "message": "Quick operation completed successfully",
            "requested_delay": delay,
            "actual_duration": round(duration, 3),
            "endpoint_timeout": "30s (global)",
            "within_timeout": True
        }
        
    except Exception as e:
        duration = time.time() - start_time
        logger.error(f"Quick operation failed: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "operation_failed",
                "message": str(e),
                "duration": round(duration, 3)
            }
        )

@router.get("/slow")
async def test_slow_operation(delay: float = 35.0) -> Dict[str, Any]:
    """
    Test a slow operation that should trigger timeout.
    
    Args:
        delay: Delay in seconds (default: 35.0 - exceeds 30s global timeout)
    """
    start_time = time.time()
    
    try:
        logger.info(f"Starting slow operation with {delay}s delay")
        await asyncio.sleep(delay)
        duration = time.time() - start_time
        
        return {
            "status": "success",
            "message": "Slow operation completed (this shouldn't happen with default timeout)",
            "requested_delay": delay,
            "actual_duration": round(duration, 3),
            "warning": "This response indicates timeout middleware may not be working"
        }
        
    except asyncio.CancelledError:
        duration = time.time() - start_time
        logger.warning(f"Slow operation cancelled after {duration:.2f}s")
        raise
    except Exception as e:
        duration = time.time() - start_time
        logger.error(f"Slow operation failed: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "operation_failed",
                "message": str(e),
                "duration": round(duration, 3)
            }
        )

@router.get("/database")
async def test_database_timeout(operation_time: float = 12.0) -> Dict[str, Any]:
    """
    Test database operation with specific timeout.
    
    Args:
        operation_time: Simulated database operation time in seconds
    """
    start_time = time.time()
    
    try:
        async with database_timeout_context(10.0):  # 10 second database timeout
            logger.info(f"Starting database operation for {operation_time}s")
            await asyncio.sleep(operation_time)
            duration = time.time() - start_time
            
            return {
                "status": "success",
                "message": "Database operation completed",
                "operation_time": operation_time,
                "actual_duration": round(duration, 3),
                "database_timeout": "10s",
                "within_timeout": duration < 10.0
            }
            
    except TimeoutException as e:
        duration = time.time() - start_time
        logger.warning(f"Database operation timed out after {duration:.2f}s")
        
        return JSONResponse(
            status_code=504,
            content={
                "status": "timeout",
                "error": "database_timeout",
                "message": "Database operation exceeded timeout limit",
                "timeout_limit": 10.0,
                "elapsed_time": round(duration, 3),
                "requested_time": operation_time
            }
        )
    except Exception as e:
        duration = time.time() - start_time
        logger.error(f"Database operation failed: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "database_error",
                "message": str(e),
                "duration": round(duration, 3)
            }
        )

@router.get("/heavy-computation")
@with_timeout(timeout_seconds=15.0)
async def test_heavy_computation(iterations: int = 5000000) -> Dict[str, Any]:
    """
    Test heavy computation with custom timeout decorator.
    
    Args:
        iterations: Number of iterations for computation
    """
    start_time = time.time()
    logger.info(f"Starting heavy computation with {iterations} iterations")
    
    try:
        # Simulate CPU-intensive work
        result = 0
        for i in range(iterations):
            result += i * i
            # Yield control periodically to allow timeout checking
            if i % 10000 == 0:
                await asyncio.sleep(0)
        
        duration = time.time() - start_time
        
        return {
            "status": "success",
            "message": "Heavy computation completed",
            "iterations": iterations,
            "result": result % 1000000,  # Truncate for readability
            "computation_time": round(duration, 3),
            "timeout_limit": "15s",
            "within_timeout": duration < 15.0
        }
        
    except asyncio.CancelledError:
        duration = time.time() - start_time
        logger.warning(f"Heavy computation cancelled after {duration:.2f}s")
        raise
    except Exception as e:
        duration = time.time() - start_time
        logger.error(f"Heavy computation failed: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "computation_failed",
                "message": str(e),
                "duration": round(duration, 3)
            }
        )

@router.get("/middleware-test")
async def test_middleware_timeout(delay: float = 25.0) -> Dict[str, Any]:
    """
    Test middleware timeout handling (should be caught by TimeoutMiddleware).
    
    Args:
        delay: Delay in seconds to test middleware timeout
    """
    start_time = time.time()
    
    try:
        logger.info(f"Testing middleware timeout with {delay}s delay")
        await asyncio.sleep(delay)
        duration = time.time() - start_time
        
        return {
            "status": "success",
            "message": "Operation completed (middleware timeout may not be working)",
            "delay": delay,
            "actual_duration": round(duration, 3),
            "warning": "If you see this with delay > 30s, middleware timeout is not working"
        }
        
    except asyncio.CancelledError:
        duration = time.time() - start_time
        logger.info(f"Middleware timeout test cancelled after {duration:.2f}s")
        raise

@router.get("/custom-timeout")
async def test_custom_timeout(
    delay: float = 8.0,
    timeout: Optional[float] = 5.0
) -> Dict[str, Any]:
    """
    Test custom timeout using the with_timeout decorator.
    
    Args:
        delay: Operation delay in seconds
        timeout: Custom timeout in seconds
    """
    if timeout:
        # Apply custom timeout dynamically
        @with_timeout(timeout_seconds=timeout)
        async def timed_operation():
            start_time = time.time()
            await asyncio.sleep(delay)
            return time.time() - start_time
        
        try:
            duration = await timed_operation()
            return {
                "status": "success",
                "message": "Custom timeout operation completed",
                "delay": delay,
                "timeout": timeout,
                "actual_duration": round(duration, 3),
                "within_timeout": duration < timeout
            }
            
        except TimeoutException:
            return JSONResponse(
                status_code=504,
                content={
                    "status": "timeout",
                    "error": "custom_timeout",
                    "message": f"Operation exceeded custom timeout of {timeout}s",
                    "delay": delay,
                    "timeout": timeout
                }
            )
    else:
        # No timeout applied
        start_time = time.time()
        await asyncio.sleep(delay)
        duration = time.time() - start_time
        
        return {
            "status": "success",
            "message": "Operation completed without custom timeout",
            "delay": delay,
            "actual_duration": round(duration, 3),
            "timeout": "none"
        }

@router.get("/stress-test")
async def timeout_stress_test(
    concurrent_requests: int = 5,
    delay_per_request: float = 3.0
) -> Dict[str, Any]:
    """
    Stress test timeout handling with concurrent requests.
    
    Args:
        concurrent_requests: Number of concurrent operations
        delay_per_request: Delay for each operation
    """
    start_time = time.time()
    
    async def single_operation(request_id: int):
        """Single operation for stress testing."""
        op_start = time.time()
        await asyncio.sleep(delay_per_request)
        return {
            "request_id": request_id,
            "duration": round(time.time() - op_start, 3)
        }
    
    try:
        # Run concurrent operations
        tasks = [
            single_operation(i) 
            for i in range(concurrent_requests)
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        total_duration = time.time() - start_time
        
        # Process results
        successful = [r for r in results if isinstance(r, dict)]
        failed = [r for r in results if isinstance(r, Exception)]
        
        return {
            "status": "completed",
            "message": "Stress test completed",
            "concurrent_requests": concurrent_requests,
            "delay_per_request": delay_per_request,
            "total_duration": round(total_duration, 3),
            "successful_operations": len(successful),
            "failed_operations": len(failed),
            "results": successful,
            "errors": [str(e) for e in failed]
        }
        
    except Exception as e:
        duration = time.time() - start_time
        logger.error(f"Stress test failed: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "stress_test_failed",
                "message": str(e),
                "duration": round(duration, 3)
            }
        )

@router.get("/metrics")
async def timeout_metrics(request: Request) -> Dict[str, Any]:
    """
    Get timeout-related metrics from the middleware.
    """
    # Try to get timeout middleware metrics
    timeout_middleware = None
    for middleware in request.app.middleware_stack:
        if hasattr(middleware, 'cls') and middleware.cls.__name__ == 'TimeoutMiddleware':
            timeout_middleware = middleware.kwargs.get('app')
            break
    
    if timeout_middleware and hasattr(timeout_middleware, 'get_metrics'):
        metrics = timeout_middleware.get_metrics()
        return {
            "status": "available",
            "message": "Timeout metrics retrieved",
            "metrics": metrics,
            "timestamp": time.time()
        }
    else:
        return {
            "status": "unavailable",
            "message": "Timeout middleware metrics not available",
            "timestamp": time.time(),
            "note": "Metrics may not be enabled or middleware not properly configured"
        }
