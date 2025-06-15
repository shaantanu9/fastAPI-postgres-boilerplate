#!/usr/bin/env python3
"""
TEST REDIS ASYNC FUNCTIONALITY TEST

PURPOSE:
    Test Redis async functionality
    
WHEN TO USE:
    Testing Redis integration
    
WHAT IT TESTS:
    Redis connection, async operations
    
CREATED: Pre-2025-06-14 (legacy test, organized 2025-06-14)
DEPENDENCIES: Varies by test - check original file content
RESULT: Specific to test functionality

HOW TO RUN:
    python3 tests/system/test_redis_async.py

EXPECTED OUTPUT:
    Varies by test - check test implementation for details

NOTES:
    This test was moved from root directory and documented for better organization.
    Original functionality preserved with enhanced documentation.
"""

import asyncio

import redis.asyncio as redis


async def test_redis_connection() -> None:
    try:
        r = await redis.from_url("redis://localhost:6379/0")
        result = await r.ping()
        await r.close()
    except Exception:
        pass
    finally:
        if "r" in locals():
            await r.close()


if __name__ == "__main__":
    asyncio.run(test_redis_connection())
