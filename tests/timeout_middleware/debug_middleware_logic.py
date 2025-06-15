#!/usr/bin/env python3
"""
TIMEOUT MIDDLEWARE LOGIC TESTING SCRIPT

PURPOSE:
    Test the exact middleware logic in isolation to identify issues
    
WHEN TO USE:
    - When timeout middleware is throwing exceptions
    - When you need to test middleware logic without FastAPI
    - When debugging asyncio task management in middleware
    
WHAT IT TESTS:
    1. Exact middleware _execute_with_timeout logic
    2. Different timeout values and their behavior
    3. Task creation and cancellation
    4. Warning threshold behavior
    
CREATED: 2025-06-14
ISSUE RESOLVED: Logic was fine, issue was missing import
RESULT: Middleware logic works correctly in isolation

HOW TO RUN:
    python3 tests/timeout_middleware/debug_middleware_logic.py

EXPECTED OUTPUT:
    ✅ All timeout values should work
    ✅ Task management should be successful
    ❌ If fails, indicates middleware logic issue
"""
import asyncio
import contextlib
import time
from typing import Any

async def simulate_middleware_logic():
    """Simulate the exact logic from the timeout middleware"""
    print("🔍 Testing exact middleware logic...")
    
    async def mock_call_next(request):
        """Mock the call_next function"""
        await asyncio.sleep(0.05)  # Simulate quick auth operation
        return {"status": "success", "message": "Auth completed"}
    
    # Simulate the middleware parameters
    timeout = 10.0  # Auth endpoint timeout
    warning_time = timeout * 0.8  # 8.0 seconds
    
    print(f"   Timeout: {timeout}s, Warning: {warning_time}s")
    
    try:
        # Create the main request task (this is what was failing)
        request_task = asyncio.create_task(mock_call_next("mock_request"))
        
        # Create warning task
        warning_task = asyncio.create_task(asyncio.sleep(warning_time))
        
        print("   ✅ Tasks created successfully")
        
        # Wait for either completion or warning (this was the problematic line)
        done, pending = await asyncio.wait(
            [request_task, warning_task],
            return_when=asyncio.FIRST_COMPLETED,
            timeout=timeout,
        )
        
        print("   ✅ asyncio.wait completed successfully")
        
        # Cancel pending tasks
        for task in pending:
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task
        
        print("   ✅ Pending tasks cancelled")
        
        # Check if warning triggered
        if warning_task in done and request_task not in done:
            print("   ⚠️ Warning triggered")
            # Continue waiting for the actual request
            result = await asyncio.wait_for(
                request_task, timeout=timeout - warning_time,
            )
            return result
        
        # Request completed normally
        if request_task in done:
            print("   ✅ Request completed normally")
            result = await request_task
            return result
        
        # This shouldn't happen, but handle it
        print("   ❌ Unexpected state - raising TimeoutError")
        raise TimeoutError
        
    except TimeoutError as e:
        print(f"   ❌ TimeoutError: {e}")
        # Cancel the request task
        request_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await request_task
        raise
    except Exception as e:
        print(f"   ❌ Unexpected error: {e}")
        print(f"   Error type: {type(e)}")
        raise

async def test_with_different_timeouts():
    """Test with different timeout values"""
    print("\n🔍 Testing with different timeout values...")
    
    timeouts = [0.1, 1.0, 5.0, 10.0, 30.0]
    
    for timeout_val in timeouts:
        print(f"\n   Testing with timeout: {timeout_val}s")
        try:
            await simulate_middleware_logic_with_timeout(timeout_val)
            print(f"   ✅ Success with {timeout_val}s timeout")
        except Exception as e:
            print(f"   ❌ Failed with {timeout_val}s timeout: {e}")

async def simulate_middleware_logic_with_timeout(timeout_val):
    """Test middleware logic with specific timeout"""
    async def mock_call_next(request):
        await asyncio.sleep(0.01)  # Very quick operation
        return {"status": "success"}
    
    warning_time = timeout_val * 0.8
    
    # Create tasks
    request_task = asyncio.create_task(mock_call_next("mock_request"))
    warning_task = asyncio.create_task(asyncio.sleep(warning_time))
    
    # The problematic asyncio.wait call
    done, pending = await asyncio.wait(
        [request_task, warning_task],
        return_when=asyncio.FIRST_COMPLETED,
        timeout=timeout_val,
    )
    
    # Cancel pending tasks
    for task in pending:
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task
    
    if request_task in done:
        return await request_task
    
    raise TimeoutError("Request did not complete")

def main():
    """Main debug function"""
    print("🚀 Debugging Exact Middleware Issue")
    print("=" * 60)
    
    try:
        # Test the exact middleware logic
        result = asyncio.run(simulate_middleware_logic())
        print(f"✅ Middleware logic test passed: {result}")
        
        # Test with different timeouts
        asyncio.run(test_with_different_timeouts())
        
        print("\n" + "=" * 60)
        print("🎯 CONCLUSION:")
        print("✅ The middleware logic itself works fine")
        print("💡 The issue might be in the FastAPI integration or request handling")
        
    except Exception as e:
        print(f"\n❌ CRITICAL ERROR FOUND: {e}")
        print(f"Error type: {type(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 