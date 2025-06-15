#!/usr/bin/env python3
"""
ENDPOINT AVAILABILITY DIAGNOSTIC TEST

PURPOSE:
    Test endpoint availability and token validation issues
    
WHEN TO USE:
    - When endpoints return 404
    - When token validation fails
    - Debugging routing issues
    
WHAT IT TESTS:
    1. Available auth endpoints
    2. Token format and validation
    3. Session endpoint accessibility
    4. Router configuration
    
CREATED: 2025-06-14 (diagnostic test)
DEPENDENCIES: Requires running FastAPI server
"""

import requests
import json
from datetime import datetime

BASE_URL = "http://localhost:8000"

def test_endpoint_discovery():
    """Test which auth endpoints are available."""
    print("🔍 ENDPOINT DISCOVERY TEST")
    print("=" * 60)
    
    # Test various auth endpoint patterns
    endpoints_to_test = [
        "/api/v1/auth/me",
        "/api/v1/auth/me/sessions", 
        "/api/v1/auth/refresh",
        "/api/v1/auth/login",
        "/api/v1/user-management/sessions",
        "/api/v1/user-management/profile",
        "/docs",
        "/openapi.json"
    ]
    
    print("Testing endpoint availability (without auth):")
    for endpoint in endpoints_to_test:
        try:
            response = requests.get(f"{BASE_URL}{endpoint}", timeout=5)
            status = response.status_code
            if status == 401:
                print(f"   ✅ {endpoint}: {status} (Auth required - endpoint exists)")
            elif status == 404:
                print(f"   ❌ {endpoint}: {status} (Not found)")
            elif status == 200:
                print(f"   ✅ {endpoint}: {status} (Public endpoint)")
            else:
                print(f"   ⚠️  {endpoint}: {status} (Other status)")
        except Exception as e:
            print(f"   ❌ {endpoint}: ERROR - {e}")

def test_openapi_routes():
    """Check OpenAPI spec for available routes."""
    print("\n📋 OPENAPI ROUTES CHECK")
    print("=" * 60)
    
    try:
        response = requests.get(f"{BASE_URL}/openapi.json", timeout=10)
        if response.status_code == 200:
            openapi_spec = response.json()
            paths = openapi_spec.get("paths", {})
            
            auth_paths = [path for path in paths.keys() if "/auth/" in path]
            user_mgmt_paths = [path for path in paths.keys() if "/user-management/" in path]
            
            print("Auth endpoints in OpenAPI spec:")
            for path in sorted(auth_paths):
                methods = list(paths[path].keys())
                print(f"   ✅ {path}: {methods}")
            
            print("\nUser Management endpoints in OpenAPI spec:")
            for path in sorted(user_mgmt_paths):
                methods = list(paths[path].keys())
                print(f"   ✅ {path}: {methods}")
                
            return auth_paths, user_mgmt_paths
        else:
            print(f"   ❌ Failed to get OpenAPI spec: {response.status_code}")
            return [], []
    except Exception as e:
        print(f"   ❌ Error getting OpenAPI spec: {e}")
        return [], []

def test_token_validation():
    """Test token creation and validation."""
    print("\n🔐 TOKEN VALIDATION TEST")
    print("=" * 60)
    
    # First, create a user and login
    test_user = {
        "username": f"testuser_{datetime.now().strftime('%H%M%S')}",
        "email": f"testuser_{datetime.now().strftime('%H%M%S')}@example.com",
        "first_name": "Test",
        "last_name": "User",
        "password": "Phoenix7002&#"  # Strong password that passes validation
    }
    
    try:
        # Register user
        print("1. Registering test user...")
        reg_response = requests.post(f"{BASE_URL}/api/v1/auth/register", json=test_user, timeout=10)
        if reg_response.status_code != 201:
            print(f"   ❌ Registration failed: {reg_response.status_code} - {reg_response.text}")
            return False
        print(f"   ✅ User registered: {reg_response.status_code}")
        
        # Login
        print("2. Logging in...")
        login_data = {
            "username_or_email": test_user["username"],
            "password": test_user["password"]
        }
        login_response = requests.post(f"{BASE_URL}/api/v1/auth/login", json=login_data, timeout=10)
        if login_response.status_code != 200:
            print(f"   ❌ Login failed: {login_response.status_code} - {login_response.text}")
            return False
        
        login_result = login_response.json()
        access_token = login_result.get("access_token")
        refresh_token = login_result.get("refresh_token")
        
        print(f"   ✅ Login successful: {login_response.status_code}")
        print(f"   📝 Access token length: {len(access_token) if access_token else 0}")
        print(f"   📝 Refresh token length: {len(refresh_token) if refresh_token else 0}")
        
        # Test access token
        print("3. Testing access token...")
        headers = {"Authorization": f"Bearer {access_token}"}
        
        # Try different endpoints with the token
        token_test_endpoints = [
            "/api/v1/auth/me",
            "/api/v1/auth/me/sessions",
            "/api/v1/user-management/profile"
        ]
        
        for endpoint in token_test_endpoints:
            try:
                response = requests.get(f"{BASE_URL}{endpoint}", headers=headers, timeout=5)
                if response.status_code == 200:
                    print(f"   ✅ {endpoint}: {response.status_code} (Token works)")
                elif response.status_code == 404:
                    print(f"   ❌ {endpoint}: {response.status_code} (Endpoint not found)")
                elif response.status_code == 401:
                    print(f"   ❌ {endpoint}: {response.status_code} (Token invalid)")
                else:
                    print(f"   ⚠️  {endpoint}: {response.status_code} (Other status)")
            except Exception as e:
                print(f"   ❌ {endpoint}: ERROR - {e}")
        
        # Test refresh token
        print("4. Testing refresh token...")
        refresh_data = {"refresh_token": refresh_token}
        refresh_response = requests.post(f"{BASE_URL}/api/v1/auth/refresh", json=refresh_data, timeout=10)
        
        if refresh_response.status_code == 200:
            print(f"   ✅ Refresh successful: {refresh_response.status_code}")
            refresh_result = refresh_response.json()
            new_access_token = refresh_result.get("access_token")
            
            # Test new token
            print("5. Testing new access token...")
            new_headers = {"Authorization": f"Bearer {new_access_token}"}
            test_response = requests.get(f"{BASE_URL}/api/v1/user-management/profile", headers=new_headers, timeout=5)
            
            if test_response.status_code == 200:
                print(f"   ✅ New token works: {test_response.status_code}")
            else:
                print(f"   ❌ New token failed: {test_response.status_code} - {test_response.text[:200]}")
                
                # Debug: Check token format
                print(f"   📝 Original token starts with: {access_token[:50]}...")
                print(f"   📝 New token starts with: {new_access_token[:50]}...")
        else:
            print(f"   ❌ Refresh failed: {refresh_response.status_code} - {refresh_response.text}")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Token validation test failed: {e}")
        return False

def main():
    """Run all diagnostic tests."""
    print("🔧 ENDPOINT AVAILABILITY & TOKEN DIAGNOSTIC")
    print("=" * 80)
    
    # Test 1: Endpoint discovery
    test_endpoint_discovery()
    
    # Test 2: OpenAPI routes
    auth_paths, user_mgmt_paths = test_openapi_routes()
    
    # Test 3: Token validation
    token_test_success = test_token_validation()
    
    # Summary
    print("\n" + "=" * 80)
    print("🎯 DIAGNOSTIC SUMMARY:")
    print(f"   OpenAPI Spec Available: {'✅' if auth_paths or user_mgmt_paths else '❌'}")
    print(f"   Auth Endpoints Found: {len(auth_paths)}")
    print(f"   User Mgmt Endpoints Found: {len(user_mgmt_paths)}")
    print(f"   Token Validation: {'✅' if token_test_success else '❌'}")
    
    if auth_paths:
        print(f"\n📋 Available Auth Endpoints:")
        for path in sorted(auth_paths):
            print(f"   - {path}")
    
    if user_mgmt_paths:
        print(f"\n📋 Available User Management Endpoints:")
        for path in sorted(user_mgmt_paths):
            print(f"   - {path}")

if __name__ == "__main__":
    main() 