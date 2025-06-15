"""Enterprise WebSocket Manager
Real-time communication with Redis pub/sub, authentication, and scalable architecture.
"""

import asyncio
import json
import uuid
from datetime import datetime, timedelta
from enum import Enum
from typing import Any

import jwt
from fastapi import WebSocket
from fastapi.websockets import WebSocketState
from jwt import PyJWTError
from loguru import logger
from pydantic import BaseModel, ValidationError

from app.core.config import get_settings
from app.core.redis_manager import redis_manager

# Get JWT settings
settings = get_settings()
SECRET_KEY = settings.jwt_secret_token
ALGORITHM = "HS256"


class MessageType(str, Enum):
    """WebSocket message types."""

    PING = "ping"
    PONG = "pong"
    AUTH = "auth"
    SUBSCRIBE = "subscribe"
    UNSUBSCRIBE = "unsubscribe"
    MESSAGE = "message"
    NOTIFICATION = "notification"
    ERROR = "error"
    STATUS = "status"


class ConnectionStatus(str, Enum):
    """Connection status states."""

    CONNECTING = "connecting"
    AUTHENTICATED = "authenticated"
    ACTIVE = "active"
    DISCONNECTED = "disconnected"
    ERROR = "error"


class WebSocketMessage(BaseModel):
    """WebSocket message structure."""

    type: MessageType
    data: dict[str, Any] | None = None
    channel: str | None = None
    timestamp: datetime | None = None
    message_id: str | None = None


class ConnectionInfo(BaseModel):
    """Connection metadata."""

    connection_id: str
    user_id: str | None = None
    status: ConnectionStatus
    connected_at: datetime
    last_ping: datetime | None = None
    subscribed_channels: set[str] = set()
    metadata: dict[str, Any] | None = None


class WebSocketConnection:
    """Individual WebSocket connection wrapper."""

    def __init__(self, websocket: WebSocket, connection_id: str) -> None:
        self.websocket = websocket
        self.connection_id = connection_id
        self.user_id: str | None = None
        self.status = ConnectionStatus.CONNECTING
        self.connected_at = datetime.utcnow()
        self.last_ping: datetime | None = None
        self.subscribed_channels: set[str] = set()
        self.metadata: dict[str, Any] = {}

    async def send_message(self, message: WebSocketMessage) -> None:
        """Send message to client."""
        try:
            if self.websocket.client_state == WebSocketState.CONNECTED:
                message_dict = message.dict()
                if message.timestamp is None:
                    message_dict["timestamp"] = datetime.utcnow().isoformat()
                if message.message_id is None:
                    message_dict["message_id"] = str(uuid.uuid4())

                await self.websocket.send_text(json.dumps(message_dict))
                logger.debug(f"Sent message to {self.connection_id}: {message.type}")
            else:
                logger.warning(
                    f"Cannot send message to disconnected websocket: {self.connection_id}",
                )
        except Exception as e:
            logger.error(f"Failed to send message to {self.connection_id}: {e}")
            self.status = ConnectionStatus.ERROR

    async def send_error(self, error_message: str, error_code: str | None = None) -> None:
        """Send error message to client."""
        error_msg = WebSocketMessage(
            type=MessageType.ERROR, data={"message": error_message, "code": error_code},
        )
        await self.send_message(error_msg)

    def is_authenticated(self) -> bool:
        """Check if connection is authenticated."""
        return self.user_id is not None and self.status in [
            ConnectionStatus.AUTHENTICATED,
            ConnectionStatus.ACTIVE,
        ]


class EnterpriseWebSocketManager:
    """Enterprise WebSocket manager with Redis backing and authentication."""

    def __init__(self) -> None:
        self.settings = get_settings()
        self.connections: dict[str, WebSocketConnection] = {}
        self.user_connections: dict[str, set[str]] = {}  # user_id -> connection_ids
        self.channel_subscriptions: dict[
            str, set[str],
        ] = {}  # channel -> connection_ids
        self.heartbeat_interval = 30  # seconds
        self.connection_timeout = 300  # 5 minutes
        self._heartbeat_task: asyncio.Task | None = None

    async def initialize(self) -> None:
        """Initialize WebSocket manager."""
        await redis_manager.initialize()

        # Start heartbeat task
        if not self._heartbeat_task:
            self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())

        logger.info("WebSocket manager initialized")

    async def connect(self, websocket: WebSocket, token: str | None = None) -> str:
        """Accept new WebSocket connection."""
        await websocket.accept()

        connection_id = str(uuid.uuid4())
        connection = WebSocketConnection(websocket, connection_id)

        self.connections[connection_id] = connection

        # Send welcome message
        welcome_msg = WebSocketMessage(
            type=MessageType.STATUS,
            data={
                "status": "connected",
                "connection_id": connection_id,
                "server_time": datetime.utcnow().isoformat(),
                "requires_auth": True,
            },
        )
        await connection.send_message(welcome_msg)

        # If token provided, try to authenticate immediately
        if token:
            await self._authenticate_connection(connection, token)

        logger.info(f"WebSocket connected: {connection_id}")
        return connection_id

    async def disconnect(self, connection_id: str) -> None:
        """Disconnect WebSocket connection."""
        connection = self.connections.get(connection_id)
        if not connection:
            return

        try:
            # Unsubscribe from all channels
            for channel in list(connection.subscribed_channels):
                await self._unsubscribe_from_channel(connection, channel)

            # Remove from user connections
            if connection.user_id:
                user_connections = self.user_connections.get(connection.user_id, set())
                user_connections.discard(connection_id)
                if not user_connections:
                    del self.user_connections[connection.user_id]

            # Remove connection
            connection.status = ConnectionStatus.DISCONNECTED
            del self.connections[connection_id]

            logger.info(f"WebSocket disconnected: {connection_id}")

        except Exception as e:
            logger.error(f"Error during WebSocket disconnect: {e}")

    async def _authenticate_connection(
        self, connection: WebSocketConnection, token: str,
    ) -> bool:
        """Authenticate WebSocket connection."""
        try:
            # Verify JWT token
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            user_id = payload.get("sub")

            if not user_id:
                await connection.send_error("Invalid token: missing user ID")
                return False

            connection.user_id = user_id
            connection.status = ConnectionStatus.AUTHENTICATED

            # Track user connections
            if user_id not in self.user_connections:
                self.user_connections[user_id] = set()
            self.user_connections[user_id].add(connection.connection_id)

            # Send authentication success
            auth_msg = WebSocketMessage(
                type=MessageType.STATUS,
                data={
                    "status": "authenticated",
                    "user_id": user_id,
                    "connection_id": connection.connection_id,
                },
            )
            await connection.send_message(auth_msg)

            logger.info(
                f"WebSocket authenticated: {connection.connection_id} (user: {user_id})",
            )
            return True

        except PyJWTError as e:
            logger.error(f"WebSocket JWT authentication failed: {e}")
            await connection.send_error("Invalid or expired token", "AUTH_ERROR")
            return False
        except Exception as e:
            logger.error(f"WebSocket authentication failed: {e}")
            await connection.send_error("Authentication failed", "AUTH_ERROR")
            return False

    async def handle_message(self, connection_id: str, message_text: str) -> None:
        """Handle incoming WebSocket message."""
        connection = self.connections.get(connection_id)
        if not connection:
            logger.warning(f"Message received for unknown connection: {connection_id}")
            return

        try:
            # Parse message
            message_data = json.loads(message_text)
            message = WebSocketMessage(**message_data)

            logger.debug(f"Received message from {connection_id}: {message.type}")

            # Handle different message types
            if message.type == MessageType.PING:
                await self._handle_ping(connection)
            elif message.type == MessageType.AUTH:
                await self._handle_auth(connection, message)
            elif message.type == MessageType.SUBSCRIBE:
                await self._handle_subscribe(connection, message)
            elif message.type == MessageType.UNSUBSCRIBE:
                await self._handle_unsubscribe(connection, message)
            elif message.type == MessageType.MESSAGE:
                await self._handle_user_message(connection, message)
            else:
                await connection.send_error(f"Unknown message type: {message.type}")

        except ValidationError as e:
            await connection.send_error(f"Invalid message format: {e}")
        except json.JSONDecodeError:
            await connection.send_error("Invalid JSON format")
        except Exception as e:
            logger.error(f"Error handling WebSocket message: {e}")
            await connection.send_error("Internal server error")

    async def _handle_ping(self, connection: WebSocketConnection) -> None:
        """Handle ping message."""
        connection.last_ping = datetime.utcnow()
        pong_msg = WebSocketMessage(type=MessageType.PONG)
        await connection.send_message(pong_msg)

    async def _handle_auth(
        self, connection: WebSocketConnection, message: WebSocketMessage,
    ) -> None:
        """Handle authentication message."""
        if not message.data or "token" not in message.data:
            await connection.send_error("Authentication token required")
            return

        token = message.data["token"]
        await self._authenticate_connection(connection, token)

    async def _handle_subscribe(
        self, connection: WebSocketConnection, message: WebSocketMessage,
    ) -> None:
        """Handle channel subscription."""
        if not connection.is_authenticated():
            await connection.send_error("Authentication required")
            return

        if not message.channel:
            await connection.send_error("Channel name required")
            return

        await self._subscribe_to_channel(connection, message.channel)

    async def _handle_unsubscribe(
        self, connection: WebSocketConnection, message: WebSocketMessage,
    ) -> None:
        """Handle channel unsubscription."""
        if not message.channel:
            await connection.send_error("Channel name required")
            return

        await self._unsubscribe_from_channel(connection, message.channel)

    async def _handle_user_message(
        self, connection: WebSocketConnection, message: WebSocketMessage,
    ) -> None:
        """Handle user message for broadcasting."""
        if not connection.is_authenticated():
            await connection.send_error("Authentication required")
            return

        if not message.channel:
            await connection.send_error("Channel name required")
            return

        # Add sender information
        if not message.data:
            message.data = {}
        message.data["sender_id"] = connection.user_id
        message.data["sender_connection"] = connection.connection_id

        # Broadcast to channel
        await self.broadcast_to_channel(message.channel, message)

    async def _subscribe_to_channel(
        self, connection: WebSocketConnection, channel: str,
    ) -> None:
        """Subscribe connection to channel."""
        try:
            # Check permissions (implement your channel access logic here)
            if not await self._check_channel_permissions(connection.user_id, channel):
                await connection.send_error(f"Access denied to channel: {channel}")
                return

            # Add to local subscriptions
            connection.subscribed_channels.add(channel)

            if channel not in self.channel_subscriptions:
                self.channel_subscriptions[channel] = set()
            self.channel_subscriptions[channel].add(connection.connection_id)

            # Subscribe to Redis channel for cluster support
            await redis_manager.websocket_subscribe(
                channel, lambda data: self._handle_redis_message(channel, data),
            )

            # Send subscription confirmation
            sub_msg = WebSocketMessage(
                type=MessageType.STATUS,
                data={"status": "subscribed", "channel": channel},
            )
            await connection.send_message(sub_msg)

            logger.info(
                f"Connection {connection.connection_id} subscribed to {channel}",
            )

        except Exception as e:
            logger.error(f"Failed to subscribe to channel {channel}: {e}")
            await connection.send_error(f"Subscription failed: {e!s}")

    async def _unsubscribe_from_channel(
        self, connection: WebSocketConnection, channel: str,
    ) -> None:
        """Unsubscribe connection from channel."""
        try:
            connection.subscribed_channels.discard(channel)

            if channel in self.channel_subscriptions:
                self.channel_subscriptions[channel].discard(connection.connection_id)
                if not self.channel_subscriptions[channel]:
                    del self.channel_subscriptions[channel]

            # Send unsubscription confirmation
            unsub_msg = WebSocketMessage(
                type=MessageType.STATUS,
                data={"status": "unsubscribed", "channel": channel},
            )
            await connection.send_message(unsub_msg)

            logger.info(
                f"Connection {connection.connection_id} unsubscribed from {channel}",
            )

        except Exception as e:
            logger.error(f"Failed to unsubscribe from channel {channel}: {e}")

    async def _check_channel_permissions(
        self, user_id: str | None, channel: str,
    ) -> bool:
        """Check if user has permission to access channel."""
        # Implement your channel permission logic here
        # For now, allow access to public channels and user-specific channels

        if (
            channel.startswith(("public.", f"user.{user_id}.", "broadcast."))
        ):
            return True
        # Check database for custom permissions
        return False

    async def _handle_redis_message(self, channel: str, data: dict[str, Any]) -> None:
        """Handle message from Redis pub/sub."""
        try:
            message = WebSocketMessage(**data)
            await self.broadcast_to_channel(channel, message, exclude_sender=False)
        except Exception as e:
            logger.error(f"Failed to handle Redis message for channel {channel}: {e}")

    async def broadcast_to_channel(
        self, channel: str, message: WebSocketMessage, exclude_sender: bool = True,
    ) -> None:
        """Broadcast message to all subscribers of a channel."""
        if channel not in self.channel_subscriptions:
            return

        sender_connection = (
            message.data.get("sender_connection") if message.data else None
        )

        disconnected_connections = []

        for connection_id in self.channel_subscriptions[channel]:
            if exclude_sender and connection_id == sender_connection:
                continue

            connection = self.connections.get(connection_id)
            if connection:
                try:
                    await connection.send_message(message)
                except Exception as e:
                    logger.error(f"Failed to send message to {connection_id}: {e}")
                    disconnected_connections.append(connection_id)
            else:
                disconnected_connections.append(connection_id)

        # Clean up disconnected connections
        for conn_id in disconnected_connections:
            self.channel_subscriptions[channel].discard(conn_id)

        # Publish to Redis for cluster support
        await redis_manager.websocket_publish(channel, message.dict())

    async def send_to_user(self, user_id: str, message: WebSocketMessage) -> None:
        """Send message to all connections of a specific user."""
        user_connections = self.user_connections.get(user_id, set())

        for connection_id in list(user_connections):
            connection = self.connections.get(connection_id)
            if connection:
                try:
                    await connection.send_message(message)
                except Exception as e:
                    logger.error(f"Failed to send message to user {user_id}: {e}")
            else:
                user_connections.discard(connection_id)

    async def _heartbeat_loop(self) -> None:
        """Background task for connection heartbeat and cleanup."""
        while True:
            try:
                await asyncio.sleep(self.heartbeat_interval)

                current_time = datetime.utcnow()
                timeout_threshold = current_time - timedelta(
                    seconds=self.connection_timeout,
                )

                expired_connections = []

                for connection_id, connection in self.connections.items():
                    # Check for timed out connections
                    last_activity = connection.last_ping or connection.connected_at

                    if last_activity < timeout_threshold:
                        expired_connections.append(connection_id)

                # Clean up expired connections
                for connection_id in expired_connections:
                    logger.info(f"Cleaning up expired connection: {connection_id}")
                    await self.disconnect(connection_id)

                logger.debug(f"Heartbeat: {len(self.connections)} active connections")

            except Exception as e:
                logger.error(f"Heartbeat loop error: {e}")

    async def get_connection_stats(self) -> dict[str, Any]:
        """Get WebSocket connection statistics."""
        return {
            "total_connections": len(self.connections),
            "authenticated_connections": len(
                [c for c in self.connections.values() if c.is_authenticated()],
            ),
            "active_users": len(self.user_connections),
            "active_channels": len(self.channel_subscriptions),
            "total_subscriptions": sum(
                len(subs) for subs in self.channel_subscriptions.values()
            ),
        }

    async def shutdown(self) -> None:
        """Shutdown WebSocket manager."""
        # Cancel heartbeat task
        if self._heartbeat_task:
            self._heartbeat_task.cancel()

        # Disconnect all connections
        connection_ids = list(self.connections.keys())
        for connection_id in connection_ids:
            await self.disconnect(connection_id)

        logger.info("WebSocket manager shutdown complete")


# Global WebSocket manager instance
websocket_manager = EnterpriseWebSocketManager()
