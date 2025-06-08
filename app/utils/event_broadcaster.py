"""Event Broadcasting System for FastAPI Applications.

This module provides a scalable event broadcasting system that:
1. Supports tenant-aware event segregation
2. Uses Redis for distributed event publication
3. Integrates with WebSockets for real-time client notifications
4. Provides structured event types and filtering
5. Enables persistent event history

Usage:
    # Anywhere in application code
    from app.utils.event_broadcaster import get_event_broadcaster

    # Emit an event
    broadcaster = await get_event_broadcaster()
    await broadcaster.emit(
        event_type="user.created",
        tenant_id="tenant123",
        data={"user_id": "user456", "email": "user@example.com"},
        targets=["admin", "audit"]
    )
"""

import asyncio
import json
import logging
import uuid
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, Field, field_validator

from app.core.config import get_settings
from app.utils.websocket_manager import RedisPubSubManager

if TYPE_CHECKING:
    from redis.asyncio import Redis

# Configure logging
logger = logging.getLogger(__name__)


class EventPriority(str, Enum):
    """Priority levels for events."""

    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


class EventScope(str, Enum):
    """Scope of the event (determines visibility)."""

    SYSTEM = "system"  # System-level events (visible to admins)
    TENANT = "tenant"  # Tenant-level events (visible within tenant)
    USER = "user"  # User-level events (visible to specific users)
    PUBLIC = "public"  # Public events (visible to all authenticated users)


class EventPayload(BaseModel):
    """Standard structure for event payload."""

    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    event_type: str
    tenant_id: str | None = None
    user_id: str | None = None
    timestamp: datetime = Field(default_factory=datetime.now)
    priority: EventPriority = EventPriority.NORMAL
    scope: EventScope = EventScope.TENANT
    data: dict[str, Any] = {}
    targets: list[str] = []  # Target rooms, users, or channels
    persistent: bool = False  # Whether to store in event history

    @field_validator("event_type")
    @classmethod
    def validate_event_type(cls, v):
        """Validate event type follows the namespace.action pattern."""
        if not v or "." not in v:
            msg = "event_type must follow format 'namespace.action'"
            raise ValueError(msg)
        return v

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary with datetime handling."""
        result = self.dict()
        result["timestamp"] = self.timestamp.isoformat()
        return result


class EventSubscription(BaseModel):
    """Represents a subscription to event types."""

    subscriber_id: str
    tenant_id: str | None = None
    event_types: list[str] = []  # Can include wildcards, e.g. "user.*"
    min_priority: EventPriority = EventPriority.LOW
    created_at: datetime = Field(default_factory=datetime.now)


class EventBroadcaster:
    """Event broadcasting system for real-time application events.

    This class manages event emission, subscription, and delivery
    across a distributed system using Redis and WebSockets.
    """

    def __init__(self, redis_url: str | None = None) -> None:
        """Initialize the event broadcaster.

        Args:
            redis_url: Optional Redis URL. If None, uses settings value.

        """
        self.redis_url = redis_url
        self.redis_client: Redis | None = None
        self.pubsub_manager = RedisPubSubManager(redis_url)

        # In-memory subscriptions by subscriber ID
        self.subscriptions: dict[str, list[EventSubscription]] = {}

        # In-memory recent events (for immediate replay)
        self.recent_events: dict[str, list[EventPayload]] = {}
        self.max_recent_events = 100  # Per tenant

        # Task to process system-wide events
        self._system_event_task = None

        logger.info("EventBroadcaster initialized")

    async def connect(self) -> None:
        """Connect to Redis if not already connected."""
        await self.pubsub_manager.connect()

        # Subscribe to system-wide events
        if self._system_event_task is None:
            pubsub = await self.pubsub_manager.subscribe("events:system")
            self._system_event_task = asyncio.create_task(
                self._process_system_events(pubsub),
            )

    async def disconnect(self) -> None:
        """Disconnect from Redis and clean up resources."""
        # Cancel event processing task
        if self._system_event_task:
            self._system_event_task.cancel()
            self._system_event_task = None

        # Disconnect pub/sub manager
        await self.pubsub_manager.disconnect()

    async def emit(
        self,
        event_type: str,
        data: dict[str, Any],
        tenant_id: str | None = None,
        user_id: str | None = None,
        priority: EventPriority = EventPriority.NORMAL,
        scope: EventScope = EventScope.TENANT,
        targets: list[str] | None = None,
        persistent: bool = False,
    ) -> str:
        """Emit an event for broadcasting.

        Args:
            event_type: Type of event in format "namespace.action"
            data: Event payload data
            tenant_id: Optional tenant identifier for isolation
            user_id: Optional user who triggered the event
            priority: Priority level of the event
            scope: Scope determining event visibility
            targets: Optional specific targets for the event
            persistent: Whether to persist the event in history

        Returns:
            Unique ID of the emitted event

        """
        # Connect to Redis if needed
        await self.connect()

        # Create event payload
        event = EventPayload(
            event_type=event_type,
            tenant_id=tenant_id,
            user_id=user_id,
            data=data,
            priority=priority,
            scope=scope,
            targets=targets or [],
            persistent=persistent,
        )

        # Convert to dictionary for serialization
        event_dict = event.to_dict()

        # Store in recent events if applicable
        if tenant_id:
            self._add_to_recent_events(tenant_id, event)

        # Persist event if requested
        if persistent:
            await self._store_event(event)

        # Process event to trigger notifications
        await self._process_event(event_dict)

        # Determine channels to publish to
        channels = self._get_event_channels(event)

        # Publish to Redis for distributed broadcasting
        for channel in channels:
            await self.pubsub_manager.publish(channel, event_dict)

        return event.event_id

    async def subscribe(
        self,
        subscriber_id: str,
        event_types: list[str],
        tenant_id: str | None = None,
        min_priority: EventPriority = EventPriority.LOW,
    ) -> None:
        """Subscribe to events matching specified types.

        Args:
            subscriber_id: Unique ID for the subscriber
            event_types: List of event types to subscribe to (can use wildcards)
            tenant_id: Optional tenant filter
            min_priority: Minimum priority to receive

        """
        subscription = EventSubscription(
            subscriber_id=subscriber_id,
            tenant_id=tenant_id,
            event_types=event_types,
            min_priority=min_priority,
        )

        if subscriber_id not in self.subscriptions:
            self.subscriptions[subscriber_id] = []

        self.subscriptions[subscriber_id].append(subscription)

        # Subscribe to Redis channels if needed
        for event_type in event_types:
            if event_type.endswith(".*"):
                # Wildcard subscription needs special handling
                namespace = event_type.split(".")[0]
                channel = f"events:{tenant_id or '*'}:{namespace}:*"
            else:
                channel = f"events:{tenant_id or '*'}:{event_type}"

            # For system-wide events, we're already subscribed
            if channel not in {"events:system", "events:*:*"}:
                await self.pubsub_manager.subscribe(channel)
                # TODO: Store subscription for cleanup

    async def unsubscribe(self, subscriber_id: str) -> None:
        """Unsubscribe from all events.

        Args:
            subscriber_id: Unique ID of the subscriber to remove

        """
        if subscriber_id in self.subscriptions:
            del self.subscriptions[subscriber_id]
            # TODO: Clean up Redis subscriptions if no more local subscribers

    async def get_recent_events(
        self, tenant_id: str, event_types: list[str] | None = None, limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Get recent events for a tenant, optionally filtered by type.

        Args:
            tenant_id: Tenant identifier
            event_types: Optional list of event types to filter by
            limit: Maximum number of events to return

        Returns:
            List of recent events as dicts

        """
        if tenant_id not in self.recent_events:
            return []

        events = self.recent_events[tenant_id]

        if event_types:
            # Filter by event type
            events = [
                e
                for e in events
                if any(
                    self._event_type_matches(e.event_type, pattern)
                    for pattern in event_types
                )
            ]

        # Sort by timestamp (newest first) and limit
        events.sort(key=lambda e: e.timestamp, reverse=True)
        return [e.to_dict() for e in events[:limit]]

    async def get_historical_events(
        self,
        tenant_id: str,
        event_types: list[str] | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Get historical events from persistent storage.

        Args:
            tenant_id: Tenant identifier
            event_types: Optional list of event types to filter by
            start_time: Optional start time filter
            end_time: Optional end time filter
            limit: Maximum number of events to return

        Returns:
            List of historical events as dicts

        """
        # TODO: Implement fetching from database
        # For now, we'll just return recent events
        return await self.get_recent_events(tenant_id, event_types, limit)

    async def _store_event(self, event: EventPayload) -> None:
        """Store an event in persistent storage.

        Args:
            event: Event payload to store

        """
        # TODO: Implement database storage

    def _add_to_recent_events(self, tenant_id: str, event: EventPayload) -> None:
        """Add an event to the in-memory recent events list.

        Args:
            tenant_id: Tenant identifier
            event: Event to add

        """
        if tenant_id not in self.recent_events:
            self.recent_events[tenant_id] = []

        # Add to list
        self.recent_events[tenant_id].append(event)

        # Trim if exceeding max size
        if len(self.recent_events[tenant_id]) > self.max_recent_events:
            # Remove oldest events
            self.recent_events[tenant_id] = self.recent_events[tenant_id][
                -self.max_recent_events :
            ]

    def _get_event_channels(self, event: EventPayload) -> list[str]:
        """Get Redis channels to publish an event to.

        Args:
            event: Event payload

        Returns:
            List of channel names

        """
        channels = []

        # Always publish to the specific event type channel
        if event.tenant_id:
            channels.append(f"events:{event.tenant_id}:{event.event_type}")

        # For public and system scope, also publish to wider channels
        if event.scope == EventScope.PUBLIC:
            channels.append(f"events:public:{event.event_type}")
        elif event.scope == EventScope.SYSTEM:
            channels.append(f"events:system:{event.event_type}")

        # Add target-specific channels
        for target in event.targets:
            if event.tenant_id:
                channels.append(f"events:{event.tenant_id}:target:{target}")
            else:
                channels.append(f"events:target:{target}")

        return channels

    @staticmethod
    def _event_type_matches(event_type: str, pattern: str) -> bool:
        """Check if an event type matches a pattern (supports wildcards).

        Args:
            event_type: Actual event type
            pattern: Pattern to match against (can include wildcards)

        Returns:
            True if matches, False otherwise

        """
        if pattern in {"*", "*.*"}:
            return True

        if pattern.endswith(".*"):
            namespace = pattern.split(".")[0]
            return event_type.startswith(f"{namespace}.")

        return event_type == pattern

    async def _process_system_events(self, pubsub) -> None:
        """Process incoming events from the system-wide channel.

        Args:
            pubsub: Redis PubSub subscription

        """
        try:
            async for message in pubsub.listen():
                if message and message["type"] == "message":
                    event_data = json.loads(message["data"])
                    await self._process_event(event_data)
        except Exception as e:
            logger.exception(f"Error processing system events: {e}")

    async def _process_event(self, event_data: dict[str, Any]) -> None:
        """Process an incoming event and deliver to subscribers.

        Args:
            event_data: Event data dictionary

        """
        try:
            # Get notification service
            from app.utils.notification_service import get_notification_service

            notification_service = await get_notification_service()

            # Convert event data to EventPayload
            event = EventPayload(**event_data)

            # Process the event to trigger a notification
            await notification_service.process_event(event)

        except Exception as e:
            logger.exception(f"Error processing event: {e}")

    async def _process_event(self, event_data: dict[str, Any]) -> None:
        """Process an incoming event and deliver to subscribers.

        Args:
            event_data: Event data dictionary

        """
        try:
            # Get notification service
            from app.utils.notification_service import get_notification_service

            notification_service = await get_notification_service()

            # Convert event data to EventPayload
            event = EventPayload(**event_data)

            # Process the event to trigger a notification
            await notification_service.process_event(event)

        except Exception as e:
            logger.exception(f"Error processing event: {e}")


# Global instance for application-wide use
_event_broadcaster = None


async def get_event_broadcaster() -> EventBroadcaster:
    """Get or create the global event broadcaster instance.

    Returns:
        Event broadcaster instance

    """
    global _event_broadcaster
    if _event_broadcaster is None:
        settings = get_settings()
        _event_broadcaster = EventBroadcaster(redis_url=settings.REDIS_URL)
        await _event_broadcaster.connect()
    return _event_broadcaster


# Clean up resources on application shutdown
async def cleanup_event_broadcaster() -> None:
    """Clean up event broadcaster resources on application shutdown."""
    global _event_broadcaster
    if _event_broadcaster:
        await _event_broadcaster.disconnect()
        _event_broadcaster = None
        logger.info("Event broadcaster resources cleaned up")
