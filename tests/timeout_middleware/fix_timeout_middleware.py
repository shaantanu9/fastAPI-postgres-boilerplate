#!/usr/bin/env python3
"""
TIMEOUT MIDDLEWARE FIX SCRIPT

PURPOSE:
    Fix the timeout middleware by adding enhanced error handling and debugging
    
WHEN TO USE:
    - When timeout middleware is throwing TIMEOUT_MIDDLEWARE_ERROR
    - When you need to add better error handling to timeout middleware
    - When debugging timeout middleware issues
    
WHAT IT DOES:
    1. Backs up the original timeout middleware
    2. Creates an enhanced version with better error handling
    3. Adds detailed logging for debugging
    4. Improves exception handling in _execute_with_timeout
    
CREATED: 2025-06-14
ISSUE FIXED: Added proper exception handling to reveal root cause
RESULT: Enhanced middleware revealed the missing security_service import

HOW TO RUN:
    python3 tests/timeout_middleware/fix_timeout_middleware.py

EXPECTED OUTPUT:
    ✅ Backup created
    ✅ Enhanced middleware installed
    💡 Server restart required to apply changes
"""
import shutil
from datetime import datetime


def backup_original_middleware():
    """Backup the original middleware file"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = f"app/middleware/timeout_middleware_backup_{timestamp}.py"
    
    shutil.copy("app/middleware/timeout_middleware.py", backup_path)
    print(f"✅ Backed up original middleware to: {backup_path}")
    return backup_path


def create_fixed_middleware():
    """Create a fixed version of the timeout middleware"""
    
    fixed_middleware_content = '''"""
Timeout middleware with enhanced error handling and debugging.
"""
import asyncio
import contextlib
import time
from typing import Any, Dict, Optional

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.logger import logger


class TimeoutMiddleware(BaseHTTPMiddleware):
    """
    Enhanced timeout middleware with better error handling and debugging.
    
    ENHANCEMENTS ADDED:
    - Detailed error logging with stack traces
    - Better exception handling in _execute_with_timeout
    - Request path and method logging
    - Duration tracking for all requests
    - Specific error messages for different failure types
    """
    
    def __init__(
        self,
        app,
        default_timeout: float = 30.0,
        auth_timeout: float = 15.0,  # Increased from 10.0
        warning_threshold: float = 0.8,
    ):
        super().__init__(app)
        self.default_timeout = default_timeout
        self.auth_timeout = auth_timeout
        self.warning_threshold = warning_threshold
        
        # Log initialization
        logger.info(f"🕐 TimeoutMiddleware initialized:")
        logger.info(f"   Default timeout: {default_timeout}s")
        logger.info(f"   Auth timeout: {auth_timeout}s")
        logger.info(f"   Warning threshold: {warning_threshold}")

    async def dispatch(self, request: Request, call_next) -> Response:
        """Enhanced dispatch with better error handling"""
        start_time = time.time()
        path = request.url.path
        method = request.method
        
        # Determine timeout based on path
        timeout = self._get_timeout_for_path(path)
        
        logger.debug(f"🔄 Processing {method} {path} (timeout: {timeout}s)")
        
        try:
            # Execute with timeout and enhanced error handling
            response = await self._execute_with_timeout(
                request, call_next, timeout, path, method
            )
            
            # Add timing headers
            duration = time.time() - start_time
            response.headers["x-request-duration"] = f"{duration:.3f}"
            response.headers["x-timeout-limit"] = str(timeout)
            
            logger.debug(f"✅ Completed {method} {path} in {duration:.3f}s")
            return response
            
        except Exception as e:
            # Enhanced error handling with detailed logging
            duration = time.time() - start_time
            error_type = type(e).__name__
            
            logger.error(f"❌ Timeout middleware error for {method} {path}:")
            logger.error(f"   Error type: {error_type}")
            logger.error(f"   Error message: {str(e)}")
            logger.error(f"   Duration: {duration:.3f}s")
            logger.error(f"   Timeout limit: {timeout}s")
            
            # Log stack trace for debugging
            import traceback
            logger.error(f"   Stack trace: {traceback.format_exc()}")
            
            # Return detailed error response
            from fastapi.responses import JSONResponse
            return JSONResponse(
                status_code=500,
                content={
                    "detail": f"Internal server error during timeout handling",
                    "error_code": "TIMEOUT_MIDDLEWARE_ERROR",
                    "error_type": error_type,
                    "error_message": str(e),
                    "path": path,
                    "method": method,
                    "duration": round(duration, 3),
                    "timeout_limit": timeout,
                },
                headers={
                    "x-request-duration": f"{duration:.3f}",
                    "x-timeout-limit": str(timeout),
                    "x-error-type": error_type,
                }
            )

    async def _execute_with_timeout(
        self, 
        request: Request, 
        call_next, 
        timeout: float,
        path: str,
        method: str
    ) -> Response:
        """Enhanced execute with timeout with better error handling"""
        
        try:
            logger.debug(f"🚀 Starting {method} {path} with {timeout}s timeout")
            
            # Create the main request task
            request_task = asyncio.create_task(call_next(request))
            logger.debug(f"   ✅ Request task created")
            
            # Create warning task
            warning_time = timeout * self.warning_threshold
            warning_task = asyncio.create_task(asyncio.sleep(warning_time))
            logger.debug(f"   ✅ Warning task created ({warning_time}s)")
            
            # Wait for either completion or warning
            logger.debug(f"   🔄 Waiting for completion...")
            done, pending = await asyncio.wait(
                [request_task, warning_task],
                return_when=asyncio.FIRST_COMPLETED,
                timeout=timeout,
            )
            logger.debug(f"   ✅ asyncio.wait completed")
            
            # Cancel pending tasks
            for task in pending:
                task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await task
            logger.debug(f"   ✅ Pending tasks cancelled")
            
            # Check if warning triggered
            if warning_task in done and request_task not in done:
                logger.warning(f"⚠️ Request {method} {path} taking longer than {warning_time}s")
                # Continue waiting for the actual request
                try:
                    result = await asyncio.wait_for(
                        request_task, timeout=timeout - warning_time,
                    )
                    logger.debug(f"   ✅ Request completed after warning")
                    return result
                except asyncio.TimeoutError:
                    logger.error(f"❌ Request {method} {path} timed out after {timeout}s")
                    request_task.cancel()
                    with contextlib.suppress(asyncio.CancelledError):
                        await request_task
                    raise
            
            # Request completed normally
            if request_task in done:
                logger.debug(f"   ✅ Request completed normally")
                result = await request_task
                return result
            
            # This shouldn't happen, but handle it
            logger.error(f"❌ Unexpected state for {method} {path}")
            raise TimeoutError(f"Request {method} {path} did not complete within {timeout}s")
            
        except asyncio.TimeoutError as e:
            logger.error(f"❌ Timeout error for {method} {path}: {e}")
            # Cancel the request task
            if 'request_task' in locals():
                request_task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await request_task
            raise
        except Exception as e:
            logger.error(f"❌ Unexpected error in _execute_with_timeout for {method} {path}: {e}")
            logger.error(f"   Error type: {type(e).__name__}")
            # This is the key enhancement - we re-raise the original exception
            # instead of wrapping it, so we can see the real error
            raise

    def _get_timeout_for_path(self, path: str) -> float:
        """Determine timeout based on request path"""
        if "/auth/" in path or "/user-management/" in path:
            return self.auth_timeout
        return self.default_timeout
'''
    
    # Write the fixed middleware
    with open("app/middleware/timeout_middleware.py", "w") as f:
        f.write(fixed_middleware_content)
    
    print("✅ Enhanced timeout middleware created")
    print("💡 Key improvements:")
    print("   - Better exception handling and logging")
    print("   - Detailed error responses with debugging info")
    print("   - Increased auth timeout from 10s to 15s")
    print("   - Stack trace logging for debugging")
    print("   - Request path and method tracking")


def main():
    """Main fix function"""
    print("🔧 Fixing Timeout Middleware")
    print("=" * 50)
    
    try:
        # Backup original
        backup_path = backup_original_middleware()
        
        # Create fixed version
        create_fixed_middleware()
        
        print("\n" + "=" * 50)
        print("🎉 TIMEOUT MIDDLEWARE FIX COMPLETE")
        print(f"📁 Backup saved to: {backup_path}")
        print("🔄 Please restart the FastAPI server to apply changes:")
        print("   pkill -f uvicorn")
        print("   uvicorn app.main:app --reload")
        
    except Exception as e:
        print(f"❌ Error during fix: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main() 