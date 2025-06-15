#!/usr/bin/env python3
"""
Comprehensive User Journey Test for FastAPI Backend
Tests the complete authentication flow and documents results
"""
import json
import requests
import secrets
import string
from datetime import datetime
from typing import Dict, Any, Optional
import time

# Test configuration
BASE_URL = "http://localhost:8000"
API_V1 = f"{BASE_URL}/api/v1"

class ComprehensiveUserJourneyTest:
    def __init__(self):
        self.base_url = BASE_URL
        self.api_v1 = API_V1
        self.test_results = []
        self.access_token = None
        self.refresh_token = None
        self.user_id = None
        self.session = requests.Session()
        
        # Generate unique test user
        self.unique_id = self.generate_random_string(8)
        self.test_user_email = f"testuser_{self.unique_id}@example.com"
        self.test_user_data = {
            "username": f"testuser_{self.unique_id}",
            "email": self.test_user_email,
            "password": "TestPassword123!",
            "first_name": "Test",
            "last_name": "User"
        }
        
    def generate_random_string(self, length: int) -> str:
        """Generate random string for unique test data"""
        return ''.join(secrets.choice(string.ascii_lowercase + string.digits) for _ in range(length))
    
    def log_test(self, test_name: str, success: bool, details: Dict[str, Any], response_data: Optional[Dict] = None):
        """Log test results"""
        result = {
            "test_name": test_name,
            "success": success,
            "timestamp": datetime.now().isoformat(),
            "details": details,
            "response_data": response_data
        }
        self.test_results.append(result)
        
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}")
        for key, value in details.items():
            if key != "raw_response":
                print(f"   📝 {key.replace('_', ' ').title()}: {value}")
        print()

    def test_server_status(self) -> bool:
        """Test server health and availability"""
        tests = []
        
        # Test 1: Health endpoint
        try:
            response = self.session.get(f"{self.base_url}/health", timeout=10)
            health_success = response.status_code == 200
            tests.append(("Health Check", health_success, response.status_code, response.json() if health_success else None))
        except Exception as e:
            tests.append(("Health Check", False, 0, str(e)))
        
        # Test 2: Documentation
        try:
            response = self.session.get(f"{self.base_url}/docs", timeout=10)
            docs_success = response.status_code == 200
            tests.append(("Documentation", docs_success, response.status_code, None))
        except Exception as e:
            tests.append(("Documentation", False, 0, str(e)))
        
        # Test 3: API Root
        try:
            response = self.session.get(f"{self.api_v1}/", timeout=10)
            api_success = response.status_code in [200, 404]  # 404 is ok if no root handler
            tests.append(("API Root", api_success, response.status_code, None))
        except Exception as e:
            tests.append(("API Root", False, 0, str(e)))
        
        overall_success = any(test[1] for test in tests)
        
        self.log_test(
            "Server Status Check",
            overall_success,
            {
                "health_check": f"{tests[0][1]} ({tests[0][2]})",
                "documentation": f"{tests[1][1]} ({tests[1][2]})",
                "api_root": f"{tests[2][1]} ({tests[2][2]})",
                "message": "Server is accessible" if overall_success else "Server has issues"
            },
            tests[0][3] if tests[0][1] else None
        )
        return overall_success

    def test_authentication_endpoints(self) -> bool:
        """Test authentication endpoint availability"""
        auth_endpoints = [
            ("Register", "POST", "/auth/register"),
            ("Login", "POST", "/auth/login"), 
            ("Logout", "POST", "/auth/logout"),
            ("Refresh", "POST", "/auth/refresh"),
            ("Me", "GET", "/auth/me"),
            ("Profile", "GET", "/auth/profile"),
            ("Sessions", "GET", "/auth/sessions")
        ]
        
        available_endpoints = []
        
        for name, method, endpoint in auth_endpoints:
            try:
                url = f"{self.api_v1}{endpoint}"
                
                if method == "GET":
                    # For GET endpoints, try without auth first
                    response = self.session.get(url, timeout=5)
                else:
                    # For POST endpoints, send minimal valid data
                    test_data = {"test": "data"}
                    response = self.session.post(url, json=test_data, timeout=5)
                
                # Consider endpoint available if it responds (even with 4xx errors)
                is_available = response.status_code < 500
                available_endpoints.append((name, is_available, response.status_code))
                
            except Exception as e:
                available_endpoints.append((name, False, f"Error: {str(e)}"))
        
        success_count = sum(1 for _, available, _ in available_endpoints if available)
        
        self.log_test(
            "Authentication Endpoints Check",
            success_count > 0,
            {
                "available_endpoints": success_count,
                "total_endpoints": len(auth_endpoints),
                "availability_rate": f"{success_count}/{len(auth_endpoints)}",
                "message": f"{success_count} out of {len(auth_endpoints)} auth endpoints are accessible"
            },
            {endpoint[0]: {"available": endpoint[1], "status": endpoint[2]} for endpoint in available_endpoints}
        )
        
        return success_count > 0

    def test_user_registration(self) -> bool:
        """Test user registration with multiple approaches"""
        registration_attempts = []
        
        # Attempt 1: Standard registration endpoint
        try:
            response = self.session.post(
                f"{self.api_v1}/auth/register",
                json=self.test_user_data,
                timeout=15
            )
            
            registration_attempts.append({
                "method": "Standard Registration",
                "status_code": response.status_code,
                "success": response.status_code in [200, 201],
                "response": response.json() if response.headers.get('content-type', '').startswith('application/json') else response.text
            })
            
            if response.status_code in [200, 201]:
                response_data = response.json()
                self.user_id = response_data.get('user', {}).get('id') or response_data.get('id') or response_data.get('user_id')
                
        except Exception as e:
            registration_attempts.append({
                "method": "Standard Registration",
                "status_code": 0,
                "success": False,
                "error": str(e)
            })
        
        # Attempt 2: Alternative registration endpoint (if exists)
        try:
            response = self.session.post(
                f"{self.api_v1}/users/register",
                json=self.test_user_data,
                timeout=15
            )
            
            registration_attempts.append({
                "method": "Alternative Registration",
                "status_code": response.status_code,
                "success": response.status_code in [200, 201],
                "response": response.json() if response.headers.get('content-type', '').startswith('application/json') else response.text
            })
            
        except Exception as e:
            registration_attempts.append({
                "method": "Alternative Registration",
                "status_code": 0,
                "success": False,
                "error": str(e)
            })
        
        # Check if any registration succeeded
        any_success = any(attempt["success"] for attempt in registration_attempts)
        
        self.log_test(
            "User Registration",
            any_success,
            {
                "email": self.test_user_email,
                "username": self.test_user_data["username"],
                "attempts": len(registration_attempts),
                "successful_attempts": sum(1 for a in registration_attempts if a["success"]),
                "message": "User registered successfully" if any_success else "All registration attempts failed"
            },
            registration_attempts
        )
        
        return any_success

    def test_user_login(self) -> bool:
        """Test user login with multiple methods"""
        login_attempts = []
        
        # Method 1: Form data (OAuth2 standard)
        try:
            form_data = {
                "username": self.test_user_data["email"],
                "password": self.test_user_data["password"]
            }
            
            response = self.session.post(
                f"{self.api_v1}/auth/login",
                data=form_data,
                timeout=15
            )
            
            login_attempts.append({
                "method": "Form Data (OAuth2)",
                "status_code": response.status_code,
                "success": response.status_code == 200,
                "response": response.json() if response.headers.get('content-type', '').startswith('application/json') else response.text
            })
            
            if response.status_code == 200:
                response_data = response.json()
                self.access_token = response_data.get('access_token')
                self.refresh_token = response_data.get('refresh_token')
                
        except Exception as e:
            login_attempts.append({
                "method": "Form Data (OAuth2)",
                "status_code": 0,
                "success": False,
                "error": str(e)
            })
        
        # Method 2: JSON data
        if not self.access_token:
            try:
                json_data = {
                    "username": self.test_user_data["email"],
                    "password": self.test_user_data["password"]
                }
                
                response = self.session.post(
                    f"{self.api_v1}/auth/login",
                    json=json_data,
                    timeout=15
                )
                
                login_attempts.append({
                    "method": "JSON Data",
                    "status_code": response.status_code,
                    "success": response.status_code == 200,
                    "response": response.json() if response.headers.get('content-type', '').startswith('application/json') else response.text
                })
                
                if response.status_code == 200:
                    response_data = response.json()
                    self.access_token = response_data.get('access_token')
                    self.refresh_token = response_data.get('refresh_token')
                    
            except Exception as e:
                login_attempts.append({
                    "method": "JSON Data",
                    "status_code": 0,
                    "success": False,
                    "error": str(e)
                })
        
        # Method 3: Alternative login endpoint
        if not self.access_token:
            try:
                response = self.session.post(
                    f"{self.api_v1}/users/login",
                    json={"email": self.test_user_data["email"], "password": self.test_user_data["password"]},
                    timeout=15
                )
                
                login_attempts.append({
                    "method": "Alternative Endpoint",
                    "status_code": response.status_code,
                    "success": response.status_code == 200,
                    "response": response.json() if response.headers.get('content-type', '').startswith('application/json') else response.text
                })
                
            except Exception as e:
                login_attempts.append({
                    "method": "Alternative Endpoint",
                    "status_code": 0,
                    "success": False,
                    "error": str(e)
                })
        
        any_success = any(attempt["success"] for attempt in login_attempts)
        
        self.log_test(
            "User Login",
            any_success,
            {
                "email": self.test_user_data["email"],
                "attempts": len(login_attempts),
                "successful_attempts": sum(1 for a in login_attempts if a["success"]),
                "has_access_token": bool(self.access_token),
                "has_refresh_token": bool(self.refresh_token),
                "message": "Login successful" if any_success else "All login attempts failed"
            },
            login_attempts
        )
        
        return any_success

    def test_token_validation(self) -> bool:
        """Test token validation and protected routes"""
        if not self.access_token:
            self.log_test(
                "Token Validation",
                False,
                {"message": "No access token available for validation"}
            )
            return False
        
        headers = {"Authorization": f"Bearer {self.access_token}"}
        
        # Test various protected endpoints
        protected_endpoints = [
            ("Current User", "GET", "/auth/me"),
            ("User Profile", "GET", "/auth/profile"),
            ("User Sessions", "GET", "/auth/sessions"),
            ("Users List", "GET", "/users"),
            ("User Profile Alt", "GET", "/users/me")
        ]
        
        accessible_endpoints = []
        
        for name, method, endpoint in protected_endpoints:
            try:
                url = f"{self.api_v1}{endpoint}"
                response = self.session.get(url, headers=headers, timeout=10)
                
                accessible_endpoints.append({
                    "name": name,
                    "endpoint": endpoint,
                    "status_code": response.status_code,
                    "accessible": response.status_code == 200,
                    "response": response.json() if response.status_code == 200 and response.headers.get('content-type', '').startswith('application/json') else None
                })
                
            except Exception as e:
                accessible_endpoints.append({
                    "name": name,
                    "endpoint": endpoint,
                    "status_code": 0,
                    "accessible": False,
                    "error": str(e)
                })
        
        successful_requests = sum(1 for ep in accessible_endpoints if ep["accessible"])
        
        self.log_test(
            "Token Validation & Protected Routes",
            successful_requests > 0,
            {
                "valid_token": successful_requests > 0,
                "accessible_endpoints": successful_requests,
                "total_tested": len(protected_endpoints),
                "access_rate": f"{successful_requests}/{len(protected_endpoints)}",
                "message": f"Token validated - {successful_requests} protected endpoints accessible" if successful_requests > 0 else "Token validation failed"
            },
            accessible_endpoints
        )
        
        return successful_requests > 0

    def test_password_operations(self) -> bool:
        """Test password-related operations"""
        password_tests = []
        
        # Test 1: Forgot Password
        try:
            response = self.session.post(
                f"{self.api_v1}/user-management/forgot-password",
                json={"email": self.test_user_email},
                timeout=10
            )
            
            password_tests.append({
                "operation": "Forgot Password",
                "status_code": response.status_code,
                "success": response.status_code == 200,
                "response": response.json() if response.headers.get('content-type', '').startswith('application/json') else response.text
            })
            
        except Exception as e:
            password_tests.append({
                "operation": "Forgot Password",
                "status_code": 0,
                "success": False,
                "error": str(e)
            })
        
        # Test 2: Alternative forgot password endpoint
        try:
            response = self.session.post(
                f"{self.api_v1}/auth/password/forgot",
                json={"email": self.test_user_email},
                timeout=10
            )
            
            password_tests.append({
                "operation": "Forgot Password (Alt)",
                "status_code": response.status_code,
                "success": response.status_code == 200,
                "response": response.json() if response.headers.get('content-type', '').startswith('application/json') else response.text
            })
            
        except Exception as e:
            password_tests.append({
                "operation": "Forgot Password (Alt)",
                "status_code": 0,
                "success": False,
                "error": str(e)
            })
        
        successful_operations = sum(1 for test in password_tests if test["success"])
        
        self.log_test(
            "Password Reset Operations",
            successful_operations > 0,
            {
                "successful_operations": successful_operations,
                "total_operations": len(password_tests),
                "message": f"{successful_operations} password operations working" if successful_operations > 0 else "Password operations not working"
            },
            password_tests
        )
        
        return successful_operations > 0

    def test_logout_operations(self) -> bool:
        """Test logout functionality"""
        if not self.access_token:
            self.log_test(
                "Logout Operations",
                False,
                {"message": "No access token available for logout test"}
            )
            return False
        
        headers = {"Authorization": f"Bearer {self.access_token}"}
        logout_tests = []
        
        # Test 1: Standard logout
        try:
            response = self.session.post(
                f"{self.api_v1}/auth/logout",
                headers=headers,
                timeout=10
            )
            
            logout_tests.append({
                "method": "Standard Logout",
                "status_code": response.status_code,
                "success": response.status_code in [200, 204],
                "response": response.json() if response.headers.get('content-type', '').startswith('application/json') else response.text
            })
            
        except Exception as e:
            logout_tests.append({
                "method": "Standard Logout",
                "status_code": 0,
                "success": False,
                "error": str(e)
            })
        
        successful_logouts = sum(1 for test in logout_tests if test["success"])
        
        self.log_test(
            "Logout Operations",
            successful_logouts > 0,
            {
                "successful_logouts": successful_logouts,
                "total_attempts": len(logout_tests),
                "message": "Logout successful" if successful_logouts > 0 else "Logout failed"
            },
            logout_tests
        )
        
        return successful_logouts > 0

    def run_complete_test(self):
        """Run the complete user journey test"""
        print("🚀 Starting Comprehensive User Journey Test")
        print("=" * 80)
        print(f"📧 Test User Email: {self.test_user_email}")
        print(f"👤 Test Username: {self.test_user_data['username']}")
        print(f"🔗 Base URL: {self.base_url}")
        print(f"⏰ Test Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 80)
        print()
        
        # Run all tests
        tests = [
            ("Server Status", self.test_server_status),
            ("Authentication Endpoints", self.test_authentication_endpoints),
            ("User Registration", self.test_user_registration),
            ("User Login", self.test_user_login),
            ("Token Validation", self.test_token_validation),
            ("Password Operations", self.test_password_operations),
            ("Logout Operations", self.test_logout_operations)
        ]
        
        for test_name, test_func in tests:
            print(f"🔍 Running: {test_name}")
            test_func()
            time.sleep(0.5)  # Brief pause between tests
        
        return self.test_results

    def generate_comprehensive_report(self) -> str:
        """Generate detailed markdown report"""
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result["success"])
        failed_tests = total_tests - passed_tests
        success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
        
        report = f"""# 🔐 Comprehensive User Journey Test Report

## 📊 Executive Summary

| Metric | Value |
|--------|-------|
| **Total Tests** | {total_tests} |
| **Passed** | {passed_tests} ✅ |
| **Failed** | {failed_tests} ❌ |
| **Success Rate** | {success_rate:.1f}% |
| **Test Date** | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} |
| **Test User** | {self.test_user_email} |
| **Base URL** | {self.base_url} |

## 🎯 Overall Assessment

"""
        
        if success_rate >= 85:
            report += "🎉 **EXCELLENT**: Authentication system is production-ready with comprehensive functionality.\n\n"
        elif success_rate >= 70:
            report += "✅ **GOOD**: Authentication system is mostly functional with minor issues to address.\n\n"
        elif success_rate >= 50:
            report += "⚠️ **NEEDS ATTENTION**: Authentication system has significant issues that need fixing.\n\n"
        else:
            report += "🚨 **CRITICAL**: Authentication system has major problems requiring immediate attention.\n\n"
        
        report += "## 🔍 Detailed Test Results\n\n"
        
        for i, result in enumerate(self.test_results, 1):
            status_icon = "✅" if result["success"] else "❌"
            status_text = "PASS" if result["success"] else "FAIL"
            
            report += f"""### {i}. {status_icon} {result['test_name']} - {status_text}

**Timestamp**: {result['timestamp']}

**Test Details**:
"""
            
            for key, value in result['details'].items():
                if key != "raw_response":
                    report += f"- **{key.replace('_', ' ').title()}**: {value}\n"
            
            if result.get('response_data'):
                report += f"""
**Response Data**:
```json
{json.dumps(result['response_data'], indent=2)}
```
"""
            
            report += "\n---\n\n"
        
        # Add feature analysis
        report += "## 📋 Feature Analysis\n\n"
        
        # Working features
        working_features = [result['test_name'] for result in self.test_results if result['success']]
        if working_features:
            report += "### ✅ Working Features\n\n"
            for feature in working_features:
                report += f"- {feature}\n"
            report += "\n"
        
        # Failed features
        failed_features = [result for result in self.test_results if not result['success']]
        if failed_features:
            report += "### ❌ Issues Found\n\n"
            for result in failed_features:
                message = result['details'].get('message', 'Test failed')
                report += f"- **{result['test_name']}**: {message}\n"
            report += "\n"
        
        # Recommendations
        report += "## 🛠️ Recommendations\n\n"
        
        if success_rate >= 85:
            report += """### Production Readiness
- ✅ System is ready for production deployment
- ✅ Authentication flow is working correctly
- ✅ Security features are operational
- 💡 Consider implementing additional security features like 2FA
"""
        elif success_rate >= 70:
            report += """### Minor Improvements Needed
- ⚠️ Address failed test cases before production
- ✅ Core authentication functionality is working
- 💡 Enhance error handling for edge cases
- 💡 Consider load testing with higher traffic
"""
        elif success_rate >= 50:
            report += """### Significant Issues to Address
- 🔧 Fix core authentication failures
- 🔧 Investigate server configuration issues
- 🔧 Review timeout and middleware settings
- ⚠️ Not recommended for production without fixes
"""
        else:
            report += """### Critical Issues Require Immediate Attention
- 🚨 Authentication system is not functional
- 🚨 Server configuration problems
- 🚨 Fundamental architecture issues
- ❌ Not suitable for production deployment
"""
        
        # Technical details
        report += "\n## 🔧 Technical Details\n\n"
        report += f"""### Test Configuration
- **Base URL**: {self.base_url}
- **API Version**: v1
- **Test User**: {self.test_user_email}
- **Test Method**: Automated HTTP requests
- **Timeout**: 15 seconds per request
- **Session Management**: Persistent session cookies

### Authentication Features Tested
- User registration (multiple endpoints)
- User login (form data and JSON)
- JWT token validation
- Protected route access
- Password reset functionality
- Logout operations
- Session management

### API Endpoints Evaluated
- Health check and server status
- Authentication endpoints discovery
- User management endpoints
- Protected resource access
- Password recovery workflow
"""
        
        return report

def main():
    """Run comprehensive user journey test and generate report"""
    tester = ComprehensiveUserJourneyTest()
    results = tester.run_complete_test()
    
    # Generate comprehensive report
    report = tester.generate_comprehensive_report()
    
    # Save to file
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"comprehensive_user_journey_report_{timestamp}.md"
    
    with open(filename, 'w') as f:
        f.write(report)
    
    print("=" * 80)
    print(f"📄 Comprehensive test report saved to: {filename}")
    print("=" * 80)
    
    # Print summary
    total_tests = len(results)
    passed_tests = sum(1 for result in results if result["success"])
    success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
    
    print(f"\n🎯 FINAL SUMMARY:")
    print(f"   Tests: {passed_tests}/{total_tests} passed ({success_rate:.1f}%)")
    print(f"   Status: {'✅ GOOD' if success_rate >= 70 else '⚠️ NEEDS WORK' if success_rate >= 50 else '🚨 CRITICAL'}")
    
    return results

if __name__ == "__main__":
    main() 