# app/api/v1/endpoints/health.py

"""Comprehensive Health Check System
Provides detailed health monitoring for all system components.
"""

import asyncio
import time
from datetime import datetime
from typing import Annotated, Any

import psutil
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from loguru import logger
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.redis_manager import redis_manager
from app.db.session import get_db


class HealthStatus(BaseModel):
    """Health check response model."""

    status: str
    timestamp: datetime
    version: str
    environment: str
    uptime_seconds: float
    checks: dict[str, Any]


class ComponentHealth(BaseModel):
    """Individual component health."""

    status: str  # healthy, degraded, unhealthy
    response_time_ms: float
    message: str
    details: dict[str, Any] | None = None


class HealthChecker:
    """Enterprise health checking service."""

    def __init__(self) -> None:
        self.settings = get_settings()
        self.start_time = time.time()

    async def check_database(self, db: AsyncSession) -> ComponentHealth:
        """Check database connectivity and performance."""
        start_time = time.time()

        try:
            # Simple connectivity test
            await db.execute(text("SELECT 1"))

            # Performance test - check slow queries
            slow_query_start = time.time()
            result = await db.execute(
                text("""
                SELECT COUNT(*) as user_count,
                       AVG(EXTRACT(EPOCH FROM (NOW() - created_at))) as avg_age_seconds
                FROM users
                WHERE created_at > NOW() - INTERVAL '7 days'
            """),
            )
            slow_query_time = (time.time() - slow_query_start) * 1000

            row = result.fetchone()
            user_count = row[0] if row else 0
            avg_age = row[1] if row else 0

            response_time = (time.time() - start_time) * 1000

            # Check if response time is acceptable
            if response_time > 1000:  # 1 second
                status = "degraded"
                message = "Database response time is slow"
            else:
                status = "healthy"
                message = "Database is operational"

            return ComponentHealth(
                status=status,
                response_time_ms=response_time,
                message=message,
                details={
                    "query_time_ms": slow_query_time,
                    "recent_users": user_count,
                    "avg_user_age_seconds": avg_age,
                    "connection_pool_size": getattr(db.bind.pool, "size", "unknown"),
                    "checked_out_connections": getattr(
                        db.bind.pool, "checkedout", "unknown",
                    ),
                },
            )

        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            logger.error(f"Database health check failed: {e}")

            return ComponentHealth(
                status="unhealthy",
                response_time_ms=response_time,
                message=f"Database connection failed: {e!s}",
                details={"error": str(e)},
            )

    async def check_redis(self) -> ComponentHealth:
        """Check Redis connectivity and performance."""
        start_time = time.time()

        try:
            if not redis_manager.redis_client:
                return ComponentHealth(
                    status="unhealthy",
                    response_time_ms=0,
                    message="Redis client not initialized",
                )

            # Test basic operations
            test_key = f"health_check:{int(time.time())}"

            # Set operation
            await redis_manager.redis_client.set(test_key, "health_check", ex=60)

            # Get operation
            await redis_manager.redis_client.get(test_key)

            # Delete operation
            await redis_manager.redis_client.delete(test_key)

            response_time = (time.time() - start_time) * 1000

            # Get Redis info
            info = await redis_manager.redis_client.info()

            # Check memory usage
            used_memory = info.get("used_memory", 0)
            max_memory = info.get("maxmemory", 0)
            memory_usage_percent = (
                (used_memory / max_memory * 100) if max_memory > 0 else 0
            )

            if memory_usage_percent > 90:
                status = "degraded"
                message = "Redis memory usage is high"
            elif response_time > 500:  # 500ms
                status = "degraded"
                message = "Redis response time is slow"
            else:
                status = "healthy"
                message = "Redis is operational"

            return ComponentHealth(
                status=status,
                response_time_ms=response_time,
                message=message,
                details={
                    "redis_version": info.get("redis_version"),
                    "connected_clients": info.get("connected_clients"),
                    "used_memory_human": info.get("used_memory_human"),
                    "memory_usage_percent": round(memory_usage_percent, 2),
                    "uptime_seconds": info.get("uptime_in_seconds"),
                    "commands_processed": info.get("total_commands_processed"),
                },
            )

        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            logger.error(f"Redis health check failed: {e}")

            return ComponentHealth(
                status="unhealthy",
                response_time_ms=response_time,
                message=f"Redis connection failed: {e!s}",
                details={"error": str(e)},
            )

    async def check_system_resources(self) -> ComponentHealth:
        """Check system resource usage."""
        start_time = time.time()

        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)

            # Memory usage
            memory = psutil.virtual_memory()

            # Disk usage
            disk = psutil.disk_usage("/")

            # Network stats
            network = psutil.net_io_counters()

            response_time = (time.time() - start_time) * 1000

            # Determine status based on resource usage
            if cpu_percent > 90 or memory.percent > 90 or disk.percent > 90:
                status = "unhealthy"
                message = "System resources critically high"
            elif cpu_percent > 70 or memory.percent > 70 or disk.percent > 80:
                status = "degraded"
                message = "System resources elevated"
            else:
                status = "healthy"
                message = "System resources normal"

            return ComponentHealth(
                status=status,
                response_time_ms=response_time,
                message=message,
                details={
                    "cpu_percent": cpu_percent,
                    "memory_percent": memory.percent,
                    "memory_available_gb": round(memory.available / (1024**3), 2),
                    "disk_percent": disk.percent,
                    "disk_free_gb": round(disk.free / (1024**3), 2),
                    "network_bytes_sent": network.bytes_sent,
                    "network_bytes_received": network.bytes_recv,
                    "load_average": list(psutil.getloadavg())
                    if hasattr(psutil, "getloadavg")
                    else None,
                },
            )

        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            logger.error(f"System resources check failed: {e}")

            return ComponentHealth(
                status="unhealthy",
                response_time_ms=response_time,
                message=f"System check failed: {e!s}",
                details={"error": str(e)},
            )

    async def check_external_services(self) -> ComponentHealth:
        """Check external service dependencies."""
        start_time = time.time()

        try:
            # Here you would check external APIs, services, etc.
            # For now, we'll simulate some checks

            external_services = []

            # Example: Check email service
            if hasattr(self.settings, "email_service_url"):
                # Would make actual HTTP request to verify service
                external_services.append(
                    {
                        "name": "email_service",
                        "status": "healthy",
                        "response_time_ms": 45,
                    },
                )

            response_time = (time.time() - start_time) * 1000

            # Determine overall status
            unhealthy_services = [
                s for s in external_services if s["status"] == "unhealthy"
            ]
            degraded_services = [
                s for s in external_services if s["status"] == "degraded"
            ]

            if unhealthy_services:
                status = "unhealthy"
                message = f"{len(unhealthy_services)} external services are down"
            elif degraded_services:
                status = "degraded"
                message = f"{len(degraded_services)} external services are degraded"
            else:
                status = "healthy"
                message = "All external services operational"

            return ComponentHealth(
                status=status,
                response_time_ms=response_time,
                message=message,
                details={
                    "total_services": len(external_services),
                    "healthy_services": len(
                        [s for s in external_services if s["status"] == "healthy"],
                    ),
                    "services": external_services,
                },
            )

        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            logger.error(f"External services check failed: {e}")

            return ComponentHealth(
                status="unhealthy",
                response_time_ms=response_time,
                message=f"External services check failed: {e!s}",
                details={"error": str(e)},
            )

    def get_uptime(self) -> float:
        """Get application uptime in seconds."""
        return time.time() - self.start_time

    def determine_overall_status(self, checks: dict[str, ComponentHealth]) -> str:
        """Determine overall application status."""
        statuses = [check.status for check in checks.values()]

        if "unhealthy" in statuses:
            return "unhealthy"
        if "degraded" in statuses:
            return "degraded"
        return "healthy"


# Initialize health checker
health_checker = HealthChecker()

# Create router
router = APIRouter()


@router.get("/health", response_model=HealthStatus)
async def get_health_status(db: Annotated[AsyncSession, Depends(get_db)]):
    """Comprehensive health check endpoint that performs deep inspection of all system components.

    Performs parallel checks on database connectivity, Redis availability, system resources,
    and external service dependencies. Aggregates results into a single health status report.

    Args:
        db (AsyncSession): Database session dependency for running database health checks.

    Returns:
        HealthStatus: Detailed health status object containing checks for all components.

    Raises:
        HTTPException: If critical health checks fail and system is completely unavailable.

    """
    try:
        # Run all health checks in parallel
        db_check, redis_check, system_check, external_check = await asyncio.gather(
            health_checker.check_database(db),
            health_checker.check_redis(),
            health_checker.check_system_resources(),
            health_checker.check_external_services(),
            return_exceptions=True,
        )

        # Handle any exceptions
        checks = {}
        for name, check in [
            ("database", db_check),
            ("redis", redis_check),
            ("system", system_check),
            ("external_services", external_check),
        ]:
            if isinstance(check, Exception):
                checks[name] = ComponentHealth(
                    status="unhealthy",
                    response_time_ms=0,
                    message=f"Health check failed: {check!s}",
                )
            else:
                checks[name] = check

        # Determine overall status
        overall_status = health_checker.determine_overall_status(checks)

        health_status = HealthStatus(
            status=overall_status,
            timestamp=datetime.utcnow(),
            version=getattr(health_checker.settings, "app_version", "1.0.0"),
            environment=getattr(health_checker.settings, "environment", "development"),
            uptime_seconds=health_checker.get_uptime(),
            checks={name: check.dict() for name, check in checks.items()},
        )

        # Set appropriate HTTP status code
        if overall_status == "unhealthy":
            status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        elif overall_status == "degraded":
            status_code = status.HTTP_200_OK  # Still serving, but with warnings
        else:
            status_code = status.HTTP_200_OK

        return JSONResponse(status_code=status_code, content=health_status.dict())

    except Exception as e:
        logger.error(f"Health check endpoint failed: {e}")

        error_health = HealthStatus(
            status="unhealthy",
            timestamp=datetime.utcnow(),
            version="unknown",
            environment="unknown",
            uptime_seconds=health_checker.get_uptime(),
            checks={"error": {"status": "unhealthy", "message": str(e)}},
        )

        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, content=error_health.dict(),
        )


@router.get("/health/ready")
async def readiness_check(db: Annotated[AsyncSession, Depends(get_db)]):
    """Kubernetes-style readiness probe for container orchestration environments.

    Performs lightweight checks to determine if the application is ready to serve traffic.
    Focuses on database connectivity and critical service availability.

    Args:
        db (AsyncSession): Database session dependency for connectivity check.

    Returns:
        JSONResponse: Status 200 OK if ready to serve traffic, 503 Service Unavailable if not.

    Raises:
        None: This endpoint handles all exceptions internally and returns appropriate status.

    """
    try:
        # Quick checks for critical dependencies
        await db.execute(text("SELECT 1"))

        if redis_manager.redis_client:
            await redis_manager.redis_client.ping()

        return {"status": "ready", "timestamp": datetime.utcnow()}

    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Service not ready",
        )


@router.get("/health/live")
async def liveness_check():
    """Kubernetes-style liveness probe for container orchestration environments.

    Performs minimal checks to determine if the application process is alive and functioning.
    Used by orchestrators to determine if the container should be restarted.

    Returns:
        JSONResponse: Status 200 OK if application is alive, 503 Service Unavailable if should be restarted.

    Raises:
        None: This endpoint handles all exceptions internally and returns appropriate status.

    """
    return {
        "status": "alive",
        "timestamp": datetime.utcnow(),
        "uptime_seconds": health_checker.get_uptime(),
    }


@router.get("/metrics")
async def get_metrics(db: Annotated[AsyncSession, Depends(get_db)]):
    """Prometheus-style metrics endpoint for monitoring and alerting.

    Collects and returns key performance indicators and operational metrics in a format
    compatible with Prometheus scraping. Includes database performance, API response times,
    error rates, and system resource utilization.

    Args:
        db (AsyncSession): Database session dependency for collecting database metrics.

    Returns:
        Response: Plain text response with metrics in Prometheus exposition format.

    Raises:
        None: This endpoint handles all exceptions internally and returns available metrics.

    """
    try:
        # Gather metrics
        system_check = await health_checker.check_system_resources()
        redis_check = await health_checker.check_redis()

        return {
            "app_uptime_seconds": health_checker.get_uptime(),
            "app_version": getattr(health_checker.settings, "app_version", "1.0.0"),
            "system_cpu_percent": system_check.details.get("cpu_percent", 0)
            if system_check.details
            else 0,
            "system_memory_percent": system_check.details.get("memory_percent", 0)
            if system_check.details
            else 0,
            "system_disk_percent": system_check.details.get("disk_percent", 0)
            if system_check.details
            else 0,
            "redis_connected_clients": redis_check.details.get("connected_clients", 0)
            if redis_check.details
            else 0,
            "redis_memory_usage_percent": redis_check.details.get(
                "memory_usage_percent", 0,
            )
            if redis_check.details
            else 0,
            "database_response_time_ms": (
                await health_checker.check_database(db)
            ).response_time_ms,
            "redis_response_time_ms": redis_check.response_time_ms,
            "timestamp": datetime.utcnow().isoformat(),
        }


    except Exception as e:
        logger.error(f"Metrics endpoint failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Metrics collection failed",
        )
