#!/usr/bin/env python3
"""
COMPREHENSIVE TIMEOUT SYSTEM TEST

PURPOSE:
    Test all timeout functionality including middleware, decorators, database timeouts, and rate limiting
    
WHEN TO USE:
    - Testing timeout middleware functionality
    - Verifying custom timeout decorators work
    - Testing database timeout contexts
    - Validating rate limiting integration
    - Performance testing under timeout conditions
    - Debugging timeout-related issues
    
WHAT IT TESTS:
    1. Basic health checks for timeout system
    2. Timeout functionality with different delays
    3. Database timeout scenarios
    4. Custom timeout decorators
    5. Rate limiting functionality
    6. Stress testing scenarios
    7. Metrics and monitoring
    
CREATED: Pre-2025-06-14 (legacy system test)
DEPENDENCIES: Requires running FastAPI server with timeout endpoints
RESULT: Comprehensive timeout system validation

HOW TO RUN:
    1. Ensure FastAPI server is running: uvicorn app.main:app --reload
    2. Ensure timeout test endpoints are available
    3. python3 tests/system/test_timeout_system.py

EXPECTED OUTPUT:
    ✅ Health checks should pass
    ✅ Quick operations should succeed
    ✅ Slow operations should timeout appropriately
    ✅ Database timeouts should be enforced
    ✅ Rate limiting should work

TEST ENDPOINTS REQUIRED:
    - /api/v1/test/timeout/health
    - /api/v1/test/timeout/quick
    - /api/v1/test/timeout/slow
    - /api/v1/test/timeout/database
    - /api/v1/test/timeout/custom-timeout
    - /api/v1/test/rate-limit/*
"""

import asyncio
import sys
import time
from dataclasses import dataclass
from typing import Any

import aiohttp


@dataclass
class TestResult:
    """Test result container."""

    name: str
    success: bool
    duration: float
    status_code: int
    response: dict[str, Any] | None = None
    error: str | None = None


class TimeoutSystemTester:
    """Comprehensive timeout system tester."""

    def __init__(self, base_url: str = "http://localhost:8000") -> None:
        self.base_url = base_url
        self.results: list[TestResult] = []

    async def run_test(
        self,
        name: str,
        endpoint: str,
        params: dict[str, Any] | None = None,
        expected_status: int = 200,
        timeout: float | None = None,
    ) -> TestResult:
        """Run a single test."""
        print(f"🔍 Running: {name}")
        
        start_time = time.time()

        try:
            timeout_config = aiohttp.ClientTimeout(total=timeout) if timeout else None

            async with aiohttp.ClientSession(timeout=timeout_config) as session:
                async with session.get(
                    f"{self.base_url}{endpoint}", params=params or {},
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
                        response=response_data,
                    )

                    if success:
                        print(f"   ✅ Success: {response.status} ({duration:.3f}s)")
                    else:
                        print(f"   ❌ Failed: Expected {expected_status}, got {response.status} ({duration:.3f}s)")

                    return result

        except asyncio.TimeoutError:
            duration = time.time() - start_time
            result = TestResult(
                name=name,
                success=(expected_status == 504),  # Timeout expected
                duration=duration,
                status_code=504,
                error="Client timeout",
            )

            if result.success:
                print(f"   ✅ Expected timeout: 504 ({duration:.3f}s)")
            else:
                print(f"   ❌ Unexpected timeout: {duration:.3f}s")

            return result

        except Exception as e:
            duration = time.time() - start_time
            result = TestResult(
                name=name, success=False, duration=duration, status_code=0, error=str(e),
            )
            print(f"   ❌ Error: {e} ({duration:.3f}s)")
            return result


    async def test_basic_health_checks(self) -> None:
        """Test basic health checks."""
        print("\n🏥 Testing Basic Health Checks...")
        
        # App health
        result = await self.run_test("Application Health Check", "/health")
        self.results.append(result)

        # Timeout system health
        result = await self.run_test(
            "Timeout System Health", "/api/v1/test/timeout/health",
        )
        self.results.append(result)

        # Rate limiting health
        result = await self.run_test(
            "Rate Limiting Health", "/api/v1/test/rate-limit/health",
        )
        self.results.append(result)

    async def test_timeout_functionality(self) -> None:
        """Test timeout functionality."""
        print("\n⏱️ Testing Timeout Functionality...")
        
        # Quick operation (should succeed)
        result = await self.run_test(
            "Quick Operation (1s delay)", "/api/v1/test/timeout/quick", {"delay": 1.0},
        )
        self.results.append(result)

        # Medium operation (should succeed)
        result = await self.run_test(
            "Medium Operation (5s delay)", "/api/v1/test/timeout/quick", {"delay": 5.0},
        )
        self.results.append(result)

        # Slow operation (should timeout with middleware)
        result = await self.run_test(
            "Slow Operation (35s delay - should timeout)",
            "/api/v1/test/timeout/slow",
            {"delay": 35.0},
            expected_status=504,
            timeout=40.0,  # Client timeout longer than server
        )
        self.results.append(result)

        # Database timeout test
        result = await self.run_test(
            "Database Timeout (12s operation, 10s limit)",
            "/api/v1/test/timeout/database",
            {"operation_time": 12.0},
            expected_status=504,
        )
        self.results.append(result)

        # Database success test
        result = await self.run_test(
            "Database Success (8s operation, 10s limit)",
            "/api/v1/test/timeout/database",
            {"operation_time": 8.0},
        )
        self.results.append(result)

        # Custom timeout test (should timeout)
        result = await self.run_test(
            "Custom Timeout (8s delay, 5s timeout)",
            "/api/v1/test/timeout/custom-timeout",
            {"delay": 8.0, "timeout": 5.0},
            expected_status=504,
        )
        self.results.append(result)

        # Custom timeout test (should succeed)
        result = await self.run_test(
            "Custom Timeout Success (3s delay, 5s timeout)",
            "/api/v1/test/timeout/custom-timeout",
            {"delay": 3.0, "timeout": 5.0},
        )
        self.results.append(result)

    async def test_rate_limiting(self) -> None:
        """Test rate limiting functionality."""
        print("\n🚦 Testing Rate Limiting...")
        
        # Basic rate limit test
        result = await self.run_test(
            "Basic Rate Limit Test", "/api/v1/test/rate-limit/basic-test",
        )
        self.results.append(result)

        # Enhanced rate limit test
        result = await self.run_test(
            "Enhanced Rate Limit Test", "/api/v1/test/rate-limit/enhanced-test",
        )
        self.results.append(result)

        # Rate limiting status
        result = await self.run_test(
            "Rate Limiting Status", "/api/v1/test/rate-limit/status",
        )
        self.results.append(result)

    async def test_stress_scenarios(self) -> None:
        """Test stress scenarios."""
        print("\n💪 Testing Stress Scenarios...")
        
        # Concurrent requests
        print("   Testing concurrent requests...")
        concurrent_tasks = []
        for i in range(5):
            task = self.run_test(
                f"Concurrent Request {i+1}",
                "/api/v1/test/timeout/quick",
                {"delay": 2.0}
            )
            concurrent_tasks.append(task)
        
        concurrent_results = await asyncio.gather(*concurrent_tasks)
        self.results.extend(concurrent_results)
        
        successful_concurrent = sum(1 for r in concurrent_results if r.success)
        print(f"   📊 Concurrent results: {successful_concurrent}/{len(concurrent_results)} successful")

    async def test_metrics_and_monitoring(self) -> None:
        """Test metrics and monitoring."""
        print("\n📊 Testing Metrics and Monitoring...")
        
        # Metrics endpoint
        result = await self.run_test(
            "Timeout Metrics", "/api/v1/test/timeout/metrics",
        )
        self.results.append(result)

    def print_summary(self):
        """Print test summary."""
        print("\n" + "=" * 60)
        print("📊 TIMEOUT SYSTEM TEST SUMMARY")
        print("=" * 60)
        
        total_tests = len(self.results)
        successful_tests = sum(1 for r in self.results if r.success)
        success_rate = (successful_tests / total_tests) * 100 if total_tests > 0 else 0
        
        print(f"📈 Success Rate: {success_rate:.1f}% ({successful_tests}/{total_tests})")
        
        # Calculate average duration
        durations = [r.duration for r in self.results if r.duration is not None]
        avg_duration = sum(durations) / len(durations) if durations else 0
        print(f"⏱️ Average Duration: {avg_duration:.3f}s")
        
        print("\n📋 Individual Test Results:")
        for result in self.results:
            status = "✅" if result.success else "❌"
            duration_str = f"{result.duration:.3f}s" if result.duration else "N/A"
            print(f"   {status} {result.name}: {result.status_code} ({duration_str})")
            if not result.success and result.error:
                print(f"      Error: {result.error}")
        
        # Recommendations
        print("\n💡 Recommendations:")
        if success_rate == 100:
            print("   🎉 All timeout tests passed! System is working correctly.")
        elif success_rate >= 80:
            print("   ✅ Timeout system is mostly functional with minor issues.")
        elif success_rate >= 60:
            print("   ⚠️ Timeout system has significant issues that need attention.")
        else:
            print("   ❌ Timeout system has critical issues requiring immediate attention.")


async def main() -> None:
    """Main test function."""
    print("🚀 Comprehensive Timeout System Test")
    print("=" * 60)
    
    tester = TimeoutSystemTester()
    
    try:
        # Check if server is running
        print("🔍 Checking server availability...")
        result = await tester.run_test("Server Check", "/health")
        if not result.success:
            print("❌ Server not available. Please start the FastAPI server.")
            print("   Command: uvicorn app.main:app --reload")
            return
        print("✅ Server is running")
        
        # Run all test suites
        await tester.test_basic_health_checks()
        await tester.test_timeout_functionality()
        await tester.test_rate_limiting()
        await tester.test_stress_scenarios()
        await tester.test_metrics_and_monitoring()
        
        # Print summary
        tester.print_summary()
        
    except Exception as e:
        print(f"❌ Test execution failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main()) 