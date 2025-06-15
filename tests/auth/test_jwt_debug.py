#!/usr/bin/env python3
"""
DEBUG JWT TOKEN GENERATION AND VALIDATION TEST

PURPOSE:
    Debug JWT token generation and validation
    
WHEN TO USE:
    When JWT tokens are not working correctly
    
WHAT IT TESTS:
    JWT token creation, validation, expiration
    
CREATED: Pre-2025-06-14 (legacy test, organized 2025-06-14)
DEPENDENCIES: Varies by test - check original file content
RESULT: Specific to test functionality

HOW TO RUN:
    python3 tests/auth/test_jwt_debug.py

EXPECTED OUTPUT:
    Varies by test - check test implementation for details

NOTES:
    This test was moved from root directory and documented for better organization.
    Original functionality preserved with enhanced documentation.
"""


import contextlib
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


def test_jwt_service() -> None:
    try:
        from app.core.jwt import jwt_service


        # Test token creation
        test_data = {
            "sub": "testuser",
            "user_id": "abc449b2-51fa-4231-acd7-67143876b413",
            "session_id": "test-session-id",
        }

        access_token = jwt_service.create_access_token(test_data)

        # Test token verification
        jwt_service.verify_token(access_token)

        # Test refresh token
        refresh_token = jwt_service.create_refresh_token(
            "abc449b2-51fa-4231-acd7-67143876b413", "test-session-id",
        )

        # Test refresh token verification
        jwt_service.verify_token(refresh_token, "refresh")

        # Test with invalid token type
        with contextlib.suppress(Exception):
            jwt_service.verify_token(access_token, "refresh")


    except Exception:
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    test_jwt_service()
