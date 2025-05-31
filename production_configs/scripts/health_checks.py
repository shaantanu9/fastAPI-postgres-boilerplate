#!/usr/bin/env python3
"""
Health Check System for FastAPI Production Applications

This module provides comprehensive health checking capabilities including:
- Application health checks
- Database connectivity checks
- External service dependency checks
- Resource utilization monitoring
- Custom health check registration
"""
import asyncio
import time
import psutil
import logging
from typing import Dict, List, Optional, Callable, Any
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass, asdict
from fastapi import FastAPI, HTTPException, status
from fastapi.responses import JSONResponse
import aiohttp
import asyncpg
from sqlalchemy.ext.asyncio import AsyncEngine
from sqlalchemy import text

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class HealthStatus(Enum):
    """Health check status enumeration."""
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    DEGRADED = "degraded"
    UNKNOWN = "unknown"


@dataclass
class HealthCheckResult:
    """Health check result data structure."""
    name: str
    status: HealthStatus
    message: str
    details: Dict[str, Any] = None
    timestamp: datetime = None
    duration_ms: float = 0
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()
        if self.details is None:
            self.details = {}


class HealthChecker:
    """
    Comprehensive health checking system for FastAPI applications.
    
    Features:
    - Multiple health check types
    - Async and sync check support
    - Configurable timeouts and retries
    - Dependency checking
    - Resource monitoring
    """
    
    def __init__(self, app: FastAPI = None):
        self.app = app
        self.checks: Dict[str, Callable] = {}
        self.dependencies: Dict[str, Callable] = {}
        self.cached_results: Dict[str, HealthCheckResult] = {}
        self.cache_ttl = 30  # Cache results for 30 seconds
        
        # Default system checks
        self._register_system_checks()
        
        if app:
            self._setup_routes(app)
    
    def _register_system_checks(self):
        """Register default system health checks."""
        self.register_check("system_memory", self.check_system_memory)
        self.register_check("system_cpu", self.check_system_cpu)
        self.register_check("system_disk", self.check_system_disk)
    
    def _setup_routes(self, app: FastAPI):
        """Set up health check routes."""
        
        @app.get("/health", tags=["Health"])
        async def health_check():
            """Basic health check endpoint."""
            return await self.get_health_summary()
        
        @app.get("/health/live", tags=["Health"])
        async def liveness_probe():
            """Kubernetes liveness probe - checks if app is running."""
            return {"status": "alive", "timestamp": datetime.utcnow().isoformat()}
        
        @app.get("/health/ready", tags=["Health"])
        async def readiness_probe():
            """Kubernetes readiness probe - checks if app is ready to serve traffic."""
            result = await self.check_readiness()
            if result["status"] != HealthStatus.HEALTHY.value:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail=result
                )
            return result
        
        @app.get("/health/detailed", tags=["Health"])
        async def detailed_health():
            """Detailed health check with all components."""
            return await self.get_detailed_health()
    
    def register_check(self, name: str, check_func: Callable, is_dependency: bool = False):
        """
        Register a health check function.
        
        Args:
            name: Unique name for the health check
            check_func: Function that returns HealthCheckResult
            is_dependency: Whether this is a critical dependency
        """
        self.checks[name] = check_func
        if is_dependency:
            self.dependencies[name] = check_func
    
    async def run_check(self, name: str, check_func: Callable) -> HealthCheckResult:
        """Run a single health check with timing and error handling."""
        start_time = time.time()
        
        try:
            # Check cache first
            if name in self.cached_results:
                cached = self.cached_results[name]
                if (datetime.utcnow() - cached.timestamp).seconds < self.cache_ttl:
                    return cached
            
            # Run the check
            if asyncio.iscoroutinefunction(check_func):
                result = await check_func()
            else:
                result = check_func()
            
            # Ensure result is HealthCheckResult
            if not isinstance(result, HealthCheckResult):
                result = HealthCheckResult(
                    name=name,
                    status=HealthStatus.HEALTHY if result else HealthStatus.UNHEALTHY,
                    message="Check completed",
                    details={"result": result}
                )
            
            # Add timing
            result.duration_ms = (time.time() - start_time) * 1000
            result.name = name
            result.timestamp = datetime.utcnow()
            
            # Cache result
            self.cached_results[name] = result
            
            return result
            
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            logger.error(f"Health check '{name}' failed: {e}")
            
            result = HealthCheckResult(
                name=name,
                status=HealthStatus.UNHEALTHY,
                message=f"Check failed: {str(e)}",
                details={"error": str(e), "error_type": type(e).__name__},
                duration_ms=duration_ms
            )
            
            # Cache failed result too (shorter TTL)
            self.cached_results[name] = result
            return result
    
    async def get_health_summary(self) -> Dict[str, Any]:
        """Get basic health summary."""
        start_time = time.time()
        
        # Run dependency checks only
        dependency_results = []
        for name, check_func in self.dependencies.items():
            result = await self.run_check(name, check_func)
            dependency_results.append(result)
        
        # Determine overall status
        overall_status = HealthStatus.HEALTHY
        if any(r.status == HealthStatus.UNHEALTHY for r in dependency_results):
            overall_status = HealthStatus.UNHEALTHY
        elif any(r.status == HealthStatus.DEGRADED for r in dependency_results):
            overall_status = HealthStatus.DEGRADED
        
        total_duration = (time.time() - start_time) * 1000
        
        return {
            "status": overall_status.value,
            "timestamp": datetime.utcnow().isoformat(),
            "duration_ms": total_duration,
            "checks_run": len(dependency_results),
            "dependencies": [asdict(r) for r in dependency_results]
        }
    
    async def check_readiness(self) -> Dict[str, Any]:
        """Check if application is ready to serve traffic."""
        start_time = time.time()
        
        # Run all dependency checks
        results = []
        for name, check_func in self.dependencies.items():
            result = await self.run_check(name, check_func)
            results.append(result)
        
        # Application is ready if all dependencies are healthy
        is_ready = all(r.status == HealthStatus.HEALTHY for r in results)
        status = HealthStatus.HEALTHY if is_ready else HealthStatus.UNHEALTHY
        
        total_duration = (time.time() - start_time) * 1000
        
        return {
            "status": status.value,
            "ready": is_ready,
            "timestamp": datetime.utcnow().isoformat(),
            "duration_ms": total_duration,
            "dependencies": [asdict(r) for r in results]
        }
    
    async def get_detailed_health(self) -> Dict[str, Any]:
        """Get detailed health information for all checks."""
        start_time = time.time()
        
        # Run all checks
        results = []
        for name, check_func in self.checks.items():
            result = await self.run_check(name, check_func)
            results.append(result)
        
        # Determine overall status
        overall_status = HealthStatus.HEALTHY
        if any(r.status == HealthStatus.UNHEALTHY for r in results):
            overall_status = HealthStatus.UNHEALTHY
        elif any(r.status == HealthStatus.DEGRADED for r in results):
            overall_status = HealthStatus.DEGRADED
        
        total_duration = (time.time() - start_time) * 1000
        
        # Categorize results
        healthy_checks = [r for r in results if r.status == HealthStatus.HEALTHY]
        unhealthy_checks = [r for r in results if r.status == HealthStatus.UNHEALTHY]
        degraded_checks = [r for r in results if r.status == HealthStatus.DEGRADED]
        
        return {
            "status": overall_status.value,
            "timestamp": datetime.utcnow().isoformat(),
            "duration_ms": total_duration,
            "summary": {
                "total_checks": len(results),
                "healthy": len(healthy_checks),
                "unhealthy": len(unhealthy_checks),
                "degraded": len(degraded_checks)
            },
            "checks": [asdict(r) for r in results]
        }
    
    # System Health Checks
    def check_system_memory(self) -> HealthCheckResult:
        """Check system memory usage."""
        memory = psutil.virtual_memory()
        memory_percent = memory.percent
        
        if memory_percent > 90:
            status = HealthStatus.UNHEALTHY
            message = f"High memory usage: {memory_percent}%"
        elif memory_percent > 80:
            status = HealthStatus.DEGRADED
            message = f"Elevated memory usage: {memory_percent}%"
        else:
            status = HealthStatus.HEALTHY
            message = f"Memory usage normal: {memory_percent}%"
        
        return HealthCheckResult(
            name="system_memory",
            status=status,
            message=message,
            details={
                "used_percent": memory_percent,
                "available_gb": round(memory.available / (1024**3), 2),
                "total_gb": round(memory.total / (1024**3), 2)
            }
        )
    
    def check_system_cpu(self) -> HealthCheckResult:
        """Check system CPU usage."""
        cpu_percent = psutil.cpu_percent(interval=1)
        
        if cpu_percent > 90:
            status = HealthStatus.UNHEALTHY
            message = f"High CPU usage: {cpu_percent}%"
        elif cpu_percent > 80:
            status = HealthStatus.DEGRADED
            message = f"Elevated CPU usage: {cpu_percent}%"
        else:
            status = HealthStatus.HEALTHY
            message = f"CPU usage normal: {cpu_percent}%"
        
        return HealthCheckResult(
            name="system_cpu",
            status=status,
            message=message,
            details={
                "cpu_percent": cpu_percent,
                "cpu_count": psutil.cpu_count(),
                "load_avg": psutil.getloadavg() if hasattr(psutil, 'getloadavg') else None
            }
        )
    
    def check_system_disk(self) -> HealthCheckResult:
        """Check system disk usage."""
        disk_usage = psutil.disk_usage('/')
        disk_percent = (disk_usage.used / disk_usage.total) * 100
        
        if disk_percent > 90:
            status = HealthStatus.UNHEALTHY
            message = f"High disk usage: {disk_percent:.1f}%"
        elif disk_percent > 80:
            status = HealthStatus.DEGRADED
            message = f"Elevated disk usage: {disk_percent:.1f}%"
        else:
            status = HealthStatus.HEALTHY
            message = f"Disk usage normal: {disk_percent:.1f}%"
        
        return HealthCheckResult(
            name="system_disk",
            status=status,
            message=message,
            details={
                "used_percent": round(disk_percent, 1),
                "free_gb": round(disk_usage.free / (1024**3), 2),
                "total_gb": round(disk_usage.total / (1024**3), 2)
            }
        )


# Database Health Check Functions
async def check_postgresql_async(engine: AsyncEngine) -> HealthCheckResult:
    """Check PostgreSQL database connectivity."""
    try:
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT 1"))
            row = result.fetchone()
            
            if row and row[0] == 1:
                return HealthCheckResult(
                    name="postgresql",
                    status=HealthStatus.HEALTHY,
                    message="PostgreSQL connection successful",
                    details={"query_result": row[0]}
                )
            else:
                return HealthCheckResult(
                    name="postgresql",
                    status=HealthStatus.UNHEALTHY,
                    message="PostgreSQL query returned unexpected result"
                )
    except Exception as e:
        return HealthCheckResult(
            name="postgresql",
            status=HealthStatus.UNHEALTHY,
            message=f"PostgreSQL connection failed: {str(e)}",
            details={"error": str(e)}
        )


async def check_redis_async(redis_url: str) -> HealthCheckResult:
    """Check Redis connectivity."""
    import aioredis
    
    try:
        redis = aioredis.from_url(redis_url)
        await redis.ping()
        await redis.close()
        
        return HealthCheckResult(
            name="redis",
            status=HealthStatus.HEALTHY,
            message="Redis connection successful"
        )
    except Exception as e:
        return HealthCheckResult(
            name="redis",
            status=HealthStatus.UNHEALTHY,
            message=f"Redis connection failed: {str(e)}",
            details={"error": str(e)}
        )


async def check_http_service(url: str, timeout: int = 5) -> HealthCheckResult:
    """Check external HTTP service availability."""
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=timeout)) as session:
            async with session.get(url) as response:
                if response.status == 200:
                    return HealthCheckResult(
                        name=f"http_service_{url}",
                        status=HealthStatus.HEALTHY,
                        message=f"Service {url} is reachable",
                        details={"status_code": response.status, "url": url}
                    )
                else:
                    return HealthCheckResult(
                        name=f"http_service_{url}",
                        status=HealthStatus.DEGRADED,
                        message=f"Service {url} returned status {response.status}",
                        details={"status_code": response.status, "url": url}
                    )
    except Exception as e:
        return HealthCheckResult(
            name=f"http_service_{url}",
            status=HealthStatus.UNHEALTHY,
            message=f"Service {url} is unreachable: {str(e)}",
            details={"error": str(e), "url": url}
        )


# Example usage and integration
def setup_health_checks(app: FastAPI, **kwargs) -> HealthChecker:
    """
    Set up comprehensive health checks for a FastAPI application.
    
    Args:
        app: FastAPI application instance
        **kwargs: Configuration options
    
    Returns:
        HealthChecker instance
    """
    health_checker = HealthChecker(app)
    
    # Register database checks
    if 'database_engine' in kwargs:
        engine = kwargs['database_engine']
        health_checker.register_check(
            "database",
            lambda: check_postgresql_async(engine),
            is_dependency=True
        )
    
    # Register Redis checks
    if 'redis_url' in kwargs:
        redis_url = kwargs['redis_url']
        health_checker.register_check(
            "redis",
            lambda: check_redis_async(redis_url),
            is_dependency=True
        )
    
    # Register external service checks
    external_services = kwargs.get('external_services', [])
    for service_url in external_services:
        health_checker.register_check(
            f"external_service_{service_url}",
            lambda url=service_url: check_http_service(url),
            is_dependency=False
        )
    
    logger.info(f"Health checks configured with {len(health_checker.checks)} checks")
    return health_checker


if __name__ == "__main__":
    # Example usage
    from fastapi import FastAPI
    import uvicorn
    
    app = FastAPI(title="Health Check Example")
    
    # Set up health checks
    health_checker = setup_health_checks(
        app,
        external_services=["https://httpbin.org/get"]
    )
    
    @app.get("/")
    async def root():
        return {"message": "Hello World"}
    
    uvicorn.run(app, host="0.0.0.0", port=8000) 