import asyncio

import redis.asyncio as redis


async def test_redis_connection() -> None:
    try:
        r = await redis.from_url("redis://localhost:6379/0")
        result = await r.ping()
        await r.close()
    except Exception:
        pass
    finally:
        if "r" in locals():
            await r.close()


if __name__ == "__main__":
    asyncio.run(test_redis_connection())
