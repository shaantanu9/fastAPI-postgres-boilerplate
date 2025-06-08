"""Monitoring Plugin.

This plugin provides comprehensive monitoring and observability features:
- Performance metrics collection
- Request/response monitoring
- Health checks
- Application metrics dashboard
- Real-time alerts
"""

import asyncio
import time
from collections import defaultdict, deque
from datetime import datetime, timedelta
from typing import Any

import psutil
from fastapi import APIRouter, Request
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.plugin_system import PluginBase, PluginMetadata


class MetricsCollector:
    """Collects and stores application metrics."""

    def __init__(self) -> None:
        self.request_count = 0
        self.response_times = deque(maxlen=1000)
        self.status_codes = defaultdict(int)
        self.endpoints = defaultdict(int)
        self.start_time = datetime.utcnow()
        self.errors = []

    def record_request(
        self, method: str, path: str, status_code: int, response_time: float,
    ) -> None:
        """Record a request."""
        self.request_count += 1
        self.response_times.append(response_time)
        self.status_codes[status_code] += 1
        self.endpoints[f"{method} {path}"] += 1

        if status_code >= 400:
            self.errors.append(
                {
                    "timestamp": datetime.utcnow().isoformat(),
                    "method": method,
                    "path": path,
                    "status_code": status_code,
                    "response_time": response_time,
                },
            )

            # Keep only last 100 errors
            if len(self.errors) > 100:
                self.errors.pop(0)

    def get_metrics(self) -> dict:
        """Get current metrics."""
        avg_response_time = (
            sum(self.response_times) / len(self.response_times)
            if self.response_times
            else 0
        )
        uptime = datetime.utcnow() - self.start_time

        # System metrics
        cpu_percent = psutil.cpu_percent()
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage("/")

        return {
            "application": {
                "uptime_seconds": uptime.total_seconds(),
                "total_requests": self.request_count,
                "average_response_time_ms": round(avg_response_time, 2),
                "requests_per_minute": self._calculate_rpm(),
                "status_codes": dict(self.status_codes),
                "top_endpoints": self._get_top_endpoints(),
                "recent_errors": self.errors[-10:],  # Last 10 errors
            },
            "system": {
                "cpu_percent": cpu_percent,
                "memory": {
                    "total": memory.total,
                    "available": memory.available,
                    "percent": memory.percent,
                    "used": memory.used,
                },
                "disk": {
                    "total": disk.total,
                    "used": disk.used,
                    "free": disk.free,
                    "percent": (disk.used / disk.total) * 100,
                },
            },
            "health": {
                "status": self._get_health_status(),
                "checks": self._perform_health_checks(),
            },
        }

    def _calculate_rpm(self) -> float:
        """Calculate requests per minute."""
        uptime_minutes = (datetime.utcnow() - self.start_time).total_seconds() / 60
        return round(self.request_count / max(uptime_minutes, 1), 2)

    def _get_top_endpoints(self) -> list[dict]:
        """Get top 10 most accessed endpoints."""
        sorted_endpoints = sorted(
            self.endpoints.items(), key=lambda x: x[1], reverse=True,
        )
        return [
            {"endpoint": endpoint, "count": count}
            for endpoint, count in sorted_endpoints[:10]
        ]

    def _get_health_status(self) -> str:
        """Determine overall health status."""
        cpu_percent = psutil.cpu_percent()
        memory = psutil.virtual_memory()

        if cpu_percent > 90 or memory.percent > 90:
            return "critical"
        if cpu_percent > 70 or memory.percent > 70:
            return "warning"
        return "healthy"

    def _perform_health_checks(self) -> dict:
        """Perform various health checks."""
        checks = {}

        # CPU check
        cpu_percent = psutil.cpu_percent()
        checks["cpu"] = {
            "status": "ok"
            if cpu_percent < 80
            else "warning"
            if cpu_percent < 95
            else "critical",
            "value": cpu_percent,
            "unit": "percent",
        }

        # Memory check
        memory = psutil.virtual_memory()
        checks["memory"] = {
            "status": "ok"
            if memory.percent < 80
            else "warning"
            if memory.percent < 95
            else "critical",
            "value": memory.percent,
            "unit": "percent",
        }

        # Response time check
        avg_response_time = (
            sum(self.response_times) / len(self.response_times)
            if self.response_times
            else 0
        )
        checks["response_time"] = {
            "status": "ok"
            if avg_response_time < 200
            else "warning"
            if avg_response_time < 500
            else "critical",
            "value": round(avg_response_time, 2),
            "unit": "ms",
        }

        return checks


class MonitoringMiddleware(BaseHTTPMiddleware):
    """Middleware to collect request/response metrics."""

    def __init__(self, app, metrics_collector: MetricsCollector) -> None:
        super().__init__(app)
        self.metrics_collector = metrics_collector

    async def dispatch(self, request: Request, call_next):
        start_time = time.time()

        response = await call_next(request)

        process_time = (time.time() - start_time) * 1000  # Convert to milliseconds

        # Record metrics
        self.metrics_collector.record_request(
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            response_time=process_time,
        )

        return response


class MonitoringPlugin(PluginBase):
    """Comprehensive monitoring plugin for application observability."""

    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="monitoring",
            version="1.2.0",
            description="Comprehensive monitoring with metrics, health checks, and observability",
            author="Your Team",
            min_app_version="1.0.0",
            dependencies=[],
            tags=["monitoring", "metrics", "observability", "health"],
            priority=5,  # High priority - monitoring should load early
        )

    def __init__(self) -> None:
        super().__init__()
        self.router = APIRouter()
        self.metrics_collector = MetricsCollector()
        self.alerts = []
        self.setup_routes()

    def setup_routes(self) -> None:
        """Setup monitoring routes."""

        @self.router.get("/monitoring/metrics", tags=["Monitoring"])
        async def get_metrics():
            """Get comprehensive application and system metrics."""
            return self.metrics_collector.get_metrics()

        @self.router.get("/monitoring/health", tags=["Monitoring"])
        async def health_check():
            """Detailed health check endpoint."""
            metrics = self.metrics_collector.get_metrics()
            health_data = metrics["health"]

            # Emit health check event
            self.emit_event("health_check_performed", status=health_data["status"])

            return {
                "status": health_data["status"],
                "timestamp": datetime.utcnow().isoformat(),
                "checks": health_data["checks"],
                "uptime_seconds": metrics["application"]["uptime_seconds"],
                "version": "1.0.0",
            }

        @self.router.get("/monitoring/alerts", tags=["Monitoring"])
        async def get_alerts():
            """Get recent alerts and notifications."""
            return {
                "alerts": self.alerts[-50:],  # Last 50 alerts
                "count": len(self.alerts),
            }

        @self.router.get("/monitoring/performance", tags=["Monitoring"])
        async def get_performance():
            """Get detailed performance metrics."""
            metrics = self.metrics_collector.get_metrics()

            return {
                "response_times": {
                    "average": metrics["application"]["average_response_time_ms"],
                    "recent_samples": list(self.metrics_collector.response_times)[
                        -20:
                    ],  # Last 20 samples
                },
                "throughput": {
                    "requests_per_minute": metrics["application"][
                        "requests_per_minute"
                    ],
                    "total_requests": metrics["application"]["total_requests"],
                },
                "errors": {
                    "recent_errors": metrics["application"]["recent_errors"],
                    "error_rate": self._calculate_error_rate(),
                },
            }

        @self.router.get("/monitoring/dashboard", tags=["Monitoring"])
        async def monitoring_dashboard():
            """Get dashboard data for monitoring UI."""
            metrics = self.metrics_collector.get_metrics()

            return {
                "overview": {
                    "status": metrics["health"]["status"],
                    "uptime": metrics["application"]["uptime_seconds"],
                    "total_requests": metrics["application"]["total_requests"],
                    "avg_response_time": metrics["application"][
                        "average_response_time_ms"
                    ],
                },
                "system": metrics["system"],
                "recent_activity": {
                    "top_endpoints": metrics["application"]["top_endpoints"],
                    "status_distribution": metrics["application"]["status_codes"],
                    "recent_errors": metrics["application"]["recent_errors"],
                },
                "alerts": self.alerts[-10:],  # Last 10 alerts
            }

    async def initialize(self, app, context) -> None:
        """Initialize the monitoring plugin."""
        await super().initialize(app, context)

        # Register monitoring service
        context.register_service("monitoring", self)
        context.register_service("metrics_collector", self.metrics_collector)

        # Subscribe to events
        self.subscribe_event("application_startup", self.on_startup)
        self.subscribe_event("user_login", self.on_user_login)
        self.subscribe_event("user_logout", self.on_user_logout)

        # Start monitoring tasks
        asyncio.create_task(self._periodic_health_check())
        asyncio.create_task(self._alert_monitor())

        # Status will be set by plugin manager - don't override here

    async def startup(self) -> None:
        """Plugin startup tasks."""
        await super().startup()

        # Emit monitoring ready event
        self.emit_event(
            "monitoring_ready", features=["metrics", "health_checks", "alerts"],
        )

        self._add_alert("info", "Monitoring plugin started successfully")

    async def shutdown(self) -> None:
        """Plugin shutdown tasks."""
        await super().shutdown()

        # Emit monitoring shutdown event
        self.emit_event("monitoring_shutdown")

        self._add_alert("info", "Monitoring plugin shutting down")

    def get_routes(self) -> list[Any]:
        """Return monitoring routes."""
        return [self.router]

    def get_middleware(self) -> list[Any]:
        """Return monitoring middleware."""
        # Temporarily disable middleware to fix initialization issues
        # TODO: Fix middleware proper initialization
        return []

    async def _periodic_health_check(self) -> None:
        """Perform periodic health checks and generate alerts."""
        while True:
            try:
                await asyncio.sleep(60)  # Check every minute

                metrics = self.metrics_collector.get_metrics()
                health_status = metrics["health"]["status"]

                if health_status == "critical":
                    self._add_alert("critical", "System health is critical")
                elif health_status == "warning":
                    self._add_alert("warning", "System health degraded")

                # Check for high error rate
                error_rate = self._calculate_error_rate()
                if error_rate > 10:  # More than 10% error rate
                    self._add_alert(
                        "warning", f"High error rate detected: {error_rate:.1f}%",
                    )

                # Emit periodic health check event
                self.emit_event(
                    "periodic_health_check", status=health_status, error_rate=error_rate,
                )

            except Exception:
                pass

    async def _alert_monitor(self) -> None:
        """Monitor for conditions that should trigger alerts."""
        while True:
            try:
                await asyncio.sleep(30)  # Check every 30 seconds

                # Check CPU usage
                cpu_percent = psutil.cpu_percent()
                if cpu_percent > 90:
                    self._add_alert("critical", f"High CPU usage: {cpu_percent:.1f}%")

                # Check memory usage
                memory = psutil.virtual_memory()
                if memory.percent > 90:
                    self._add_alert(
                        "critical", f"High memory usage: {memory.percent:.1f}%",
                    )

                # Check recent errors
                recent_errors = len(
                    [
                        e
                        for e in self.metrics_collector.errors
                        if datetime.fromisoformat(e["timestamp"])
                        > datetime.utcnow() - timedelta(minutes=5)
                    ],
                )
                if recent_errors > 10:
                    self._add_alert(
                        "warning",
                        f"High error count in last 5 minutes: {recent_errors}",
                    )

            except Exception:
                pass

    def _add_alert(self, level: str, message: str) -> None:
        """Add an alert."""
        alert = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": level,
            "message": message,
            "plugin": "monitoring",
        }

        self.alerts.append(alert)

        # Keep only last 1000 alerts
        if len(self.alerts) > 1000:
            self.alerts.pop(0)

        # Emit alert event
        self.emit_event("alert_generated", alert=alert)


    def _calculate_error_rate(self) -> float:
        """Calculate current error rate percentage."""
        if not self.metrics_collector.status_codes:
            return 0.0

        error_count = sum(
            count
            for status, count in self.metrics_collector.status_codes.items()
            if status >= 400
        )
        total_count = sum(self.metrics_collector.status_codes.values())

        return (error_count / total_count) * 100 if total_count > 0 else 0.0

    async def on_startup(self, **kwargs) -> None:
        """Handle application startup event."""
        self._add_alert("info", "Application started - monitoring active")

    async def on_user_login(self, **kwargs) -> None:
        """Handle user login event."""
        kwargs.get("username", "unknown")
        kwargs.get("plugin", "default")

    async def on_user_logout(self, **kwargs) -> None:
        """Handle user logout event."""
        kwargs.get("plugin", "default")
