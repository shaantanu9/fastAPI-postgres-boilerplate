#!/usr/bin/env python3
"""
DEBUG AUTHENTICATION ISSUES AND TEST AUTH ENDPOINTS TEST

PURPOSE:
    Debug authentication issues and test auth endpoints
    
WHEN TO USE:
    When auth endpoints are failing or need debugging
    
WHAT IT TESTS:
    Auth endpoint responses, error handling, token validation
    
CREATED: Pre-2025-06-14 (legacy test, organized 2025-06-14)
DEPENDENCIES: Varies by test - check original file content
RESULT: Specific to test functionality

HOW TO RUN:
    python3 tests/auth/test_auth_debug.py

EXPECTED OUTPUT:
    Varies by test - check test implementation for details

NOTES:
    This test was moved from root directory and documented for better organization.
    Original functionality preserved with enhanced documentation.
"""


import asyncio
import os
import sys

# Set environment variables
os.environ["DATABASE_URL"] = (
    "postgresql+asyncpg://postgres:img2bffnlhslfigs@localhost:5433/code_myind"
)
os.environ["DATABASE_URL_WITHOUT_ASYNC"] = (
    "postgresql://postgres:img2bffnlhslfigs@localhost:5433/code_myind"
)
os.environ["JWT_SECRET_TOKEN"] = (
    "your-super-secret-jwt-key-change-this-in-production-2025"
)

sys.path.append(".")


async def test_authentication() -> None:
    try:
        from app.db.session import get_db
        from app.services.user_service import enhanced_user_service


        # Get database session
        db_gen = get_db()
        db = await db_gen.__anext__()


        # Create a mock request
        class MockRequest:
            def __init__(self) -> None:
                self.client = type("obj", (object,), {"host": "127.0.0.1"})()
                self.headers = {}

        request = MockRequest()

        # Test authentication
        user = await enhanced_user_service.authenticate_user(
            db, "testuser", "MyStr0ng!P@ssw0rd2025", request,
        )

        if user:
            pass
        else:
            pass

        # Test with wrong password
        user_wrong = await enhanced_user_service.authenticate_user(
            db, "testuser", "wrongpassword", request,
        )

        if user_wrong:
            pass
        else:
            pass

        await db.close()

    except Exception:
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_authentication())
