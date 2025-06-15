#!/usr/bin/env python3
"""Comprehensive User Journey Test for FastAPI Backend."""
import json
import requests
import secrets
import string
from datetime import datetime
from typing import Dict, Any, Optional
import time

BASE_URL = "http://localhost:8000"
API_V1 = f"{BASE_URL}/api/v1"

class UserJourneyTest:
    def __init__(self):
        self.base_url = BASE_URL
        self.api_v1 = API_V1
        self.test_results = []
        self.access_token = None
        self.refresh_token = None
        
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
        return ''.join(secrets.choice(string.ascii_lowercase + string.digits) for _ in range(length))
    
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
        try:
            response = requests.get(f"{self.base_url}/health", timeout=10)
            success = response.status_code == 200
            
            self.log_test(
                "Server Health Check",
                success,
                {
                    "status_code": response.status_code,
                    "message": "Server is running" if success else "Server not responding"
                },
                response.json() if success else None
            )
            return success
        except Exception as e:
            self.log_test("Server Health Check", False, {"error": str(e)})
            return False

    def test_user_registration(self) -> bool:
        try:
            response = requests.post(
                f"{self.api_v1}/auth/register",
                json=self.test_user_data,
                timeout=15
            )
            
            success = response.status_code in [200, 201]
            response_data = response.json() if response.headers.get('content-type', '').startswith('application/json') else None
            
            self.log_test(
                "User Registration",
                success,
                {
                    "status_code": response.status_code,
                    "email": self.test_user_email,
                    "username": self.test_user_data["username"],
                    "message": "User registered successfully" if success else f"Registration failed: {response.text}"
                },
                response_data
            )
            return success
            
        except Exception as e:
            self.log_test("User Registration", False, {"error": str(e)})
            return False

    def test_user_login(self) -> bool:
        try:
            # Try form data (OAuth2 standard)
            form_data = {
                "username": self.test_user_data["email"],
                "password": self.test_user_data["password"]
            }
            
            response = requests.post(
                f"{self.api_v1}/auth/login",
                data=form_data,
                timeout=15
            )
            
            success = response.status_code == 200
            response_data = response.json() if success else None
            
            if success and response_data:
                self.access_token = response_data.get('access_token')
                self.refresh_token = response_data.get('refresh_token')
            
            self.log_test(
                "User Login",
                success,
                {
                    "status_code": response.status_code,
                    "email": self.test_user_data["email"],
                    "has_access_token": bool(self.access_token),
                    "has_refresh_token": bool(self.refresh_token),
                    "message": "Login successful" if success else f"Login failed: {response.text}"
                },
                {"access_token": "***REDACTED***", "token_type": response_data.get('token_type')} if success else None
            )
            return success
            
        except Exception as e:
            self.log_test("User Login", False, {"error": str(e)})
            return False

    def test_token_validation(self) -> bool:
        if not self.access_token:
            self.log_test("Token Validation", False, {"message": "No access token available"})
            return False
            
        try:
            headers = {"Authorization": f"Bearer {self.access_token}"}
            
            # Try to access protected endpoint
            endpoints = ["/auth/me", "/auth/profile", "/users/me"]
            
            for endpoint in endpoints:
                try:
                    response = requests.get(f"{self.api_v1}{endpoint}", headers=headers, timeout=10)
                    if response.status_code == 200:
                        self.log_test(
                            "Token Validation", 
                            True, 
                            {"endpoint": endpoint, "message": "Token is valid"}
                        )
                        return True
                except:
                    continue
            
            self.log_test("Token Validation", False, {"message": "No accessible protected endpoints"})
            return False
            
        except Exception as e:
            self.log_test("Token Validation", False, {"error": str(e)})
            return False

    def test_password_reset(self) -> bool:
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
                    "message": "Password reset email sent" if success else f"Reset failed: {response.text}"
                },
                response_data
            )
            return success
            
        except Exception as e:
            self.log_test("Password Reset", False, {"error": str(e)})
            return False

    def run_all_tests(self):
        print("🚀 Starting Comprehensive User Journey Test")
        print("=" * 80)
        print(f"📧 Test User Email: {self.test_user_email}")
        print(f"👤 Test Username: {self.test_user_data['username']}")
        print(f"🔗 Base URL: {self.base_url}")
        print("=" * 80)
        print()
        
        tests = [
            self.test_server_health,
            self.test_user_registration,
            self.test_user_login,
            self.test_token_validation,
            self.test_password_reset
        ]
        
        for test_func in tests:
            test_func()
            time.sleep(0.5)
        
        return self.test_results

    def generate_report(self) -> str:
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result["success"])
        failed_tests = total_tests - passed_tests
        success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
        
        report = f"""# 🔐 User Journey Test Report

## 📊 Test Summary

| Metric | Value |
|--------|-------|
| **Total Tests** | {total_tests} |
| **Passed** | {passed_tests} ✅ |
| **Failed** | {failed_tests} ❌ |
| **Success Rate** | {success_rate:.1f}% |
| **Test Date** | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} |
| **Test User** | {self.test_user_email} |

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
        if success_rate >= 80:
            report += "🎉 **EXCELLENT**: Authentication system is working well!\n\n"
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
        
        return report

def main():
    tester = UserJourneyTest()
    results = tester.run_all_tests()
    
    # Generate report
    report = tester.generate_report()
    
    # Save to file
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"user_journey_report_{timestamp}.md"
    
    with open(filename, 'w') as f:
        f.write(report)
    
    print("=" * 80)
    print(f"📄 Test report saved to: {filename}")
    print("=" * 80)
    
    # Print summary
    total_tests = len(results)
    passed_tests = sum(1 for result in results if result["success"])
    success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
    
    print(f"\n🎯 FINAL SUMMARY:")
    print(f"   Tests: {passed_tests}/{total_tests} passed ({success_rate:.1f}%)")
    if success_rate >= 80:
        print("   Status: ✅ EXCELLENT - Ready for production!")
    elif success_rate >= 60:
        print("   Status: ⚠️ GOOD - Minor issues to fix")
    elif success_rate >= 40:
        print("   Status: 🔧 NEEDS WORK - Several issues found")
    else:
        print("   Status: 🚨 CRITICAL - Major problems")
    
    return results

if __name__ == "__main__":
    main() 