"""Prometheus Metrics System for FastAPI
- Request/response metrics
- Database performance metrics
- Business metrics
- Custom metrics support.
"""

import time
from threading import Lock

from fastapi import Response
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    REGISTRY,
    CollectorRegistry,
    Counter,
    Gauge,
    Histogram,
    Info,
    generate_latest,
)

from app.core.logging import get_logger

logger = get_logger(__name__)


class MetricsCollector:
    """Centralized metrics collection for the application."""

    def __init__(self, registry: CollectorRegistry = REGISTRY) -> None:
        self.registry = registry
        self._lock = Lock()
        self._initialize_metrics()

    def _initialize_metrics(self) -> None:
        """Initialize all Prometheus metrics."""
        # Application info
        self.app_info = Info(
            "app_info", "Application information", registry=self.registry,
        )

        # Request metrics
        self.request_duration = Histogram(
            "http_request_duration_seconds",
            "HTTP request duration in seconds",
            ["method", "path", "status_code"],
            registry=self.registry,
            buckets=(0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
        )

        self.request_count = Counter(
            "http_requests_total",
            "Total HTTP requests",
            ["method", "path", "status_code"],
            registry=self.registry,
        )

        self.request_size = Histogram(
            "http_request_size_bytes",
            "HTTP request size in bytes",
            ["method", "path"],
            registry=self.registry,
        )

        self.response_size = Histogram(
            "http_response_size_bytes",
            "HTTP response size in bytes",
            ["method", "path", "status_code"],
            registry=self.registry,
        )

        # Authentication metrics
        self.auth_attempts = Counter(
            "auth_attempts_total",
            "Total authentication attempts",
            ["type", "status"],  # type: login/refresh, status: success/failure
            registry=self.registry,
        )

        self.active_sessions = Gauge(
            "active_sessions_total",
            "Current active user sessions",
            registry=self.registry,
        )

        # Database metrics
        self.db_query_duration = Histogram(
            "db_query_duration_seconds",
            "Database query duration in seconds",
            ["operation", "table"],
            registry=self.registry,
            buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.0),
        )

        self.db_query_count = Counter(
            "db_queries_total",
            "Total database queries",
            ["operation", "table", "status"],
            registry=self.registry,
        )

        self.db_connection_pool = Gauge(
            "db_connection_pool_size",
            "Database connection pool size",
            ["state"],  # state: active/idle/total
            registry=self.registry,
        )

        # Business metrics
        self.user_registrations = Counter(
            "user_registrations_total",
            "Total user registrations",
            registry=self.registry,
        )

        self.api_operations = Counter(
            "api_operations_total",
            "Total API operations by type",
            ["operation_type", "resource", "status"],
            registry=self.registry,
        )

        # System metrics
        self.memory_usage = Gauge(
            "system_memory_usage_bytes",
            "System memory usage in bytes",
            ["type"],  # type: used/available/total
            registry=self.registry,
        )

        self.cpu_usage = Gauge(
            "system_cpu_usage_percent",
            "System CPU usage percentage",
            registry=self.registry,
        )

        self.disk_usage = Gauge(
            "system_disk_usage_bytes",
            "System disk usage in bytes",
            ["type"],  # type: used/free/total
            registry=self.registry,
        )

        # Error metrics
        self.error_count = Counter(
            "errors_total",
            "Total errors by type",
            ["error_type", "source"],
            registry=self.registry,
        )

        # Background task metrics
        self.task_duration = Histogram(
            "background_task_duration_seconds",
            "Background task duration in seconds",
            ["task_name", "status"],
            registry=self.registry,
        )

        self.task_queue_size = Gauge(
            "background_task_queue_size",
            "Background task queue size",
            ["queue_name"],
            registry=self.registry,
        )

        # Cache metrics
        self.cache_operations = Counter(
            "cache_operations_total",
            "Total cache operations",
            [
                "operation",
                "status",
            ],  # operation: get/set/delete, status: hit/miss/success/error
            registry=self.registry,
        )

        logger.info("Prometheus metrics initialized")

    def set_app_info(self, version: str, environment: str, build_time: str) -> None:
        """Set application information."""
        self.app_info.info(
            {"version": version, "environment": environment, "build_time": build_time},
        )

    # Request metrics methods
    def record_request(
        self,
        method: str,
        path: str,
        status_code: int,
        duration: float,
        request_size: int = 0,
        response_size: int = 0,
    ) -> None:
        """Record HTTP request metrics."""
        # Normalize path to avoid high cardinality
        normalized_path = self._normalize_path(path)

        with self._lock:
            self.request_duration.labels(
                method=method, path=normalized_path, status_code=status_code,
            ).observe(duration)

            self.request_count.labels(
                method=method, path=normalized_path, status_code=status_code,
            ).inc()

            if request_size > 0:
                self.request_size.labels(method=method, path=normalized_path).observe(
                    request_size,
                )

            if response_size > 0:
                self.response_size.labels(
                    method=method, path=normalized_path, status_code=status_code,
                ).observe(response_size)

    def record_auth_attempt(self, auth_type: str, success: bool) -> None:
        """Record authentication attempt."""
        status = "success" if success else "failure"
        self.auth_attempts.labels(type=auth_type, status=status).inc()

    def update_active_sessions(self, count: int) -> None:
        """Update active sessions count."""
        self.active_sessions.set(count)

    # Database metrics methods
    def record_db_query(
        self, operation: str, table: str, duration: float, success: bool = True,
    ) -> None:
        """Record database query metrics."""
        status = "success" if success else "error"

        with self._lock:
            self.db_query_duration.labels(operation=operation, table=table).observe(
                duration,
            )

            self.db_query_count.labels(
                operation=operation, table=table, status=status,
            ).inc()

    def update_db_pool_stats(self, active: int, idle: int, total: int) -> None:
        """Update database connection pool statistics."""
        self.db_connection_pool.labels(state="active").set(active)
        self.db_connection_pool.labels(state="idle").set(idle)
        self.db_connection_pool.labels(state="total").set(total)

    # Business metrics methods
    def record_user_registration(self) -> None:
        """Record user registration."""
        self.user_registrations.inc()

    def record_api_operation(
        self, operation_type: str, resource: str, success: bool = True,
    ) -> None:
        """Record API operation."""
        status = "success" if success else "error"
        self.api_operations.labels(
            operation_type=operation_type, resource=resource, status=status,
        ).inc()

    # System metrics methods
    def update_system_metrics(
        self,
        memory_stats: dict[str, int],
        cpu_percent: float,
        disk_stats: dict[str, int],
    ) -> None:
        """Update system resource metrics."""
        # Memory metrics
        for mem_type, value in memory_stats.items():
            self.memory_usage.labels(type=mem_type).set(value)

        # CPU metrics
        self.cpu_usage.set(cpu_percent)

        # Disk metrics
        for disk_type, value in disk_stats.items():
            self.disk_usage.labels(type=disk_type).set(value)

    def record_error(self, error_type: str, source: str) -> None:
        """Record error occurrence."""
        self.error_count.labels(error_type=error_type, source=source).inc()

    # Background task metrics
    def record_task_execution(
        self, task_name: str, duration: float, success: bool = True,
    ) -> None:
        """Record background task execution."""
        status = "success" if success else "error"
        self.task_duration.labels(task_name=task_name, status=status).observe(duration)

    def update_task_queue_size(self, queue_name: str, size: int) -> None:
        """Update task queue size."""
        self.task_queue_size.labels(queue_name=queue_name).set(size)

    # Cache metrics
    def record_cache_operation(
        self, operation: str, hit: bool | None = None, success: bool = True,
    ) -> None:
        """Record cache operation."""
        if operation == "get":
            status = "hit" if hit else "miss"
        else:
            status = "success" if success else "error"

        self.cache_operations.labels(operation=operation, status=status).inc()

    def _normalize_path(self, path: str) -> str:
        """Normalize path to reduce cardinality."""
        # Replace IDs with placeholders
        import re

        # Replace UUIDs
        path = re.sub(
            r"/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
            "/{uuid}",
            path,
            flags=re.IGNORECASE,
        )

        # Replace numeric IDs
        return re.sub(r"/\d+(?=/|$)", "/{id}", path)


    def get_metrics(self) -> str:
        """Get Prometheus metrics in text format."""
        return generate_latest(self.registry).decode("utf-8")


# Global metrics instance
metrics = MetricsCollector()


# FastAPI endpoint for metrics
async def get_prometheus_metrics():
    """FastAPI endpoint to expose Prometheus metrics."""
    metrics_data = metrics.get_metrics()
    return Response(content=metrics_data, media_type=CONTENT_TYPE_LATEST)


# Context manager for timing operations
class MetricsTimer:
    """Context manager for timing operations with metrics."""

    def __init__(self, metric_func, *args, **kwargs) -> None:
        self.metric_func = metric_func
        self.args = args
        self.kwargs = kwargs
        self.start_time = None

    def __enter__(self):
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = time.time() - self.start_time
        success = exc_type is None
        self.metric_func(*self.args, duration=duration, success=success, **self.kwargs)


# Decorator for automatic metrics collection
def track_time(metric_name: str, labels: dict[str, str] | None = None):
    """Decorator to automatically track function execution time."""

    def decorator(func):
        def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                return func(*args, **kwargs)
            except Exception:
                raise
            finally:
                duration = time.time() - start_time
                # This would need to be connected to specific metrics
                # Implementation depends on the specific metric being tracked
                logger.info(f"Function {func.__name__} took {duration:.3f}s")

        return wrapper

    return decorator
