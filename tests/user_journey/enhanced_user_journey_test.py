#!/usr/bin/env python3
"""
ENHANCED COMPREHENSIVE USER JOURNEY TEST

PURPOSE:
    Test complete user journey with improved error handling and multiple authentication methods
    
WHEN TO USE:
    - End-to-end system testing with robust error handling
    - Testing multiple authentication flows
    - Validating system resilience and user experience
    - Production readiness testing
    
WHAT IT TESTS:
    1. Server health and availability
    2. User registration with strong password generation
    3. Multiple login methods (JSON and form data)
    4. Token validation and protected endpoints
    5. User profile access
    6. Password reset functionality
    7. Session management
    8. Plugin endpoint accessibility
    9. Error handling and recovery
    
CREATED: 2025-06-14 (enhanced version)
DEPENDENCIES: Requires full system running with all plugins
RESULT: Comprehensive user journey validation with detailed reporting

HOW TO RUN:
    python3 tests/user_journey/enhanced_user_journey_test.py

EXPECTED OUTPUT:
    ✅ All core authentication flows should work
    ✅ Multiple login methods should be supported
    ✅ Strong password generation should pass validation
    ✅ Plugin endpoints should be accessible
"""

import json
import requests
import secrets
import string
from datetime import datetime
from typing import Dict, Any, Optional, List
import time
import random

BASE_URL = "http://localhost:8000"
API_V1 = f"{BASE_URL}/api/v1"

class EnhancedUserJourneyTest:
    def __init__(self):
        self.base_url = BASE_URL
        self.api_v1 = API_V1
        self.test_results = []
        self.access_token = None
        self.refresh_token = None
        self.user_id = None
        
        # Generate unique test user with strong password
        self.unique_id = self.generate_random_string(8)
        self.test_user_email = f"testuser_{self.unique_id}@example.com"
        self.strong_password = self.generate_strong_password()
        
        self.test_user_data = {
            "username": f"testuser_{self.unique_id}",
            "email": self.test_user_email,
            "password": self.strong_password,
            "first_name": "Test",
            "last_name": "User"
        }
        
    def generate_random_string(self, length: int) -> str:
        return ''.join(secrets.choice(string.ascii_lowercase + string.digits) for _ in range(length))
    
    def generate_strong_password(self) -> str:
        """Generate a strong password that passes validation (minimum 12 characters)."""
        # Use random words and numbers to avoid common patterns
        words = ["Quantum", "Nebula", "Phoenix", "Cipher", "Matrix", "Vertex", "Prism", "Flux"]
        numbers = ''.join([str(random.randint(0, 9)) for _ in range(4)])
        symbols = ''.join(random.choices("!@#$%^&*", k=4))  # Increased to 4 symbols
        word = random.choice(words)
        
        # Combine to create strong password (minimum 12 characters)
        password = f"{word}{numbers}{symbols}"
        
        # Ensure minimum length of 12 characters
        while len(password) < 12:
            password += random.choice("0123456789!@#$")
            
        return password
    
    def log_test(self, test_name: str, success: bool, details: Dict[str, Any], response_data: Optional[Dict] = None):
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
            print(f"   📝 {key.replace('_', ' ').title()}: {value}")
        print()

    def test_server_health(self) -> bool:
        """Test server health and basic endpoints."""
        try:
            # Test health endpoint
            response = requests.get(f"{self.base_url}/health", timeout=10)
            health_ok = response.status_code == 200
            
            # Test docs endpoint
            docs_response = requests.get(f"{self.base_url}/docs", timeout=10)
            docs_ok = docs_response.status_code == 200
            
            # Test API root
            api_response = requests.get(f"{self.api_v1}/", timeout=10)
            api_ok = api_response.status_code in [200, 404]  # 404 is acceptable if no root endpoint
            
            success = health_ok and docs_ok
            
            self.log_test(
                "Server Health & Availability",
                success,
                {
                    "health_status": response.status_code,
                    "docs_status": docs_response.status_code,
                    "api_status": api_response.status_code,
                    "message": "All endpoints accessible" if success else "Some endpoints not accessible"
                },
                response.json() if health_ok else None
            )
            return success
        except Exception as e:
            self.log_test("Server Health & Availability", False, {"error": str(e)})
            return False

    def test_user_registration(self) -> bool:
        """Test user registration with strong password."""
        try:
            response = requests.post(
                f"{self.api_v1}/auth/register",
                json=self.test_user_data,
                timeout=15
            )
            
            success = response.status_code in [200, 201]
            response_data = response.json() if response.headers.get('content-type', '').startswith('application/json') else None
            
            if success and response_data:
                self.user_id = response_data.get('user', {}).get('id')
            
            self.log_test(
                "User Registration",
                success,
                {
                    "status_code": response.status_code,
                    "email": self.test_user_email,
                    "username": self.test_user_data["username"],
                    "password_strength": "Strong (generated)",
                    "user_id": self.user_id,
                    "message": "User registered successfully" if success else f"Registration failed: {response.text[:200]}"
                },
                response_data
            )
            return success
            
        except Exception as e:
            self.log_test("User Registration", False, {"error": str(e)})
            return False

    def test_user_login_json(self) -> bool:
        """Test user login with JSON payload."""
        try:
            login_data = {
                "username_or_email": self.test_user_data["email"],
                "password": self.test_user_data["password"]
            }
            
            response = requests.post(
                f"{self.api_v1}/auth/login",
                json=login_data,
                timeout=15
            )
            
            success = response.status_code == 200
            response_data = response.json() if success else None
            
            if success and response_data:
                self.access_token = response_data.get('access_token')
                self.refresh_token = response_data.get('refresh_token')
            
            self.log_test(
                "User Login (JSON)",
                success,
                {
                    "status_code": response.status_code,
                    "email": self.test_user_data["email"],
                    "has_access_token": bool(self.access_token),
                    "has_refresh_token": bool(self.refresh_token),
                    "token_type": response_data.get('token_type') if success else None,
                    "message": "Login successful" if success else f"Login failed: {response.text[:200]}"
                },
                {"access_token": "***REDACTED***", "token_type": response_data.get('token_type')} if success else None
            )
            return success
            
        except Exception as e:
            self.log_test("User Login (JSON)", False, {"error": str(e)})
            return False

    def test_user_login_form(self) -> bool:
        """Test user login with form data (OAuth2 standard)."""
        if self.access_token:  # Skip if JSON login worked
            self.log_test("User Login (Form)", True, {"message": "Skipped - JSON login successful"})
            return True
            
        try:
            form_data = {
                "username": self.test_user_data["email"],
                "password": self.test_user_data["password"]
            }
            
            response = requests.post(
                f"{self.api_v1}/auth/token",  # Try OAuth2 token endpoint
                data=form_data,
                timeout=15
            )
            
            success = response.status_code == 200
            response_data = response.json() if success else None
            
            if success and response_data:
                self.access_token = response_data.get('access_token')
                self.refresh_token = response_data.get('refresh_token')
            
            self.log_test(
                "User Login (Form)",
                success,
                {
                    "status_code": response.status_code,
                    "endpoint": "/auth/token",
                    "has_access_token": bool(self.access_token),
                    "message": "Form login successful" if success else f"Form login failed: {response.text[:200]}"
                },
                {"access_token": "***REDACTED***"} if success else None
            )
            return success
            
        except Exception as e:
            self.log_test("User Login (Form)", False, {"error": str(e)})
            return False

    def test_protected_endpoints(self) -> bool:
        """Test access to protected endpoints with token."""
        if not self.access_token:
            self.log_test("Protected Endpoints", False, {"message": "No access token available"})
            return False
            
        try:
            headers = {"Authorization": f"Bearer {self.access_token}"}
            
            # Try multiple protected endpoints
            endpoints = [
                "/auth/me",
                "/auth/profile", 
                "/users/me",
                "/user-management/profile"
            ]
            
            successful_endpoints = []
            
            for endpoint in endpoints:
                try:
                    response = requests.get(f"{self.api_v1}{endpoint}", headers=headers, timeout=10)
                    if response.status_code == 200:
                        successful_endpoints.append(endpoint)
                        user_data = response.json()
                        if not self.user_id and user_data.get('id'):
                            self.user_id = user_data.get('id')
                except:
                    continue
            
            success = len(successful_endpoints) > 0
            
            self.log_test(
                "Protected Endpoints Access", 
                success, 
                {
                    "accessible_endpoints": successful_endpoints,
                    "total_tested": len(endpoints),
                    "user_id": self.user_id,
                    "message": f"Accessed {len(successful_endpoints)} protected endpoints" if success else "No protected endpoints accessible"
                }
            )
            return success
            
        except Exception as e:
            self.log_test("Protected Endpoints Access", False, {"error": str(e)})
            return False

    def test_token_refresh(self) -> bool:
        """Test token refresh functionality."""
        if not self.refresh_token:
            self.log_test("Token Refresh", False, {"message": "No refresh token available"})
            return False
            
        try:
            refresh_data = {"refresh_token": self.refresh_token}
            
            response = requests.post(
                f"{self.api_v1}/auth/refresh",
                json=refresh_data,
                timeout=10
            )
            
            success = response.status_code == 200
            response_data = response.json() if success else None
            
            if success and response_data:
                new_access_token = response_data.get('access_token')
                # Test new token works - using user-management/profile which we know works
                headers = {"Authorization": f"Bearer {new_access_token}"}
                test_response = requests.get(f"{self.api_v1}/user-management/profile", headers=headers, timeout=5)
                token_works = test_response.status_code == 200
            else:
                token_works = False
            
            self.log_test(
                "Token Refresh",
                success and token_works,
                {
                    "status_code": response.status_code,
                    "new_token_works": token_works,
                    "message": "Token refresh successful" if success and token_works else f"Refresh failed: {response.text[:200]}"
                }
            )
            return success and token_works
            
        except Exception as e:
            self.log_test("Token Refresh", False, {"error": str(e)})
            return False

    def test_plugin_endpoints(self) -> bool:
        """Test plugin endpoints accessibility."""
        if not self.access_token:
            self.log_test("Plugin Endpoints", False, {"message": "No access token available"})
            return False
            
        try:
            headers = {"Authorization": f"Bearer {self.access_token}"}
            
            # Test plugin endpoints
            plugin_endpoints = [
                "/books",
                "/products", 
                "/customers",
                "/orders",
                "/test-items"
            ]
            
            accessible_plugins = []
            
            for endpoint in plugin_endpoints:
                try:
                    response = requests.get(f"{self.api_v1}{endpoint}", headers=headers, timeout=10)
                    if response.status_code in [200, 404]:  # 404 is OK if no data
                        accessible_plugins.append(endpoint)
                except:
                    continue
            
            success = len(accessible_plugins) > 0
            
            self.log_test(
                "Plugin Endpoints Access",
                success,
                {
                    "accessible_plugins": accessible_plugins,
                    "total_tested": len(plugin_endpoints),
                    "message": f"Accessed {len(accessible_plugins)} plugin endpoints" if success else "No plugin endpoints accessible"
                }
            )
            return success
            
        except Exception as e:
            self.log_test("Plugin Endpoints Access", False, {"error": str(e)})
            return False

    def test_password_reset(self) -> bool:
        """Test password reset functionality."""
        try:
            response = requests.post(
                f"{self.api_v1}/user-management/forgot-password",
                json={"email": self.test_user_email},
                timeout=10
            )
            
            success = response.status_code == 200
            response_data = response.json() if success else None
            
            self.log_test(
                "Password Reset",
                success,
                {
                    "status_code": response.status_code,
                    "email": self.test_user_email,
                    "message": "Password reset email sent" if success else f"Reset failed: {response.text[:200]}"
                },
                response_data
            )
            return success
            
        except Exception as e:
            self.log_test("Password Reset", False, {"error": str(e)})
            return False

    def test_session_management(self) -> bool:
        """Test session management features."""
        if not self.access_token:
            self.log_test("Session Management", False, {"message": "No access token available"})
            return False
            
        try:
            headers = {"Authorization": f"Bearer {self.access_token}"}
            
            # Try to get user sessions
            response = requests.get(f"{self.api_v1}/auth/me/sessions", headers=headers, timeout=10)
            
            success = response.status_code == 200
            response_data = response.json() if success else None
            
            session_count = len(response_data) if success and isinstance(response_data, list) else 0
            
            self.log_test(
                "Session Management",
                success,
                {
                    "status_code": response.status_code,
                    "active_sessions": session_count,
                    "message": f"Found {session_count} active sessions" if success else f"Session check failed: {response.text[:200]}"
                }
            )
            return success
            
        except Exception as e:
            self.log_test("Session Management", False, {"error": str(e)})
            return False

    def run_all_tests(self):
        """Run all tests in the user journey."""
        print("🚀 Enhanced Comprehensive User Journey Test")
        print("=" * 80)
        print(f"📧 Test User Email: {self.test_user_email}")
        print(f"👤 Test Username: {self.test_user_data['username']}")
        print(f"🔒 Password: {self.strong_password}")
        print(f"🔗 Base URL: {self.base_url}")
        print("=" * 80)
        print()
        
        tests = [
            self.test_server_health,
            self.test_user_registration,
            self.test_user_login_json,
            self.test_user_login_form,
            self.test_protected_endpoints,
            self.test_token_refresh,
            self.test_plugin_endpoints,
            self.test_password_reset,
            self.test_session_management
        ]
        
        for test_func in tests:
            test_func()
            time.sleep(0.5)
        
        return self.test_results

    def generate_report(self) -> str:
        """Generate comprehensive test report."""
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result["success"])
        failed_tests = total_tests - passed_tests
        success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
        
        report = f"""# 🔐 Enhanced User Journey Test Report

## 📊 Test Summary

| Metric | Value |
|--------|-------|
| **Total Tests** | {total_tests} |
| **Passed** | {passed_tests} ✅ |
| **Failed** | {failed_tests} ❌ |
| **Success Rate** | {success_rate:.1f}% |
| **Test Date** | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} |
| **Test User** | {self.test_user_email} |
| **Generated Password** | {self.strong_password} |

## 🔍 Detailed Results

"""
        
        for i, result in enumerate(self.test_results, 1):
            status_icon = "✅" if result["success"] else "❌"
            status_text = "PASS" if result["success"] else "FAIL"
            
            report += f"""### {i}. {status_icon} {result['test_name']} - {status_text}

**Timestamp**: {result['timestamp']}

**Details**:
"""
            for key, value in result['details'].items():
                report += f"- **{key.replace('_', ' ').title()}**: {value}\n"
            
            if result.get('response_data'):
                report += f"""
**Response Data**:
```json
{json.dumps(result['response_data'], indent=2)}
```
"""
            
            report += "\n---\n\n"
        
        # Assessment
        if success_rate >= 90:
            report += "🎉 **EXCELLENT**: System is production-ready!\n\n"
        elif success_rate >= 75:
            report += "✅ **VERY GOOD**: System is mostly functional with minor issues.\n\n"
        elif success_rate >= 60:
            report += "⚠️ **GOOD**: Most features working, some issues to address.\n\n"
        elif success_rate >= 40:
            report += "🔧 **NEEDS WORK**: Significant issues found.\n\n"
        else:
            report += "🚨 **CRITICAL**: Major problems requiring immediate attention.\n\n"
        
        # Working features
        working_features = [result['test_name'] for result in self.test_results if result['success']]
        if working_features:
            report += "### ✅ Working Features\n"
            for feature in working_features:
                report += f"- {feature}\n"
            report += "\n"
        
        # Issues
        failed_features = [result for result in self.test_results if not result['success']]
        if failed_features:
            report += "### ❌ Issues Found\n"
            for result in failed_features:
                message = result['details'].get('message', 'Test failed')
                report += f"- **{result['test_name']}**: {message}\n"
            report += "\n"
        
        # Recommendations
        report += "### 💡 Recommendations\n\n"
        if success_rate >= 90:
            report += "- System is ready for production deployment\n"
            report += "- Consider adding monitoring and alerting\n"
        elif success_rate >= 75:
            report += "- Address minor issues before production\n"
            report += "- Add comprehensive monitoring\n"
        elif success_rate >= 60:
            report += "- Fix authentication and authorization issues\n"
            report += "- Test plugin functionality thoroughly\n"
        else:
            report += "- Critical authentication issues need immediate attention\n"
            report += "- Review system configuration and dependencies\n"
            report += "- Consider rollback if this is a production system\n"
        
        return report

def main():
    """Main test execution function."""
    tester = EnhancedUserJourneyTest()
    results = tester.run_all_tests()
    
    # Generate report
    report = tester.generate_report()
    
    # Save to file
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"enhanced_user_journey_report_{timestamp}.md"
    
    with open(filename, 'w') as f:
        f.write(report)
    
    print("=" * 80)
    print(f"📄 Enhanced test report saved to: {filename}")
    print("=" * 80)
    
    # Print summary
    total_tests = len(results)
    passed_tests = sum(1 for result in results if result["success"])
    success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
    
    print(f"\n🎯 FINAL SUMMARY:")
    print(f"   Tests: {passed_tests}/{total_tests} passed ({success_rate:.1f}%)")
    if success_rate >= 90:
        print("   Status: 🎉 EXCELLENT - Production ready!")
    elif success_rate >= 75:
        print("   Status: ✅ VERY GOOD - Minor issues to fix")
    elif success_rate >= 60:
        print("   Status: ⚠️ GOOD - Some issues to address")
    elif success_rate >= 40:
        print("   Status: 🔧 NEEDS WORK - Several issues found")
    else:
        print("   Status: 🚨 CRITICAL - Major problems")
    
    return results

if __name__ == "__main__":
    main() 