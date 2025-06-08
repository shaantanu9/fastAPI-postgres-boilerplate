"""Notification Service.

This module provides a service for sending, delivering, and managing notifications.
It integrates with the event broadcaster to listen for events and trigger notifications.
"""

import json
import logging
from datetime import datetime
from typing import Any

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.session import get_db
from app.models.notification import (
    Notification,
    NotificationChannel,
    NotificationPriority,
    NotificationTemplate,
)
from app.utils.event_broadcaster import EventPayload, get_event_broadcaster
from app.utils.websocket_manager import get_websocket_manager

# Configure logging
logger = logging.getLogger(__name__)


class NotificationService:
    """Service for handling notifications.

    This class manages sending, delivering, and tracking notifications.
    It integrates with the event broadcaster to listen for events and trigger notifications.
    """

    def __init__(
        self,
        db_session: AsyncSession,
        event_broadcaster=Depends(get_event_broadcaster),
        websocket_manager=Depends(get_websocket_manager),
    ) -> None:
        """Initialize the notification service.

        Args:
            db_session: Database session
            event_broadcaster: Event broadcaster instance
            websocket_manager: WebSocket manager instance

        """
        self.db_session = db_session
        self.event_broadcaster = event_broadcaster
        self.websocket_manager = websocket_manager
        self.settings = get_settings()

        # In-memory cache for notification templates
        self.templates: dict[str, NotificationTemplate] = {}

        logger.info("NotificationService initialized")

    async def initialize(self) -> None:
        """Initialize the notification service (load templates, subscribe to events)."""
        # Load notification templates from database
        await self._load_preferences()
        await self._load_templates()

        # Subscribe to relevant events
        await self._subscribe_to_events()

    async def _load_preferences(self) -> None:
        """Load notification preferences from the database into the cache."""
        # TODO: Implement preference loading from database
        # For now, we don't load any preferences
        logger.info("Loaded notification preferences")

    async def _load_templates(self) -> None:
        """Load notification templates from the database into the cache."""
        # TODO: Implement template loading from database
        # For now, we'll just define some hardcoded templates
        self.templates = {
            "user.created": NotificationTemplate(
                name="user.created",
                title_template="Welcome to the platform!",
                body_template="Hi {{user.name}}, welcome to our platform!",
            ),
            "task.completed": NotificationTemplate(
                name="task.completed",
                title_template="Task Completed!",
                body_template="Task '{{task.name}}' has been completed.",
            ),
        }
        logger.info(f"Loaded {len(self.templates)} notification templates")

    async def _subscribe_to_events(self) -> None:
        """Subscribe to relevant events using the event broadcaster."""
        # Subscribe to user-related events
        await self.event_broadcaster.subscribe(
            subscriber_id="notification_service",
            event_types=["user.created", "user.updated", "user.deleted"],
        )

        # Subscribe to task-related events
        await self.event_broadcaster.subscribe(
            subscriber_id="notification_service",
            event_types=["task.created", "task.updated", "task.completed"],
        )

        logger.info("Subscribed to relevant events")

    async def create_notification(
        self,
        tenant_id: str | None,
        user_id: str | None,
        title: str,
        body: str,
        category: str,
        priority: NotificationPriority = NotificationPriority.NORMAL,
        data: dict[str, Any] | None = None,
        source_type: str | None = None,
        source_id: str | None = None,
        delivery_channel: str | None = None,
    ) -> Notification:
        """Create a new notification.

        Args:
            tenant_id: Tenant ID
            user_id: User ID
            title: Notification title
            body: Notification body
            category: Notification category
            priority: Notification priority
            data: Additional data
            source_type: Source type
            source_id: Source ID
            delivery_channel: Delivery channel

        Returns:
            Created notification object

        """
        notification = Notification(
            tenant_id=tenant_id,
            user_id=user_id,
            title=title,
            body=body,
            category=category,
            priority=priority,
            data=data,
            source_type=source_type,
            source_id=source_id,
            delivery_channel=delivery_channel,
        )

        self.db_session.add(notification)
        await self.db_session.commit()
        await self.db_session.refresh(notification)

        logger.info(f"Created notification {notification.id}")
        return notification

    async def send_notification(self, notification: Notification) -> None:
        """Send a notification to the user through the specified channel.

        Args:
            notification: Notification object to send

        """
        # Determine delivery channel
        channel = notification.delivery_channel or NotificationChannel.IN_APP

        # Send via WebSocket (in-app)
        if channel == NotificationChannel.IN_APP:
            await self._send_websocket_notification(notification)

        # TODO: Implement other channels (email, SMS, push, webhook)

        # Update delivery status
        notification.delivered = True
        notification.delivered_at = datetime.utcnow()
        await self.db_session.commit()
        logger.info(f"Sent notification {notification.id} via {channel}")

    async def _send_websocket_notification(self, notification: Notification) -> None:
        """Send a notification to a user via WebSocket.

        Args:
            notification: Notification object

        """
        if not notification.tenant_id or not notification.user_id:
            logger.warning(
                "Cannot send WebSocket notification without tenant and user ID",
            )
            return

        # Convert to dictionary for JSON serialization
        notification_dict = {
            "id": str(notification.id),
            "title": notification.title,
            "body": notification.body,
            "category": notification.category,
            "priority": notification.priority,
            "data": notification.data,
            "source_type": notification.source_type,
            "source_id": notification.source_id,
            "status": notification.status,
            "created_at": notification.created_at.isoformat(),
        }

        # Send to the user's room (if connected)
        room_id = f"user:{notification.user_id}"
        await self.websocket_manager.broadcast_to_room(
            tenant_id=str(notification.tenant_id),
            room_id=room_id,
            message=json.dumps(notification_dict),
        )

        logger.debug(
            f"Sent WebSocket notification {notification.id} to user {notification.user_id}",
        )

    async def process_event(self, event: EventPayload) -> None:
        """Process an incoming event and trigger a notification.

        Args:
            event: Event payload

        """
        logger.info(f"Processing event: {event.event_type}")

        # Get notification template
        template = self.templates.get(event.event_type)
        if not template:
            logger.warning(f"No template found for event type: {event.event_type}")
            return

        # Render title and body
        title = template.title_template
        body = template.body_template

        # Replace placeholders with event data
        if event.data:
            try:
                title = title.format(**event.data)
                body = body.format(**event.data)
            except KeyError as e:
                logger.exception(f"Missing key in event data: {e}")
                return

        # Create notification
        notification = await self.create_notification(
            tenant_id=event.tenant_id,
            user_id=event.user_id,
            title=title,
            body=body,
            category=template.category,
            priority=template.priority,
            data=event.data,
            source_type=event.event_type,
            source_id=event.event_id,
        )

        # Send notification
        await self.send_notification(notification)


# Global instance for application-wide use
_notification_service = None


async def get_notification_service(
    db: AsyncSession = Depends(get_db),
    event_broadcaster=Depends(get_event_broadcaster),
    websocket_manager=Depends(get_websocket_manager),
) -> NotificationService:
    """Get or create the global notification service instance.

    Returns:
        Notification service instance

    """
    global _notification_service
    if _notification_service is None:
        _notification_service = NotificationService(
            db_session=db,
            event_broadcaster=event_broadcaster,
            websocket_manager=websocket_manager,
        )
        await _notification_service.initialize()
    return _notification_service


# Dependency for FastAPI endpoints
async def get_notification_service_dep(
    service: NotificationService = Depends(get_notification_service),
) -> NotificationService:
    """FastAPI dependency for notification service."""
    return service
