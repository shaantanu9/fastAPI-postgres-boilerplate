import asyncio
import weakref
from typing import Dict, Any, Optional
from fastapi import WebSocket, Request
from weakref import WeakSet, WeakValueDictionary

class WebSocketManager:
    """
    Modular, scalable WebSocket manager for FastAPI:
    - Connection tracking (WeakSet/WeakValueDictionary)
    - Room/channel support
    - Presence tracking (to be integrated)
    - Direct messaging (to be integrated)
    - Redis Pub/Sub (to be integrated)
    - Heartbeat/ping for dead connection cleanup
    - In-memory message history (to be integrated)
    Usage: Inject via get_websocket_manager() dependency or app.state.websocket_manager
    """
    def __init__(self):
        self.connections: WeakValueDictionary = WeakValueDictionary()
        self.rooms: Dict[str, WeakSet] = {}
        self.websocket_to_id: weakref.WeakKeyDictionary = weakref.WeakKeyDictionary()
        self.user_connections: Dict[str, WeakSet] = {}
        self._heartbeat_task: Optional[asyncio.Task] = None
        self._heartbeat_interval = 30
        # Placeholders for advanced features
        self.presence = None  # To be set by presence module
        self.redis_pubsub = None  # To be set by redis_pubsub module
        self.history = None  # To be set by history module

    async def connect(self, websocket: WebSocket, connection_id: str, room: Optional[str] = None, user_id: Optional[str] = None):
        await websocket.accept()
        self.connections[connection_id] = websocket
        self.websocket_to_id[websocket] = connection_id
        if room:
            if room not in self.rooms:
                self.rooms[room] = WeakSet()
            self.rooms[room].add(websocket)
        if user_id:
            if user_id not in self.user_connections:
                self.user_connections[user_id] = WeakSet()
            self.user_connections[user_id].add(websocket)
        # Presence tracking (optional)
        if self.presence:
            await self.presence.user_join(user_id, room)

    async def disconnect(self, websocket: WebSocket, room: Optional[str] = None, user_id: Optional[str] = None):
        connection_id = self.websocket_to_id.get(websocket)
        if connection_id and connection_id in self.connections:
            del self.connections[connection_id]
        if room and room in self.rooms:
            self.rooms[room].discard(websocket)
        if user_id and user_id in self.user_connections:
            self.user_connections[user_id].discard(websocket)
        # Presence tracking (optional)
        if self.presence:
            await self.presence.user_leave(user_id, room)

    async def broadcast(self, message: str, room: Optional[str] = None):
        # Redis Pub/Sub broadcast (optional)
        if self.redis_pubsub:
            await self.redis_pubsub.publish(message, room)
        targets = self.rooms[room] if room and room in self.rooms else self.connections.values()
        for ws in list(targets):
            try:
                await ws.send_text(message)
            except Exception:
                pass
        # Message history (optional)
        if self.history and room:
            await self.history.add_message(room, message)

    # Placeholder for authentication (to be implemented)
    async def authenticate(self, websocket: WebSocket, token: str) -> Optional[str]:
        # Return user_id if valid, else None
        return None

    # --- Heartbeat logic ---
    async def _heartbeat_loop(self):
        while True:
            await asyncio.sleep(self._heartbeat_interval)
            dead = []
            for ws in list(self.connections.values()):
                try:
                    await ws.send_text("__ping__")
                except Exception:
                    dead.append(ws)
            for ws in dead:
                await self.disconnect(ws)

    def start_heartbeat(self, interval: int = 30):
        self._heartbeat_interval = interval
        if not self._heartbeat_task or self._heartbeat_task.done():
            self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())

    def stop_heartbeat(self):
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            self._heartbeat_task = None

# Dependency for FastAPI
_websocket_manager_instance = None

def get_websocket_manager(request: Request = None):
    if request is not None and hasattr(request.app.state, 'websocket_manager'):
        return request.app.state.websocket_manager
    global _websocket_manager_instance
    if _websocket_manager_instance is None:
        _websocket_manager_instance = WebSocketManager()
    return _websocket_manager_instance

    # Add more methods as needed (heartbeat, direct messaging, etc.) 