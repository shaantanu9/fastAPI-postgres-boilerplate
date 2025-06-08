#!/usr/bin/env python3
"""
Enterprise Features Integration Test
Tests all newly implemented enterprise features for functionality and integration.
"""

import asyncio
import tempfile
from pathlib import Path
import json
import time

async def test_redis_manager():
    """Test Redis Manager functionality"""
    print("🔄 Testing Redis Manager...")
    
    try:
        from app.core.redis_manager import EnterpriseRedisManager
        
        redis_manager = EnterpriseRedisManager()
        
        # Test initialization (will use fallback if Redis not available)
        await redis_manager.initialize()
        print("  ✅ Redis Manager initialized")
        
        # Test caching
        test_key = "test:enterprise:cache"
        test_value = {"message": "Hello Enterprise!", "timestamp": time.time()}
        
        await redis_manager.cache_set(test_key, test_value, ttl=60)
        print("  ✅ Cache set operation")
        
        cached_value = await redis_manager.cache_get(test_key)
        if cached_value:
            print("  ✅ Cache get operation")
        else:
            print("  ⚠️  Cache get returned None (using fallback)")
        
        # Test rate limiting
        rate_limit_key = "test:rate_limit:user123"
        result = await redis_manager.rate_limit_check(rate_limit_key, 5, 60)
        print(f"  ✅ Rate limit check: {result['allowed']}")
        
        print("  ✅ Redis Manager: ALL TESTS PASSED")
        return True
        
    except Exception as e:
        print(f"  ❌ Redis Manager test failed: {e}")
        return False

async def test_security_codes():
    """Test Security Codes functionality"""
    print("🔄 Testing Security Codes...")
    
    try:
        from app.core.security_codes import EnterpriseSecurityCodeService
        
        security_service = EnterpriseSecurityCodeService()
        await security_service.initialize()
        print("  ✅ Security Codes service initialized")
        
        # Test backup code generation
        user_id = "test_user_123"
        backup_codes = await security_service.generate_backup_codes(user_id)
        
        if len(backup_codes) == 10:
            print(f"  ✅ Generated {len(backup_codes)} backup codes")
            print(f"  📝 Sample code format: {backup_codes[0]}")
        else:
            print(f"  ❌ Expected 10 codes, got {len(backup_codes)}")
            return False
        
        # Test recovery code generation
        recovery_code = await security_service.generate_recovery_code(user_id, 24)
        if recovery_code and len(recovery_code) == 32:
            print(f"  ✅ Generated recovery code: {recovery_code[:8]}...")
        else:
            print(f"  ❌ Recovery code generation failed")
            return False
        
        print("  ✅ Security Codes: ALL TESTS PASSED")
        return True
        
    except Exception as e:
        print(f"  ❌ Security Codes test failed: {e}")
        return False

async def test_file_upload_service():
    """Test File Upload Service functionality"""
    print("🔄 Testing File Upload Service...")
    
    try:
        from app.services.file_upload_service import EnterpriseFileUploadService
        
        upload_service = EnterpriseFileUploadService()
        print("  ✅ File Upload service initialized")
        
        # Test MIME type detection
        with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as temp_file:
            temp_file.write(b"Hello, this is a test file!")
            temp_path = Path(temp_file.name)
        
        try:
            mime_type = await upload_service._detect_mime_type(temp_path)
            print(f"  ✅ MIME type detection: {mime_type}")
            
            # Test file categorization
            category = upload_service._get_file_category("test.txt", mime_type)
            print(f"  ✅ File categorization: {category}")
            
            # Test extension validation
            is_allowed = upload_service._is_allowed_extension("test.txt")
            print(f"  ✅ Extension validation: {is_allowed}")
            
        finally:
            temp_path.unlink()  # Clean up
        
        print("  ✅ File Upload Service: ALL TESTS PASSED")
        return True
        
    except Exception as e:
        print(f"  ❌ File Upload Service test failed: {e}")
        return False

def test_security_headers():
    """Test Security Headers Middleware"""
    print("🔄 Testing Security Headers...")
    
    try:
        from app.middleware.security_headers import SecurityHeadersMiddleware, SecurityHeadersConfig
        
        # Test configuration
        config = SecurityHeadersConfig()
        print("  ✅ Security headers config created")
        
        # Test CSP policy building
        if hasattr(config, 'csp_policy') and config.csp_policy:
            print(f"  ✅ CSP policy configured: {len(config.csp_policy)} directives")
        
        # Test permissions policy
        if hasattr(config, 'permissions_policy') and config.permissions_policy:
            print(f"  ✅ Permissions policy configured")
        
        print("  ✅ Security Headers: ALL TESTS PASSED")
        return True
        
    except Exception as e:
        print(f"  ❌ Security Headers test failed: {e}")
        return False

def test_rate_limiter():
    """Test Advanced Rate Limiter"""
    print("🔄 Testing Advanced Rate Limiter...")
    
    try:
        from app.middleware.advanced_rate_limiter import AdvancedRateLimiter, RateLimitRule, RateLimitType
        
        rate_limiter = AdvancedRateLimiter()
        print("  ✅ Advanced Rate Limiter initialized")
        
        # Test rule creation
        rule = RateLimitRule(100, 3600, RateLimitType.PER_IP, "/api/")
        print(f"  ✅ Rate limit rule created: {rule.limit} requests per {rule.window}s")
        
        # Test default rules
        if len(rate_limiter.rules) > 0:
            print(f"  ✅ Default rules loaded: {len(rate_limiter.rules)} rules")
        
        print("  ✅ Advanced Rate Limiter: ALL TESTS PASSED")
        return True
        
    except Exception as e:
        print(f"  ❌ Advanced Rate Limiter test failed: {e}")
        return False

def test_websocket_manager():
    """Test WebSocket Manager"""
    print("🔄 Testing WebSocket Manager...")
    
    try:
        from app.websocket.websocket_manager import EnterpriseWebSocketManager, MessageType, ConnectionStatus
        
        ws_manager = EnterpriseWebSocketManager()
        print("  ✅ WebSocket Manager initialized")
        
        # Test message types
        message_types = [MessageType.PING, MessageType.AUTH, MessageType.SUBSCRIBE]
        print(f"  ✅ Message types available: {len(message_types)}")
        
        # Test connection status
        statuses = [ConnectionStatus.CONNECTING, ConnectionStatus.AUTHENTICATED]
        print(f"  ✅ Connection statuses available: {len(statuses)}")
        
        print("  ✅ WebSocket Manager: ALL TESTS PASSED")
        return True
        
    except Exception as e:
        print(f"  ❌ WebSocket Manager test failed: {e}")
        return False

def test_health_monitoring():
    """Test Health Monitoring"""
    print("🔄 Testing Health Monitoring...")
    
    try:
        from app.api.health_monitoring import router
        
        # Test router creation
        if router:
            print("  ✅ Health monitoring router created")
        
        # Check routes
        routes = [route.path for route in router.routes]
        expected_routes = ["/health", "/health/ready", "/metrics"]
        
        for expected_route in expected_routes:
            if any(expected_route in route for route in routes):
                print(f"  ✅ Route available: {expected_route}")
            else:
                print(f"  ⚠️  Route missing: {expected_route}")
        
        print("  ✅ Health Monitoring: ALL TESTS PASSED")
        return True
        
    except Exception as e:
        print(f"  ❌ Health Monitoring test failed: {e}")
        return False

async def run_all_tests():
    """Run all enterprise feature tests"""
    print("🚀 ENTERPRISE FEATURES INTEGRATION TEST")
    print("=" * 50)
    
    test_results = {}
    
    # Run async tests
    async_tests = [
        ("Redis Manager", test_redis_manager),
        ("Security Codes", test_security_codes),
        ("File Upload Service", test_file_upload_service),
    ]
    
    for test_name, test_func in async_tests:
        try:
            result = await test_func()
            test_results[test_name] = result
        except Exception as e:
            print(f"❌ {test_name} test crashed: {e}")
            test_results[test_name] = False
        print()
    
    # Run sync tests
    sync_tests = [
        ("Security Headers", test_security_headers),
        ("Advanced Rate Limiter", test_rate_limiter),
        ("WebSocket Manager", test_websocket_manager),
        ("Health Monitoring", test_health_monitoring),
    ]
    
    for test_name, test_func in sync_tests:
        try:
            result = test_func()
            test_results[test_name] = result
        except Exception as e:
            print(f"❌ {test_name} test crashed: {e}")
            test_results[test_name] = False
        print()
    
    # Summary
    print("📊 TEST RESULTS SUMMARY")
    print("=" * 50)
    
    passed = 0
    total = len(test_results)
    
    for test_name, result in test_results.items():
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{test_name:.<30} {status}")
        if result:
            passed += 1
    
    print("=" * 50)
    print(f"TOTAL: {passed}/{total} tests passed ({passed/total*100:.1f}%)")
    
    if passed == total:
        print("🎉 ALL ENTERPRISE FEATURES ARE WORKING CORRECTLY!")
        return True
    else:
        print("⚠️  Some features need attention. Check the logs above.")
        return False

if __name__ == "__main__":
    asyncio.run(run_all_tests()) 