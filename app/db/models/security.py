"""Security-related database models.
Defines models for API keys, security events, and other security-related entities.
"""

import uuid
from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from app.db.base import Base

# APIKey model moved to app.models.security.api_key to avoid duplication


class SecurityEvent(Base):
    """Security event log for audit trail."""

    __tablename__ = "security_events"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

    # Event details
    event_type = Column(String(50), nullable=False, index=True)
    event_category = Column(String(50), nullable=False, index=True)
    event_data = Column(JSON, nullable=False)  # Structured event data

    # Context
    user_id = Column(String, ForeignKey("users.id"), nullable=True)
    organization_id = Column(String, ForeignKey("organizations.id"), nullable=True)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)

    # Risk assessment
    risk_score = Column(Integer, default=0)  # 0-100
    status = Column(String(20), nullable=False)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User")
    organization = relationship("Organization")


class SecurityConfiguration(Base):
    """Global and organization-specific security configurations."""

    __tablename__ = "security_configurations"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    organization_id = Column(String, ForeignKey("organizations.id"), nullable=True)

    # Password policy
    password_min_length = Column(Integer, default=8)
    password_require_uppercase = Column(Boolean, default=True)
    password_require_lowercase = Column(Boolean, default=True)
    password_require_numbers = Column(Boolean, default=True)
    password_require_special = Column(Boolean, default=True)
    password_max_age_days = Column(Integer, default=90)

    # Authentication settings
    mfa_required = Column(Boolean, default=False)
    allowed_auth_methods = Column(JSON, default=list)  # ["password", "sso", "passkey"]
    session_timeout_minutes = Column(Integer, default=60)
    max_sessions_per_user = Column(Integer, default=5)

    # API security
    api_key_expiry_days = Column(Integer, default=365)
    api_rate_limit_per_minute = Column(Integer, default=60)

    # IP security
    allowed_ip_ranges = Column(JSON, default=list)  # List of allowed CIDR ranges
    geo_blocking_enabled = Column(Boolean, default=False)
    blocked_countries = Column(JSON, default=list)

    # Audit settings
    audit_log_retention_days = Column(Integer, default=365)
    high_risk_notification_threshold = Column(Integer, default=75)

    # Updated timestamp
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    organization = relationship("Organization")


class BlockedIP(Base):
    """IP addresses blocked due to suspicious activity."""

    __tablename__ = "blocked_ips"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    ip_address = Column(String(45), nullable=False, unique=True, index=True)

    # Block details
    reason = Column(String(255), nullable=False)
    risk_score = Column(Integer, default=0)
    block_count = Column(Integer, default=1)

    # Duration
    blocked_until = Column(DateTime, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class SecurityAlert(Base):
    """Security alerts for suspicious activities."""

    __tablename__ = "security_alerts"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

    # Alert details
    alert_type = Column(String(50), nullable=False)
    severity = Column(String(20), nullable=False)  # low, medium, high, critical
    description = Column(Text, nullable=False)

    # Context
    user_id = Column(String, ForeignKey("users.id"), nullable=True)
    organization_id = Column(String, ForeignKey("organizations.id"), nullable=True)
    ip_address = Column(String(45), nullable=True)
    related_event_id = Column(String, ForeignKey("security_events.id"), nullable=True)

    # Alert status
    is_resolved = Column(Boolean, default=False)
    resolved_at = Column(DateTime, nullable=True)
    resolved_by = Column(String, ForeignKey("users.id"), nullable=True)
    resolution_notes = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", foreign_keys=[user_id])
    resolver = relationship("User", foreign_keys=[resolved_by])
    organization = relationship("Organization")
    related_event = relationship("SecurityEvent")
