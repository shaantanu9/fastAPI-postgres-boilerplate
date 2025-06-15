#!/usr/bin/env python3
"""Debug script to test token refresh functionality."""

import requests
import json
from datetime import datetime

BASE_URL = "http://localhost:8000"

def test_token_refresh():
    """Test token refresh functionality step by step."""
    print("🔐 TOKEN REFRESH DEBUG TEST")
    print("=" * 50)
    
    # Step 1: Register a test user
    print("1. Registering test user...")
    test_user = {
        "username": f"debug_user_{datetime.now().strftime('%H%M%S')}",
        "email": f"debug_user_{datetime.now().strftime('%H%M%S')}@example.com",
        "first_name": "Debug",
        "last_name": "User",
        "password": "Phoenix7854#@UniquePass"
    }
    
    try:
        reg_response = requests.post(f"{BASE_URL}/api/v1/auth/register", json=test_user, timeout=10)
        if reg_response.status_code != 201:
            print(f"   ❌ Registration failed: {reg_response.status_code}")
            print(f"   Response: {reg_response.text}")
            return False
        print(f"   ✅ User registered successfully")
    except Exception as e:
        print(f"   ❌ Registration error: {e}")
        return False
    
    # Step 2: Login to get tokens
    print("2. Logging in to get tokens...")
    login_data = {
        "username_or_email": test_user["username"],
        "password": test_user["password"]
    }
    
    try:
        login_response = requests.post(f"{BASE_URL}/api/v1/auth/login", json=login_data, timeout=10)
        if login_response.status_code != 200:
            print(f"   ❌ Login failed: {login_response.status_code}")
            print(f"   Response: {login_response.text}")
            return False
        
        login_result = login_response.json()
        access_token = login_result.get("access_token")
        refresh_token = login_result.get("refresh_token")
        
        print(f"   ✅ Login successful")
        print(f"   📝 Access token length: {len(access_token) if access_token else 0}")
        print(f"   📝 Refresh token length: {len(refresh_token) if refresh_token else 0}")
        
        if not access_token or not refresh_token:
            print("   ❌ Missing tokens in response")
            return False
            
    except Exception as e:
        print(f"   ❌ Login error: {e}")
        return False
    
    # Step 3: Test original access token
    print("3. Testing original access token...")
    headers = {"Authorization": f"Bearer {access_token}"}
    
    try:
        me_response = requests.get(f"{BASE_URL}/api/v1/auth/me", headers=headers, timeout=10)
        print(f"   📝 Original token status: {me_response.status_code}")
        if me_response.status_code == 200:
            print("   ✅ Original token works")
            user_data = me_response.json()
            print(f"   📝 User ID: {user_data.get('id', 'not found')}")
        else:
            print(f"   ❌ Original token failed: {me_response.text}")
            return False
    except Exception as e:
        print(f"   ❌ Original token test error: {e}")
        return False
    
    # Step 4: Refresh the token
    print("4. Refreshing token...")
    refresh_data = {"refresh_token": refresh_token}
    
    try:
        refresh_response = requests.post(f"{BASE_URL}/api/v1/auth/refresh", json=refresh_data, timeout=10)
        print(f"   📝 Refresh response status: {refresh_response.status_code}")
        
        if refresh_response.status_code != 200:
            print(f"   ❌ Refresh failed: {refresh_response.text}")
            return False
        
        refresh_result = refresh_response.json()
        new_access_token = refresh_result.get("access_token")
        
        print(f"   ✅ Refresh successful")
        print(f"   📝 New access token length: {len(new_access_token) if new_access_token else 0}")
        print(f"   📝 Tokens are different: {access_token != new_access_token}")
        
        if not new_access_token:
            print("   ❌ No new access token in response")
            return False
            
    except Exception as e:
        print(f"   ❌ Refresh error: {e}")
        return False
    
    # Step 5: Test new access token
    print("5. Testing new access token...")
    new_headers = {"Authorization": f"Bearer {new_access_token}"}
    
    try:
        new_me_response = requests.get(f"{BASE_URL}/api/v1/auth/me", headers=new_headers, timeout=10)
        print(f"   📝 New token status: {new_me_response.status_code}")
        
        if new_me_response.status_code == 200:
            print("   ✅ New token works!")
            user_data = new_me_response.json()
            print(f"   📝 User ID: {user_data.get('id', 'not found')}")
            return True
        else:
            print(f"   ❌ New token failed: {new_me_response.text}")
            print(f"   📝 Response headers: {dict(new_me_response.headers)}")
            
            # Debug: Check if it's a JWT parsing issue
            print("   🔍 Debugging new token...")
            try:
                import jwt
                # Decode without verification to see structure
                decoded = jwt.decode(new_access_token, options={"verify_signature": False})
                print(f"   📝 Token payload: {json.dumps(decoded, indent=2, default=str)}")
            except Exception as jwt_e:
                print(f"   ❌ JWT decode error: {jwt_e}")
            
            return False
            
    except Exception as e:
        print(f"   ❌ New token test error: {e}")
        return False

if __name__ == "__main__":
    success = test_token_refresh()
    if success:
        print("\n🎉 TOKEN REFRESH WORKING!")
    else:
        print("\n❌ TOKEN REFRESH FAILED!") 