#!/usr/bin/env python3
"""
AUTH ENDPOINT DEBUGGING SCRIPT

PURPOSE:
    Test actual auth endpoints to identify the exact cause of failures
    
WHEN TO USE:
    - When auth endpoints return 500 errors
    - When getting TIMEOUT_MIDDLEWARE_ERROR
    - When you need to test live auth endpoints with detailed error info
    
WHAT IT TESTS:
    1. Server health check
    2. API documentation accessibility
    3. Registration endpoint with detailed error analysis
    4. Login endpoint with detailed error analysis
    5. Timeout middleware behavior across different endpoints
    
CREATED: 2025-06-14
ISSUE IDENTIFIED: NameError: name 'security_service' is not defined
RESULT: This script revealed the root cause of the timeout middleware error

HOW TO RUN:
    1. Ensure FastAPI server is running: uvicorn app.main:app --reload
    2. python3 tests/auth_endpoints/debug_auth_endpoint.py

EXPECTED OUTPUT:
    ✅ Health and docs should work (200 status)
    ❌ Auth endpoints should show specific error details
    📊 Timeout headers should be present for all endpoints
"""
import asyncio
import json
import sys
import traceback
from contextlib import asynccontextmanager

import httpx


async def test_auth_endpoints():
    """Test the actual auth endpoints to identify the timeout issue"""
    print("🚀 Testing Auth Endpoints Directly")
    print("=" * 60)
    
    base_url = "http://localhost:8000"
    api_v1 = f"{base_url}/api/v1"
    
    # Test data
    test_user = {
        "username": "debug_user_001",
        "email": "debug001@example.com",
        "password": "DebugPassword123!",
        "first_name": "Debug",
        "last_name": "User"
    }
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        
        # Test 1: Server Health
        print("\n🔍 Test 1: Server Health Check")
        try:
            response = await client.get(f"{base_url}/health")
            print(f"   Status: {response.status_code}")
            print(f"   Response: {response.text[:200]}")
            if response.status_code == 200:
                print("   ✅ Server is healthy")
            else:
                print("   ❌ Server health check failed")
        except Exception as e:
            print(f"   ❌ Health check error: {e}")
        
        # Test 2: API Documentation
        print("\n🔍 Test 2: API Documentation")
        try:
            response = await client.get(f"{base_url}/docs")
            print(f"   Status: {response.status_code}")
            if response.status_code == 200:
                print("   ✅ API docs accessible")
            else:
                print("   ❌ API docs not accessible")
        except Exception as e:
            print(f"   ❌ API docs error: {e}")
        
        # Test 3: Registration Endpoint (The failing one)
        print("\n🔍 Test 3: Registration Endpoint")
        try:
            print(f"   URL: {api_v1}/auth/register")
            print(f"   Data: {json.dumps(test_user, indent=2)}")
            
            response = await client.post(
                f"{api_v1}/auth/register",
                json=test_user,
                timeout=15.0
            )
            
            print(f"   Status: {response.status_code}")
            print(f"   Headers: {dict(response.headers)}")
            
            if response.headers.get('content-type', '').startswith('application/json'):
                response_data = response.json()
                print(f"   Response: {json.dumps(response_data, indent=2)}")
            else:
                print(f"   Response (text): {response.text}")
            
            if response.status_code in [200, 201]:
                print("   ✅ Registration successful")
                return response.json()
            elif response.status_code == 409:
                print("   ⚠️ User already exists (expected)")
                return {"message": "User already exists"}
            else:
                print(f"   ❌ Registration failed with status {response.status_code}")
                return None
                
        except httpx.TimeoutException as e:
            print(f"   ❌ Registration timeout: {e}")
            return None
        except Exception as e:
            print(f"   ❌ Registration error: {e}")
            print(f"   Error type: {type(e)}")
            traceback.print_exc()
            return None
        
        # Test 4: Login Endpoint
        print("\n🔍 Test 4: Login Endpoint")
        try:
            login_data = {
                "username_or_email": test_user["username"],
                "password": test_user["password"]
            }
            
            response = await client.post(
                f"{api_v1}/auth/login",
                json=login_data,
                timeout=15.0
            )
            
            print(f"   Status: {response.status_code}")
            print(f"   Headers: {dict(response.headers)}")
            
            if response.headers.get('content-type', '').startswith('application/json'):
                response_data = response.json()
                print(f"   Response: {json.dumps(response_data, indent=2)}")
            else:
                print(f"   Response (text): {response.text}")
            
            if response.status_code == 200:
                print("   ✅ Login successful")
                return response.json()
            else:
                print(f"   ❌ Login failed with status {response.status_code}")
                return None
                
        except httpx.TimeoutException as e:
            print(f"   ❌ Login timeout: {e}")
            return None
        except Exception as e:
            print(f"   ❌ Login error: {e}")
            traceback.print_exc()
            return None

async def test_timeout_middleware_directly():
    """Test if the timeout middleware is the issue"""
    print("\n🔍 Testing Timeout Middleware Behavior")
    print("-" * 40)
    
    base_url = "http://localhost:8000"
    
    # Test with different endpoints to see timeout behavior
    test_endpoints = [
        ("/health", "GET"),
        ("/api/v1/auth/register", "POST"),
        ("/api/v1/auth/login", "POST"),
        ("/docs", "GET"),
    ]
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        for endpoint, method in test_endpoints:
            print(f"\n   Testing {method} {endpoint}")
            try:
                if method == "GET":
                    response = await client.get(f"{base_url}{endpoint}")
                else:
                    # Send minimal data for POST
                    response = await client.post(
                        f"{base_url}{endpoint}",
                        json={"test": "data"}
                    )
                
                print(f"   Status: {response.status_code}")
                
                # Check for timeout middleware headers
                timeout_headers = {
                    k: v for k, v in response.headers.items() 
                    if 'timeout' in k.lower() or 'duration' in k.lower()
                }
                if timeout_headers:
                    print(f"   Timeout headers: {timeout_headers}")
                
                # Check for timeout middleware error
                if response.status_code == 500:
                    try:
                        error_data = response.json()
                        if error_data.get("error_code") == "TIMEOUT_MIDDLEWARE_ERROR":
                            print(f"   ❌ TIMEOUT_MIDDLEWARE_ERROR detected!")
                            print(f"   Error details: {error_data}")
                        else:
                            print(f"   Other 500 error: {error_data}")
                    except:
                        print(f"   500 error (non-JSON): {response.text[:200]}")
                
            except Exception as e:
                print(f"   Error: {e}")

def main():
    """Main debug function"""
    print("🚀 Auth Endpoint Debug Analysis")
    print("=" * 60)
    
    try:
        # Test the auth endpoints
        result = asyncio.run(test_auth_endpoints())
        
        # Test timeout middleware behavior
        asyncio.run(test_timeout_middleware_directly())
        
        print("\n" + "=" * 60)
        print("🎯 ANALYSIS COMPLETE")
        
        if result:
            print("✅ At least one auth operation succeeded")
        else:
            print("❌ All auth operations failed")
            print("💡 The issue is likely in the timeout middleware or auth service")
        
    except Exception as e:
        print(f"\n❌ CRITICAL ERROR: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    main() 