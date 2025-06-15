#!/usr/bin/env python3
"""
Production Readiness Checker for FastAPI PostgreSQL Boilerplate
Identifies memory leaks, errors, and production issues
"""

import asyncio
import gc
import logging
import os
import psutil
import sys
import time
import tracemalloc
from pathlib import Path
from typing import Any, Dict, List, Optional

import sqlalchemy
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ProductionReadinessChecker:
    """Comprehensive production readiness checker"""
    
    def __init__(self):
        self.issues = []
        self.warnings = []
        self.recommendations = []
        self.start_time = time.time()
        
    def add_issue(self, category: str, severity: str, description: str, fix: str = None):
        """Add an issue to the report"""
        self.issues.append({
            "category": category,
            "severity": severity,
            "description": description,
            "fix": fix or "Manual investigation required",
            "timestamp": time.time()
        })
        
    def add_warning(self, category: str, description: str, recommendation: str = None):
        """Add a warning to the report"""
        self.warnings.append({
            "category": category,
            "description": description,
            "recommendation": recommendation or "Review recommended",
            "timestamp": time.time()
        })
        
    def add_recommendation(self, category: str, description: str, priority: str = "medium"):
        """Add a recommendation"""
        self.recommendations.append({
            "category": category,
            "description": description,
            "priority": priority,
            "timestamp": time.time()
        })

    async def check_memory_leaks(self):
        """Check for potential memory leaks"""
        logger.info("🔍 Checking for memory leaks...")
        
        # Start memory tracing
        tracemalloc.start()
        
        try:
            # Check database connection pooling
            await self._check_database_connections()
            
            # Check Redis connections
            await self._check_redis_connections()
            
            # Check WebSocket connections
            await self._check_websocket_connections()
            
            # Check task queue memory usage
            await self._check_task_queue_memory()
            
            # Check plugin memory usage
            await self._check_plugin_memory()
            
        except Exception as e:
            self.add_issue(
                "memory_check", 
                "critical", 
                f"Memory leak check failed: {e}",
                "Review memory checking implementation"
            )
        finally:
            # Stop memory tracing
            tracemalloc.stop()

    async def _check_database_connections(self):
        """Check database connection management"""
        try:
            from app.db.session import get_db, engine
            
            # Test async context manager
            async for session in get_db():
                # Check if session is properly configured
                if not isinstance(session, AsyncSession):
                    self.add_issue(
                        "database",
                        "critical",
                        "Database session is not AsyncSession",
                        "Fix session configuration in app/db/session.py"
                    )
                
                # Check session lifecycle
                if hasattr(session, '_connection') and session._connection:
                    self.add_warning(
                        "database",
                        "Session has active connection during test",
                        "Monitor connection lifecycle"
                    )
                break
            
            # Check connection pool settings
            if hasattr(engine, 'pool'):
                pool = engine.pool
                self.add_recommendation(
                    "database",
                    f"Connection pool size: {getattr(pool, 'size', 'unknown')}",
                    "low"
                )
                
        except Exception as e:
            self.add_issue(
                "database",
                "high",
                f"Database connection check failed: {e}",
                "Review database configuration"
            )

    async def _check_redis_connections(self):
        """Check Redis connection management"""
        try:
            from app.db.session import get_redis
            
            # Test Redis connection cleanup
            async for redis_client in get_redis():
                if redis_client is None:
                    self.add_warning(
                        "redis",
                        "Redis client is None - fallback mode",
                        "Ensure Redis is running for production"
                    )
                else:
                    # Check Redis connection health
                    try:
                        await redis_client.ping()
                        self.add_recommendation(
                            "redis",
                            "Redis connection healthy",
                            "low"
                        )
                    except Exception as e:
                        self.add_issue(
                            "redis",
                            "medium",
                            f"Redis ping failed: {e}",
                            "Check Redis server status"
                        )
                break
                
        except Exception as e:
            self.add_issue(
                "redis",
                "medium",
                f"Redis connection check failed: {e}",
                "Review Redis configuration"
            )

    async def _check_websocket_connections(self):
        """Check WebSocket connection management"""
        try:
            # Check if WebSocket manager exists and is properly configured
            websocket_files = [
                "app/websocket/websocket_manager.py",
                "app/utils/websocket_manager.py"
            ]
            
            for ws_file in websocket_files:
                if Path(ws_file).exists():
                    self.add_recommendation(
                        "websocket",
                        f"WebSocket manager found: {ws_file}",
                        "low"
                    )
                    
                    # Check for cleanup functions
                    with open(ws_file, 'r') as f:
                        content = f.read()
                        if 'cleanup' in content and 'shutdown' in content:
                            self.add_recommendation(
                                "websocket",
                                "WebSocket cleanup functions found",
                                "low"
                            )
                        else:
                            self.add_warning(
                                "websocket",
                                "WebSocket cleanup functions may be missing",
                                "Ensure proper WebSocket cleanup on shutdown"
                            )
                    break
            else:
                self.add_recommendation(
                    "websocket",
                    "No WebSocket manager found - not using WebSockets",
                    "low"
                )
                
        except Exception as e:
            self.add_warning(
                "websocket",
                f"WebSocket check failed: {e}",
                "Manual review recommended"
            )

    async def _check_task_queue_memory(self):
        """Check task queue memory usage"""
        try:
            # Check if task queue is properly configured
            task_queue_files = [
                "app/utils/task_queue.py",
                "app/utils/procrastinate_manager.py"
            ]
            
            for tq_file in task_queue_files:
                if Path(tq_file).exists():
                    with open(tq_file, 'r') as f:
                        content = f.read()
                        
                        # Check for memory cleanup
                        if 'cleanup' in content or 'shutdown' in content:
                            self.add_recommendation(
                                "task_queue",
                                f"Task queue cleanup found in {tq_file}",
                                "low"
                            )
                        else:
                            self.add_warning(
                                "task_queue",
                                f"No cleanup found in {tq_file}",
                                "Ensure proper task queue cleanup"
                            )
                            
                        # Check for queue size limits
                        if 'maxsize' in content or 'max_size' in content:
                            self.add_recommendation(
                                "task_queue",
                                "Queue size limits found",
                                "low"
                            )
                        else:
                            self.add_warning(
                                "task_queue",
                                "No queue size limits found",
                                "Consider adding queue size limits to prevent memory issues"
                            )
                            
        except Exception as e:
            self.add_warning(
                "task_queue",
                f"Task queue check failed: {e}",
                "Manual review recommended"
            )

    async def _check_plugin_memory(self):
        """Check plugin memory usage"""
        try:
            plugin_dir = Path("app/plugins")
            if plugin_dir.exists():
                plugin_count = len([p for p in plugin_dir.iterdir() if p.is_dir() and not p.name.startswith('.')])
                
                if plugin_count > 10:
                    self.add_warning(
                        "plugins",
                        f"Large number of plugins detected: {plugin_count}",
                        "Monitor memory usage with many plugins"
                    )
                else:
                    self.add_recommendation(
                        "plugins",
                        f"Plugin count reasonable: {plugin_count}",
                        "low"
                    )
                    
                # Check for plugin cleanup
                for plugin_path in plugin_dir.iterdir():
                    if plugin_path.is_dir() and not plugin_path.name.startswith('.'):
                        init_file = plugin_path / "__init__.py"
                        if init_file.exists():
                            with open(init_file, 'r') as f:
                                content = f.read()
                                if 'cleanup' not in content and 'shutdown' not in content:
                                    self.add_warning(
                                        "plugins",
                                        f"Plugin {plugin_path.name} may lack cleanup",
                                        "Ensure plugins have proper cleanup methods"
                                    )
                                    
        except Exception as e:
            self.add_warning(
                "plugins",
                f"Plugin memory check failed: {e}",
                "Manual review recommended"
            )

    async def check_error_handling(self):
        """Check error handling robustness"""
        logger.info("🔍 Checking error handling...")
        
        try:
            # Check exception handlers
            await self._check_exception_handlers()
            
            # Check logging configuration
            await self._check_logging_config()
            
            # Check error aggregation
            await self._check_error_aggregation()
            
        except Exception as e:
            self.add_issue(
                "error_handling",
                "high",
                f"Error handling check failed: {e}",
                "Review error handling implementation"
            )

    async def _check_exception_handlers(self):
        """Check exception handler configuration"""
        try:
            exception_handler_file = "app/core/exception_handlers.py"
            if Path(exception_handler_file).exists():
                with open(exception_handler_file, 'r') as f:
                    content = f.read()
                    
                    # Check for comprehensive exception handling
                    required_handlers = [
                        'AppException',
                        'HTTPException', 
                        'SQLAlchemyError',
                        'generic_exception_handler'
                    ]
                    
                    for handler in required_handlers:
                        if handler in content:
                            self.add_recommendation(
                                "error_handling",
                                f"Exception handler found: {handler}",
                                "low"
                            )
                        else:
                            self.add_warning(
                                "error_handling",
                                f"Missing exception handler: {handler}",
                                f"Add {handler} to exception handlers"
                            )
            else:
                self.add_issue(
                    "error_handling",
                    "high",
                    "Exception handlers file not found",
                    "Create app/core/exception_handlers.py"
                )
                
        except Exception as e:
            self.add_warning(
                "error_handling",
                f"Exception handler check failed: {e}",
                "Manual review recommended"
            )

    async def _check_logging_config(self):
        """Check logging configuration"""
        try:
            logging_file = "app/core/logging.py"
            if Path(logging_file).exists():
                self.add_recommendation(
                    "logging",
                    "Logging configuration found",
                    "low"
                )
                
                with open(logging_file, 'r') as f:
                    content = f.read()
                    
                    # Check for structured logging
                    if 'json' in content.lower() or 'structured' in content.lower():
                        self.add_recommendation(
                            "logging",
                            "Structured logging detected",
                            "low"
                        )
                    else:
                        self.add_warning(
                            "logging",
                            "No structured logging detected",
                            "Consider using structured logging for production"
                        )
                        
                    # Check for log rotation
                    if 'rotate' in content.lower() or 'rotation' in content.lower():
                        self.add_recommendation(
                            "logging",
                            "Log rotation configured",
                            "low"
                        )
                    else:
                        self.add_warning(
                            "logging",
                            "No log rotation detected",
                            "Configure log rotation to prevent disk space issues"
                        )
            else:
                self.add_warning(
                    "logging",
                    "No logging configuration file found",
                    "Create comprehensive logging configuration"
                )
                
        except Exception as e:
            self.add_warning(
                "logging",
                f"Logging check failed: {e}",
                "Manual review recommended"
            )

    async def _check_error_aggregation(self):
        """Check error aggregation system"""
        try:
            error_agg_file = "app/core/error_aggregator.py"
            if Path(error_agg_file).exists():
                self.add_recommendation(
                    "error_handling",
                    "Error aggregation system found",
                    "low"
                )
            else:
                self.add_warning(
                    "error_handling",
                    "No error aggregation system found",
                    "Consider implementing error aggregation for production monitoring"
                )
                
        except Exception as e:
            self.add_warning(
                "error_handling",
                f"Error aggregation check failed: {e}",
                "Manual review recommended"
            )

    async def check_security_issues(self):
        """Check for security vulnerabilities"""
        logger.info("🔍 Checking security issues...")
        
        try:
            # Check authentication system
            await self._check_authentication()
            
            # Check input validation
            await self._check_input_validation()
            
            # Check rate limiting
            await self._check_rate_limiting()
            
            # Check CORS configuration
            await self._check_cors_config()
            
        except Exception as e:
            self.add_issue(
                "security",
                "critical",
                f"Security check failed: {e}",
                "Review security implementation"
            )

    async def _check_authentication(self):
        """Check authentication system"""
        try:
            auth_files = [
                "app/core/security.py",
                "app/api/v1/endpoints/auth.py",
                "app/services/auth_service.py"
            ]
            
            auth_found = False
            for auth_file in auth_files:
                if Path(auth_file).exists():
                    auth_found = True
                    with open(auth_file, 'r') as f:
                        content = f.read()
                        
                        # Check for JWT implementation
                        if 'jwt' in content.lower() or 'token' in content.lower():
                            self.add_recommendation(
                                "security",
                                f"JWT authentication found in {auth_file}",
                                "medium"
                            )
                        
                        # Check for password hashing
                        if 'bcrypt' in content or 'hash' in content:
                            self.add_recommendation(
                                "security",
                                "Password hashing found",
                                "medium"
                            )
                        else:
                            self.add_issue(
                                "security",
                                "critical",
                                "No password hashing detected",
                                "Implement secure password hashing"
                            )
            
            if not auth_found:
                self.add_issue(
                    "security",
                    "critical",
                    "No authentication system found",
                    "Implement authentication system"
                )
                
        except Exception as e:
            self.add_warning(
                "security",
                f"Authentication check failed: {e}",
                "Manual review recommended"
            )

    async def _check_input_validation(self):
        """Check input validation"""
        try:
            # Check for Pydantic models
            schema_files = list(Path("app").rglob("schemas.py"))
            if schema_files:
                self.add_recommendation(
                    "security",
                    f"Found {len(schema_files)} schema files",
                    "low"
                )
                
                # Check for validation in schemas
                for schema_file in schema_files[:3]:  # Check first 3
                    with open(schema_file, 'r') as f:
                        content = f.read()
                        if 'validator' in content or 'Field' in content:
                            self.add_recommendation(
                                "security",
                                f"Input validation found in {schema_file.name}",
                                "medium"
                            )
            else:
                self.add_warning(
                    "security",
                    "No schema files found",
                    "Implement input validation with Pydantic schemas"
                )
                
        except Exception as e:
            self.add_warning(
                "security",
                f"Input validation check failed: {e}",
                "Manual review recommended"
            )

    async def _check_rate_limiting(self):
        """Check rate limiting configuration"""
        try:
            rate_limit_file = "app/core/rate_limiting.py"
            if Path(rate_limit_file).exists():
                self.add_recommendation(
                    "security",
                    "Rate limiting system found",
                    "medium"
                )
            else:
                self.add_warning(
                    "security",
                    "No rate limiting system found",
                    "Implement rate limiting to prevent abuse"
                )
                
        except Exception as e:
            self.add_warning(
                "security",
                f"Rate limiting check failed: {e}",
                "Manual review recommended"
            )

    async def _check_cors_config(self):
        """Check CORS configuration"""
        try:
            main_file = "app/main.py"
            if Path(main_file).exists():
                with open(main_file, 'r') as f:
                    content = f.read()
                    
                    if 'cors' in content.lower():
                        if 'allow_origins=["*"]' in content:
                            self.add_issue(
                                "security",
                                "high",
                                "CORS allows all origins",
                                "Restrict CORS origins for production"
                            )
                        else:
                            self.add_recommendation(
                                "security",
                                "CORS configuration found",
                                "medium"
                            )
                    else:
                        self.add_warning(
                            "security",
                            "No CORS configuration found",
                            "Configure CORS for frontend access"
                        )
            
        except Exception as e:
            self.add_warning(
                "security",
                f"CORS check failed: {e}",
                "Manual review recommended"
            )

    async def check_performance_issues(self):
        """Check for performance issues"""
        logger.info("🔍 Checking performance issues...")
        
        try:
            # Check database query optimization
            await self._check_database_performance()
            
            # Check caching implementation
            await self._check_caching()
            
            # Check async implementation
            await self._check_async_implementation()
            
        except Exception as e:
            self.add_issue(
                "performance",
                "medium",
                f"Performance check failed: {e}",
                "Review performance implementation"
            )

    async def _check_database_performance(self):
        """Check database performance"""
        try:
            # Check for indexes in models
            model_files = list(Path("app").rglob("models.py"))
            
            for model_file in model_files:
                with open(model_file, 'r') as f:
                    content = f.read()
                    
                    if '__table_args__' in content and 'Index' in content:
                        self.add_recommendation(
                            "performance",
                            f"Database indexes found in {model_file.name}",
                            "medium"
                        )
                    elif 'class ' in content and 'Base' in content:
                        self.add_warning(
                            "performance",
                            f"No indexes found in {model_file.name}",
                            "Consider adding database indexes for performance"
                        )
            
            # Check for connection pooling
            session_file = "app/db/session.py"
            if Path(session_file).exists():
                with open(session_file, 'r') as f:
                    content = f.read()
                    
                    if 'pool' in content.lower() or 'sessionmaker' in content:
                        self.add_recommendation(
                            "performance",
                            "Database connection pooling configured",
                            "medium"
                        )
                        
        except Exception as e:
            self.add_warning(
                "performance",
                f"Database performance check failed: {e}",
                "Manual review recommended"
            )

    async def _check_caching(self):
        """Check caching implementation"""
        try:
            cache_files = [
                "app/plugins/cache_plugin.py",
                "app/core/cache.py",
                "app/core/redis_manager.py"
            ]
            
            cache_found = False
            for cache_file in cache_files:
                if Path(cache_file).exists():
                    cache_found = True
                    self.add_recommendation(
                        "performance",
                        f"Caching system found: {cache_file}",
                        "medium"
                    )
                    break
            
            if not cache_found:
                self.add_warning(
                    "performance",
                    "No caching system found",
                    "Implement caching for improved performance"
                )
                
        except Exception as e:
            self.add_warning(
                "performance",
                f"Caching check failed: {e}",
                "Manual review recommended"
            )

    async def _check_async_implementation(self):
        """Check async implementation"""
        try:
            # Check main app file
            main_file = "app/main.py"
            if Path(main_file).exists():
                with open(main_file, 'r') as f:
                    content = f.read()
                    
                    if 'async def' in content:
                        self.add_recommendation(
                            "performance",
                            "Async functions found in main app",
                            "medium"
                        )
                    
                    if 'asyncio' in content:
                        self.add_recommendation(
                            "performance",
                            "Asyncio usage detected",
                            "medium"
                        )
            
            # Check service files for async patterns
            service_files = list(Path("app").rglob("services.py"))
            async_services = 0
            
            for service_file in service_files:
                with open(service_file, 'r') as f:
                    content = f.read()
                    if 'async def' in content:
                        async_services += 1
            
            if async_services > 0:
                self.add_recommendation(
                    "performance",
                    f"Async services found: {async_services}",
                    "medium"
                )
            else:
                self.add_warning(
                    "performance",
                    "No async services found",
                    "Consider using async patterns for I/O operations"
                )
                
        except Exception as e:
            self.add_warning(
                "performance",
                f"Async implementation check failed: {e}",
                "Manual review recommended"
            )

    def check_system_resources(self):
        """Check current system resource usage"""
        logger.info("🔍 Checking system resources...")
        
        try:
            # Get current process info
            process = psutil.Process()
            
            # Memory usage
            memory_info = process.memory_info()
            memory_mb = memory_info.rss / 1024 / 1024
            
            if memory_mb > 1000:  # > 1GB
                self.add_warning(
                    "resources",
                    f"High memory usage: {memory_mb:.1f}MB",
                    "Monitor memory usage and optimize if needed"
                )
            else:
                self.add_recommendation(
                    "resources",
                    f"Memory usage normal: {memory_mb:.1f}MB",
                    "low"
                )
            
            # CPU usage
            cpu_percent = process.cpu_percent()
            if cpu_percent > 80:
                self.add_warning(
                    "resources",
                    f"High CPU usage: {cpu_percent}%",
                    "Monitor CPU usage and optimize if needed"
                )
            
            # Open files
            open_files = len(process.open_files())
            if open_files > 100:
                self.add_warning(
                    "resources",
                    f"Many open files: {open_files}",
                    "Check for file handle leaks"
                )
            
            # Threads
            num_threads = process.num_threads()
            if num_threads > 50:
                self.add_warning(
                    "resources",
                    f"Many threads: {num_threads}",
                    "Monitor thread usage for potential issues"
                )
            
        except Exception as e:
            self.add_warning(
                "resources",
                f"System resource check failed: {e}",
                "Manual system monitoring recommended"
            )

    def check_configuration(self):
        """Check configuration for production readiness"""
        logger.info("🔍 Checking configuration...")
        
        try:
            # Check environment configuration
            env_file = ".env"
            if Path(env_file).exists():
                self.add_recommendation(
                    "configuration",
                    "Environment file found",
                    "medium"
                )
                
                with open(env_file, 'r') as f:
                    content = f.read()
                    
                    # Check for production settings
                    if 'DEBUG=False' in content or 'ENVIRONMENT=production' in content:
                        self.add_recommendation(
                            "configuration",
                            "Production environment detected",
                            "high"
                        )
                    else:
                        self.add_warning(
                            "configuration",
                            "Development environment detected",
                            "Set production environment variables"
                        )
                    
                    # Check for secrets
                    if 'SECRET' in content or 'PASSWORD' in content:
                        self.add_warning(
                            "configuration",
                            "Secrets found in .env file",
                            "Ensure .env is not committed to version control"
                        )
            else:
                self.add_warning(
                    "configuration",
                    "No .env file found",
                    "Create environment configuration file"
                )
            
            # Check requirements.txt
            req_file = "requirements.txt"
            if Path(req_file).exists():
                self.add_recommendation(
                    "configuration",
                    "Requirements file found",
                    "medium"
                )
                
                with open(req_file, 'r') as f:
                    content = f.read()
                    
                    # Check for pinned versions
                    lines = [line.strip() for line in content.split('\n') if line.strip() and not line.startswith('#')]
                    unpinned = [line for line in lines if '==' not in line and line]
                    
                    if unpinned:
                        self.add_warning(
                            "configuration",
                            f"Unpinned dependencies found: {len(unpinned)}",
                            "Pin all dependency versions for production"
                        )
                    else:
                        self.add_recommendation(
                            "configuration",
                            "All dependencies pinned",
                            "high"
                        )
            else:
                self.add_issue(
                    "configuration",
                    "medium",
                    "No requirements.txt found",
                    "Create requirements.txt with pinned versions"
                )
            
            # Check Docker configuration
            docker_files = ["Dockerfile", "docker-compose.yml", "docker-compose.prod.yml"]
            docker_found = any(Path(f).exists() for f in docker_files)
            
            if docker_found:
                self.add_recommendation(
                    "configuration",
                    "Docker configuration found",
                    "medium"
                )
            else:
                self.add_warning(
                    "configuration",
                    "No Docker configuration found",
                    "Consider Docker for consistent deployments"
                )
                
        except Exception as e:
            self.add_warning(
                "configuration",
                f"Configuration check failed: {e}",
                "Manual configuration review recommended"
            )

    def generate_report(self) -> Dict[str, Any]:
        """Generate comprehensive report"""
        duration = time.time() - self.start_time
        
        # Categorize issues by severity
        critical_issues = [i for i in self.issues if i['severity'] == 'critical']
        high_issues = [i for i in self.issues if i['severity'] == 'high']
        medium_issues = [i for i in self.issues if i['severity'] == 'medium']
        
        # Calculate scores
        total_checks = len(self.issues) + len(self.warnings) + len(self.recommendations)
        critical_score = max(0, 100 - (len(critical_issues) * 25))
        high_score = max(0, 100 - (len(high_issues) * 10))
        medium_score = max(0, 100 - (len(medium_issues) * 5))
        warning_score = max(0, 100 - (len(self.warnings) * 2))
        
        overall_score = (critical_score + high_score + medium_score + warning_score) / 4
        
        return {
            "summary": {
                "overall_score": round(overall_score, 1),
                "duration_seconds": round(duration, 2),
                "total_checks": total_checks,
                "critical_issues": len(critical_issues),
                "high_issues": len(high_issues),
                "medium_issues": len(medium_issues),
                "warnings": len(self.warnings),
                "recommendations": len(self.recommendations),
                "status": "READY" if len(critical_issues) == 0 and len(high_issues) == 0 else "NEEDS_ATTENTION"
            },
            "issues": {
                "critical": critical_issues,
                "high": high_issues,
                "medium": medium_issues
            },
            "warnings": self.warnings,
            "recommendations": self.recommendations,
            "next_steps": self._generate_next_steps(critical_issues, high_issues, medium_issues)
        }

    def _generate_next_steps(self, critical_issues, high_issues, medium_issues) -> List[str]:
        """Generate next steps based on issues found"""
        next_steps = []
        
        if critical_issues:
            next_steps.append("🚨 CRITICAL: Fix all critical issues immediately before production deployment")
            for issue in critical_issues[:3]:  # Top 3 critical
                next_steps.append(f"   - {issue['description']}: {issue['fix']}")
        
        if high_issues:
            next_steps.append("⚠️ HIGH: Address high priority issues before production")
            for issue in high_issues[:2]:  # Top 2 high
                next_steps.append(f"   - {issue['description']}: {issue['fix']}")
        
        if medium_issues:
            next_steps.append("📋 MEDIUM: Plan to address medium priority issues")
            if len(medium_issues) > 5:
                next_steps.append(f"   - {len(medium_issues)} medium priority issues found")
        
        if not critical_issues and not high_issues:
            next_steps.append("✅ Good! No critical or high priority issues found")
            next_steps.append("🔍 Review warnings and recommendations for optimization")
        
        next_steps.append("📊 Run this check regularly to maintain production readiness")
        
        return next_steps

    def print_report(self, report: Dict[str, Any]):
        """Print formatted report"""
        print("\n" + "="*80)
        print("🔍 PRODUCTION READINESS REPORT")
        print("="*80)
        
        summary = report['summary']
        print(f"\n📊 OVERALL SCORE: {summary['overall_score']}/100")
        print(f"⏱️  Duration: {summary['duration_seconds']}s")
        print(f"🔍 Total Checks: {summary['total_checks']}")
        print(f"📈 Status: {summary['status']}")
        
        print(f"\n🚨 Critical Issues: {summary['critical_issues']}")
        print(f"⚠️  High Issues: {summary['high_issues']}")
        print(f"📋 Medium Issues: {summary['medium_issues']}")
        print(f"⚡ Warnings: {summary['warnings']}")
        print(f"💡 Recommendations: {summary['recommendations']}")
        
        # Print critical issues
        if report['issues']['critical']:
            print("\n🚨 CRITICAL ISSUES:")
            for issue in report['issues']['critical']:
                print(f"   ❌ [{issue['category']}] {issue['description']}")
                print(f"      Fix: {issue['fix']}")
        
        # Print high issues
        if report['issues']['high']:
            print("\n⚠️ HIGH PRIORITY ISSUES:")
            for issue in report['issues']['high']:
                print(f"   🔸 [{issue['category']}] {issue['description']}")
                print(f"      Fix: {issue['fix']}")
        
        # Print next steps
        print("\n📋 NEXT STEPS:")
        for step in report['next_steps']:
            print(f"   {step}")
        
        print("\n" + "="*80)
        print("💡 TIP: Fix critical and high issues before production deployment")
        print("="*80)

async def main():
    """Main function to run all checks"""
    print("🚀 Starting Production Readiness Check...")
    
    checker = ProductionReadinessChecker()
    
    try:
        # Run all checks
        await checker.check_memory_leaks()
        await checker.check_error_handling()
        await checker.check_security_issues()
        await checker.check_performance_issues()
        checker.check_system_resources()
        checker.check_configuration()
        
        # Generate and print report
        report = checker.generate_report()
        checker.print_report(report)
        
        # Save report to file
        import json
        with open("production_readiness_report.json", "w") as f:
            json.dump(report, f, indent=2, default=str)
        
        print(f"\n📄 Detailed report saved to: production_readiness_report.json")
        
        # Return exit code based on critical issues
        if report['summary']['critical_issues'] > 0:
            print("\n❌ FAILED: Critical issues found - not ready for production")
            sys.exit(1)
        elif report['summary']['high_issues'] > 0:
            print("\n⚠️ WARNING: High priority issues found - review before production")
            sys.exit(2)
        else:
            print("\n✅ PASSED: No critical issues found - ready for production")
            sys.exit(0)
            
    except Exception as e:
        print(f"\n❌ ERROR: Production readiness check failed: {e}")
        print(f"Traceback: {e.__class__.__name__}")
        sys.exit(3)

if __name__ == "__main__":
    asyncio.run(main()) 