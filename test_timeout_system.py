#!/usr/bin/env python3
"""
Comprehensive test script for the enhanced timeout system.

This script tests all timeout functionality including:
- Middleware timeout enforcement
- Custom timeout decorators
- Database timeout contexts
- Rate limiting integration
- Error handling and metrics
"""
import asyncio
import aiohttp
import time
import json
import sys
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

@dataclass
class TestResult:
    """Test result container."""
    name: str
    success: bool
    duration: float
    status_code: int
    response: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

class TimeoutSystemTester:
    """Comprehensive timeout system tester."""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.results: List[TestResult] = []
        
    async def run_test(
        self, 
        name: str, 
        endpoint: str, 
        params: Optional[Dict[str, Any]] = None,
        expected_status: int = 200,
        timeout: Optional[float] = None
    ) -> TestResult:
        """Run a single test."""
        print(f"\n🧪 Testing: {name}")
        print(f"   Endpoint: {endpoint}")
        if params:
            print(f"   Params: {params}")
        
        start_time = time.time()
        
        try:
            timeout_config = aiohttp.ClientTimeout(total=timeout) if timeout else None
            
            async with aiohttp.ClientSession(timeout=timeout_config) as session:
                async with session.get(
                    f"{self.base_url}{endpoint}",
                    params=params or {}
                ) as response:
                    duration = time.time() - start_time
                    
                    try:
                        response_data = await response.json()
                    except:
                        response_data = {"text": await response.text()}
                    
                    success = response.status == expected_status
                    
                    result = TestResult(
                        name=name,
                        success=success,
                        duration=duration,
                        status_code=response.status,
                        response=response_data
                    )
                    
                    if success:
                        print(f"   ✅ PASS - {response.status} in {duration:.2f}s")
                    else:
                        print(f"   ❌ FAIL - Expected {expected_status}, got {response.status} in {duration:.2f}s")
                        print(f"   Response: {response_data}")
                    
                    return result
                    
        except asyncio.TimeoutError:
            duration = time.time() - start_time
            result = TestResult(
                name=name,
                success=(expected_status == 504),  # Timeout expected
                duration=duration,
                status_code=504,
                error="Client timeout"
            )
            
            if result.success:
                print(f"   ✅ PASS - Timeout as expected in {duration:.2f}s")
            else:
                print(f"   ❌ FAIL - Unexpected timeout in {duration:.2f}s")
            
            return result
            
        except Exception as e:
            duration = time.time() - start_time
            result = TestResult(
                name=name,
                success=False,
                duration=duration,
                status_code=0,
                error=str(e)
            )
            
            print(f"   ❌ ERROR - {str(e)} in {duration:.2f}s")
            return result
    
    async def test_basic_health_checks(self):
        """Test basic health checks."""
        print("\n" + "="*60)
        print("🏥 BASIC HEALTH CHECKS")
        print("="*60)
        
        # App health
        result = await self.run_test(
            "Application Health Check",
            "/health"
        )
        self.results.append(result)
        
        # Timeout system health
        result = await self.run_test(
            "Timeout System Health",
            "/api/v1/test/timeout/health"
        )
        self.results.append(result)
        
        # Rate limiting health
        result = await self.run_test(
            "Rate Limiting Health",
            "/api/v1/test/rate-limit/health"
        )
        self.results.append(result)
    
    async def test_timeout_functionality(self):
        """Test timeout functionality."""
        print("\n" + "="*60)
        print("⏱️  TIMEOUT FUNCTIONALITY TESTS")
        print("="*60)
        
        # Quick operation (should succeed)
        result = await self.run_test(
            "Quick Operation (1s delay)",
            "/api/v1/test/timeout/quick",
            {"delay": 1.0}
        )
        self.results.append(result)
        
        # Medium operation (should succeed)
        result = await self.run_test(
            "Medium Operation (5s delay)",
            "/api/v1/test/timeout/quick",
            {"delay": 5.0}
        )
        self.results.append(result)
        
        # Slow operation (should timeout with middleware)
        result = await self.run_test(
            "Slow Operation (35s delay - should timeout)",
            "/api/v1/test/timeout/slow",
            {"delay": 35.0},
            expected_status=504,
            timeout=40.0  # Client timeout longer than server
        )
        self.results.append(result)
        
        # Database timeout test
        result = await self.run_test(
            "Database Timeout (12s operation, 10s limit)",
            "/api/v1/test/timeout/database",
            {"operation_time": 12.0},
            expected_status=504
        )
        self.results.append(result)
        
        # Database success test
        result = await self.run_test(
            "Database Success (8s operation, 10s limit)",
            "/api/v1/test/timeout/database",
            {"operation_time": 8.0}
        )
        self.results.append(result)
        
        # Custom timeout test (should timeout)
        result = await self.run_test(
            "Custom Timeout (8s delay, 5s timeout)",
            "/api/v1/test/timeout/custom-timeout",
            {"delay": 8.0, "timeout": 5.0},
            expected_status=504
        )
        self.results.append(result)
        
        # Custom timeout test (should succeed)
        result = await self.run_test(
            "Custom Timeout Success (3s delay, 5s timeout)",
            "/api/v1/test/timeout/custom-timeout",
            {"delay": 3.0, "timeout": 5.0}
        )
        self.results.append(result)
    
    async def test_rate_limiting(self):
        """Test rate limiting functionality."""
        print("\n" + "="*60)
        print("🚦 RATE LIMITING TESTS")
        print("="*60)
        
        # Basic rate limit test
        result = await self.run_test(
            "Basic Rate Limit Test",
            "/api/v1/test/rate-limit/basic-test"
        )
        self.results.append(result)
        
        # Enhanced rate limit test
        result = await self.run_test(
            "Enhanced Rate Limit Test",
            "/api/v1/test/rate-limit/enhanced-test"
        )
        self.results.append(result)
        
        # Rate limiting status
        result = await self.run_test(
            "Rate Limiting Status",
            "/api/v1/test/rate-limit/status"
        )
        self.results.append(result)
        
        # Test rate limit enforcement (multiple requests)
        print("\n🔄 Testing rate limit enforcement...")
        for i in range(3):
            result = await self.run_test(
                f"Rate Limit Enforcement Test {i+1}",
                "/api/v1/test/rate-limit/strict-test"
            )
            self.results.append(result)
            await asyncio.sleep(0.5)  # Small delay between requests
    
    async def test_stress_scenarios(self):
        """Test stress scenarios."""
        print("\n" + "="*60)
        print("💪 STRESS TESTS")
        print("="*60)
        
        # Heavy computation test
        result = await self.run_test(
            "Heavy Computation (5M iterations)",
            "/api/v1/test/timeout/heavy-computation",
            {"iterations": 5000000}
        )
        self.results.append(result)
        
        # Concurrent timeout stress test
        result = await self.run_test(
            "Concurrent Operations Stress Test",
            "/api/v1/test/timeout/stress-test",
            {"concurrent_requests": 3, "delay_per_request": 2.0}
        )
        self.results.append(result)
        
        # Middleware timeout test
        result = await self.run_test(
            "Middleware Timeout Test (25s delay)",
            "/api/v1/test/timeout/middleware-test",
            {"delay": 25.0}
        )
        self.results.append(result)
    
    async def test_metrics_and_monitoring(self):
        """Test metrics and monitoring."""
        print("\n" + "="*60)
        print("📊 METRICS AND MONITORING")
        print("="*60)
        
        # Timeout metrics
        result = await self.run_test(
            "Timeout Metrics",
            "/api/v1/test/timeout/metrics"
        )
        self.results.append(result)
        
        # Rate limiting metrics (if available)
        result = await self.run_test(
            "Rate Limiting Metrics",
            "/api/v1/test/rate-limit/status"
        )
        self.results.append(result)
    
    def print_summary(self):
        """Print test summary."""
        print("\n" + "="*60)
        print("📋 TEST SUMMARY")
        print("="*60)
        
        total_tests = len(self.results)
        passed_tests = sum(1 for r in self.results if r.success)
        failed_tests = total_tests - passed_tests
        
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {passed_tests} ✅")
        print(f"Failed: {failed_tests} ❌")
        print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        
        if failed_tests > 0:
            print(f"\n❌ FAILED TESTS:")
            for result in self.results:
                if not result.success:
                    print(f"   • {result.name}")
                    if result.error:
                        print(f"     Error: {result.error}")
                    else:
                        print(f"     Status: {result.status_code}")
        
        print(f"\n⏱️  PERFORMANCE SUMMARY:")
        durations = [r.duration for r in self.results if r.duration > 0]
        if durations:
            print(f"   Average Duration: {sum(durations)/len(durations):.2f}s")
            print(f"   Max Duration: {max(durations):.2f}s")
            print(f"   Min Duration: {min(durations):.2f}s")
        
        return failed_tests == 0

async def main():
    """Main test runner."""
    print("🚀 Starting Comprehensive Timeout System Tests")
    print("=" * 60)
    
    tester = TimeoutSystemTester()
    
    try:
        # Run all test suites
        await tester.test_basic_health_checks()
        await tester.test_timeout_functionality()
        await tester.test_rate_limiting()
        await tester.test_stress_scenarios()
        await tester.test_metrics_and_monitoring()
        
        # Print summary
        success = tester.print_summary()
        
        if success:
            print("\n🎉 All tests passed! Timeout system is working correctly.")
            sys.exit(0)
        else:
            print("\n⚠️  Some tests failed. Please check the issues above.")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n\n⏹️  Tests interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n💥 Test runner failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    # Check if server is running
    print("🔍 Checking if FastAPI server is running...")
    try:
        import requests
        response = requests.get("http://localhost:8000/health", timeout=5)
        if response.status_code == 200:
            print("✅ Server is running, starting tests...")
            asyncio.run(main())
        else:
            print(f"❌ Server returned status {response.status_code}")
            sys.exit(1)
    except requests.exceptions.RequestException:
        print("❌ Server is not running. Please start the FastAPI server first:")
        print("   uvicorn app.main:app --reload")
        sys.exit(1) 