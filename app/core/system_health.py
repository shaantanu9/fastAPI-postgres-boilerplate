"""System Health Checker.

This module provides comprehensive health checking for all system components
including database, Redis, Procrastinate, authentication, and middleware.
"""

import asyncio
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

from loguru import logger
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.session import get_db


class SystemHealthChecker:
    """Comprehensive system health checker."""
    
    def __init__(self):
        self.settings = get_settings()
        self.health_checks = []
        self._register_health_checks()
    
    def _register_health_checks(self) -> None:
        """Register all health check functions."""
        self.health_checks = [
            ("Database Connection", self.check_database),
            ("Redis Connection", self.check_redis),
            ("Procrastinate", self.check_procrastinate),
            ("Authentication Service", self.check_auth_service),
            ("Alembic Migrations", self.check_alembic),
            ("Middleware Configuration", self.check_middleware),
            ("Environment Configuration", self.check_environment),
        ]
    
    async def check_database(self) -> Dict[str, Any]:
        """Check database connectivity and health."""
        status = {
            "healthy": False,
            "connection": False,
            "version": None,
            "pool_status": None,
            "response_time_ms": None,
        }
        
        try:
            start_time = time.time()
            
            # Get database session
            async for db in get_db():
                # Test basic connection
                result = await db.execute(text("SELECT version()"))
                version = result.scalar()
                status["version"] = version
                status["connection"] = True
                
                # Test a simple query
                await db.execute(text("SELECT 1"))
                
                # Calculate response time
                end_time = time.time()
                status["response_time_ms"] = round((end_time - start_time) * 1000, 2)
                
                status["healthy"] = True
                break
                
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            status["error"] = str(e)
            
        return status
    
    async def check_redis(self) -> Dict[str, Any]:
        """Check Redis connectivity and health."""
        status = {
            "healthy": False,
            "connection": False,
            "version": None,
            "memory_usage": None,
            "response_time_ms": None,
        }
        
        try:
            # Try to import and connect to Redis
            from app.core.cache import cache_service
            
            start_time = time.time()
            
            # Test Redis connection
            if hasattr(cache_service, 'redis') and cache_service.redis:
                # Test ping
                await cache_service.redis.ping()
                status["connection"] = True
                
                # Get Redis info
                info = await cache_service.redis.info()
                status["version"] = info.get("redis_version")
                status["memory_usage"] = info.get("used_memory_human")
                
                # Test set/get operation
                test_key = "health_check_test"
                await cache_service.redis.set(test_key, "test_value", ex=10)
                test_value = await cache_service.redis.get(test_key)
                
                if test_value == "test_value":
                    status["healthy"] = True
                
                # Cleanup test key
                await cache_service.redis.delete(test_key)
                
            end_time = time.time()
            status["response_time_ms"] = round((end_time - start_time) * 1000, 2)
            
        except ImportError:
            status["error"] = "Redis not configured or cache service not available"
        except Exception as e:
            logger.error(f"Redis health check failed: {e}")
            status["error"] = str(e)
            
        return status
    
    async def check_procrastinate(self) -> Dict[str, Any]:
        """Check Procrastinate task queue health."""
        status = {
            "healthy": False,
            "initialized": False,
            "schema_ready": False,
            "connection": False,
        }
        
        try:
            # Try to import Procrastinate manager
            from app.core.procrastinate_enhanced import enhanced_procrastinate_manager
            
            # Check if initialized
            status["initialized"] = enhanced_procrastinate_manager.is_initialized
            
            if enhanced_procrastinate_manager.is_initialized:
                # Perform health check
                health_result = await enhanced_procrastinate_manager.health_check()
                status.update(health_result)
                status["healthy"] = health_result.get("status") == "healthy"
            else:
                status["error"] = "Procrastinate not initialized"
                
        except ImportError:
            status["error"] = "Procrastinate not available"
        except Exception as e:
            logger.error(f"Procrastinate health check failed: {e}")
            status["error"] = str(e)
            
        return status
    
    async def check_auth_service(self) -> Dict[str, Any]:
        """Check authentication service health."""
        status = {
            "healthy": False,
            "service_available": False,
            "security_service_available": False,
            "jwt_service_available": False,
        }
        
        try:
            # Check if auth service is available
            from app.services.auth_service import unified_auth_service
            status["service_available"] = True
            
            # Check security service
            if hasattr(unified_auth_service, 'security_service') and unified_auth_service.security_service:
                status["security_service_available"] = True
            
            # Check JWT service
            from app.core.jwt import jwt_service
            status["jwt_service_available"] = True
            
            # Test basic functionality (password hashing)
            test_password = "test_password_123"
            hashed = unified_auth_service.security_service.hash_password(test_password)
            verified = unified_auth_service.security_service.verify_password(test_password, hashed)
            
            if verified:
                status["healthy"] = True
            else:
                status["error"] = "Password verification failed"
                
        except Exception as e:
            logger.error(f"Auth service health check failed: {e}")
            status["error"] = str(e)
            
        return status
    
    async def check_alembic(self) -> Dict[str, Any]:
        """Check Alembic migration system health."""
        status = {
            "healthy": False,
            "configured": False,
            "current_revision": None,
            "pending_migrations": [],
            "migration_count": 0,
        }
        
        try:
            # Try to import Alembic manager
            from app.core.alembic_manager import alembic_manager
            
            # Check Alembic setup
            alembic_status = alembic_manager.check_alembic_setup()
            status.update(alembic_status)
            
            # Validate migrations
            validation = alembic_manager.validate_migrations()
            status["healthy"] = validation["valid"]
            
            if not validation["valid"]:
                status["errors"] = validation["errors"]
                status["warnings"] = validation["warnings"]
            
            status["configured"] = True
            
        except ImportError:
            status["error"] = "Alembic manager not available"
        except Exception as e:
            logger.error(f"Alembic health check failed: {e}")
            status["error"] = str(e)
            
        return status
    
    async def check_middleware(self) -> Dict[str, Any]:
        """Check middleware configuration health."""
        status = {
            "healthy": False,
            "middleware_count": 0,
            "security_headers": False,
            "rate_limiting": False,
            "logging": False,
            "cors": False,
        }
        
        try:
            # Check if middleware config is available
            from app.core.middleware_config import get_middleware_config
            
            config = get_middleware_config()
            status["middleware_config"] = config
            
            # Check specific middleware availability
            middleware_modules = [
                ("app.middleware.security_headers", "security_headers"),
                ("app.middleware.rate_limiter", "rate_limiting"),
                ("app.middleware.logging_middleware", "logging"),
            ]
            
            available_middleware = 0
            for module_path, name in middleware_modules:
                try:
                    __import__(module_path)
                    status[name] = True
                    available_middleware += 1
                except ImportError:
                    status[name] = False
            
            status["middleware_count"] = available_middleware
            status["cors"] = True  # FastAPI built-in
            status["healthy"] = available_middleware >= 2  # At least 2 middleware available
            
        except Exception as e:
            logger.error(f"Middleware health check failed: {e}")
            status["error"] = str(e)
            
        return status
    
    async def check_environment(self) -> Dict[str, Any]:
        """Check environment configuration health."""
        status = {
            "healthy": False,
            "database_url": False,
            "jwt_secret": False,
            "redis_url": False,
            "environment": self.settings.ENVIRONMENT,
        }
        
        try:
            # Check required environment variables
            required_vars = [
                ("database_url", "database_url"),
                ("jwt_secret_token", "jwt_secret"),
            ]
            
            optional_vars = [
                ("redis_url", "redis_url"),
            ]
            
            missing_required = []
            available_optional = 0
            
            for var_name, status_key in required_vars:
                if hasattr(self.settings, var_name) and getattr(self.settings, var_name):
                    status[status_key] = True
                else:
                    status[status_key] = False
                    missing_required.append(var_name)
            
            for var_name, status_key in optional_vars:
                if hasattr(self.settings, var_name) and getattr(self.settings, var_name):
                    status[status_key] = True
                    available_optional += 1
                else:
                    status[status_key] = False
            
            status["healthy"] = len(missing_required) == 0
            status["missing_required"] = missing_required
            status["optional_available"] = available_optional
            
        except Exception as e:
            logger.error(f"Environment health check failed: {e}")
            status["error"] = str(e)
            
        return status
    
    async def run_all_checks(self) -> Dict[str, Any]:
        """Run all health checks and return comprehensive status."""
        overall_status = {
            "healthy": True,
            "timestamp": datetime.utcnow().isoformat(),
            "checks": {},
            "summary": {
                "total_checks": len(self.health_checks),
                "passed": 0,
                "failed": 0,
                "warnings": 0,
            }
        }
        
        logger.info("🔍 Running comprehensive system health checks...")
        
        for check_name, check_func in self.health_checks:
            try:
                logger.info(f"  🔎 Checking {check_name}...")
                check_result = await check_func()
                overall_status["checks"][check_name] = check_result
                
                if check_result.get("healthy", False):
                    overall_status["summary"]["passed"] += 1
                    logger.info(f"  ✅ {check_name}: HEALTHY")
                else:
                    overall_status["summary"]["failed"] += 1
                    overall_status["healthy"] = False
                    error = check_result.get("error", "Unknown error")
                    logger.warning(f"  ❌ {check_name}: UNHEALTHY - {error}")
                
            except Exception as e:
                logger.error(f"  💥 {check_name}: ERROR - {e}")
                overall_status["checks"][check_name] = {
                    "healthy": False,
                    "error": f"Health check failed: {e}"
                }
                overall_status["summary"]["failed"] += 1
                overall_status["healthy"] = False
        
        # Log summary
        if overall_status["healthy"]:
            logger.info("🎉 All system health checks passed!")
        else:
            logger.warning(f"⚠️ System health issues detected: {overall_status['summary']['failed']} failed checks")
        
        return overall_status
    
    async def get_quick_status(self) -> Dict[str, Any]:
        """Get a quick system status without detailed checks."""
        status = {
            "status": "unknown",
            "timestamp": datetime.utcnow().isoformat(),
            "uptime": None,
            "version": "1.0.0",
        }
        
        try:
            # Quick database check
            async for db in get_db():
                await db.execute(text("SELECT 1"))
                status["status"] = "healthy"
                break
        except Exception:
            status["status"] = "unhealthy"
        
        return status


# Global instance
system_health_checker = SystemHealthChecker()


async def get_system_health() -> Dict[str, Any]:
    """Get comprehensive system health status."""
    return await system_health_checker.run_all_checks()


async def get_quick_health() -> Dict[str, Any]:
    """Get quick health status."""
    return await system_health_checker.get_quick_status() 