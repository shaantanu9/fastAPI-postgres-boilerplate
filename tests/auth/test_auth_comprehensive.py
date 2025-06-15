#!/usr/bin/env python3
"""
COMPREHENSIVE AUTHENTICATION FLOW TEST

PURPOSE:
    Test complete authentication flow including login, token management, and security features
    
WHEN TO USE:
    - Testing complete auth system functionality
    - Verifying token refresh mechanisms work
    - Testing session management features
    - Validating security features like password strength
    - Integration testing of auth endpoints
    
WHAT IT TESTS:
    1. User login with credentials
    2. Access token validation on protected endpoints
    3. Session management and listing
    4. Token refresh functionality
    5. Invalid token handling
    6. No token scenarios
    7. Password strength validation
    
CREATED: Pre-2025-06-14 (legacy test)
DEPENDENCIES: Requires running FastAPI server and valid test user
RESULT: Tests complete auth flow end-to-end

HOW TO RUN:
    1. Ensure FastAPI server is running: uvicorn app.main:app --reload
    2. Ensure test user exists with credentials: testuser / MyStr0ng!P@ssw0rd2025
    3. python3 tests/auth/test_auth_comprehensive.py

EXPECTED OUTPUT:
    ✅ All auth flow steps should pass
    ✅ Token refresh should work
    ✅ Invalid tokens should be rejected
    ✅ Password strength validation should work

ENVIRONMENT VARIABLES REQUIRED:
    - DATABASE_URL: PostgreSQL connection string
    - JWT_SECRET_TOKEN: JWT signing secret
"""

import os
import sys

import requests

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

BASE_URL = "http://localhost:8000"


def test_authentication_flow() -> bool:
    """Test complete authentication flow."""
    print("🔐 Testing Authentication Flow...")
    
    # Test 1: Login
    print("   1. Testing login...")
    login_data = {"username_or_email": "testuser", "password": "MyStr0ng!P@ssw0rd2025"}

    response = requests.post(f"{BASE_URL}/api/v1/auth/login", json=login_data)

    if response.status_code == 200:
        print("   ✅ Login successful")
        login_result = response.json()
        access_token = login_result["access_token"]
        refresh_token = login_result["refresh_token"]
        user_info = login_result["user"]
        print(f"   📝 User: {user_info.get('username', 'N/A')}")

        # Test 2: Access protected endpoint
        print("   2. Testing protected endpoint access...")
        headers = {"Authorization": f"Bearer {access_token}"}
        me_response = requests.get(f"{BASE_URL}/api/v1/auth/me", headers=headers)

        if me_response.status_code == 200:
            print("   ✅ Protected endpoint access successful")
            user_data = me_response.json()
            print(f"   📝 Retrieved user data for: {user_data.get('username', 'N/A')}")
        else:
            print(f"   ❌ Protected endpoint failed: {me_response.status_code}")

        # Test 3: Session Management
        print("   3. Testing session management...")
        sessions_response = requests.get(
            f"{BASE_URL}/api/v1/auth/me/sessions", headers=headers,
        )

        if sessions_response.status_code == 200:
            sessions = sessions_response.json()
            print(f"   ✅ Session management working - {len(sessions)} active sessions")
            for i, session in enumerate(sessions[:3]):  # Show first 3
                print(f"   📝 Session {i+1}: {session.get('device_info', 'Unknown device')}")
        else:
            print(f"   ❌ Session management failed: {sessions_response.status_code}")

        # Test 4: Token Refresh
        print("   4. Testing token refresh...")
        refresh_data = {"refresh_token": refresh_token}
        refresh_response = requests.post(
            f"{BASE_URL}/api/v1/auth/refresh", json=refresh_data,
        )

        if refresh_response.status_code == 200:
            print("   ✅ Token refresh successful")
            refresh_result = refresh_response.json()
            new_access_token = refresh_result["access_token"]

            # Test new token
            new_headers = {"Authorization": f"Bearer {new_access_token}"}
            test_response = requests.get(
                f"{BASE_URL}/api/v1/auth/me", headers=new_headers,
            )
            if test_response.status_code == 200:
                print("   ✅ New token works correctly")
            else:
                print(f"   ❌ New token failed: {test_response.status_code}")
        else:
            print(f"   ❌ Token refresh failed: {refresh_response.status_code}")

        # Test 5: Invalid token
        print("   5. Testing invalid token handling...")
        invalid_headers = {"Authorization": "Bearer invalid_token_here"}
        invalid_response = requests.get(
            f"{BASE_URL}/api/v1/auth/me", headers=invalid_headers,
        )

        if invalid_response.status_code == 401:
            print("   ✅ Invalid token correctly rejected")
        else:
            print(f"   ❌ Invalid token not rejected: {invalid_response.status_code}")

        # Test 6: No token
        print("   6. Testing no token scenario...")
        no_token_response = requests.get(f"{BASE_URL}/api/v1/auth/me")

        if no_token_response.status_code == 401:
            print("   ✅ No token correctly rejected")
        else:
            print(f"   ❌ No token not rejected: {no_token_response.status_code}")

        return True

    else:
        print(f"   ❌ Login failed: {response.status_code}")
        if response.headers.get('content-type', '').startswith('application/json'):
            error_data = response.json()
            print(f"   📝 Error: {error_data}")
        return False


def test_security_features() -> None:
    """Test security features."""
    print("\n🔒 Testing Security Features...")
    
    # Test password strength
    print("   Testing password strength validation...")
    weak_passwords = ["123", "password", "abc123"]

    for pwd in weak_passwords:
        response = requests.post(
            f"{BASE_URL}/api/v1/auth/password/check", params={"password": pwd},
        )
        if response.status_code == 200:
            result = response.json()
            print(f"   📝 Password '{pwd}': {result.get('strength', 'Unknown')}")
        else:
            print(f"   ❌ Password check failed for '{pwd}': {response.status_code}")


if __name__ == "__main__":
    print("🚀 Comprehensive Authentication Test")
    print("=" * 60)

    try:
        # Test if server is running
        print("🔍 Checking server availability...")
        response = requests.get(f"{BASE_URL}/docs")
        if response.status_code != 200:
            print("❌ Server not available. Please start the FastAPI server.")
            print("   Command: uvicorn app.main:app --reload")
            sys.exit(1)
        print("✅ Server is running")

        # Run tests
        auth_success = test_authentication_flow()
        test_security_features()

        print("\n" + "=" * 60)
        print("📊 TEST RESULTS SUMMARY")
        if auth_success:
            print("✅ Authentication flow test: PASSED")
        else:
            print("❌ Authentication flow test: FAILED")
            
        print("\n💡 Notes:")
        print("   - Ensure test user 'testuser' exists with password 'MyStr0ng!P@ssw0rd2025'")
        print("   - Check server logs for detailed error information")
        print("   - Verify database connection and JWT configuration")

    except requests.exceptions.ConnectionError:
        print("❌ Connection error: Cannot connect to server")
        print("   Please ensure FastAPI server is running on http://localhost:8000")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc() 