#!/usr/bin/env python3

import asyncio
import os
import sys

# Set environment variables
os.environ['DATABASE_URL'] = 'postgresql+asyncpg://postgres:img2bffnlhslfigs@localhost:5433/code_myind'
os.environ['DATABASE_URL_WITHOUT_ASYNC'] = 'postgresql://postgres:img2bffnlhslfigs@localhost:5433/code_myind'
os.environ['JWT_SECRET_TOKEN'] = 'your-super-secret-jwt-key-change-this-in-production-2025'

sys.path.append('.')

async def test_login_flow():
    try:
        from app.db.session import get_db
        from app.services.user_service import enhanced_user_service
        from app.core.jwt import jwt_service
        from app.db.schemas.user import LoginRequest
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
        
        # Step 1: Test authentication
        print("🔍 Step 1: Testing authentication...")
        user = await enhanced_user_service.authenticate_user(
            db, "testuser", "MyStr0ng!P@ssw0rd2025", request
        )
        
        if not user:
            print("❌ Authentication failed")
            return
        
        print(f"✅ Authentication successful: {user.username}")
        
        # Step 2: Test session creation
        print("🔍 Step 2: Testing session creation...")
        session = await enhanced_user_service.create_session(db, user, request)
        print(f"✅ Session created: {session.id}")
        
        # Step 3: Test JWT token creation
        print("🔍 Step 3: Testing JWT token creation...")
        access_token = jwt_service.create_access_token(
            data={"sub": user.username, "user_id": user.id, "session_id": session.id}
        )
        print(f"✅ Access token created: {access_token[:50]}...")
        
        refresh_token = jwt_service.create_refresh_token(user.id, session.id)
        print(f"✅ Refresh token created: {refresh_token[:50]}...")
        
        # Step 4: Update session with refresh token
        print("🔍 Step 4: Updating session with refresh token...")
        session.refresh_token = refresh_token
        await db.commit()
        print("✅ Session updated and committed")
        
        print("🎉 All steps completed successfully!")
        
        await db.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_login_flow()) 