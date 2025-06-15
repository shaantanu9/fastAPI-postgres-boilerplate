#!/usr/bin/env python3
"""
Comprehensive User Journey Test for FastAPI Backend
Tests registration, login, authentication, and protected routes
"""
import asyncio
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

class UserJourneyTester:
    def __init__(self):
        self.base_url = BASE_URL
        self.api_v1 = API_V1
        self.test_results = []
        self.access_token = None
        self.refresh_token = None
        self.user_id = None
        self.test_user_email = f"test_{self.generate_random_string(8)}@example.com"
        self.test_user_data = {
            "username": f"testuser_{self.generate_random_string(6)}",
            "email": self.test_user_email,
            "password": "SecureTestPassword123!",
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
        if details.get("message"):
            print(f"   📝 {details['message']}")
        if not success and details.get("error"):
            print(f"   🚨 Error: {details['error']}")
        print()

    def test_server_health(self) -> bool:
        """Test if server is running and responsive"""
        try:
            response = requests.get(f"{self.base_url}/health", timeout=5)
            success = response.status_code == 200
            
            self.log_test(
                "Server Health Check",
                success,
                {
                    "status_code": response.status_code,
                    "message": "Server is running and responsive" if success else "Server health check failed"
                },
                response.json() if success else None
            )
            return success
        except Exception as e:
            self.log_test(
                "Server Health Check", 
                False, 
                {"error": str(e), "message": "Server is not accessible"}
            )
            return False

    def test_api_documentation(self) -> bool:
        """Test API documentation accessibility"""
        try:
            response = requests.get(f"{self.base_url}/docs", timeout=5)
            success = response.status_code == 200
            
            self.log_test(
                "API Documentation Access",
                success,
                {
                    "status_code": response.status_code,
                    "message": "API docs accessible" if success else "API docs not accessible"
                }
            )
            return success
        except Exception as e:
            self.log_test(
                "API Documentation Access",
                False,
                {"error": str(e), "message": "Could not access API documentation"}
            )
            return False

    def test_user_registration(self) -> bool:
        """Test user registration endpoint"""
        try:
            response = requests.post(
                f"{self.api_v1}/auth/register",
                json=self.test_user_data,
                timeout=10
            )
            
            success = response.status_code in [200, 201]
            response_data = response.json() if response.headers.get('content-type', '').startswith('application/json') else None
            
            if success and response_data:
                self.user_id = response_data.get('user', {}).get('id') or response_data.get('id')
            
            self.log_test(
                "User Registration",
                success,
                {
                    "status_code": response.status_code,
                    "email": self.test_user_data["email"],
                    "username": self.test_user_data["username"],
                    "message": "User registered successfully" if success else f"Registration failed with status {response.status_code}"
                },
                response_data
            )
            return success
            
        except Exception as e:
            self.log_test(
                "User Registration",
                False,
                {"error": str(e), "message": "Registration request failed"}
            )
            return False

    def test_user_login(self) -> bool:
        """Test user login endpoint"""
        try:
            # Try form data first (OAuth2 standard)
            login_data = {
                "username": self.test_user_data["email"],
                "password": self.test_user_data["password"]
            }
            
            response = requests.post(
                f"{self.api_v1}/auth/login",
                data=login_data,
                timeout=10
            )
            
            # If form data fails, try JSON
            if response.status_code != 200:
                response = requests.post(
                    f"{self.api_v1}/auth/login",
                    json=login_data,
                    timeout=10
                )
            
            success = response.status_code == 200
            response_data = response.json() if response.headers.get('content-type', '').startswith('application/json') else None
            
            if success and response_data:
                self.access_token = response_data.get('access_token')
                self.refresh_token = response_data.get('refresh_token')
                if not self.user_id:
                    self.user_id = response_data.get('user', {}).get('id')
            
            self.log_test(
                "User Login",
                success,
                {
                    "status_code": response.status_code,
                    "email": self.test_user_data["email"],
                    "has_access_token": bool(self.access_token),
                    "has_refresh_token": bool(self.refresh_token),
                    "message": "Login successful" if success else f"Login failed with status {response.status_code}"
                },
                {"access_token": "***REDACTED***", "token_type": response_data.get('token_type')} if response_data and success else response_data
            )
            return success
            
        except Exception as e:
            self.log_test(
                "User Login",
                False,
                {"error": str(e), "message": "Login request failed"}
            )
            return False

    def test_token_validation(self) -> bool:
        """Test token validation by accessing protected endpoint"""
        if not self.access_token:
            self.log_test(
                "Token Validation",
                False,
                {"message": "No access token available for validation"}
            )
            return False
            
        try:
            headers = {"Authorization": f"Bearer {self.access_token}"}
            
            # Try to access user profile or any protected endpoint
            endpoints_to_try = [
                "/auth/me",
                "/auth/profile", 
                "/users/me",
                "/user/profile"
            ]
            
            success = False
            response_data = None
            
            for endpoint in endpoints_to_try:
                try:
                    response = requests.get(
                        f"{self.api_v1}{endpoint}",
                        headers=headers,
                        timeout=5
                    )
                    if response.status_code == 200:
                        success = True
                        response_data = response.json()
                        break
                except:
                    continue
            
            self.log_test(
                "Token Validation",
                success,
                {
                    "has_valid_token": success,
                    "message": "Token is valid and accepted" if success else "Token validation failed"
                },
                response_data
            )
            return success
            
        except Exception as e:
            self.log_test(
                "Token Validation",
                False,
                {"error": str(e), "message": "Token validation request failed"}
            )
            return False

    def test_protected_routes(self) -> bool:
        """Test access to protected routes"""
        if not self.access_token:
            self.log_test(
                "Protected Routes Access",
                False,
                {"message": "No access token available"}
            )
            return False
        
        headers = {"Authorization": f"Bearer {self.access_token}"}
        protected_endpoints = [
            "/auth/me",
            "/auth/profile",
            "/auth/sessions",
            "/users",
            "/admin/users"
        ]
        
        accessible_count = 0
        total_tested = 0
        results = {}
        
        for endpoint in protected_endpoints:
            try:
                response = requests.get(
                    f"{self.api_v1}{endpoint}",
                    headers=headers,
                    timeout=5
                )
                total_tested += 1
                
                if response.status_code == 200:
                    accessible_count += 1
                    results[endpoint] = {"status": "accessible", "code": 200}
                elif response.status_code == 401:
                    results[endpoint] = {"status": "unauthorized", "code": 401}
                elif response.status_code == 403:
                    results[endpoint] = {"status": "forbidden", "code": 403}
                else:
                    results[endpoint] = {"status": "other", "code": response.status_code}
                    
            except Exception as e:
                results[endpoint] = {"status": "error", "error": str(e)}
        
        success = accessible_count > 0
        
        self.log_test(
            "Protected Routes Access",
            success,
            {
                "accessible_endpoints": accessible_count,
                "total_tested": total_tested,
                "message": f"Successfully accessed {accessible_count}/{total_tested} protected endpoints" if success else "No protected endpoints accessible"
            },
            results
        )
        return success

    def test_token_refresh(self) -> bool:
        """Test token refresh functionality"""
        if not self.refresh_token:
            self.log_test(
                "Token Refresh",
                False,
                {"message": "No refresh token available"}
            )
            return False
        
        try:
            response = requests.post(
                f"{self.api_v1}/auth/refresh",
                json={"refresh_token": self.refresh_token},
                timeout=10
            )
            
            # Also try form data
            if response.status_code != 200:
                response = requests.post(
                    f"{self.api_v1}/auth/refresh",
                    data={"refresh_token": self.refresh_token},
                    timeout=10
                )
            
            success = response.status_code == 200
            response_data = response.json() if success else None
            
            if success and response_data:
                new_access_token = response_data.get('access_token')
                if new_access_token:
                    self.access_token = new_access_token
            
            self.log_test(
                "Token Refresh",
                success,
                {
                    "status_code": response.status_code,
                    "has_new_token": bool(response_data and response_data.get('access_token')) if success else False,
                    "message": "Token refreshed successfully" if success else f"Token refresh failed with status {response.status_code}"
                },
                {"access_token": "***REDACTED***"} if success else response_data
            )
            return success
            
        except Exception as e:
            self.log_test(
                "Token Refresh",
                False,
                {"error": str(e), "message": "Token refresh request failed"}
            )
            return False

    def test_password_reset_flow(self) -> bool:
        """Test password reset functionality"""
        try:
            response = requests.post(
                f"{self.api_v1}/user-management/forgot-password",
                json={"email": self.test_user_email},
                timeout=10
            )
            
            success = response.status_code == 200
            response_data = response.json() if success else None
            
            self.log_test(
                "Password Reset Flow",
                success,
                {
                    "status_code": response.status_code,
                    "email": self.test_user_email,
                    "message": "Password reset email sent" if success else f"Password reset failed with status {response.status_code}"
                },
                response_data
            )
            return success
            
        except Exception as e:
            self.log_test(
                "Password Reset Flow",
                False,
                {"error": str(e), "message": "Password reset request failed"}
            )
            return False

    def test_user_logout(self) -> bool:
        """Test user logout functionality"""
        if not self.access_token:
            self.log_test(
                "User Logout",
                False,
                {"message": "No access token available for logout"}
            )
            return False
        
        try:
            headers = {"Authorization": f"Bearer {self.access_token}"}
            
            response = requests.post(
                f"{self.api_v1}/auth/logout",
                headers=headers,
                timeout=10
            )
            
            success = response.status_code in [200, 204]
            response_data = response.json() if response.headers.get('content-type', '').startswith('application/json') else None
            
            self.log_test(
                "User Logout",
                success,
                {
                    "status_code": response.status_code,
                    "message": "Logout successful" if success else f"Logout failed with status {response.status_code}"
                },
                response_data
            )
            return success
            
        except Exception as e:
            self.log_test(
                "User Logout",
                False,
                {"error": str(e), "message": "Logout request failed"}
            )
            return False

    def test_complete_user_journey(self):
        """Run complete user journey test"""
        print("🚀 Starting Comprehensive User Journey Test")
        print("=" * 60)
        print(f"📧 Test User Email: {self.test_user_email}")
        print(f"👤 Test Username: {self.test_user_data['username']}")
        print(f"🔗 Base URL: {self.base_url}")
        print("=" * 60)
        print()
        
        # Run all tests in sequence
        tests = [
            self.test_server_health,
            self.test_api_documentation,
            self.test_user_registration,
            self.test_user_login,
            self.test_token_validation,
            self.test_protected_routes,
            self.test_token_refresh,
            self.test_password_reset_flow,
            self.test_user_logout
        ]
        
        for test_func in tests:
            test_func()
            time.sleep(0.5)  # Small delay between tests
        
        return self.test_results

    def generate_report(self) -> str:
        """Generate markdown report"""
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result["success"])
        failed_tests = total_tests - passed_tests
        success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
        
        report = f"""# User Journey Test Report

## 📊 Test Summary

- **Total Tests**: {total_tests}
- **Passed**: {passed_tests} ✅
- **Failed**: {failed_tests} ❌
- **Success Rate**: {success_rate:.1f}%
- **Test Date**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
- **Test User**: {self.test_user_email}

## 🔍 Detailed Results

"""
        
        for result in self.test_results:
            status_icon = "✅" if result["success"] else "❌"
            status_text = "PASS" if result["success"] else "FAIL"
            
            report += f"""### {status_icon} {result['test_name']} - {status_text}

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
        
        # Add recommendations
        report += f"""## 🎯 Recommendations

### ✅ Working Features
"""
        
        working_features = [result['test_name'] for result in self.test_results if result['success']]
        for feature in working_features:
            report += f"- {feature}\n"
        
        if failed_tests > 0:
            report += f"""
### ⚠️ Issues Found
"""
            failed_features = [result for result in self.test_results if not result['success']]
            for result in failed_features:
                report += f"- **{result['test_name']}**: {result['details'].get('message', 'Test failed')}\n"
        
        report += f"""
### 🚀 Overall Assessment

The user journey test completed with a **{success_rate:.1f}% success rate**. 

"""
        
        if success_rate >= 80:
            report += "🎉 **EXCELLENT**: The authentication system is working well and ready for production use."
        elif success_rate >= 60:
            report += "⚠️ **GOOD**: The system is mostly functional with some areas needing attention."
        elif success_rate >= 40:
            report += "🔧 **NEEDS WORK**: Several core features need fixing before production deployment."
        else:
            report += "🚨 **CRITICAL**: Major issues found that need immediate attention."
        
        return report

def main():
    """Main test execution"""
    tester = UserJourneyTester()
    results = tester.test_complete_user_journey()
    
    # Generate and save report
    report = tester.generate_report()
    
    # Save to file
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"user_journey_test_report_{timestamp}.md"
    
    with open(filename, 'w') as f:
        f.write(report)
    
    print("=" * 60)
    print(f"📄 Test report saved to: {filename}")
    print("=" * 60)
    
    return results

if __name__ == "__main__":
    main() 