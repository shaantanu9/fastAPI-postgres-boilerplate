"""
MessageHistory module for in-memory message history in FastAPI WebSocket system.
- Usage: Attach to WebSocketManager.history
- Methods: add_message(room, message), get_history(room, limit=50)
"""
import asyncio
from collections import defaultdict, deque

class MessageHistory:
    def __init__(self, max_history=50):
        self.room_history = defaultdict(lambda: deque(maxlen=max_history))
        self.lock = asyncio.Lock()

    async def add_message(self, room: str, message: str):
        async with self.lock:
            self.room_history[room].append(message)

    async def get_history(self, room: str, limit=50):
        async with self.lock:
            return list(self.room_history[room])[-limit:] 