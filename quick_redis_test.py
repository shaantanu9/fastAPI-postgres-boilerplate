#!/usr/bin/env python3
"""Quick Redis connectivity and functionality test"""

import asyncio
import redis.asyncio as redis

async def test_redis_basic():
    """Test basic Redis connectivity"""
    print("🔄 Testing Redis basic connectivity...")
    try:
        client = redis.from_url('redis://localhost:6379/0')
        
        # Test ping
        result = await client.ping()
        print(f"  ✅ Redis Ping: {result}")
        
        # Test set/get
        await client.set('test_key', 'test_value')
        value = await client.get('test_key')
        print(f"  ✅ Redis Set/Get: {value.decode() if value else None}")
        
        # Test cleanup
        await client.delete('test_key')
        print("  ✅ Redis cleanup successful")
        
        await client.close()
        return True
        
    except Exception as e:
        print(f"  ❌ Redis basic test failed: {e}")
        return False

async def test_redis_manager():
    """Test our Redis Manager"""
    print("🔄 Testing Redis Manager...")
    try:
        from app.core.redis_manager import EnterpriseRedisManager
        
        redis_manager = EnterpriseRedisManager()
        success = await redis_manager.initialize()
        
        if success:
            print("  ✅ Redis Manager initialized successfully")
            
            # Test caching
            await redis_manager.cache_set("test:cache", {"message": "Hello Redis!"}, ttl=60)
            cached_value = await redis_manager.cache_get("test:cache")
            
            if cached_value:
                print(f"  ✅ Cache operations working: {cached_value}")
            else:
                print("  ❌ Cache operations failed")
                return False
            
            # Test rate limiting
            result = await redis_manager.rate_limit_check("test:user", 5, 60)
            print(f"  ✅ Rate limiting working: allowed={result['allowed']}")
            
            return True
        else:
            print("  ❌ Redis Manager initialization failed")
            return False
            
    except Exception as e:
        print(f"  ❌ Redis Manager test failed: {e}")
        return False

async def test_security_codes():
    """Test Security Codes service"""
    print("🔄 Testing Security Codes...")
    try:
        from app.core.security_codes import EnterpriseSecurityCodeService
        
        security_service = EnterpriseSecurityCodeService()
        await security_service.initialize()
        print("  ✅ Security Codes service initialized")
        
        # Test backup code generation
        user_id = "test_user_redis"
        backup_codes = await security_service.generate_backup_codes(user_id)
        
        if len(backup_codes) == 10:
            print(f"  ✅ Generated {len(backup_codes)} backup codes")
            print(f"  📝 Sample code: {backup_codes[0]}")
        else:
            print(f"  ❌ Expected 10 codes, got {len(backup_codes)}")
            return False
        
        # Test recovery code generation
        recovery_code = await security_service.generate_recovery_code(user_id, 1)
        if recovery_code and len(recovery_code) == 32:
            print(f"  ✅ Generated recovery code: {recovery_code[:8]}...")
        else:
            print("  ❌ Recovery code generation failed")
            return False
        
        # Test code verification
        verification_result = await security_service.verify_recovery_code(recovery_code)
        if verification_result:
            print(f"  ✅ Recovery code verification working")
        else:
            print("  ❌ Recovery code verification failed")
            return False
        
        return True
        
    except Exception as e:
        print(f"  ❌ Security Codes test failed: {e}")
        return False

async def main():
    """Run all Redis tests"""
    print("🚀 REDIS FUNCTIONALITY TEST")
    print("=" * 40)
    
    tests = [
        ("Basic Redis", test_redis_basic),
        ("Redis Manager", test_redis_manager),
        ("Security Codes", test_security_codes),
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        try:
            result = await test_func()
            results[test_name] = result
        except Exception as e:
            print(f"❌ {test_name} crashed: {e}")
            results[test_name] = False
        print()
    
    # Summary
    print("📊 REDIS TEST RESULTS")
    print("=" * 40)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{test_name:.<20} {status}")
        if result:
            passed += 1
    
    print("=" * 40)
    print(f"TOTAL: {passed}/{total} tests passed ({passed/total*100:.1f}%)")
    
    if passed == total:
        print("🎉 ALL REDIS FEATURES ARE WORKING!")
    else:
        print("⚠️  Some Redis features need attention")

if __name__ == "__main__":
    asyncio.run(main()) 