#!/usr/bin/env python3

import asyncio
import os
import sys

# Set environment variables
os.environ['DATABASE_URL'] = 'postgresql+asyncpg://postgres:img2bffnlhslfigs@localhost:5433/code_myind'
os.environ['DATABASE_URL_WITHOUT_ASYNC'] = 'postgresql://postgres:img2bffnlhslfigs@localhost:5433/code_myind'
os.environ['JWT_SECRET_TOKEN'] = 'your-super-secret-jwt-key-change-this-in-production-2025'

sys.path.append('.')

async def test_user_creation():
    try:
        from app.db.session import get_db
        from app.services.user_service import enhanced_user_service
        from app.db.schemas.user import UserCreate
        
        print("✅ Imports successful")
        
        # Get database session
        db_gen = get_db()
        db = await db_gen.__anext__()
        
        print("✅ Database connection successful")
        
        # Create test user
        user_data = UserCreate(
            username="testuser",
            email="test@example.com",
            first_name="Test",
            last_name="User",
            password="MyStr0ng!P@ssw0rd2025"
        )
        
        print("✅ UserCreate object created")
        print(f"User data: {user_data}")
        
        # Try to create user
        user = await enhanced_user_service.create_user(db, user_data)
        
        print(f"✅ User created successfully: {user.username} ({user.email})")
        
        await db.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_user_creation()) 