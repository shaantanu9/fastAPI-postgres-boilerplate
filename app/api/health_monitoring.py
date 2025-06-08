"""
Comprehensive Health Monitoring System
"""

import asyncio
import psutil
import time
from datetime import datetime
from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from pydantic import BaseModel
from loguru import logger

from app.db.session import get_db
from app.core.redis_manager import redis_manager
from app.core.config import get_settings


class HealthCheck:
    """Enterprise health monitoring"""
    
    def __init__(self):
        self.settings = get_settings()
        self.start_time = time.time()
        
    async def check_database(self, db: AsyncSession) -> Dict[str, Any]:
        """Check database health"""
        start_time = time.time()
        try:
            await db.execute(text("SELECT 1"))
            response_time = (time.time() - start_time) * 1000
            
            return {
                "status": "healthy" if response_time < 1000 else "degraded",
                "response_time_ms": response_time,
                "message": "Database operational"
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "response_time_ms": (time.time() - start_time) * 1000,
                "message": f"Database error: {str(e)}"
            }
    
    async def check_redis(self) -> Dict[str, Any]:
        """Check Redis health"""
        start_time = time.time()
        try:
            if redis_manager.redis_client:
                await redis_manager.redis_client.ping()
                info = await redis_manager.redis_client.info()
                response_time = (time.time() - start_time) * 1000
                
                return {
                    "status": "healthy",
                    "response_time_ms": response_time,
                    "message": "Redis operational",
                    "details": {
                        "connected_clients": info.get('connected_clients', 0),
                        "used_memory": info.get('used_memory_human', '0'),
                        "version": info.get('redis_version', 'unknown')
                    }
                }
            else:
                return {
                    "status": "unhealthy",
                    "response_time_ms": 0,
                    "message": "Redis not connected"
                }
        except Exception as e:
            return {
                "status": "unhealthy",
                "response_time_ms": (time.time() - start_time) * 1000,
                "message": f"Redis error: {str(e)}"
            }
    
    async def check_system(self) -> Dict[str, Any]:
        """Check system resources"""
        try:
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            if cpu_percent > 90 or memory.percent > 90:
                status = "unhealthy"
            elif cpu_percent > 70 or memory.percent > 70:
                status = "degraded"
            else:
                status = "healthy"
            
            return {
                "status": status,
                "response_time_ms": 0,
                "message": "System resources checked",
                "details": {
                    "cpu_percent": cpu_percent,
                    "memory_percent": memory.percent,
                    "disk_percent": disk.percent
                }
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "response_time_ms": 0,
                "message": f"System check error: {str(e)}"
            }
    
    def get_uptime(self) -> float:
        return time.time() - self.start_time


health_checker = HealthCheck()
router = APIRouter()


@router.get("/health")
async def health_status(db: AsyncSession = Depends(get_db)):
    """Comprehensive health check"""
    try:
        db_check, redis_check, system_check = await asyncio.gather(
            health_checker.check_database(db),
            health_checker.check_redis(),
            health_checker.check_system(),
            return_exceptions=True
        )
        
        checks = {
            "database": db_check if not isinstance(db_check, Exception) else {"status": "unhealthy", "message": str(db_check)},
            "redis": redis_check if not isinstance(redis_check, Exception) else {"status": "unhealthy", "message": str(redis_check)},
            "system": system_check if not isinstance(system_check, Exception) else {"status": "unhealthy", "message": str(system_check)}
        }
        
        # Overall status
        statuses = [check["status"] for check in checks.values()]
        if "unhealthy" in statuses:
            overall_status = "unhealthy"
            status_code = 503
        elif "degraded" in statuses:
            overall_status = "degraded"
            status_code = 200
        else:
            overall_status = "healthy"
            status_code = 200
        
        response = {
            "status": overall_status,
            "timestamp": datetime.utcnow().isoformat(),
            "uptime_seconds": health_checker.get_uptime(),
            "checks": checks
        }
        
        return JSONResponse(status_code=status_code, content=response)
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "timestamp": datetime.utcnow().isoformat(),
                "message": f"Health check failed: {str(e)}"
            }
        )


@router.get("/health/ready")
async def readiness_probe(db: AsyncSession = Depends(get_db)):
    """Kubernetes readiness probe"""
    try:
        await db.execute(text("SELECT 1"))
        if redis_manager.redis_client:
            await redis_manager.redis_client.ping()
        return {"status": "ready"}
    except Exception:
        raise HTTPException(status_code=503, detail="Not ready")


@router.get("/health/live")
async def liveness_probe():
    """Kubernetes liveness probe"""
    return {
        "status": "alive",
        "uptime": health_checker.get_uptime()
    }


@router.get("/metrics")
async def prometheus_metrics(db: AsyncSession = Depends(get_db)):
    """Prometheus-style metrics"""
    try:
        system_check = await health_checker.check_system()
        
        metrics = {
            "app_uptime_seconds": health_checker.get_uptime(),
            "system_cpu_percent": system_check.get("details", {}).get("cpu_percent", 0),
            "system_memory_percent": system_check.get("details", {}).get("memory_percent", 0),
            "system_disk_percent": system_check.get("details", {}).get("disk_percent", 0),
            "timestamp": datetime.utcnow().isoformat()
        }
        
        return metrics
        
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Metrics failed: {str(e)}") 