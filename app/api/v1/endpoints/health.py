# app/api/v1/endpoints/health.py

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from typing import Dict, Any

from app.core.health import HealthChecker, HealthStatus


router = APIRouter()
health_checker = HealthChecker()


@router.get("/")
async def basic_health() -> Dict[str, str]:
    """Basic health check for load balancers"""
    return {"status": "ok", "message": "Service is running"}


@router.get("/health")
async def health_check() -> HealthStatus:
    """Comprehensive health check with all system components"""
    return await health_checker.get_comprehensive_health()


@router.get("/ready")
async def readiness_check() -> Dict[str, Any]:
    """Kubernetes readiness probe - checks critical dependencies"""
    result = await health_checker.get_readiness_check()
    
    if not result["ready"]:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service not ready"
        )
    
    return result


@router.get("/live")
async def liveness_check() -> Dict[str, Any]:
    """Kubernetes liveness probe - basic application health"""
    return await health_checker.get_liveness_check()


@router.get("/health/database")
async def database_health() -> Dict[str, Any]:
    """Detailed database health check"""
    return await health_checker.check_database()


@router.get("/health/redis")
async def redis_health() -> Dict[str, Any]:
    """Detailed Redis health check"""
    return await health_checker.check_redis()


@router.get("/health/system")
async def system_health() -> Dict[str, Any]:
    """System resource health check"""
    disk_health = await health_checker.check_disk_space()
    memory_health = await health_checker.check_memory()
    cpu_health = await health_checker.check_cpu()
    
    return {
        "disk": disk_health,
        "memory": memory_health,
        "cpu": cpu_health
    }


@router.get("/health/queue")
async def queue_health() -> Dict[str, Any]:
    """Background job queue health check"""
    return await health_checker.check_procrastinate_queue() 