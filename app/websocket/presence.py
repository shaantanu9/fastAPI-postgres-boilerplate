"""
Presence module for tracking online users in FastAPI WebSocket system.
- Usage: Attach to WebSocketManager.presence
- Methods: user_join(user_id, room), user_leave(user_id, room), get_online_users(room=None)
"""
import asyncio
from collections import defaultdict

class Presence:
    def __init__(self):
        self.room_users = defaultdict(set)  # room -> set of user_ids
        self.global_users = set()
        self.lock = asyncio.Lock()

    async def user_join(self, user_id: str, room: str):
        async with self.lock:
            self.room_users[room].add(user_id)
            self.global_users.add(user_id)

    async def user_leave(self, user_id: str, room: str):
        async with self.lock:
            self.room_users[room].discard(user_id)
            if not any(user_id in users for users in self.room_users.values()):
                self.global_users.discard(user_id)

    async def get_online_users(self, room: str = None):
        async with self.lock:
            if room:
                return list(self.room_users[room])
            return list(self.global_users) 