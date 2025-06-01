# app/core/health.py

import asyncio
import psutil
import redis
from datetime import datetime
from typing import Dict, Any, Optional
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import status
from pydantic import BaseModel

from app.db.session import get_db
from app.core.config import get_settings


class HealthStatus(BaseModel):
    status: str
    timestamp: datetime
    version: str
    environment: str
    details: Dict[str, Any]


class HealthChecker:
    """Enterprise-level health check system"""
    
    def __init__(self):
        self.settings = get_settings()
        
    async def check_database(self) -> Dict[str, Any]:
        """Check database connectivity and performance"""
        try:
            async for session in get_db():
                start_time = datetime.now()
                result = await session.execute(text("SELECT 1"))
                end_time = datetime.now()
                
                response_time = (end_time - start_time).total_seconds() * 1000
                
                return {
                    "status": "healthy",
                    "response_time_ms": round(response_time, 2),
                    "connection_pool_size": session.bind.pool.size(),
                    "checked_out_connections": session.bind.pool.checkedout(),
                }
                break  # Exit after first iteration
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "response_time_ms": None
            }

    async def check_redis(self) -> Dict[str, Any]:
        """Check Redis connectivity and performance"""
        try:
            redis_client = redis.from_url(
                self.settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True
            )
            
            start_time = datetime.now()
            await asyncio.get_event_loop().run_in_executor(
                None, redis_client.ping
            )
            end_time = datetime.now()
            
            response_time = (end_time - start_time).total_seconds() * 1000
            
            # Get Redis info
            info = await asyncio.get_event_loop().run_in_executor(
                None, redis_client.info
            )
            
            return {
                "status": "healthy",
                "response_time_ms": round(response_time, 2),
                "connected_clients": info.get("connected_clients", 0),
                "used_memory_human": info.get("used_memory_human", "N/A"),
                "redis_version": info.get("redis_version", "unknown")
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "response_time_ms": None
            }

    async def check_disk_space(self) -> Dict[str, Any]:
        """Check disk space usage"""
        try:
            disk_usage = psutil.disk_usage('/')
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
                "used_percent": round(used_space_percent, 2)
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e)
            }

    async def check_memory(self) -> Dict[str, Any]:
        """Check memory usage"""
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
                "used_percent": round(memory.percent, 2)
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e)
            }

    async def check_cpu(self) -> Dict[str, Any]:
        """Check CPU usage"""
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
                "cpu_count": cpu_count
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e)
            }

    async def check_procrastinate_queue(self) -> Dict[str, Any]:
        """Check Procrastinate queue health"""
        try:
            async for session in get_db():
                # Check pending jobs count
                pending_result = await session.execute(
                    text("SELECT COUNT(*) FROM procrastinate_jobs WHERE status = 'todo'")
                )
                pending_count = pending_result.scalar()
                
                # Check failed jobs count
                failed_result = await session.execute(
                    text("SELECT COUNT(*) FROM procrastinate_jobs WHERE status = 'failed'")
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
                    "failed_jobs": failed_count
                }
                break  # Exit after first iteration
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e)
            }

    async def get_comprehensive_health(self) -> HealthStatus:
        """Get comprehensive health check"""
        start_time = datetime.now()
        
        # Run all health checks concurrently
        database_health, redis_health, disk_health, memory_health, cpu_health, queue_health = await asyncio.gather(
            self.check_database(),
            self.check_redis(),
            self.check_disk_space(),
            self.check_memory(),
            self.check_cpu(),
            self.check_procrastinate_queue(),
            return_exceptions=True
        )
        
        # Determine overall status
        all_checks = [
            database_health, redis_health, disk_health, 
            memory_health, cpu_health, queue_health
        ]
        
        overall_status = "healthy"
        for check in all_checks:
            if isinstance(check, dict) and check.get("status") == "critical":
                overall_status = "critical"
                break
            elif isinstance(check, dict) and check.get("status") == "warning":
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
                "check_duration_ms": round(check_duration, 2)
            }
        )

    async def get_readiness_check(self) -> Dict[str, Any]:
        """Kubernetes readiness check - critical services only"""
        database_health = await self.check_database()
        redis_health = await self.check_redis()
        
        ready = (
            database_health.get("status") == "healthy" and 
            redis_health.get("status") == "healthy"
        )
        
        return {
            "ready": ready,
            "database": database_health.get("status"),
            "redis": redis_health.get("status")
        }

    async def get_liveness_check(self) -> Dict[str, Any]:
        """Kubernetes liveness check - basic application health"""
        return {
            "alive": True,
            "timestamp": datetime.utcnow().isoformat()
        } 