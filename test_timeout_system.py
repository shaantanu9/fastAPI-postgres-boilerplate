#!/usr/bin/env python3
"""Comprehensive test script for the enhanced timeout system.

This script tests all timeout functionality including:
- Middleware timeout enforcement
- Custom timeout decorators
- Database timeout contexts
- Rate limiting integration
- Error handling and metrics
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
        if params:
            pass

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
                        pass
                    else:
                        pass

                    return result

        except TimeoutError:
            duration = time.time() - start_time
            result = TestResult(
                name=name,
                success=(expected_status == 504),  # Timeout expected
                duration=duration,
                status_code=504,
                error="Client timeout",
            )

            if result.success:
                pass
            else:
                pass

            return result

        except Exception as e:
            duration = time.time() - start_time
            return TestResult(
                name=name, success=False, duration=duration, status_code=0, error=str(e),
            )


    async def test_basic_health_checks(self) -> None:
        """Test basic health checks."""
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

        # Test rate limit enforcement (multiple requests)
        for i in range(3):
            result = await self.run_test(
                f"Rate Limit Enforcement Test {i + 1}",
                "/api/v1/test/rate-limit/strict-test",
            )
            self.results.append(result)
            await asyncio.sleep(0.5)  # Small delay between requests

    async def test_stress_scenarios(self) -> None:
        """Test stress scenarios."""
        # Heavy computation test
        result = await self.run_test(
            "Heavy Computation (5M iterations)",
            "/api/v1/test/timeout/heavy-computation",
            {"iterations": 5000000},
        )
        self.results.append(result)

        # Concurrent timeout stress test
        result = await self.run_test(
            "Concurrent Operations Stress Test",
            "/api/v1/test/timeout/stress-test",
            {"concurrent_requests": 3, "delay_per_request": 2.0},
        )
        self.results.append(result)

        # Middleware timeout test
        result = await self.run_test(
            "Middleware Timeout Test (25s delay)",
            "/api/v1/test/timeout/middleware-test",
            {"delay": 25.0},
        )
        self.results.append(result)

    async def test_metrics_and_monitoring(self) -> None:
        """Test metrics and monitoring."""
        # Timeout metrics
        result = await self.run_test("Timeout Metrics", "/api/v1/test/timeout/metrics")
        self.results.append(result)

        # Rate limiting metrics (if available)
        result = await self.run_test(
            "Rate Limiting Metrics", "/api/v1/test/rate-limit/status",
        )
        self.results.append(result)

    def print_summary(self):
        """Print test summary."""
        total_tests = len(self.results)
        passed_tests = sum(1 for r in self.results if r.success)
        failed_tests = total_tests - passed_tests


        if failed_tests > 0:
            for result in self.results:
                if not result.success:
                    if result.error:
                        pass
                    else:
                        pass

        durations = [r.duration for r in self.results if r.duration > 0]
        if durations:
            pass

        return failed_tests == 0


async def main() -> None:
    """Main test runner."""
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
            sys.exit(0)
        else:
            sys.exit(1)

    except KeyboardInterrupt:
        sys.exit(1)
    except Exception:
        sys.exit(1)


if __name__ == "__main__":
    # Check if server is running
    try:
        import requests

        response = requests.get("http://localhost:8000/health", timeout=5)
        if response.status_code == 200:
            asyncio.run(main())
        else:
            sys.exit(1)
    except requests.exceptions.RequestException:
        sys.exit(1)
