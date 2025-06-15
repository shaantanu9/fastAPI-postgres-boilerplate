"""
Simple Production Health Endpoints
No database dependencies to avoid import issues
"""

from fastapi import APIRouter
import time
import os

router = APIRouter()

@router.get("/health")
async def health_check():
    """
    Simple health check for production monitoring
    No database dependencies
    """
    start_time = time.time()
    
    health_status = {
        "status": "healthy",
        "timestamp": time.time(),
        "checks": {}
    }
    
    # Check disk space
    try:
        import shutil
        disk_usage = shutil.disk_usage("/")
        free_gb = disk_usage.free / (1024**3)
        
        health_status["checks"]["disk"] = {
            "status": "healthy" if free_gb > 1 else "warning",
            "free_space_gb": round(free_gb, 2)
        }
        
    except Exception:
        health_status["checks"]["disk"] = {"status": "unknown"}
    
    # Check memory usage
    try:
        import psutil
        memory = psutil.virtual_memory()
        
        health_status["checks"]["memory"] = {
            "status": "healthy" if memory.percent < 85 else "warning",
            "usage_percent": memory.percent
        }
        
    except ImportError:
        health_status["checks"]["memory"] = {"status": "psutil_not_available"}
    except Exception:
        health_status["checks"]["memory"] = {"status": "unknown"}
    
    # Total response time
    response_time = (time.time() - start_time) * 1000
    health_status["response_time_ms"] = round(response_time, 2)
    
    return health_status

@router.get("/ready")
async def readiness_check():
    """Simple readiness probe"""
    return {"status": "ready", "timestamp": time.time()}

@router.get("/live")
async def liveness_check():
    """Simple liveness probe"""
    return {"status": "alive", "timestamp": time.time()}

@router.get("/metrics")
async def simple_metrics():
    """Basic application metrics"""
    try:
        import psutil
        process = psutil.Process()
        
        return {
            "timestamp": time.time(),
            "memory_usage_mb": round(process.memory_info().rss / 1024 / 1024, 2),
            "cpu_percent": process.cpu_percent(),
            "uptime_seconds": round(time.time() - process.create_time(), 2)
        }
    except ImportError:
        return {
            "timestamp": time.time(),
            "status": "psutil_not_available"
        }
    except Exception as e:
        return {
            "timestamp": time.time(),
            "error": str(e)
        } 