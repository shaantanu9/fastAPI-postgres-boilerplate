#!/usr/bin/env python3
"""Quick Redis connectivity and functionality test."""

import asyncio

import redis.asyncio as redis


async def test_redis_basic() -> bool | None:
    """Test basic Redis connectivity."""
    try:
        client = redis.from_url("redis://localhost:6379/0")

        # Test ping
        await client.ping()

        # Test set/get
        await client.set("test_key", "test_value")
        await client.get("test_key")

        # Test cleanup
        await client.delete("test_key")

        await client.close()
        return True

    except Exception:
        return False


async def test_redis_manager() -> bool | None:
    """Test our Redis Manager."""
    try:
        from app.core.redis_manager import EnterpriseRedisManager

        redis_manager = EnterpriseRedisManager()
        success = await redis_manager.initialize()

        if success:

            # Test caching
            await redis_manager.cache_set(
                "test:cache", {"message": "Hello Redis!"}, ttl=60,
            )
            cached_value = await redis_manager.cache_get("test:cache")

            if cached_value:
                pass
            else:
                return False

            # Test rate limiting
            await redis_manager.rate_limit_check("test:user", 5, 60)

            return True
        return False

    except Exception:
        return False


async def test_security_codes() -> bool | None:
    """Test Security Codes service."""
    try:
        from app.core.security_codes import EnterpriseSecurityCodeService

        security_service = EnterpriseSecurityCodeService()
        await security_service.initialize()

        # Test backup code generation
        user_id = "test_user_redis"
        backup_codes = await security_service.generate_backup_codes(user_id)

        if len(backup_codes) == 10:
            pass
        else:
            return False

        # Test recovery code generation
        recovery_code = await security_service.generate_recovery_code(user_id, 1)
        if recovery_code and len(recovery_code) == 32:
            pass
        else:
            return False

        # Test code verification
        verification_result = await security_service.verify_recovery_code(recovery_code)
        if verification_result:
            pass
        else:
            return False

        return True

    except Exception:
        return False


async def main() -> None:
    """Run all Redis tests."""
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
        except Exception:
            results[test_name] = False

    # Summary

    passed = 0
    total = len(results)

    for test_name, result in results.items():
        if result:
            passed += 1


    if passed == total:
        pass
    else:
        pass


if __name__ == "__main__":
    asyncio.run(main())
