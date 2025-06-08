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


async def test_user_creation() -> None:
    try:
        from app.db.schemas.user import UserCreate
        from app.db.session import get_db
        from app.services.user_service import enhanced_user_service


        # Get database session
        db_gen = get_db()
        db = await db_gen.__anext__()


        # Create test user
        user_data = UserCreate(
            username="testuser",
            email="test@example.com",
            first_name="Test",
            last_name="User",
            password="MyStr0ng!P@ssw0rd2025",
        )


        # Try to create user
        await enhanced_user_service.create_user(db, user_data)


        await db.close()

    except Exception:
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_user_creation())
