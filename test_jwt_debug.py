#!/usr/bin/env python3

import os
import sys

# Set environment variables
os.environ['DATABASE_URL'] = 'postgresql+asyncpg://postgres:img2bffnlhslfigs@localhost:5433/code_myind'
os.environ['DATABASE_URL_WITHOUT_ASYNC'] = 'postgresql://postgres:img2bffnlhslfigs@localhost:5433/code_myind'
os.environ['JWT_SECRET_TOKEN'] = 'your-super-secret-jwt-key-change-this-in-production-2025'

sys.path.append('.')

def test_jwt_service():
    try:
        from app.core.jwt import jwt_service
        
        print("✅ JWT service imported successfully")
        
        # Test token creation
        test_data = {
            "sub": "testuser",
            "user_id": "abc449b2-51fa-4231-acd7-67143876b413",
            "session_id": "test-session-id"
        }
        
        print(f"🔍 Creating access token with data: {test_data}")
        access_token = jwt_service.create_access_token(test_data)
        print(f"✅ Access token created: {access_token[:50]}...")
        
        # Test token verification
        print("🔍 Verifying access token...")
        payload = jwt_service.verify_token(access_token)
        print(f"✅ Token verified successfully: {payload}")
        
        # Test refresh token
        print("🔍 Creating refresh token...")
        refresh_token = jwt_service.create_refresh_token("abc449b2-51fa-4231-acd7-67143876b413", "test-session-id")
        print(f"✅ Refresh token created: {refresh_token[:50]}...")
        
        # Test refresh token verification
        print("🔍 Verifying refresh token...")
        refresh_payload = jwt_service.verify_token(refresh_token, "refresh")
        print(f"✅ Refresh token verified successfully: {refresh_payload}")
        
        # Test with invalid token type
        print("🔍 Testing invalid token type...")
        try:
            jwt_service.verify_token(access_token, "refresh")
            print("❌ Should have failed but didn't")
        except Exception as e:
            print(f"✅ Correctly failed with invalid token type: {e}")
        
        print("🎉 All JWT tests passed!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_jwt_service() 