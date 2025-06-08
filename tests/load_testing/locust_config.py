"""
Load Testing Configuration with Locust

Comprehensive performance testing suite for FastAPI application.
Tests various endpoints under different load scenarios.
"""

import json
import random
import time
from datetime import datetime
from typing import Dict, Any, List
from locust import HttpUser, task, between, events
from locust.runners import MasterRunner, WorkerRunner

# Test configuration
BASE_URL = "http://localhost:8000"
API_PREFIX = "/api/v1"

# Test data pools
TEST_USERS = [
    {"email": f"test{i}@example.com", "password": "TestPassword123!"} 
    for i in range(100)
]

TEST_ORGANIZATIONS = [
    {"name": f"Test Org {i}", "description": f"Organization {i} for testing"}
    for i in range(20)
]

class AuthenticatedUser(HttpUser):
    """Simulates authenticated user behavior"""
    
    wait_time = between(1, 3)  # Wait 1-3 seconds between requests
    weight = 3  # Higher weight = more users of this type
    
    def on_start(self):
        """Setup: Register and login user"""
        self.user_data = random.choice(TEST_USERS)
        self.token = None
        self.user_id = None
        self.org_id = None
        
        # Register user
        registration_data = {
            "email": self.user_data["email"],
            "password": self.user_data["password"],
            "username": self.user_data["email"].split("@")[0],
            "first_name": "Test",
            "last_name": "User"
        }
        
        with self.client.post(
            f"{API_PREFIX}/auth/register",
            json=registration_data,
            catch_response=True
        ) as response:
            if response.status_code in [200, 201, 409]:  # 409 = already exists
                # Login user
                self.login()
            else:
                response.failure(f"Registration failed: {response.status_code}")
    
    def login(self):
        """Login and get authentication token"""
        login_data = {
            "username": self.user_data["email"],
            "password": self.user_data["password"]
        }
        
        with self.client.post(
            f"{API_PREFIX}/auth/login",
            data=login_data,
            catch_response=True
        ) as response:
            if response.status_code == 200:
                data = response.json()
                self.token = data.get("access_token")
                self.user_id = data.get("user", {}).get("id")
                
                if self.token:
                    # Set authorization header for subsequent requests
                    self.client.headers.update({"Authorization": f"Bearer {self.token}"})
                    response.success()
                else:
                    response.failure("No token in response")
            else:
                response.failure(f"Login failed: {response.status_code}")
    
    @task(5)
    def view_profile(self):
        """View user profile - high frequency task"""
        if not self.token:
            return
            
        self.client.get(f"{API_PREFIX}/users/me", name="GET /users/me")
    
    @task(3)
    def list_organizations(self):
        """List organizations - medium frequency"""
        if not self.token:
            return
            
        self.client.get(f"{API_PREFIX}/organizations/", name="GET /organizations/")
    
    @task(2)
    def create_organization(self):
        """Create organization - lower frequency"""
        if not self.token:
            return
            
        org_data = random.choice(TEST_ORGANIZATIONS).copy()
        org_data["name"] = f"{org_data['name']} {int(time.time())}"
        
        with self.client.post(
            f"{API_PREFIX}/organizations/",
            json=org_data,
            catch_response=True,
            name="POST /organizations/"
        ) as response:
            if response.status_code in [200, 201]:
                self.org_id = response.json().get("id")
                response.success()
    
    @task(4)
    def health_check(self):
        """Health check endpoints"""
        endpoints = ["/health", "/ready", f"{API_PREFIX}/health"]
        endpoint = random.choice(endpoints)
        self.client.get(endpoint, name=f"GET {endpoint}")
    
    @task(1)
    def error_dashboard(self):
        """Access error dashboard"""
        if not self.token:
            return
            
        self.client.get(f"{API_PREFIX}/errors/dashboard", name="GET /errors/dashboard")

class AnonymousUser(HttpUser):
    """Simulates anonymous/unauthenticated user behavior"""
    
    wait_time = between(2, 5)
    weight = 1  # Lower weight = fewer users
    
    @task(10)
    def health_check(self):
        """Health check - most common anonymous request"""
        self.client.get("/health")
    
    @task(5)
    def docs_access(self):
        """API documentation access"""
        endpoints = ["/docs", "/redoc", "/openapi.json"]
        endpoint = random.choice(endpoints)
        self.client.get(endpoint, name=f"GET {endpoint}")
    
    @task(2)
    def metrics_access(self):
        """Metrics endpoint access"""
        self.client.get(f"{API_PREFIX}/health/metrics", name="GET /health/metrics")
    
    @task(1)
    def rate_limit_test(self):
        """Test rate limiting"""
        self.client.get(f"{API_PREFIX}/rate-limit/test", name="GET /rate-limit/test")

class AdminUser(HttpUser):
    """Simulates admin user with elevated permissions"""
    
    wait_time = between(3, 8)
    weight = 1  # Very few admin users
    
    def on_start(self):
        """Login as admin user"""
        self.token = None
        
        # Use predefined admin credentials
        admin_data = {
            "username": "admin@example.com",
            "password": "AdminPassword123!"
        }
        
        with self.client.post(
            f"{API_PREFIX}/auth/login",
            data=admin_data,
            catch_response=True
        ) as response:
            if response.status_code == 200:
                data = response.json()
                self.token = data.get("access_token")
                if self.token:
                    self.client.headers.update({"Authorization": f"Bearer {self.token}"})
    
    @task(3)
    def monitoring_dashboard(self):
        """Access monitoring dashboards"""
        if not self.token:
            return
            
        endpoints = [
            f"{API_PREFIX}/monitoring/metrics",
            f"{API_PREFIX}/monitoring/performance",
            f"{API_PREFIX}/monitoring/alerts"
        ]
        
        for endpoint in endpoints:
            self.client.get(endpoint, name=f"GET {endpoint}")
    
    @task(2)
    def plugin_management(self):
        """Plugin management operations"""
        if not self.token:
            return
            
        self.client.get("/plugins/status", name="GET /plugins/status")
    
    @task(1)
    def system_health(self):
        """Detailed system health check"""
        if not self.token:
            return
            
        self.client.get(f"{API_PREFIX}/plugins/system/health", name="GET /plugins/system/health")

class DatabaseStressUser(HttpUser):
    """Simulates database-intensive operations"""
    
    wait_time = between(1, 2)
    weight = 1
    
    def on_start(self):
        """Setup authenticated user for database operations"""
        self.user_data = random.choice(TEST_USERS)
        self.token = None
        
        # Quick login
        login_data = {
            "username": self.user_data["email"],
            "password": self.user_data["password"]
        }
        
        response = self.client.post(f"{API_PREFIX}/auth/login", data=login_data)
        if response.status_code == 200:
            self.token = response.json().get("access_token")
            if self.token:
                self.client.headers.update({"Authorization": f"Bearer {self.token}"})
    
    @task(3)
    def complex_queries(self):
        """Simulate complex database queries"""
        if not self.token:
            return
            
        # Paginated queries with filters
        params = {
            "page": random.randint(1, 10),
            "size": random.randint(10, 50),
            "sort": random.choice(["created_at", "name", "id"])
        }
        
        self.client.get(
            f"{API_PREFIX}/organizations/",
            params=params,
            name="GET /organizations/ (paginated)"
        )
    
    @task(2)
    def concurrent_writes(self):
        """Simulate concurrent write operations"""
        if not self.token:
            return
            
        # Create multiple resources rapidly
        for i in range(3):
            org_data = {
                "name": f"Stress Test Org {int(time.time())}_{i}",
                "description": f"Created by stress test {i}"
            }
            
            self.client.post(
                f"{API_PREFIX}/organizations/",
                json=org_data,
                name="POST /organizations/ (stress)"
            )

# Load testing scenarios
class LoadTestScenarios:
    """Predefined load testing scenarios"""
    
    @staticmethod
    def normal_load():
        """Normal production-like load"""
        return {
            "users": 50,
            "spawn_rate": 2,  # Users per second
            "run_time": "10m"
        }
    
    @staticmethod
    def peak_load():
        """Peak traffic simulation"""
        return {
            "users": 200,
            "spawn_rate": 10,
            "run_time": "15m"
        }
    
    @staticmethod
    def stress_test():
        """Stress test beyond normal capacity"""
        return {
            "users": 500,
            "spawn_rate": 20,
            "run_time": "20m"
        }
    
    @staticmethod
    def spike_test():
        """Sudden traffic spike"""
        return {
            "users": 100,
            "spawn_rate": 50,  # Very fast ramp-up
            "run_time": "5m"
        }

# Event handlers for advanced monitoring
@events.request.add_listener
def on_request(request_type, name, response_time, response_length, exception, context, **kwargs):
    """Log detailed request information"""
    if exception:
        print(f"Request failed: {request_type} {name} - {exception}")
    elif response_time > 2000:  # Log slow requests (>2s)
        print(f"Slow request: {request_type} {name} - {response_time}ms")

@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Log test start information"""
    print(f"🚀 Load test starting with {environment.runner.target_user_count} users")
    print(f"Target host: {environment.host}")

@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Generate test summary"""
    stats = environment.runner.stats
    
    print("\n" + "="*50)
    print("📊 LOAD TEST SUMMARY")
    print("="*50)
    print(f"Total requests: {stats.total.num_requests}")
    print(f"Failed requests: {stats.total.num_failures}")
    print(f"Average response time: {stats.total.avg_response_time:.2f}ms")
    print(f"95th percentile: {stats.total.get_response_time_percentile(0.95):.2f}ms")
    print(f"99th percentile: {stats.total.get_response_time_percentile(0.99):.2f}ms")
    print(f"Requests per second: {stats.total.current_rps:.2f}")
    print(f"Failure rate: {(stats.total.num_failures / max(stats.total.num_requests, 1) * 100):.2f}%")
    
    # Performance thresholds
    avg_response_time = stats.total.avg_response_time
    p95_response_time = stats.total.get_response_time_percentile(0.95)
    failure_rate = stats.total.num_failures / max(stats.total.num_requests, 1) * 100
    
    print("\n🎯 PERFORMANCE EVALUATION:")
    
    # Response time evaluation
    if avg_response_time < 200:
        print("✅ Average response time: EXCELLENT")
    elif avg_response_time < 500:
        print("✅ Average response time: GOOD")
    elif avg_response_time < 1000:
        print("⚠️  Average response time: ACCEPTABLE")
    else:
        print("❌ Average response time: POOR")
    
    # 95th percentile evaluation
    if p95_response_time < 500:
        print("✅ 95th percentile: EXCELLENT")
    elif p95_response_time < 1000:
        print("✅ 95th percentile: GOOD")
    elif p95_response_time < 2000:
        print("⚠️  95th percentile: ACCEPTABLE")
    else:
        print("❌ 95th percentile: POOR")
    
    # Failure rate evaluation
    if failure_rate < 0.1:
        print("✅ Failure rate: EXCELLENT")
    elif failure_rate < 1:
        print("✅ Failure rate: GOOD")
    elif failure_rate < 5:
        print("⚠️  Failure rate: ACCEPTABLE")
    else:
        print("❌ Failure rate: POOR")
    
    print("\n📈 RECOMMENDATIONS:")
    if avg_response_time > 1000:
        print("- Consider optimizing slow endpoints")
        print("- Review database query performance")
        print("- Check for resource bottlenecks")
    
    if failure_rate > 5:
        print("- Investigate error causes")
        print("- Check error logs for patterns")
        print("- Review rate limiting configuration")
    
    if p95_response_time > 2000:
        print("- Focus on optimizing worst-case scenarios")
        print("- Consider implementing caching")
        print("- Review timeout configurations")

# Custom configuration for different environments
class EnvironmentConfig:
    """Environment-specific configurations"""
    
    DEVELOPMENT = {
        "host": "http://localhost:8000",
        "users": 10,
        "spawn_rate": 2,
        "run_time": "2m"
    }
    
    STAGING = {
        "host": "https://staging.example.com",
        "users": 50,
        "spawn_rate": 5,
        "run_time": "5m"
    }
    
    PRODUCTION = {
        "host": "https://api.example.com",
        "users": 100,
        "spawn_rate": 10,
        "run_time": "10m"
    }

# Usage examples and CLI commands
"""
Basic usage:
locust -f locust_config.py --host=http://localhost:8000

Specific scenario:
locust -f locust_config.py --host=http://localhost:8000 -u 50 -r 5 -t 10m

Headless mode with report:
locust -f locust_config.py --host=http://localhost:8000 -u 100 -r 10 -t 15m --headless --html report.html

Distributed testing:
# Master
locust -f locust_config.py --master --host=http://localhost:8000

# Workers
locust -f locust_config.py --worker --master-host=127.0.0.1

Custom user mix:
locust -f locust_config.py --host=http://localhost:8000 AuthenticatedUser:80 AnonymousUser:20
""" 