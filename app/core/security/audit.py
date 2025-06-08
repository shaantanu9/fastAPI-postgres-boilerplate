"""Security Audit Logging module.
Provides comprehensive security event logging and monitoring capabilities.
"""

import json
import logging
from datetime import datetime, timedelta
from enum import Enum
from typing import Any

from fastapi import Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.models.security import SecurityEvent

settings = get_settings()

# Configure logger
logger = logging.getLogger(__name__)


class AuditEventType(str, Enum):
    """Types of security audit events."""

    LOGIN_SUCCESS = "login_success"
    LOGIN_FAILURE = "login_failure"
    LOGOUT = "logout"
    PASSWORD_CHANGE = "password_change"
    PASSWORD_RESET = "password_reset"
    MFA_ENABLE = "mfa_enable"
    MFA_DISABLE = "mfa_disable"
    API_KEY_CREATE = "api_key_create"
    API_KEY_DELETE = "api_key_delete"
    ROLE_CHANGE = "role_change"
    PERMISSION_CHANGE = "permission_change"
    DATA_ACCESS = "data_access"
    DATA_MODIFICATION = "data_modification"
    SETTINGS_CHANGE = "settings_change"
    SECURITY_ALERT = "security_alert"


class AuditEventCategory(str, Enum):
    """Categories of security audit events."""

    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    DATA_ACCESS = "data_access"
    CONFIGURATION = "configuration"
    SECURITY = "security"


class AuditEventStatus(str, Enum):
    """Status of security audit events."""

    SUCCESS = "success"
    FAILURE = "failure"
    BLOCKED = "blocked"
    WARNING = "warning"


class SecurityAuditLog:
    """Comprehensive security audit logging system.
    Handles logging of security-related events with proper context and persistence.
    """

    def __init__(self, db: AsyncSession) -> None:
        """Initialize audit logger.

        Args:
            db: Database session for persistence

        """
        self.db = db

    async def log_event(
        self,
        event_type: AuditEventType,
        category: AuditEventCategory,
        user_id: str | None,
        request: Request | None = None,
        status: AuditEventStatus = AuditEventStatus.SUCCESS,
        risk_score: int = 0,
        details: dict[str, Any] | None = None,
        related_resources: list[str] | None = None,
    ):
        """Log a security audit event.

        Args:
            event_type: Type of security event
            category: Category of the event
            user_id: ID of the user involved (if any)
            request: FastAPI request object (if available)
            status: Status of the event
            risk_score: Risk score (0-100)
            details: Additional event details
            related_resources: List of related resource IDs

        """
        try:
            # Gather context information
            context = await self._gather_context(request)

            # Prepare event data
            event_data = {
                "timestamp": datetime.utcnow().isoformat(),
                "context": context,
                "details": details or {},
                "related_resources": related_resources or [],
            }

            # Create security event record
            security_event = SecurityEvent(
                user_id=user_id,
                event_type=event_type,
                event_category=category,
                event_data=json.dumps(event_data),
                ip_address=context.get("ip_address"),
                user_agent=context.get("user_agent"),
                risk_score=risk_score,
                status=status,
            )

            # Persist to database
            self.db.add(security_event)
            await self.db.commit()

            # Log high-risk events
            if risk_score >= 75:
                logger.warning(
                    f"High-risk security event detected: {event_type}, "
                    f"Risk Score: {risk_score}, User ID: {user_id}",
                )

            # Return event ID for reference
            return security_event.id

        except Exception as e:
            logger.exception(f"Failed to log security event: {e!s}")
            # Ensure the event is logged even if DB persistence fails
            self._fallback_logging(event_type, category, user_id, context, details)

    async def _gather_context(self, request: Request | None) -> dict[str, Any]:
        """Gather context information from request.

        Args:
            request: FastAPI request object

        Returns:
            Dict containing context information

        """
        context = {
            "timestamp": datetime.utcnow().isoformat(),
            "environment": settings.ENVIRONMENT,
        }

        if request:
            context.update(
                {
                    "ip_address": request.client.host,
                    "user_agent": request.headers.get("user-agent"),
                    "method": request.method,
                    "path": request.url.path,
                    "headers": dict(request.headers),
                    "query_params": dict(request.query_params),
                    "cookies": dict(request.cookies),
                },
            )

            # Add session information if available
            if hasattr(request.state, "session_id"):
                context["session_id"] = request.state.session_id

        return context

    def _fallback_logging(
        self,
        event_type: AuditEventType,
        category: AuditEventCategory,
        user_id: str | None,
        context: dict[str, Any],
        details: dict[str, Any] | None,
    ) -> None:
        """Fallback logging mechanism when database persistence fails.

        Args:
            event_type: Type of security event
            category: Category of the event
            user_id: ID of the user involved
            context: Context information
            details: Additional event details

        """
        log_data = {
            "event_type": event_type,
            "category": category,
            "user_id": user_id,
            "context": context,
            "details": details,
        }

        logger.error(
            "Security event logging fallback", extra={"security_event": log_data},
        )

    async def get_user_events(
        self,
        user_id: str,
        event_types: list[AuditEventType] | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        limit: int = 100,
    ) -> list[SecurityEvent]:
        """Retrieve security events for a specific user.

        Args:
            user_id: User ID to get events for
            event_types: Optional list of event types to filter
            start_time: Optional start time for filtering
            end_time: Optional end time for filtering
            limit: Maximum number of events to return

        Returns:
            List of security events

        """
        query = select(SecurityEvent).where(SecurityEvent.user_id == user_id)

        if event_types:
            query = query.where(SecurityEvent.event_type.in_(event_types))

        if start_time:
            query = query.where(SecurityEvent.created_at >= start_time)

        if end_time:
            query = query.where(SecurityEvent.created_at <= end_time)

        query = query.order_by(SecurityEvent.created_at.desc()).limit(limit)

        result = await self.db.execute(query)
        return result.scalars().all()

    async def get_high_risk_events(
        self, min_risk_score: int = 75, limit: int = 100,
    ) -> list[SecurityEvent]:
        """Retrieve high-risk security events.

        Args:
            min_risk_score: Minimum risk score to consider
            limit: Maximum number of events to return

        Returns:
            List of high-risk security events

        """
        query = (
            select(SecurityEvent)
            .where(SecurityEvent.risk_score >= min_risk_score)
            .order_by(SecurityEvent.created_at.desc())
            .limit(limit)
        )

        result = await self.db.execute(query)
        return result.scalars().all()

    async def calculate_risk_score(
        self,
        event_type: AuditEventType,
        context: dict[str, Any],
        user_history: list[SecurityEvent] | None = None,
    ) -> int:
        """Calculate risk score for an event based on various factors.

        Args:
            event_type: Type of security event
            context: Event context information
            user_history: Optional list of user's previous security events

        Returns:
            Risk score (0-100)

        """
        base_scores = {
            AuditEventType.LOGIN_FAILURE: 60,
            AuditEventType.PASSWORD_RESET: 50,
            AuditEventType.ROLE_CHANGE: 70,
            AuditEventType.SECURITY_ALERT: 80,
        }

        score = base_scores.get(event_type, 30)

        # Adjust score based on context
        if context.get("ip_address"):
            if await self._is_suspicious_ip(context["ip_address"]):
                score += 20

        # Adjust based on user history
        if user_history:
            recent_failures = sum(
                1
                for event in user_history
                if event.event_type == AuditEventType.LOGIN_FAILURE
                and event.created_at >= datetime.utcnow() - timedelta(hours=24)
            )
            score += min(recent_failures * 10, 30)

        return min(score, 100)  # Cap at 100

    async def _is_suspicious_ip(self, ip_address: str) -> bool:
        """Check if an IP address is suspicious.

        Args:
            ip_address: IP address to check

        Returns:
            bool indicating if IP is suspicious

        """
        # Implement IP reputation check logic here
        # This could involve checking against blocklists, reputation services, etc.
        return False  # Placeholder implementation
