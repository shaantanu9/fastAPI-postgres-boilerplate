#!/usr/bin/env python3
"""
DIRECT SECURITY SERVICE TEST

PURPOSE:
    Test the security service directly to diagnose method availability issues
    
WHEN TO USE:
    - When security service methods are missing
    - When there are import or initialization issues
    - Debugging authentication problems
    
WHAT IT TESTS:
    1. Security service import and initialization
    2. Method availability (is_account_locked, handle_failed_login, etc.)
    3. Password validation functionality
    4. Hash and verify functionality
    
CREATED: 2025-06-14 (diagnostic test)
DEPENDENCIES: None (direct import test)
"""

import sys
import traceback
from datetime import datetime, timedelta

def test_security_service_import():
    """Test importing the security service."""
    try:
        from app.core.security import security_service, EnterpriseSecurityService
        print("✅ Successfully imported security_service and EnterpriseSecurityService")
        print(f"   Security service type: {type(security_service)}")
        print(f"   Security service class: {security_service.__class__.__name__}")
        return security_service
    except Exception as e:
        print(f"❌ Failed to import security service: {e}")
        traceback.print_exc()
        return None

def test_security_service_methods(security_service):
    """Test if required methods exist on the security service."""
    required_methods = [
        'is_account_locked',
        'handle_failed_login', 
        'handle_successful_login',
        'validate_password_strength',
        'hash_password',
        'verify_password'
    ]
    
    print("\n🔍 Testing method availability:")
    missing_methods = []
    
    for method_name in required_methods:
        if hasattr(security_service, method_name):
            method = getattr(security_service, method_name)
            print(f"   ✅ {method_name}: {type(method)}")
        else:
            print(f"   ❌ {method_name}: MISSING")
            missing_methods.append(method_name)
    
    return missing_methods

def test_password_functionality(security_service):
    """Test password hashing and validation."""
    print("\n🔒 Testing password functionality:")
    
    try:
        # Test password validation
        test_password = "TestPassword123!"
        validation_result = security_service.validate_password_strength(test_password)
        print(f"   ✅ Password validation: {validation_result}")
        
        # Test password hashing
        hashed = security_service.hash_password(test_password)
        print(f"   ✅ Password hashing: {len(hashed)} chars")
        
        # Test password verification
        is_valid = security_service.verify_password(test_password, hashed)
        print(f"   ✅ Password verification: {is_valid}")
        
        return True
    except Exception as e:
        print(f"   ❌ Password functionality failed: {e}")
        traceback.print_exc()
        return False

def test_account_locking(security_service):
    """Test account locking functionality."""
    print("\n🔐 Testing account locking:")
    
    try:
        # Create a mock user object
        class MockUser:
            def __init__(self):
                self.account_locked_until = None
                self.failed_login_attempts = 0
        
        user = MockUser()
        
        # Test unlocked account
        is_locked = security_service.is_account_locked(user)
        print(f"   ✅ Unlocked account check: {is_locked}")
        
        # Test locked account
        user.account_locked_until = datetime.utcnow() + timedelta(minutes=30)
        is_locked = security_service.is_account_locked(user)
        print(f"   ✅ Locked account check: {is_locked}")
        
        return True
    except Exception as e:
        print(f"   ❌ Account locking test failed: {e}")
        traceback.print_exc()
        return False

def test_enhanced_user_service():
    """Test the enhanced user service initialization."""
    print("\n👤 Testing enhanced user service:")
    
    try:
        from app.services.user_service import enhanced_user_service
        print(f"   ✅ Enhanced user service imported: {type(enhanced_user_service)}")
        print(f"   ✅ Security service in user service: {type(enhanced_user_service.security_service)}")
        
        # Test if the security service has the required methods
        if hasattr(enhanced_user_service.security_service, 'is_account_locked'):
            print("   ✅ is_account_locked method available in user service")
        else:
            print("   ❌ is_account_locked method MISSING in user service")
            
        return True
    except Exception as e:
        print(f"   ❌ Enhanced user service test failed: {e}")
        traceback.print_exc()
        return False

def main():
    """Run all diagnostic tests."""
    print("🔧 SECURITY SERVICE DIAGNOSTIC TEST")
    print("=" * 60)
    
    # Test 1: Import security service
    security_service = test_security_service_import()
    if not security_service:
        print("\n❌ CRITICAL: Cannot import security service")
        return False
    
    # Test 2: Check method availability
    missing_methods = test_security_service_methods(security_service)
    if missing_methods:
        print(f"\n❌ CRITICAL: Missing methods: {missing_methods}")
        return False
    
    # Test 3: Test password functionality
    password_ok = test_password_functionality(security_service)
    
    # Test 4: Test account locking
    locking_ok = test_account_locking(security_service)
    
    # Test 5: Test enhanced user service
    user_service_ok = test_enhanced_user_service()
    
    # Summary
    print("\n" + "=" * 60)
    print("🎯 DIAGNOSTIC SUMMARY:")
    print(f"   Security Service Import: ✅")
    print(f"   Required Methods: {'✅' if not missing_methods else '❌'}")
    print(f"   Password Functionality: {'✅' if password_ok else '❌'}")
    print(f"   Account Locking: {'✅' if locking_ok else '❌'}")
    print(f"   Enhanced User Service: {'✅' if user_service_ok else '❌'}")
    
    all_ok = not missing_methods and password_ok and locking_ok and user_service_ok
    print(f"\n🏆 OVERALL STATUS: {'✅ ALL TESTS PASSED' if all_ok else '❌ ISSUES FOUND'}")
    
    return all_ok

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 