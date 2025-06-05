import asyncio
import redis.asyncio as redis

async def test_redis_connection():
    try:
        r = await redis.from_url('redis://localhost:6379/0')
        print("Pinging Redis...")
        result = await r.ping()
        print(f"Redis ping successful: {result}")
        await r.close()
    except Exception as e:
        print(f"Error connecting to Redis: {e}")
    finally:
        if 'r' in locals():
            await r.close()

if __name__ == "__main__":
    asyncio.run(test_redis_connection())
