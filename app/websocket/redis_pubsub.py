"""
RedisPubSub module for scalable WebSocket broadcast in FastAPI.
- Usage: Attach to WebSocketManager.redis_pubsub
- Default URL: redis://localhost:6379/0
- Methods: publish(message, room), subscribe(room, callback)
- Uses redis.asyncio (redis-py >=4.2) for async support
"""
import asyncio
import redis.asyncio as aioredis

class RedisPubSub:
    def __init__(self, url: str = "redis://localhost:6379/0"):
        self.url = url
        self.redis = None
        self.sub_tasks = {}

    async def connect(self):
        if not self.redis:
            self.redis = aioredis.from_url(self.url, decode_responses=True)

    async def publish(self, message: str, room: str):
        await self.connect()
        await self.redis.publish(room, message)

    async def subscribe(self, room: str, callback):
        await self.connect()
        pubsub = self.redis.pubsub()
        await pubsub.subscribe(room)
        async def reader():
            async for msg in pubsub.listen():
                if msg["type"] == "message":
                    await callback(msg["data"])
        task = asyncio.create_task(reader())
        self.sub_tasks[room] = task

    async def close(self):
        if self.redis:
            await self.redis.close()
            self.redis = None 