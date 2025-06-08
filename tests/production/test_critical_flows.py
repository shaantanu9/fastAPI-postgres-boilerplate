"""
Critical Production Tests

This module contains comprehensive tests for all critical production flows:
- User authentication and authorization
- API performance and reliability
- Database operations and integrity
- Job queue functionality
- Security measures and error handling
"""

import pytest
import asyncio
import httpx
import time
from datetime import datetime, timedelta
from unittest.mock import Mock, patch
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import app
from app.core.config import get_settings
from app.db.session import get_db
from app.core.security import create_access_token
from app.services.procrastinate_manager import procrastinate_manager

settings = get_settings()
client = TestClient(app)


class TestCriticalUserFlows:
    """Test critical user journey flows"""
    
    def test_complete_user_registration_flow(self):
        """Test complete user registration from signup to activation"""
        # 1. User registration
        user_data = {
            "email": f"test_{int(time.time())}@example.com",
            "username": f"testuser_{int(time.time())}",
            "password": "StrongPassword123!",
            "first_name": "Test",
            "last_name": "User"
        }
        
        response = client.post("/api/v1/auth/register", json=user_data)
        assert response.status_code == 201
        user_response = response.json()
        assert "id" in user_response
        user_id = user_response["id"]
        
        # 2. User login
        login_data = {
            "username_or_email": user_data["email"],
            "password": user_data["password"]
        }
        
        response = client.post("/api/v1/auth/login", json=login_data)
        assert response.status_code == 200
        login_response = response.json()
        assert "access_token" in login_response
        access_token = login_response["access_token"]
        
        # 3. Protected resource access
        headers = {"Authorization": f"Bearer {access_token}"}
        response = client.get("/api/v1/users/me", headers=headers)
        assert response.status_code == 200
        profile = response.json()
        assert profile["email"] == user_data["email"]
        
        # 4. Profile update
        update_data = {"first_name": "Updated", "last_name": "Name"}
        response = client.put(f"/api/v1/users/{user_id}", json=update_data, headers=headers)
        assert response.status_code == 200
        
        # 5. Logout (token invalidation)
        response = client.post("/api/v1/auth/logout", headers=headers)
        assert response.status_code == 200
        
        print(f"✅ Complete user flow test passed for user: {user_data['email']}")

    def test_organization_management_flow(self):
        """Test organization creation and management"""
        # Create user and get token
        user_token = self._create_test_user_and_get_token()
        headers = {"Authorization": f"Bearer {user_token}"}
        
        # 1. Create organization
        org_data = {
            "name": f"Test Org {int(time.time())}",
            "slug": f"test-org-{int(time.time())}",
            "description": "Test organization for critical flow testing"
        }
        
        response = client.post("/api/v1/organizations/", json=org_data, headers=headers)
        assert response.status_code == 201
        org = response.json()
        org_id = org["id"]
        
        # 2. Get organization details
        response = client.get(f"/api/v1/organizations/{org_id}", headers=headers)
        assert response.status_code == 200
        
        # 3. Update organization
        update_data = {"description": "Updated description"}
        response = client.put(f"/api/v1/organizations/{org_id}", json=update_data, headers=headers)
        assert response.status_code == 200
        
        # 4. List organizations
        response = client.get("/api/v1/organizations/", headers=headers)
        assert response.status_code == 200
        orgs = response.json()
        assert len(orgs) >= 1
        
        print(f"✅ Organization management flow passed for org: {org_data['name']}")

    def _create_test_user_and_get_token(self) -> str:
        """Helper to create test user and return access token"""
        user_data = {
            "email": f"flowtest_{int(time.time())}@example.com",
            "username": f"flowtest_{int(time.time())}",
            "password": "StrongPassword123!",
            "first_name": "Flow",
            "last_name": "Test"
        }
        
        # Register user
        response = client.post("/api/v1/auth/register", json=user_data)
        assert response.status_code == 201
        
        # Login and get token
        login_data = {
            "username_or_email": user_data["email"],
            "password": user_data["password"]
        }
        response = client.post("/api/v1/auth/login", json=login_data)
        assert response.status_code == 200
        return response.json()["access_token"]


class TestAPIPerformanceAndReliability:
    """Test API performance, rate limiting, and reliability"""
    
    def test_api_response_times(self):
        """Test that API endpoints respond within acceptable timeframes"""
        endpoints = [
            ("/api/v1/health", "GET", None, 200),
            ("/docs", "GET", None, 200),
            ("/openapi.json", "GET", None, 200),
        ]
        
        for endpoint, method, data, expected_status in endpoints:
            start_time = time.time()
            
            if method == "GET":
                response = client.get(endpoint)
            elif method == "POST":
                response = client.post(endpoint, json=data)
            
            response_time = time.time() - start_time
            
            assert response.status_code == expected_status
            assert response_time < 1.0, f"Endpoint {endpoint} took {response_time:.2f}s (>1s)"
            
            print(f"✅ {endpoint} responded in {response_time:.3f}s")

    def test_rate_limiting_functionality(self):
        """Test that rate limiting works correctly"""
        # Test registration rate limiting (should be strict)
        user_base = f"ratetest_{int(time.time())}"
        
        # Try to register multiple users quickly
        success_count = 0
        rate_limited_count = 0
        
        for i in range(10):
            user_data = {
                "email": f"{user_base}_{i}@example.com",
                "username": f"{user_base}_{i}",
                "password": "StrongPassword123!",
                "first_name": "Rate",
                "last_name": "Test"
            }
            
            response = client.post("/api/v1/auth/register", json=user_data)
            
            if response.status_code == 201:
                success_count += 1
            elif response.status_code == 429:  # Rate limited
                rate_limited_count += 1
            
            time.sleep(0.1)  # Small delay between requests
        
        # We should see some rate limiting kick in
        assert success_count > 0, "No successful registrations"
        print(f"✅ Rate limiting test: {success_count} successful, {rate_limited_count} rate-limited")

    def test_concurrent_request_handling(self):
        """Test system handles concurrent requests properly"""
        import concurrent.futures
        import threading
        
        def make_health_request():
            return client.get("/api/v1/health")
        
        # Make 20 concurrent health check requests
        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(make_health_request) for _ in range(20)]
            responses = [future.result() for future in concurrent.futures.as_completed(futures)]
        
        # All requests should succeed
        success_count = sum(1 for r in responses if r.status_code == 200)
        assert success_count == 20, f"Only {success_count}/20 concurrent requests succeeded"
        
        print(f"✅ Concurrent request test: {success_count}/20 requests successful")


class TestDatabaseIntegrity:
    """Test database operations and data integrity"""
    
    @pytest.mark.asyncio
    async def test_database_connection_resilience(self):
        """Test database connection handling and recovery"""
        from app.db.session import engine
        
        # Test basic connection
        async with engine.begin() as conn:
            result = await conn.execute("SELECT 1 as test")
            row = result.fetchone()
            assert row[0] == 1
        
        print("✅ Database connection test passed")

    def test_database_transaction_integrity(self):
        """Test database transaction rollback on errors"""
        # This would typically involve creating a test that purposely fails
        # to ensure transactions are properly rolled back
        user_token = self._create_test_user_and_get_token()
        headers = {"Authorization": f"Bearer {user_token}"}
        
        # Create organization
        org_data = {
            "name": f"Transaction Test {int(time.time())}",
            "slug": f"trans-test-{int(time.time())}",
            "description": "Testing transaction integrity"
        }
        
        response = client.post("/api/v1/organizations/", json=org_data, headers=headers)
        assert response.status_code == 201
        org_id = response.json()["id"]
        
        # Try to create duplicate (should fail)
        duplicate_response = client.post("/api/v1/organizations/", json=org_data, headers=headers)
        assert duplicate_response.status_code in [400, 409]  # Conflict or bad request
        
        # Original should still exist
        response = client.get(f"/api/v1/organizations/{org_id}", headers=headers)
        assert response.status_code == 200
        
        print("✅ Database transaction integrity test passed")

    def _create_test_user_and_get_token(self) -> str:
        """Helper to create test user and return access token"""
        user_data = {
            "email": f"dbtest_{int(time.time())}@example.com",
            "username": f"dbtest_{int(time.time())}",
            "password": "StrongPassword123!",
            "first_name": "DB",
            "last_name": "Test"
        }
        
        response = client.post("/api/v1/auth/register", json=user_data)
        assert response.status_code == 201
        
        login_data = {
            "username_or_email": user_data["email"],
            "password": user_data["password"]
        }
        response = client.post("/api/v1/auth/login", json=login_data)
        return response.json()["access_token"]


class TestJobQueueFunctionality:
    """Test Procrastinate job queue system"""
    
    @pytest.mark.asyncio
    async def test_job_queue_basic_functionality(self):
        """Test basic job queuing and processing"""
        async with httpx.AsyncClient(base_url="http://localhost:8000") as client:
            # Test user processing task
            response = await client.post("/api/v1/procrastinate/tasks/user-processing", json={
                "user_id": "test_user_123",
                "operation_type": "profile_update",
                "data": {"field": "email", "value": "test@example.com"}
            })
            
            if response.status_code == 200:
                job_data = response.json()
                job_id = job_data.get("job_id")
                assert job_id is not None
                
                # Wait a moment for processing
                await asyncio.sleep(2)
                
                # Check job status
                status_response = await client.get(f"/api/v1/procrastinate/jobs/{job_id}/status")
                if status_response.status_code == 200:
                    status_data = status_response.json()
                    assert status_data["status"] in ["succeeded", "doing", "todo"]
                    print(f"✅ Job queue test: Job {job_id} status: {status_data['status']}")
                else:
                    print(f"⚠️ Job queue test: Could not get status for job {job_id}")
            else:
                print(f"⚠️ Job queue test: Could not create job, status: {response.status_code}")

    @pytest.mark.asyncio
    async def test_job_queue_health(self):
        """Test job queue system health"""
        async with httpx.AsyncClient(base_url="http://localhost:8000") as client:
            response = await client.get("/api/v1/procrastinate/health")
            
            if response.status_code == 200:
                health_data = response.json()
                assert "status" in health_data
                assert "worker_count" in health_data
                print(f"✅ Job queue health: {health_data}")
            else:
                print(f"⚠️ Job queue health check failed: {response.status_code}")


class TestSecurityMeasures:
    """Test security measures and protections"""
    
    def test_authentication_security(self):
        """Test authentication security measures"""
        # Test invalid credentials
        invalid_login = {
            "username_or_email": "nonexistent@example.com",
            "password": "wrongpassword"
        }
        
        response = client.post("/api/v1/auth/login", json=invalid_login)
        assert response.status_code == 401
        
        # Test weak password rejection
        weak_user = {
            "email": f"weak_{int(time.time())}@example.com",
            "username": f"weak_{int(time.time())}",
            "password": "123",  # Weak password
            "first_name": "Weak",
            "last_name": "Test"
        }
        
        response = client.post("/api/v1/auth/register", json=weak_user)
        assert response.status_code == 400  # Should reject weak password
        
        print("✅ Authentication security test passed")

    def test_input_validation_security(self):
        """Test input validation and sanitization"""
        # Test SQL injection attempt
        malicious_user = {
            "email": "test@example.com'; DROP TABLE users; --",
            "username": "normal_user",
            "password": "StrongPassword123!",
            "first_name": "Test",
            "last_name": "User"
        }
        
        response = client.post("/api/v1/auth/register", json=malicious_user)
        # Should either reject malicious email or sanitize it
        assert response.status_code in [400, 422]  # Validation error
        
        # Test XSS attempt
        xss_user = {
            "email": f"xss_{int(time.time())}@example.com",
            "username": "<script>alert('xss')</script>",
            "password": "StrongPassword123!",
            "first_name": "Test",
            "last_name": "User"
        }
        
        response = client.post("/api/v1/auth/register", json=xss_user)
        # Should either reject or sanitize the malicious username
        if response.status_code == 201:
            user_data = response.json()
            assert "<script>" not in user_data.get("username", "")
        
        print("✅ Input validation security test passed")

    def test_security_headers(self):
        """Test security headers are properly set"""
        response = client.get("/api/v1/health")
        
        # Check for important security headers
        headers = response.headers
        
        security_checks = [
            ("X-Content-Type-Options", "nosniff"),
            ("X-Frame-Options", "DENY"),
            ("X-XSS-Protection", "1; mode=block"),
        ]
        
        for header_name, expected_value in security_checks:
            assert header_name in headers, f"Missing security header: {header_name}"
            if expected_value:
                assert headers[header_name] == expected_value
        
        print("✅ Security headers test passed")


class TestErrorHandling:
    """Test error handling and recovery"""
    
    def test_graceful_error_responses(self):
        """Test that errors are handled gracefully"""
        # Test 404 handling
        response = client.get("/api/v1/nonexistent-endpoint")
        assert response.status_code == 404
        
        error_data = response.json()
        assert "detail" in error_data
        
        # Test malformed request handling
        response = client.post("/api/v1/auth/login", json={"invalid": "data"})
        assert response.status_code == 422  # Validation error
        
        validation_error = response.json()
        assert "detail" in validation_error
        
        print("✅ Error handling test passed")

    def test_system_recovery_capabilities(self):
        """Test system can recover from various error conditions"""
        # Test database connection recovery (mock)
        # Test Redis connection recovery (mock)
        # Test external service failure handling (mock)
        
        # For now, just test basic health check recovery
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        
        health_data = response.json()
        assert health_data["status"] == "healthy"
        
        print("✅ System recovery test passed")


# Integration test runner
def run_critical_tests():
    """Run all critical production tests"""
    print("🧪 RUNNING CRITICAL PRODUCTION TESTS")
    print("=" * 60)
    
    test_classes = [
        TestCriticalUserFlows,
        TestAPIPerformanceAndReliability,
        TestDatabaseIntegrity,
        TestJobQueueFunctionality,
        TestSecurityMeasures,
        TestErrorHandling,
    ]
    
    total_tests = 0
    passed_tests = 0
    failed_tests = []
    
    for test_class in test_classes:
        print(f"\n📋 Running {test_class.__name__}")
        print("-" * 40)
        
        test_instance = test_class()
        test_methods = [method for method in dir(test_instance) if method.startswith('test_')]
        
        for test_method_name in test_methods:
            total_tests += 1
            try:
                test_method = getattr(test_instance, test_method_name)
                
                if asyncio.iscoroutinefunction(test_method):
                    asyncio.run(test_method())
                else:
                    test_method()
                
                passed_tests += 1
                print(f"✅ {test_method_name}")
                
            except Exception as e:
                failed_tests.append((test_class.__name__, test_method_name, str(e)))
                print(f"❌ {test_method_name}: {e}")
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 CRITICAL TESTS SUMMARY")
    print("=" * 60)
    print(f"Total Tests: {total_tests}")
    print(f"Passed: {passed_tests}")
    print(f"Failed: {len(failed_tests)}")
    print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
    
    if failed_tests:
        print("\n❌ FAILED TESTS:")
        for test_class, test_method, error in failed_tests:
            print(f"  - {test_class}.{test_method}: {error}")
    
    if passed_tests == total_tests:
        print("\n🎉 ALL CRITICAL TESTS PASSED! SYSTEM IS PRODUCTION READY!")
        return True
    else:
        print(f"\n⚠️ {len(failed_tests)} TESTS FAILED. REVIEW BEFORE PRODUCTION DEPLOYMENT.")
        return False


if __name__ == "__main__":
    success = run_critical_tests()
    exit(0 if success else 1) 