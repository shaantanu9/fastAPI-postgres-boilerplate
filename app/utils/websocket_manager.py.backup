"""WebSocket Manager for Scalable Real-Time Communication.

This module provides a scalable WebSocket implementation for FastAPI with:
- Redis-backed pub/sub for horizontal scaling
- Tenant isolation for multi-tenant security
- Room-based communication channels
- Connection tracking and management
- Automatic reconnection and error handling

Usage:
    socket_manager = WebSocketManager()

    # In FastAPI endpoint:
    @app.websocket("/ws/{tenant_id}/{room_id}")
    async def websocket_endpoint(websocket: WebSocket, tenant_id: str, room_id: str):
        await socket_manager.connect(websocket, tenant_id, room_id)
        try:
            while True:
                data = await websocket.receive_text()
                await socket_manager.broadcast_to_room(tenant_id, room_id, data)
        except WebSocketDisconnect:
            await socket_manager.disconnect(websocket, tenant_id, room_id)
"""

import asyncio
import json
import logging
import uuid
from datetime import datetime
from typing import Any

import redis.asyncio as aioredis
from fastapi import WebSocket
from pydantic import BaseModel, Field

from app.core.config import get_settings

# Configure logging
logger = logging.getLogger(__name__)


class WebSocketConnection(BaseModel):
    """Model representing a WebSocket connection with metadata."""

    websocket: Any  # Cannot use WebSocket due to Pydantic validation
    tenant_id: str
    room_id: str
    user_id: str | None = None
    connection_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    connected_at: datetime = Field(default_factory=datetime.now)
    last_activity: datetime = Field(default_factory=datetime.now)

    class Config:
        arbitrary_types_allowed = True


class RedisPubSubManager:
    """Redis-based pub/sub manager for cross-server WebSocket communication."""

    def __init__(self, redis_url: str | None = None) -> None:
        """Initialize the Redis pub/sub manager.

        Args:
            redis_url: Redis connection URL. If None, uses settings value.

        """
        settings = get_settings()
        self.redis_url = redis_url or settings.REDIS_URL or "redis://localhost:6379/0"
        self.redis_client: aioredis.Redis | None = None
        self._pubsub = None
        self._channel_subscriptions: dict[str, aioredis.client.PubSub] = {}

    async def connect(self) -> None:
        """Connect to Redis if not already connected."""
        if self.redis_client is None or not self.redis_client.ping():
            try:
                self.redis_client = await aioredis.from_url(
                    self.redis_url, encoding="utf-8", decode_responses=True,
                )
                logger.info(f"Connected to Redis at {self.redis_url}")
            except Exception as e:
                logger.exception(f"Failed to connect to Redis: {e}")
                raise

    async def disconnect(self) -> None:
        """Disconnect from Redis and clean up resources."""
        if self._pubsub:
            await self._pubsub.close()

        for pubsub in self._channel_subscriptions.values():
            await pubsub.close()

        if self.redis_client:
            await self.redis_client.close()
            self.redis_client = None
            logger.info("Disconnected from Redis")

    async def publish(self, channel: str, message: str | dict[str, Any]) -> int:
        """Publish a message to a Redis channel.

        Args:
            channel: The channel name to publish to
            message: Message to publish (string or dict)

        Returns:
            Number of clients that received the message

        """
        await self.connect()  # Ensure connection

        if isinstance(message, dict):
            message = json.dumps(message)

        try:
            result = await self.redis_client.publish(channel, message)
            logger.debug(f"Published to {channel}: {message[:100]}...")
            return result
        except Exception as e:
            logger.exception(f"Failed to publish to {channel}: {e}")
            return 0

    async def subscribe(self, channel: str) -> aioredis.client.PubSub:
        """Subscribe to a Redis channel.

        Args:
            channel: Channel name to subscribe to

        Returns:
            PubSub object for receiving messages

        """
        await self.connect()  # Ensure connection

        # Create a new pubsub client
        pubsub = self.redis_client.pubsub()
        await pubsub.subscribe(channel)

        # Store subscription for cleanup
        self._channel_subscriptions[channel] = pubsub
        logger.info(f"Subscribed to channel: {channel}")

        return pubsub

    async def unsubscribe(self, channel: str) -> None:
        """Unsubscribe from a Redis channel.

        Args:
            channel: Channel to unsubscribe from

        """
        if channel in self._channel_subscriptions:
            pubsub = self._channel_subscriptions[channel]
            await pubsub.unsubscribe(channel)
            await pubsub.close()
            del self._channel_subscriptions[channel]
            logger.info(f"Unsubscribed from channel: {channel}")

    @staticmethod
    def get_tenant_room_channel(tenant_id: str, room_id: str) -> str:
        """Generate a standardized channel name for tenant+room combination.

        Args:
            tenant_id: Tenant identifier
            room_id: Room identifier

        Returns:
            Formatted channel name

        """
        return f"ws:tenant:{tenant_id}:room:{room_id}"


class WebSocketManager:
    """Manager for handling WebSocket connections with tenant isolation and Redis pub/sub.

    This class provides a scalable infrastructure for WebSocket communication
    in a multi-tenant environment, with support for room-based messaging.
    """

    def __init__(self, redis_url: str | None = None) -> None:
        """Initialize the WebSocket manager.

        Args:
            redis_url: Optional Redis URL. If None, uses value from settings.

        """
        # Map of tenant_id -> room_id -> list of WebSocketConnection objects
        self.connections: dict[str, dict[str, list[WebSocketConnection]]] = {}

        # Connection lookup by ID for fast access
        self.connection_by_id: dict[str, WebSocketConnection] = {}

        # Track active tenant+room channels
        self.active_channels: set[str] = set()

        # Initialize Redis pub/sub manager
        self.pubsub = RedisPubSubManager(redis_url)

        # Track message handlers by tenant+room
        self.message_handlers: dict[str, asyncio.Task] = {}

        logger.info("WebSocketManager initialized")

    async def connect(
        self,
        websocket: WebSocket,
        tenant_id: str,
        room_id: str,
        user_id: str | None = None,
    ) -> WebSocketConnection:
        """Accept a WebSocket connection and add it to the appropriate tenant room.

        Args:
            websocket: The WebSocket connection object
            tenant_id: Tenant identifier for isolation
            room_id: Room/channel identifier
            user_id: Optional user identifier

        Returns:
            WebSocketConnection object with connection details

        """
        await websocket.accept()

        # Create connection object
        connection = WebSocketConnection(
            websocket=websocket, tenant_id=tenant_id, room_id=room_id, user_id=user_id,
        )

        # Initialize tenant dictionary if needed
        if tenant_id not in self.connections:
            self.connections[tenant_id] = {}

        # Initialize room list if needed
        if room_id not in self.connections[tenant_id]:
            self.connections[tenant_id][room_id] = []
            await self._setup_room_subscription(tenant_id, room_id)

        # Add connection to room
        self.connections[tenant_id][room_id].append(connection)
        self.connection_by_id[connection.connection_id] = connection

        logger.info(
            f"Client connected to tenant:{tenant_id}, room:{room_id}, conn_id:{connection.connection_id}",
        )

        # Notify room about new connection if user_id is provided
        if user_id:
            await self.broadcast_to_room(
                tenant_id,
                room_id,
                {"event": "user_joined", "user_id": user_id},
                exclude_connection_id=connection.connection_id,
            )

        return connection

    async def disconnect(
        self, websocket: WebSocket, tenant_id: str, room_id: str,
    ) -> None:
        """Remove a WebSocket connection when it disconnects.

        Args:
            websocket: The WebSocket connection object
            tenant_id: Tenant identifier
            room_id: Room identifier

        """
        # Find the connection to remove
        room_connections = self.connections.get(tenant_id, {}).get(room_id, [])
        connection = None

        for conn in room_connections:
            if conn.websocket == websocket:
                connection = conn
                break

        if connection:
            # Remove from room list
            self.connections[tenant_id][room_id].remove(connection)

            # Remove from ID lookup
            if connection.connection_id in self.connection_by_id:
                del self.connection_by_id[connection.connection_id]

            # Clean up empty room
            if not self.connections[tenant_id][room_id]:
                del self.connections[tenant_id][room_id]
                await self._cleanup_room_subscription(tenant_id, room_id)

            # Clean up empty tenant
            if tenant_id in self.connections and not self.connections[tenant_id]:
                del self.connections[tenant_id]

            # Notify room about disconnection if user_id was provided
            if connection.user_id:
                await self.broadcast_to_room(
                    tenant_id,
                    room_id,
                    {"event": "user_left", "user_id": connection.user_id},
                )

            logger.info(f"Client disconnected from tenant:{tenant_id}, room:{room_id}")
        else:
            logger.warning(
                f"Attempted to disconnect a non-existing connection: tenant:{tenant_id}, room:{room_id}",
            )

    async def broadcast_to_room(
        self,
        tenant_id: str,
        room_id: str,
        message: str | dict[str, Any],
        exclude_connection_id: str | None = None,
    ) -> int:
        """Broadcast a message to all connections in a room.

        This method publishes to Redis to ensure the message reaches
        all server instances in a distributed deployment.

        Args:
            tenant_id: Tenant identifier
            room_id: Room identifier
            message: Message to broadcast (string or dict)
            exclude_connection_id: Optional connection ID to exclude

        Returns:
            Number of clients the message was sent to

        """
        # Create the channel name
        channel = RedisPubSubManager.get_tenant_room_channel(tenant_id, room_id)

        # Add metadata to dict messages
        if isinstance(message, dict):
            message_with_meta = message.copy()
            if "timestamp" not in message_with_meta:
                message_with_meta["timestamp"] = datetime.now().isoformat()
            message = message_with_meta

        # Add metadata for excluding connections
        if exclude_connection_id:
            if isinstance(message, str):
                # Convert string to dict for metadata
                try:
                    message_dict = json.loads(message)
                    message_dict["exclude_connection_id"] = exclude_connection_id
                    message = json.dumps(message_dict)
                except json.JSONDecodeError:
                    # If not JSON, create a wrapper object
                    message = json.dumps(
                        {
                            "content": message,
                            "exclude_connection_id": exclude_connection_id,
                            "timestamp": datetime.now().isoformat(),
                        },
                    )
            else:
                # Add to dict directly
                message["exclude_connection_id"] = exclude_connection_id

        # Publish to Redis for cross-server broadcasting
        return await self.pubsub.publish(channel, message)

    async def send_to_connection(
        self, connection_id: str, message: str | dict[str, Any],
    ) -> bool:
        """Send a message to a specific connection by ID.

        Args:
            connection_id: Unique connection identifier
            message: Message to send (string or dict)

        Returns:
            True if message was sent, False if connection not found

        """
        connection = self.connection_by_id.get(connection_id)
        if not connection:
            logger.warning(
                f"Attempted to send to non-existing connection: {connection_id}",
            )
            return False

        # Convert dict to JSON string if needed
        if isinstance(message, dict):
            message = json.dumps(message)

        try:
            await connection.websocket.send_text(message)
            connection.last_activity = datetime.now()
            return True
        except Exception as e:
            logger.exception(f"Error sending to connection {connection_id}: {e}")
            return False

    async def get_connections_count(
        self, tenant_id: str | None = None,
    ) -> dict[str, int]:
        """Get the number of active connections, optionally filtered by tenant.

        Args:
            tenant_id: Optional tenant to filter by

        Returns:
            Dict with counts by tenant or total count

        """
        if tenant_id:
            rooms = self.connections.get(tenant_id, {})
            return {
                "total": sum(len(conns) for conns in rooms.values()),
                "rooms": {room: len(conns) for room, conns in rooms.items()},
            }
        result = {
            "total": sum(
                len(conns)
                for tenant in self.connections.values()
                for conns in tenant.values()
            ),
            "tenants": {},
        }

        for tenant_id, rooms in self.connections.items():
            tenant_total = sum(len(conns) for conns in rooms.values())
            result["tenants"][tenant_id] = tenant_total

        return result

    async def _setup_room_subscription(self, tenant_id: str, room_id: str) -> None:
        """Set up Redis subscription for a tenant+room channel.

        Args:
            tenant_id: Tenant identifier
            room_id: Room identifier

        """
        channel = RedisPubSubManager.get_tenant_room_channel(tenant_id, room_id)

        if channel in self.active_channels:
            return  # Already subscribed

        # Subscribe to channel
        pubsub = await self.pubsub.subscribe(channel)

        # Create task to process messages
        self.message_handlers[channel] = asyncio.create_task(
            self._process_messages(pubsub, tenant_id, room_id),
        )

        self.active_channels.add(channel)

    async def _cleanup_room_subscription(self, tenant_id: str, room_id: str) -> None:
        """Clean up Redis subscription for a tenant+room channel.

        Args:
            tenant_id: Tenant identifier
            room_id: Room identifier

        """
        channel = RedisPubSubManager.get_tenant_room_channel(tenant_id, room_id)

        if channel not in self.active_channels:
            return  # Not subscribed

        # Cancel message handler task
        if channel in self.message_handlers:
            self.message_handlers[channel].cancel()
            del self.message_handlers[channel]

        # Unsubscribe from Redis
        await self.pubsub.unsubscribe(channel)
        self.active_channels.remove(channel)

    async def _process_messages(
        self, pubsub: aioredis.client.PubSub, tenant_id: str, room_id: str,
    ) -> None:
        """Process incoming messages from a Redis channel.

        Args:
            pubsub: Redis PubSub subscription
            tenant_id: Tenant identifier
            room_id: Room identifier

        """
        try:
            while True:
                message = await pubsub.get_message(ignore_subscribe_messages=True)
                if message is None:
                    await asyncio.sleep(0.01)
                    continue

                # Process the message
                try:
                    data = message["data"]
                    await self._deliver_message_to_room(tenant_id, room_id, data)
                except Exception as e:
                    logger.exception(f"Error processing message: {e}")
        except asyncio.CancelledError:
            logger.info(
                f"Message handler for tenant:{tenant_id}, room:{room_id} was cancelled",
            )
        except Exception as e:
            logger.exception(f"Unexpected error in message handler: {e}")

    async def _deliver_message_to_room(
        self, tenant_id: str, room_id: str, message: str,
    ) -> int:
        """Deliver a message to all connections in a room.

        Args:
            tenant_id: Tenant identifier
            room_id: Room identifier
            message: Message to deliver

        Returns:
            Number of connections the message was delivered to

        """
        room_connections = self.connections.get(tenant_id, {}).get(room_id, [])
        if not room_connections:
            return 0

        # Check if there's a connection to exclude
        exclude_connection_id = None
        try:
            # Parse the message if it's JSON
            message_data = message
            if isinstance(message, str):
                message_data = json.loads(message)

            if (
                isinstance(message_data, dict)
                and "exclude_connection_id" in message_data
            ):
                exclude_connection_id = message_data["exclude_connection_id"]

                # Remove the metadata if it was a dict
                if isinstance(message, dict):
                    message_copy = message_data.copy()
                    del message_copy["exclude_connection_id"]
                    message = json.dumps(message_copy)
        except (json.JSONDecodeError, TypeError):
            # Not JSON or not a dict, continue with original message
            pass

        # Deliver to connections
        count = 0
        for connection in room_connections:
            if (
                exclude_connection_id
                and connection.connection_id == exclude_connection_id
            ):
                continue

            try:
                await connection.websocket.send_text(message)
                connection.last_activity = datetime.now()
                count += 1
            except Exception as e:
                logger.exception(f"Error sending to websocket: {e}")
                # Connection might be stale, handle in separate process

        return count


# Global instance for application-wide use
_websocket_manager = None


async def get_websocket_manager() -> WebSocketManager:
    """Get or create the global WebSocket manager instance.

    Returns:
        WebSocket manager instance

    """
    global _websocket_manager
    if _websocket_manager is None:
        settings = get_settings()
        _websocket_manager = WebSocketManager(redis_url=settings.REDIS_URL)
    return _websocket_manager


# Clean up resources on application shutdown
async def cleanup_websocket_manager() -> None:
    """Clean up WebSocket manager resources on application shutdown."""
    global _websocket_manager
    if _websocket_manager:
        await _websocket_manager.pubsub.disconnect()
        _websocket_manager = None
        logger.info("WebSocket manager resources cleaned up")
