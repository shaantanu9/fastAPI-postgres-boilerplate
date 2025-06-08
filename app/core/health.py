# app/core/health.py

import asyncio
import time
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any

import psutil
import redis
from sqlalchemy import text

from app.core.config import get_settings
from app.core.logging import get_logger
from app.db.session import get_db

logger = get_logger(__name__)


class HealthStatus(Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


@dataclass
class HealthCheck:
    name: str
    status: HealthStatus
    message: str
    duration_ms: float
    details: dict[str, Any] = None
    timestamp: datetime = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()


class HealthChecker:
    """Comprehensive health check system."""

    def __init__(self) -> None:
        self.settings = get_settings()
        self.checks: dict[str, callable] = {
            "database": self._check_database,
            "system": self._check_system_resources,
            "disk": self._check_disk_space,
            "memory": self._check_memory_usage,
        }
        self._external_checks: dict[str, callable] = {}

    def register_check(self, name: str, check_function: callable) -> None:
        """Register a custom health check."""
        self._external_checks[name] = check_function
        logger.info(f"Registered health check: {name}")

    async def _check_database(self) -> HealthCheck:
        """Check database connectivity and performance."""
        start_time = time.time()

        try:
            async with get_db() as db:
                # Simple connectivity test
                result = await db.execute(text("SELECT 1"))
                await result.fetchone()

                # Check response time
                query_start = time.time()
                await db.execute(text("SELECT COUNT(*) FROM pg_stat_activity"))
                query_duration = (time.time() - query_start) * 1000

                duration_ms = (time.time() - start_time) * 1000

                if duration_ms > 1000:  # > 1 second
                    return HealthCheck(
                        name="database",
                        status=HealthStatus.DEGRADED,
                        message=f"Database responding slowly ({duration_ms:.2f}ms)",
                        duration_ms=duration_ms,
                        details={"query_duration_ms": query_duration},
                    )

                return HealthCheck(
                    name="database",
                    status=HealthStatus.HEALTHY,
                    message="Database connection successful",
                    duration_ms=duration_ms,
                    details={"query_duration_ms": query_duration},
                )

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            logger.exception(f"Database health check failed: {e}")
            return HealthCheck(
                name="database",
                status=HealthStatus.UNHEALTHY,
                message=f"Database connection failed: {e!s}",
                duration_ms=duration_ms,
                details={"error": str(e)},
            )

    async def _check_system_resources(self) -> HealthCheck:
        """Check system CPU and load."""
        start_time = time.time()

        try:
            cpu_percent = psutil.cpu_percent(interval=0.1)
            load_avg = psutil.getloadavg()
            cpu_count = psutil.cpu_count()

            duration_ms = (time.time() - start_time) * 1000

            details = {
                "cpu_percent": cpu_percent,
                "load_1min": load_avg[0],
                "load_5min": load_avg[1],
                "load_15min": load_avg[2],
                "cpu_count": cpu_count,
                "load_per_cpu": load_avg[0] / cpu_count,
            }

            # Determine status based on load
            if cpu_percent > 90 or load_avg[0] > cpu_count * 2:
                status = HealthStatus.UNHEALTHY
                message = (
                    f"High system load: CPU {cpu_percent:.1f}%, Load {load_avg[0]:.2f}"
                )
            elif cpu_percent > 70 or load_avg[0] > cpu_count * 1.5:
                status = HealthStatus.DEGRADED
                message = f"Moderate system load: CPU {cpu_percent:.1f}%, Load {load_avg[0]:.2f}"
            else:
                status = HealthStatus.HEALTHY
                message = f"System load normal: CPU {cpu_percent:.1f}%, Load {load_avg[0]:.2f}"

            return HealthCheck(
                name="system",
                status=status,
                message=message,
                duration_ms=duration_ms,
                details=details,
            )

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            return HealthCheck(
                name="system",
                status=HealthStatus.UNHEALTHY,
                message=f"System check failed: {e!s}",
                duration_ms=duration_ms,
                details={"error": str(e)},
            )

    async def _check_disk_space(self) -> HealthCheck:
        """Check available disk space."""
        start_time = time.time()

        try:
            disk_usage = psutil.disk_usage("/")

            total_gb = disk_usage.total / (1024**3)
            used_gb = disk_usage.used / (1024**3)
            free_gb = disk_usage.free / (1024**3)
            used_percent = (disk_usage.used / disk_usage.total) * 100

            duration_ms = (time.time() - start_time) * 1000

            details = {
                "total_gb": round(total_gb, 2),
                "used_gb": round(used_gb, 2),
                "free_gb": round(free_gb, 2),
                "used_percent": round(used_percent, 2),
            }

            if used_percent > 90:
                status = HealthStatus.UNHEALTHY
                message = f"Critical disk usage: {used_percent:.1f}% used"
            elif used_percent > 80:
                status = HealthStatus.DEGRADED
                message = f"High disk usage: {used_percent:.1f}% used"
            else:
                status = HealthStatus.HEALTHY
                message = f"Disk usage normal: {used_percent:.1f}% used"

            return HealthCheck(
                name="disk",
                status=status,
                message=message,
                duration_ms=duration_ms,
                details=details,
            )

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            return HealthCheck(
                name="disk",
                status=HealthStatus.UNHEALTHY,
                message=f"Disk check failed: {e!s}",
                duration_ms=duration_ms,
                details={"error": str(e)},
            )

    async def _check_memory_usage(self) -> HealthCheck:
        """Check memory usage."""
        start_time = time.time()

        try:
            memory = psutil.virtual_memory()
            swap = psutil.swap_memory()

            duration_ms = (time.time() - start_time) * 1000

            details = {
                "total_gb": round(memory.total / (1024**3), 2),
                "available_gb": round(memory.available / (1024**3), 2),
                "used_percent": memory.percent,
                "swap_total_gb": round(swap.total / (1024**3), 2),
                "swap_used_percent": swap.percent if swap.total > 0 else 0,
            }

            if memory.percent > 90:
                status = HealthStatus.UNHEALTHY
                message = f"Critical memory usage: {memory.percent:.1f}%"
            elif memory.percent > 80:
                status = HealthStatus.DEGRADED
                message = f"High memory usage: {memory.percent:.1f}%"
            else:
                status = HealthStatus.HEALTHY
                message = f"Memory usage normal: {memory.percent:.1f}%"

            return HealthCheck(
                name="memory",
                status=status,
                message=message,
                duration_ms=duration_ms,
                details=details,
            )

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            return HealthCheck(
                name="memory",
                status=HealthStatus.UNHEALTHY,
                message=f"Memory check failed: {e!s}",
                duration_ms=duration_ms,
                details={"error": str(e)},
            )

    async def run_all_checks(self) -> dict[str, Any]:
        """Run all health checks and return comprehensive report."""
        start_time = time.time()
        results = []

        # Run built-in checks
        all_checks = {**self.checks, **self._external_checks}

        for check_name, check_func in all_checks.items():
            try:
                result = await check_func()
                results.append(result)
            except Exception as e:
                logger.exception(f"Health check '{check_name}' failed: {e}")
                results.append(
                    HealthCheck(
                        name=check_name,
                        status=HealthStatus.UNHEALTHY,
                        message=f"Check failed: {e!s}",
                        duration_ms=0,
                        details={"error": str(e)},
                    ),
                )

        # Determine overall status
        statuses = [check.status for check in results]
        if HealthStatus.UNHEALTHY in statuses:
            overall_status = HealthStatus.UNHEALTHY
        elif HealthStatus.DEGRADED in statuses:
            overall_status = HealthStatus.DEGRADED
        else:
            overall_status = HealthStatus.HEALTHY

        total_duration = (time.time() - start_time) * 1000

        return {
            "status": overall_status.value,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "duration_ms": round(total_duration, 2),
            "checks": [
                {
                    "name": check.name,
                    "status": check.status.value,
                    "message": check.message,
                    "duration_ms": round(check.duration_ms, 2),
                    "details": check.details or {},
                    "timestamp": check.timestamp.isoformat() + "Z",
                }
                for check in results
            ],
            "summary": {
                "total_checks": len(results),
                "healthy": len(
                    [c for c in results if c.status == HealthStatus.HEALTHY],
                ),
                "degraded": len(
                    [c for c in results if c.status == HealthStatus.DEGRADED],
                ),
                "unhealthy": len(
                    [c for c in results if c.status == HealthStatus.UNHEALTHY],
                ),
            },
        }

    async def quick_check(self) -> dict[str, Any]:
        """Quick health check for readiness probes."""
        try:
            # Just check database connectivity
            db_check = await self._check_database()

            return {
                "status": db_check.status.value,
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "message": db_check.message,
            }
        except Exception as e:
            return {
                "status": HealthStatus.UNHEALTHY.value,
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "message": f"Health check failed: {e!s}",
            }


# Global instance
health_checker = HealthChecker()


# Convenience functions
async def get_health_status() -> dict[str, Any]:
    """Get comprehensive health status."""
    return await health_checker.run_all_checks()


async def get_readiness_status() -> dict[str, Any]:
    """Get quick readiness status."""
    return await health_checker.quick_check()


def register_health_check(name: str, check_function: callable) -> None:
    """Register a custom health check."""
    health_checker.register_check(name, check_function)


async def check_redis(self) -> dict[str, Any]:
    """Check Redis connectivity and performance."""
    try:
        redis_client = redis.from_url(
            self.settings.REDIS_URL, encoding="utf-8", decode_responses=True,
        )

        start_time = datetime.now()
        await asyncio.get_event_loop().run_in_executor(None, redis_client.ping)
        end_time = datetime.now()

        response_time = (end_time - start_time).total_seconds() * 1000

        # Get Redis info
        info = await asyncio.get_event_loop().run_in_executor(None, redis_client.info)

        return {
            "status": "healthy",
            "response_time_ms": round(response_time, 2),
            "connected_clients": info.get("connected_clients", 0),
            "used_memory_human": info.get("used_memory_human", "N/A"),
            "redis_version": info.get("redis_version", "unknown"),
        }
    except Exception as e:
        return {"status": "unhealthy", "error": str(e), "response_time_ms": None}


async def check_disk_space(self) -> dict[str, Any]:
    """Check disk space usage."""
    try:
        disk_usage = psutil.disk_usage("/")
        free_space_gb = disk_usage.free / (1024**3)
        total_space_gb = disk_usage.total / (1024**3)
        used_space_percent = (disk_usage.used / disk_usage.total) * 100

        status = "healthy"
        if used_space_percent > 90:
            status = "critical"
        elif used_space_percent > 80:
            status = "warning"

        return {
            "status": status,
            "free_space_gb": round(free_space_gb, 2),
            "total_space_gb": round(total_space_gb, 2),
            "used_percent": round(used_space_percent, 2),
        }
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}


async def check_memory(self) -> dict[str, Any]:
    """Check memory usage."""
    try:
        memory = psutil.virtual_memory()

        status = "healthy"
        if memory.percent > 90:
            status = "critical"
        elif memory.percent > 80:
            status = "warning"

        return {
            "status": status,
            "total_gb": round(memory.total / (1024**3), 2),
            "available_gb": round(memory.available / (1024**3), 2),
            "used_percent": round(memory.percent, 2),
        }
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}


async def check_cpu(self) -> dict[str, Any]:
    """Check CPU usage."""
    try:
        # Get CPU usage over 1 second interval
        cpu_percent = psutil.cpu_percent(interval=1)
        cpu_count = psutil.cpu_count()

        status = "healthy"
        if cpu_percent > 90:
            status = "critical"
        elif cpu_percent > 80:
            status = "warning"

        return {
            "status": status,
            "usage_percent": round(cpu_percent, 2),
            "cpu_count": cpu_count,
        }
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}


async def check_procrastinate_queue(self) -> dict[str, Any]:
    """Check Procrastinate queue health."""
    try:
        async for session in get_db():
            # Check pending jobs count
            pending_result = await session.execute(
                text("SELECT COUNT(*) FROM procrastinate_jobs WHERE status = 'todo'"),
            )
            pending_count = pending_result.scalar()

            # Check failed jobs count
            failed_result = await session.execute(
                text("SELECT COUNT(*) FROM procrastinate_jobs WHERE status = 'failed'"),
            )
            failed_count = failed_result.scalar()

            status = "healthy"
            if failed_count > 100:
                status = "warning"
            if pending_count > 1000:
                status = "warning"

            return {
                "status": status,
                "pending_jobs": pending_count,
                "failed_jobs": failed_count,
            }
            break  # Exit after first iteration
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}


async def get_comprehensive_health(self) -> HealthStatus:
    """Get comprehensive health check."""
    start_time = datetime.now()

    # Run all health checks concurrently
    (
        database_health,
        redis_health,
        disk_health,
        memory_health,
        cpu_health,
        queue_health,
    ) = await asyncio.gather(
        self.check_database(),
        self.check_redis(),
        self.check_disk_space(),
        self.check_memory(),
        self.check_cpu(),
        self.check_procrastinate_queue(),
        return_exceptions=True,
    )

    # Determine overall status
    all_checks = [
        database_health,
        redis_health,
        disk_health,
        memory_health,
        cpu_health,
        queue_health,
    ]

    overall_status = "healthy"
    for check in all_checks:
        if isinstance(check, dict) and check.get("status") == "critical":
            overall_status = "critical"
            break
        if isinstance(check, dict) and check.get("status") == "warning":
            overall_status = "warning"
        elif isinstance(check, dict) and check.get("status") == "unhealthy":
            overall_status = "unhealthy"

    end_time = datetime.now()
    check_duration = (end_time - start_time).total_seconds() * 1000

    return HealthStatus(
        status=overall_status,
        timestamp=datetime.utcnow(),
        version=self.settings.APP_VERSION,
        environment=self.settings.ENVIRONMENT,
        details={
            "database": database_health,
            "redis": redis_health,
            "disk": disk_health,
            "memory": memory_health,
            "cpu": cpu_health,
            "queue": queue_health,
            "check_duration_ms": round(check_duration, 2),
        },
    )


async def get_readiness_check(self) -> dict[str, Any]:
    """Kubernetes readiness check - critical services only."""
    database_health = await self.check_database()
    redis_health = await self.check_redis()

    ready = (
        database_health.get("status") == "healthy"
        and redis_health.get("status") == "healthy"
    )

    return {
        "ready": ready,
        "database": database_health.get("status"),
        "redis": redis_health.get("status"),
    }


async def get_liveness_check(self) -> dict[str, Any]:
    """Kubernetes liveness check - basic application health."""
    return {"alive": True, "timestamp": datetime.utcnow().isoformat()}
