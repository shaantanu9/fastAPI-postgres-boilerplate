#!/usr/bin/env python3
"""Simple token test without complex middleware."""

import requests
import json
from datetime import datetime

BASE_URL = "http://localhost:8000"

def simple_test():
    """Simple test focused on token refresh."""
    print("🔧 SIMPLE TOKEN REFRESH TEST")
    print("=" * 40)
    
    # Use existing endpoint that we know works
    try:
        # Try the endpoint that worked in our tests
        response = requests.get(f"{BASE_URL}/api/v1/user-management/profile", headers={
            "Authorization": "Bearer invalid_token"
        }, timeout=5)
        
        print(f"Profile endpoint status: {response.status_code}")
        if response.status_code == 401:
            print("✅ Endpoint correctly rejects invalid token")
        else:
            print(f"Response: {response.text[:200]}")
            
    except Exception as e:
        print(f"Error testing endpoint: {e}")
    
    # Test token refresh endpoint directly
    print("\nTesting refresh endpoint...")
    try:
        refresh_response = requests.post(f"{BASE_URL}/api/v1/auth/refresh", json={
            "refresh_token": "invalid_refresh_token"
        }, timeout=5)
        
        print(f"Refresh endpoint status: {refresh_response.status_code}")
        print(f"Response: {refresh_response.text[:200]}")
        
    except Exception as e:
        print(f"Error testing refresh: {e}")

if __name__ == "__main__":
    simple_test() 