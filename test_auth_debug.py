#!/usr/bin/env python3

import asyncio
import os
import sys

# Set environment variables
os.environ['DATABASE_URL'] = 'postgresql+asyncpg://postgres:img2bffnlhslfigs@localhost:5433/code_myind'
os.environ['DATABASE_URL_WITHOUT_ASYNC'] = 'postgresql://postgres:img2bffnlhslfigs@localhost:5433/code_myind'
os.environ['JWT_SECRET_TOKEN'] = 'your-super-secret-jwt-key-change-this-in-production-2025'

sys.path.append('.')

async def test_authentication():
    try:
        from app.db.session import get_db
        from app.services.user_service import enhanced_user_service
        from fastapi import Request
        
        print("✅ Imports successful")
        
        # Get database session
        db_gen = get_db()
        db = await db_gen.__anext__()
        
        print("✅ Database connection successful")
        
        # Create a mock request
        class MockRequest:
            def __init__(self):
                self.client = type('obj', (object,), {'host': '127.0.0.1'})()
                self.headers = {}
        
        request = MockRequest()
        
        # Test authentication
        print("🔍 Testing authentication...")
        user = await enhanced_user_service.authenticate_user(
            db, "testuser", "MyStr0ng!P@ssw0rd2025", request
        )
        
        if user:
            print(f"✅ Authentication successful: {user.username} ({user.email})")
        else:
            print("❌ Authentication failed")
            
        # Test with wrong password
        print("🔍 Testing with wrong password...")
        user_wrong = await enhanced_user_service.authenticate_user(
            db, "testuser", "wrongpassword", request
        )
        
        if user_wrong:
            print(f"⚠️ Authentication should have failed but succeeded: {user_wrong.username}")
        else:
            print("✅ Authentication correctly failed with wrong password")
        
        await db.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_authentication()) 