"""
Notification models for the application.

This module defines the database models for notifications, notification preferences,
and notification templates.
"""

from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any
from sqlalchemy import Column, String, DateTime, Boolean, ForeignKey, JSON, Text, Integer
from sqlalchemy.dialects.postgresql import UUID
import uuid

from app.db.base import Base


class NotificationStatus(str, Enum):
    """Status of a notification"""
    UNREAD = "unread"
    READ = "read"
    ARCHIVED = "archived"
    DELETED = "deleted"


class NotificationPriority(str, Enum):
    """Priority levels for notifications"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


class NotificationCategory(str, Enum):
    """Categories of notifications"""
    SYSTEM = "system"
    SECURITY = "security"
    BILLING = "billing"
    SUBSCRIPTION = "subscription"
    FEATURE = "feature"
    TASK = "task"
    USER = "user"
    CONTENT = "content"
    ACTIVITY = "activity"
    OTHER = "other"


class NotificationChannel(str, Enum):
    """Delivery channels for notifications"""
    IN_APP = "in_app"
    EMAIL = "email"
    SMS = "sms"
    PUSH = "push"
    WEBHOOK = "webhook"
    SLACK = "slack"


class Notification(Base):
    """
    Notification database model.
    
    Represents a notification sent to a user or tenant.
    """
    __tablename__ = "notifications"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Who the notification is for
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=True, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True)
    
    # Notification content
    title = Column(String(255), nullable=False)
    body = Column(Text, nullable=False)
    category = Column(String(50), nullable=False)
    priority = Column(String(20), nullable=False, default=NotificationPriority.NORMAL)
    
    # Additional data (link, image, etc.)
    data = Column(JSON, nullable=True)
    
    # Source info
    source_type = Column(String(50), nullable=True)
    source_id = Column(String(255), nullable=True)
    
    # Status tracking
    status = Column(String(20), nullable=False, default=NotificationStatus.UNREAD)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    read_at = Column(DateTime, nullable=True)
    
    # Delivery tracking
    delivered = Column(Boolean, nullable=False, default=False)
    delivered_at = Column(DateTime, nullable=True)
    delivery_attempts = Column(Integer, nullable=False, default=0)
    delivery_channel = Column(String(20), nullable=True)
    
    # Optional expiration
    expires_at = Column(DateTime, nullable=True)
    
    def __repr__(self) -> str:
        return f"<Notification(id={self.id}, tenant={self.tenant_id}, user={self.user_id}, status={self.status})>"


class NotificationPreference(Base):
    """
    User notification preferences.
    
    Defines how a user wants to receive different types of notifications.
    """
    __tablename__ = "notification_preferences"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    
    # Notification category and channel
    category = Column(String(50), nullable=False)
    channel = Column(String(20), nullable=False)
    
    # Preference settings
    enabled = Column(Boolean, nullable=False, default=True)
    muted_until = Column(DateTime, nullable=True)
    
    # For email/SMS/push configuration
    delivery_config = Column(JSON, nullable=True)
    
    # Control frequency of non-critical notifications
    throttle_rate = Column(Integer, nullable=True)  # in minutes
    minimum_priority = Column(String(20), nullable=False, default=NotificationPriority.LOW)
    
    # Metadata
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    class Meta:
        """Define unique constraints"""
        unique_together = ("user_id", "category", "channel")
    
    def __repr__(self) -> str:
        return f"<NotificationPreference(user={self.user_id}, category={self.category}, channel={self.channel})>"


class NotificationTemplate(Base):
    """
    Notification template for consistent messaging.
    
    Templates can contain placeholders that will be replaced with actual values.
    """
    __tablename__ = "notification_templates"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False, unique=True)
    
    # Template content
    title_template = Column(Text, nullable=False)
    body_template = Column(Text, nullable=False)
    
    # Default category and priority
    category = Column(String(50), nullable=False, default=NotificationCategory.SYSTEM)
    priority = Column(String(20), nullable=False, default=NotificationPriority.NORMAL)
    
    # Default channel configuration
    default_channels = Column(JSON, nullable=True)  # List of enabled channels
    
    # Template metadata
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self) -> str:
        return f"<NotificationTemplate(name={self.name}, category={self.category})>"
