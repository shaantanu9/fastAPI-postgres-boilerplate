"""Centralized Error Aggregation System.

Builds on existing structured logging to provide centralized error tracking,
grouping, and dashboard capabilities without external dependencies.
"""

import asyncio
import contextlib
import hashlib
import logging
import time
from collections import defaultdict, deque
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from typing import Any

from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class ErrorEvent:
    """Represents a single error event."""

    id: str
    fingerprint: str
    timestamp: datetime
    level: str
    message: str
    exception_type: str
    exception_message: str
    traceback: str
    correlation_id: str | None
    user_id: str | None
    request_path: str | None
    request_method: str | None
    client_ip: str | None
    user_agent: str | None
    context: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        data = asdict(self)
        data["timestamp"] = self.timestamp.isoformat()
        return data


@dataclass
class ErrorGroup:
    """Represents a group of similar errors."""

    fingerprint: str
    first_seen: datetime
    last_seen: datetime
    count: int
    level: str
    message: str
    exception_type: str
    sample_event: ErrorEvent
    affected_users: set
    request_paths: set

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "fingerprint": self.fingerprint,
            "first_seen": self.first_seen.isoformat(),
            "last_seen": self.last_seen.isoformat(),
            "count": self.count,
            "level": self.level,
            "message": self.message,
            "exception_type": self.exception_type,
            "sample_event": self.sample_event.to_dict(),
            "affected_users": list(self.affected_users),
            "affected_paths": list(self.request_paths),
            "rate_per_hour": self._calculate_rate(),
        }

    def _calculate_rate(self) -> float:
        """Calculate error rate per hour."""
        time_diff = (self.last_seen - self.first_seen).total_seconds() / 3600
        time_diff = max(time_diff, 1)  # Minimum 1 hour for calculation
        return round(self.count / time_diff, 2)


class ErrorAggregator:
    """Centralized error aggregation and analysis."""

    def __init__(self, max_events: int = 10000, retention_days: int = 30) -> None:
        self.max_events = max_events
        self.retention_days = retention_days
        self.events: deque = deque(maxlen=max_events)
        self.groups: dict[str, ErrorGroup] = {}
        self.stats = {
            "total_events": 0,
            "events_by_level": defaultdict(int),
            "events_by_hour": defaultdict(int),
            "top_errors": [],
            "alert_thresholds": {
                "critical_errors_per_minute": 10,
                "error_rate_increase": 2.0,  # 200% increase
                "new_error_types_per_hour": 5,
            },
        }
        self.alerts: deque = deque(maxlen=1000)
        self._cleanup_task = None

    async def start_cleanup_task(self) -> None:
        """Start the periodic cleanup task (call this when event loop is running)."""
        if self._cleanup_task is None:
            self._cleanup_task = asyncio.create_task(self._periodic_cleanup())
            logger.info("Error aggregator cleanup task started")

    async def stop_cleanup_task(self) -> None:
        """Stop the periodic cleanup task."""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._cleanup_task
            self._cleanup_task = None
            logger.info("Error aggregator cleanup task stopped")

    def add_error(
        self,
        level: str,
        message: str,
        exception_type: str = "",
        exception_message: str = "",
        traceback: str = "",
        correlation_id: str | None = None,
        user_id: str | None = None,
        request_path: str | None = None,
        request_method: str | None = None,
        client_ip: str | None = None,
        user_agent: str | None = None,
        context: dict[str, Any] | None = None,
    ) -> str:
        """Add a new error event."""
        # Create fingerprint for grouping similar errors
        fingerprint = self._create_fingerprint(
            exception_type, message, request_path, traceback,
        )

        # Create error event
        event = ErrorEvent(
            id=self._generate_event_id(),
            fingerprint=fingerprint,
            timestamp=datetime.utcnow(),
            level=level,
            message=message,
            exception_type=exception_type,
            exception_message=exception_message,
            traceback=traceback,
            correlation_id=correlation_id,
            user_id=user_id,
            request_path=request_path,
            request_method=request_method,
            client_ip=client_ip,
            user_agent=user_agent,
            context=context or {},
        )

        # Add to events
        self.events.append(event)

        # Update or create error group
        self._update_error_group(event)

        # Update statistics
        self._update_stats(event)

        # Check for alerts
        self._check_alerts(event)

        logger.info(f"Error event added: {event.id} (group: {fingerprint})")
        return event.id

    def _create_fingerprint(
        self, exception_type: str, message: str, request_path: str, traceback: str,
    ) -> str:
        """Create a fingerprint for grouping similar errors."""
        # Normalize traceback by removing line numbers and file paths
        normalized_traceback = self._normalize_traceback(traceback)

        # Create fingerprint from key components
        fingerprint_data = (
            f"{exception_type}:{message}:{request_path}:{normalized_traceback}"
        )
        return hashlib.md5(fingerprint_data.encode()).hexdigest()[:16]

    def _normalize_traceback(self, traceback: str) -> str:
        """Normalize traceback for consistent grouping."""
        if not traceback:
            return ""

        lines = traceback.split("\n")
        normalized_lines = []

        for line in lines:
            # Remove file paths and line numbers
            if 'File "' in line and ", line " in line:
                # Extract just the function name
                if "in " in line:
                    func_part = line.split("in ")[-1]
                    normalized_lines.append(f"in {func_part}")
            elif line.strip() and not line.startswith("  "):
                # Keep exception messages but normalize them
                normalized_lines.append(line.strip())

        return "\n".join(normalized_lines[:5])  # Keep first 5 meaningful lines

    def _update_error_group(self, event: ErrorEvent) -> None:
        """Update or create error group."""
        fingerprint = event.fingerprint

        if fingerprint in self.groups:
            group = self.groups[fingerprint]
            group.count += 1
            group.last_seen = event.timestamp
            group.affected_users.add(event.user_id or "anonymous")
            if event.request_path:
                group.request_paths.add(event.request_path)
        else:
            self.groups[fingerprint] = ErrorGroup(
                fingerprint=fingerprint,
                first_seen=event.timestamp,
                last_seen=event.timestamp,
                count=1,
                level=event.level,
                message=event.message,
                exception_type=event.exception_type,
                sample_event=event,
                affected_users={event.user_id or "anonymous"},
                request_paths={event.request_path} if event.request_path else set(),
            )

    def _update_stats(self, event: ErrorEvent) -> None:
        """Update statistics."""
        self.stats["total_events"] += 1
        self.stats["events_by_level"][event.level] += 1

        # Hour-based statistics
        hour_key = event.timestamp.strftime("%Y-%m-%d %H:00")
        self.stats["events_by_hour"][hour_key] += 1

        # Update top errors
        self._update_top_errors()

    def _update_top_errors(self) -> None:
        """Update top errors list."""
        sorted_groups = sorted(
            self.groups.values(), key=lambda g: g.count, reverse=True,
        )
        self.stats["top_errors"] = [
            {
                "fingerprint": group.fingerprint,
                "count": group.count,
                "message": group.message,
                "exception_type": group.exception_type,
                "rate_per_hour": group._calculate_rate(),
            }
            for group in sorted_groups[:10]
        ]

    def _check_alerts(self, event: ErrorEvent) -> None:
        """Check if event should trigger alerts."""
        now = datetime.utcnow()

        # Check critical error rate
        if event.level in ["CRITICAL", "ERROR"]:
            recent_errors = [
                e
                for e in self.events
                if e.level in ["CRITICAL", "ERROR"]
                and (now - e.timestamp).total_seconds() < 60
            ]

            if (
                len(recent_errors)
                > self.stats["alert_thresholds"]["critical_errors_per_minute"]
            ):
                self._create_alert(
                    "high_error_rate",
                    f"High error rate: {len(recent_errors)} errors in last minute",
                    "critical",
                    {"error_count": len(recent_errors)},
                )

        # Check for new error types
        group = self.groups[event.fingerprint]
        if group.count == 1:  # First occurrence of this error type
            recent_new_errors = [
                g
                for g in self.groups.values()
                if g.count == 1 and (now - g.first_seen).total_seconds() < 3600
            ]

            if (
                len(recent_new_errors)
                > self.stats["alert_thresholds"]["new_error_types_per_hour"]
            ):
                self._create_alert(
                    "new_error_spike",
                    f"Spike in new error types: {len(recent_new_errors)} in last hour",
                    "warning",
                    {"new_error_count": len(recent_new_errors)},
                )

    def _create_alert(
        self, alert_type: str, message: str, severity: str, context: dict,
    ) -> None:
        """Create an alert."""
        alert = {
            "id": self._generate_event_id(),
            "type": alert_type,
            "message": message,
            "severity": severity,
            "timestamp": datetime.utcnow().isoformat(),
            "context": context,
        }

        self.alerts.append(alert)
        logger.warning(f"Alert created: {alert_type} - {message}")

    def _generate_event_id(self) -> str:
        """Generate unique event ID."""
        return f"err_{int(time.time() * 1000)}_{hash(time.time()) % 10000}"

    async def _periodic_cleanup(self) -> None:
        """Periodic cleanup of old events."""
        while True:
            try:
                await asyncio.sleep(3600)  # Run every hour
                await self._cleanup_old_events()
            except Exception as e:
                logger.exception(f"Error in periodic cleanup: {e}")

    async def _cleanup_old_events(self) -> None:
        """Clean up old events and groups."""
        cutoff_time = datetime.utcnow() - timedelta(days=self.retention_days)

        # Clean up old events (already handled by deque maxlen)

        # Clean up old groups
        old_groups = [
            fingerprint
            for fingerprint, group in self.groups.items()
            if group.last_seen < cutoff_time
        ]

        for fingerprint in old_groups:
            del self.groups[fingerprint]

        logger.info(f"Cleaned up {len(old_groups)} old error groups")

    def get_dashboard_data(self, hours: int = 24) -> dict[str, Any]:
        """Get data for error dashboard."""
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)

        recent_events = [e for e in self.events if e.timestamp > cutoff_time]

        recent_groups = {
            fp: group
            for fp, group in self.groups.items()
            if group.last_seen > cutoff_time
        }

        return {
            "summary": {
                "total_events": len(recent_events),
                "total_groups": len(recent_groups),
                "events_by_level": self._count_by_level(recent_events),
                "top_error_groups": self._get_top_groups(recent_groups, 10),
                "error_timeline": self._get_error_timeline(recent_events, hours),
                "affected_users": len(
                    {e.user_id for e in recent_events if e.user_id},
                ),
                "affected_paths": len(
                    {e.request_path for e in recent_events if e.request_path},
                ),
            },
            "recent_alerts": list(self.alerts)[-20:],  # Last 20 alerts
            "stats": self.stats,
        }

    def _count_by_level(self, events: list[ErrorEvent]) -> dict[str, int]:
        """Count events by level."""
        counts = defaultdict(int)
        for event in events:
            counts[event.level] += 1
        return dict(counts)

    def _get_top_groups(self, groups: dict[str, ErrorGroup], limit: int) -> list[dict]:
        """Get top error groups."""
        sorted_groups = sorted(groups.values(), key=lambda g: g.count, reverse=True)
        return [group.to_dict() for group in sorted_groups[:limit]]

    def _get_error_timeline(self, events: list[ErrorEvent], hours: int) -> list[dict]:
        """Get error timeline data."""
        timeline = defaultdict(lambda: defaultdict(int))

        for event in events:
            hour_key = event.timestamp.strftime("%Y-%m-%d %H:00")
            timeline[hour_key][event.level] += 1

        # Fill in missing hours
        now = datetime.utcnow()
        result = []

        for i in range(hours):
            hour = now - timedelta(hours=i)
            hour_key = hour.strftime("%Y-%m-%d %H:00")

            data = {
                "timestamp": hour_key,
                "total": sum(timeline[hour_key].values()),
                **dict(timeline[hour_key]),
            }
            result.append(data)

        return list(reversed(result))

    def get_error_details(self, fingerprint: str) -> dict | None:
        """Get details for specific error group."""
        if fingerprint not in self.groups:
            return None

        group = self.groups[fingerprint]

        # Get recent events for this group
        recent_events = [
            e.to_dict() for e in self.events if e.fingerprint == fingerprint
        ][-50:]  # Last 50 events

        return {
            "group": group.to_dict(),
            "recent_events": recent_events,
            "occurrence_timeline": self._get_occurrence_timeline(fingerprint),
        }

    def _get_occurrence_timeline(self, fingerprint: str) -> list[dict]:
        """Get occurrence timeline for specific error."""
        events = [e for e in self.events if e.fingerprint == fingerprint]
        timeline = defaultdict(int)

        for event in events:
            hour_key = event.timestamp.strftime("%Y-%m-%d %H:00")
            timeline[hour_key] += 1

        return [
            {"timestamp": timestamp, "count": count}
            for timestamp, count in sorted(timeline.items())
        ]


# Global error aggregator instance
error_aggregator = ErrorAggregator()


# Integration with existing logging system
class ErrorAggregatorHandler(logging.Handler):
    """Custom logging handler to feed errors to aggregator."""

    def emit(self, record) -> None:
        if record.levelno >= logging.ERROR:
            # Extract error information
            exception_type = ""
            exception_message = ""
            traceback_str = ""

            if record.exc_info:
                exception_type = (
                    record.exc_info[0].__name__ if record.exc_info[0] else ""
                )
                exception_message = (
                    str(record.exc_info[1]) if record.exc_info[1] else ""
                )
                traceback_str = self.format(record) if record.exc_info else ""

            # Extract context from record
            context = {}
            correlation_id = getattr(record, "correlation_id", None)
            user_id = getattr(record, "user_id", None)

            # Add error to aggregator
            error_aggregator.add_error(
                level=record.levelname,
                message=record.getMessage(),
                exception_type=exception_type,
                exception_message=exception_message,
                traceback=traceback_str,
                correlation_id=correlation_id,
                user_id=user_id,
                context=context,
            )


def setup_error_aggregation() -> None:
    """Setup error aggregation with existing logging system."""
    handler = ErrorAggregatorHandler()
    handler.setLevel(logging.ERROR)

    # Add to root logger
    root_logger = logging.getLogger()
    root_logger.addHandler(handler)

    logger.info("Error aggregation system initialized")


async def start_error_aggregation() -> None:
    """Start error aggregation background tasks (call during app startup)."""
    await error_aggregator.start_cleanup_task()
    logger.info("Error aggregation background tasks started")


async def stop_error_aggregation() -> None:
    """Stop error aggregation background tasks (call during app shutdown)."""
    await error_aggregator.stop_cleanup_task()
    logger.info("Error aggregation background tasks stopped")
