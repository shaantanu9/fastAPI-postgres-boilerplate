#!/usr/bin/env python3
"""
Rate limiting test script.

This script tests the rate limiting functionality by making requests
to the test endpoints and verifying the responses.
"""
import asyncio
import aiohttp
import time
import json
from typing import Dict, Any

# Configuration
BASE_URL = "http://localhost:8000"
TEST_ENDPOINTS = [
    "/api/v1/test/rate-limit/basic-test",      # 5/minute
    "/api/v1/test/rate-limit/strict-test",     # 2/minute  
    "/api/v1/test/rate-limit/enhanced-test",   # Uses default limit
]

async def make_request(session: aiohttp.ClientSession, url: str) -> Dict[str, Any]:
    """Make a request and return response info."""
    try:
        start_time = time.time()
        async with session.get(url) as response:
            duration = time.time() - start_time
            
            # Get rate limit headers
            headers = dict(response.headers)
            rate_limit_headers = {
                k: v for k, v in headers.items() 
                if k.lower().startswith(('x-ratelimit', 'retry-after'))
            }
            
            return {
                "status": response.status,
                "duration": round(duration * 1000, 2),  # ms
                "rate_limit_headers": rate_limit_headers,
                "content": await response.text() if response.status != 200 else "Success"
            }
            
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "duration": 0,
            "rate_limit_headers": {},
            "content": ""
        }

async def test_endpoint(session: aiohttp.ClientSession, endpoint: str, num_requests: int = 10):
    """Test an endpoint with multiple requests."""
    print(f"\n🧪 Testing endpoint: {endpoint}")
    print(f"Making {num_requests} requests...")
    
    url = f"{BASE_URL}{endpoint}"
    results = []
    
    for i in range(num_requests):
        result = await make_request(session, url)
        results.append(result)
        
        # Print result
        status_emoji = "✅" if result["status"] == 200 else "❌" if result["status"] == 429 else "⚠️"
        print(f"  {status_emoji} Request {i+1}: Status {result['status']}, Duration: {result['duration']}ms")
        
        if result["rate_limit_headers"]:
            for header, value in result["rate_limit_headers"].items():
                print(f"    {header}: {value}")
        
        # Small delay between requests
        await asyncio.sleep(0.1)
    
    # Summary
    success_count = sum(1 for r in results if r["status"] == 200)
    rate_limited_count = sum(1 for r in results if r["status"] == 429)
    error_count = sum(1 for r in results if r["status"] not in [200, 429])
    
    print(f"\n📊 Summary for {endpoint}:")
    print(f"  ✅ Successful: {success_count}")
    print(f"  🚫 Rate Limited: {rate_limited_count}")
    print(f"  ⚠️  Errors: {error_count}")
    
    return results

async def check_status():
    """Check rate limiting system status."""
    print("\n🔍 Checking rate limiting system status...")
    
    async with aiohttp.ClientSession() as session:
        # Check health
        health_url = f"{BASE_URL}/api/v1/test/rate-limit/health"
        health_result = await make_request(session, health_url)
        
        if health_result["status"] == 200:
            print("✅ Rate limiting system is healthy")
        else:
            print(f"⚠️ Rate limiting system health check failed: {health_result['status']}")
        
        # Check status and metrics
        status_url = f"{BASE_URL}/api/v1/test/rate-limit/status"
        status_result = await make_request(session, status_url)
        
        if status_result["status"] == 200:
            try:
                content = json.loads(status_result["content"])
                metrics = content.get("metrics", {})
                config = content.get("config", {})
                
                print("\n📈 Metrics:")
                for key, value in metrics.items():
                    print(f"  {key}: {value}")
                
                print("\n⚙️ Configuration:")
                for key, value in config.items():
                    print(f"  {key}: {value}")
                    
            except json.JSONDecodeError:
                print("❌ Could not parse status response")
        else:
            print(f"❌ Could not get status: {status_result['status']}")

async def reset_rate_limits():
    """Reset rate limits for testing."""
    print("\n🔄 Resetting rate limits...")
    
    async with aiohttp.ClientSession() as session:
        reset_url = f"{BASE_URL}/api/v1/test/rate-limit/reset"
        
        try:
            async with session.post(reset_url) as response:
                if response.status == 200:
                    result = await response.json()
                    print(f"✅ Reset successful: {result.get('message', 'Unknown')}")
                else:
                    print(f"❌ Reset failed: {response.status}")
        except Exception as e:
            print(f"❌ Reset error: {e}")

async def main():
    """Main test function."""
    print("🚀 Starting Rate Limiting Tests")
    print("=" * 50)
    
    # Check initial status
    await check_status()
    
    # Reset rate limits
    await reset_rate_limits()
    
    # Test each endpoint
    async with aiohttp.ClientSession() as session:
        for endpoint in TEST_ENDPOINTS:
            await test_endpoint(session, endpoint, num_requests=8)
            
            # Wait a bit before next endpoint
            await asyncio.sleep(1)
    
    # Check final status
    print("\n" + "=" * 50)
    await check_status()
    
    print("\n🎉 Rate limiting tests completed!")
    print("\nTo test rate limiting manually:")
    print("1. Make rapid requests to: http://localhost:8000/api/v1/test/rate-limit/strict-test")
    print("2. Check status at: http://localhost:8000/api/v1/test/rate-limit/status")
    print("3. Reset limits with: curl -X POST http://localhost:8000/api/v1/test/rate-limit/reset")

if __name__ == "__main__":
    asyncio.run(main()) 