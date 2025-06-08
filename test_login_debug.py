#!/usr/bin/env python3

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


async def test_login_flow() -> None:
    try:
        from app.core.jwt import jwt_service
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

        # Step 1: Test authentication
        user = await enhanced_user_service.authenticate_user(
            db, "testuser", "MyStr0ng!P@ssw0rd2025", request,
        )

        if not user:
            return


        # Step 2: Test session creation
        session = await enhanced_user_service.create_session(db, user, request)

        # Step 3: Test JWT token creation
        jwt_service.create_access_token(
            data={"sub": user.username, "user_id": user.id, "session_id": session.id},
        )

        refresh_token = jwt_service.create_refresh_token(user.id, session.id)

        # Step 4: Update session with refresh token
        session.refresh_token = refresh_token
        await db.commit()


        await db.close()

    except Exception:
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_login_flow())
