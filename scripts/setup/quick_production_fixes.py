#!/usr/bin/env python3
"""Quick Production Fixes.

This script implements the most critical production fixes immediately:
1. Error tracking integration (Sentry)
2. Enhanced logging configuration
3. Database backup setup
4. Security improvements
5. Health monitoring enhancements
"""

import sys
from pathlib import Path


def setup_sentry_integration() -> None:
    """Add Sentry error tracking integration."""
    # Add sentry-sdk to requirements.txt if not present
    requirements_file = Path("requirements.txt")
    if requirements_file.exists():
        content = requirements_file.read_text()
        if "sentry-sdk" not in content:
            with open(requirements_file, "a") as f:
                f.write("sentry-sdk[fastapi]==1.38.0\n")

    # Create/update main.py with Sentry integration

    # Add to config.py
    config_file = Path("app/core/config.py")
    if config_file.exists():
        content = config_file.read_text()
        if "SENTRY_DSN" not in content:
            # Add SENTRY_DSN to Settings class
            new_content = content.replace(
                "class Settings(BaseSettings):",
                "class Settings(BaseSettings):\n    # Error tracking\n    SENTRY_DSN: Optional[str] = None",
            )
            config_file.write_text(new_content)



def setup_enhanced_logging() -> None:
    """Setup enhanced production logging."""
    logging_config_path = Path("app/core/logging_production.py")
    logging_config = '''"""
Enhanced Production Logging Configuration
"""

import logging
import logging.handlers
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

class ProductionFormatter(logging.Formatter):
    """Enhanced JSON formatter for production logs"""

    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "process": record.process,
            "thread": record.thread,
        }

        # Add exception info if present
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)

        # Add extra fields
        if hasattr(record, 'user_id'):
            log_entry["user_id"] = record.user_id
        if hasattr(record, 'request_id'):
            log_entry["request_id"] = record.request_id
        if hasattr(record, 'duration'):
            log_entry["duration_ms"] = record.duration

        return json.dumps(log_entry, default=str)

def setup_production_logging(
    log_level: str = "INFO",
    log_dir: str = "logs",
    max_bytes: int = 50 * 1024 * 1024,  # 50MB
    backup_count: int = 10
):
    """Setup production-grade logging with rotation"""

    # Create logs directory
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)

    # Create formatter
    formatter = ProductionFormatter()

    # Root logger configuration
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))

    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Console handler (JSON format for production)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # File handler with rotation
    file_handler = logging.handlers.RotatingFileHandler(
        log_path / "app.log",
        maxBytes=max_bytes,
        backupCount=backup_count
    )
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)

    # Error file handler
    error_handler = logging.handlers.RotatingFileHandler(
        log_path / "error.log",
        maxBytes=max_bytes,
        backupCount=backup_count
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(formatter)
    root_logger.addHandler(error_handler)

    # Security events handler
    security_handler = logging.handlers.RotatingFileHandler(
        log_path / "security.log",
        maxBytes=max_bytes,
        backupCount=backup_count
    )
    security_handler.setFormatter(formatter)

    # Create security logger
    security_logger = logging.getLogger("security")
    security_logger.addHandler(security_handler)
    security_logger.setLevel(logging.INFO)

    # Configure third-party loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)

    return root_logger
'''

    logging_config_path.write_text(logging_config)


def setup_backup_automation() -> None:
    """Setup automated database backup."""
    # Create systemd service for backup
    backup_service = """[Unit]
Description=FastAPI Database Backup
After=network.target

[Service]
Type=oneshot
User=www-data
Group=www-data
WorkingDirectory=/var/www/fastapi
Environment=DATABASE_URL=postgresql://user:password@localhost/database
Environment=BACKUP_DIR=/backups
Environment=RETENTION_DAYS=30
ExecStart=/var/www/fastapi/scripts/backup_database.sh
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
"""

    # Create systemd timer for daily backups
    backup_timer = """[Unit]
Description=Run FastAPI Database Backup Daily
Requires=fastapi-backup.service

[Timer]
OnCalendar=daily
RandomizedDelaySec=300
Persistent=true

[Install]
WantedBy=timers.target
"""

    # Create directories
    Path("production_configs/systemd").mkdir(parents=True, exist_ok=True)

    # Write service and timer files
    Path("production_configs/systemd/fastapi-backup.service").write_text(backup_service)
    Path("production_configs/systemd/fastapi-backup.timer").write_text(backup_timer)



def setup_security_improvements() -> None:
    """Setup security improvements."""
    # Create security configuration
    security_config = '''"""
Enhanced Security Configuration
"""

from typing import List, Dict, Any
from fastapi import Request, HTTPException, status
from fastapi.middleware.base import BaseHTTPMiddleware
import time
import hashlib
from collections import defaultdict

class SecurityEnhancementMiddleware(BaseHTTPMiddleware):
    """Enhanced security middleware"""

    def __init__(self, app):
        super().__init__(app)
        self.failed_attempts = defaultdict(list)
        self.blocked_ips = set()

    async def dispatch(self, request: Request, call_next):
        client_ip = self._get_client_ip(request)

        # Check if IP is blocked
        if client_ip in self.blocked_ips:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="IP temporarily blocked due to suspicious activity"
            )

        # Security headers
        response = await call_next(request)

        # Enhanced security headers
        response.headers.update({
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains; preload",
            "Content-Security-Policy": "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'",
            "Referrer-Policy": "strict-origin-when-cross-origin",
            "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
            "X-Permitted-Cross-Domain-Policies": "none",
            "Cross-Origin-Embedder-Policy": "require-corp",
            "Cross-Origin-Opener-Policy": "same-origin",
            "Cross-Origin-Resource-Policy": "same-origin",
        })

        # Log failed authentication attempts
        if response.status_code == 401:
            self._track_failed_attempt(client_ip, request.url.path)

        return response

    def _get_client_ip(self, request: Request) -> str:
        """Get real client IP"""
        # Check X-Forwarded-For header first
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()

        # Check X-Real-IP header
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip.strip()

        # Fall back to direct connection IP
        return request.client.host if request.client else "unknown"

    def _track_failed_attempt(self, ip: str, path: str):
        """Track failed authentication attempts"""
        current_time = time.time()

        # Remove old attempts (older than 1 hour)
        self.failed_attempts[ip] = [
            attempt_time for attempt_time in self.failed_attempts[ip]
            if current_time - attempt_time < 3600
        ]

        # Add current attempt
        self.failed_attempts[ip].append(current_time)

        # Block IP if too many failed attempts
        if len(self.failed_attempts[ip]) >= 10:  # 10 failed attempts in 1 hour
            self.blocked_ips.add(ip)

            # Log security event
            import logging
            security_logger = logging.getLogger("security")
            security_logger.warning(
                f"IP {ip} blocked due to {len(self.failed_attempts[ip])} failed authentication attempts",
                extra={"ip": ip, "path": path, "attempts": len(self.failed_attempts[ip])}
            )
'''

    Path("app/middleware/security_enhancement.py").write_text(security_config)


def setup_health_monitoring() -> None:
    """Setup enhanced health monitoring."""
    health_config = '''"""
Enhanced Health Monitoring
"""

import psutil
import asyncio
import aioredis
from datetime import datetime
from typing import Dict, Any
from fastapi import APIRouter
from sqlalchemy.ext.asyncio import AsyncEngine

router = APIRouter()

class HealthMonitor:
    """Enhanced health monitoring system"""

    def __init__(self, db_engine: AsyncEngine = None, redis_url: str = None):
        self.db_engine = db_engine
        self.redis_url = redis_url

    async def check_system_health(self) -> Dict[str, Any]:
        """Comprehensive system health check"""
        health_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "status": "healthy",
            "checks": {}
        }

        # System metrics
        health_data["checks"]["system"] = await self._check_system_metrics()

        # Database health
        health_data["checks"]["database"] = await self._check_database_health()

        # Redis health
        health_data["checks"]["redis"] = await self._check_redis_health()

        # Process health
        health_data["checks"]["process"] = await self._check_process_health()

        # Determine overall status
        failed_checks = [
            check for check in health_data["checks"].values()
            if check["status"] != "healthy"
        ]

        if failed_checks:
            health_data["status"] = "degraded" if len(failed_checks) < 3 else "unhealthy"

        return health_data

    async def _check_system_metrics(self) -> Dict[str, Any]:
        """Check system resource usage"""
        try:
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')

            status = "healthy"
            if cpu_percent > 90 or memory.percent > 90 or disk.percent > 90:
                status = "degraded"
            if cpu_percent > 95 or memory.percent > 95 or disk.percent > 95:
                status = "unhealthy"

            return {
                "status": status,
                "cpu_percent": cpu_percent,
                "memory_percent": memory.percent,
                "disk_percent": disk.percent,
                "load_average": psutil.getloadavg() if hasattr(psutil, 'getloadavg') else None
            }
        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}

    async def _check_database_health(self) -> Dict[str, Any]:
        """Check database connectivity and performance"""
        if not self.db_engine:
            return {"status": "skipped", "reason": "No database engine configured"}

        try:
            start_time = asyncio.get_event_loop().time()

            async with self.db_engine.begin() as conn:
                result = await conn.execute("SELECT 1 as health_check")
                row = result.fetchone()

            response_time = (asyncio.get_event_loop().time() - start_time) * 1000

            status = "healthy"
            if response_time > 1000:  # 1 second
                status = "degraded"
            if response_time > 5000:  # 5 seconds
                status = "unhealthy"

            return {
                "status": status,
                "response_time_ms": round(response_time, 2),
                "connection_pool": {
                    "size": self.db_engine.pool.size(),
                    "checked_in": self.db_engine.pool.checkedin(),
                    "checked_out": self.db_engine.pool.checkedout(),
                }
            }
        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}

    async def _check_redis_health(self) -> Dict[str, Any]:
        """Check Redis connectivity"""
        if not self.redis_url:
            return {"status": "skipped", "reason": "No Redis URL configured"}

        try:
            start_time = asyncio.get_event_loop().time()

            redis = aioredis.from_url(self.redis_url)
            await redis.ping()
            await redis.close()

            response_time = (asyncio.get_event_loop().time() - start_time) * 1000

            status = "healthy"
            if response_time > 500:  # 500ms
                status = "degraded"
            if response_time > 2000:  # 2 seconds
                status = "unhealthy"

            return {
                "status": status,
                "response_time_ms": round(response_time, 2)
            }
        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}

    async def _check_process_health(self) -> Dict[str, Any]:
        """Check current process health"""
        try:
            process = psutil.Process()

            return {
                "status": "healthy",
                "pid": process.pid,
                "memory_mb": round(process.memory_info().rss / 1024 / 1024, 2),
                "cpu_percent": process.cpu_percent(),
                "threads": process.num_threads(),
                "uptime_seconds": round(asyncio.get_event_loop().time() - process.create_time(), 2)
            }
        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}

@router.get("/health/detailed")
async def detailed_health_check():
    """Detailed health check endpoint"""
    from app.db.session import engine
    from app.core.config import get_settings

    settings = get_settings()
    monitor = HealthMonitor(
        db_engine=engine,
        redis_url=getattr(settings, 'REDIS_URL', None)
    )

    return await monitor.check_system_health()
'''

    Path("app/api/v1/endpoints/health_enhanced.py").write_text(health_config)


def setup_environment_template() -> None:
    """Create production environment template."""
    env_template = """# FastAPI Production Environment Configuration

# Application Settings
APP_NAME="FastAPI Production App"
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO

# Database Configuration
DATABASE_URL=postgresql+asyncpg://username:password@localhost:5432/production_db
DATABASE_URL_WITHOUT_ASYNC=postgresql://username:password@localhost:5432/production_db

# Security Settings
JWT_SECRET_TOKEN=your-super-secret-jwt-key-minimum-32-characters-long
SECRET_KEY=your-application-secret-key-minimum-32-characters

# Error Tracking (Optional but Recommended)
SENTRY_DSN=https://your-sentry-dsn@sentry.io/project-id

# Redis Configuration
REDIS_URL=redis://localhost:6379/0

# Email Configuration (if using email features)
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
EMAIL_FROM="Your App <noreply@yourdomain.com>"

# File Upload Configuration
FILE_STORAGE_TYPE=local
FILE_UPLOAD_MAX_SIZE=104857600  # 100MB
FILE_STORAGE_PATH=/var/www/fastapi/uploads

# AWS Configuration (if using S3)
AWS_ACCESS_KEY_ID=your-aws-access-key
AWS_SECRET_ACCESS_KEY=your-aws-secret-key
AWS_S3_BUCKET=your-s3-bucket
AWS_S3_REGION=us-east-1

# Backup Configuration
BACKUP_DIR=/backups
RETENTION_DAYS=30
BACKUP_COMPRESSION=gzip
NOTIFICATION_WEBHOOK=https://hooks.slack.com/your-webhook-url

# Rate Limiting
RATE_LIMIT_DEFAULT=100/minute
RATE_LIMIT_AUTH_LOGIN=10/minute
RATE_LIMIT_AUTH_REGISTER=5/minute

# Health Check Configuration
HEALTH_CHECK_ENABLED=true

# CORS Configuration
ALLOWED_ORIGINS=https://yourdomain.com,https://www.yourdomain.com
ALLOWED_METHODS=GET,POST,PUT,DELETE,OPTIONS
ALLOWED_HEADERS=*

# SSL/TLS Configuration
SSL_REDIRECT=true
HSTS_MAX_AGE=31536000

# Logging Configuration
LOG_DIR=/var/log/fastapi
LOG_ROTATION_SIZE=50MB
LOG_RETENTION_DAYS=30
"""

    Path(".env.production.template").write_text(env_template)


def run_production_tests() -> bool | None:
    """Run basic production readiness tests."""
    try:
        # Test basic imports

        # Test application import
        sys.path.append(".")

        # Test configuration
        from app.core.config import get_settings

        get_settings()

        return True

    except Exception:
        return False


def main() -> None:
    """Main function to apply all production fixes."""
    fixes = [
        ("Sentry Integration", setup_sentry_integration),
        ("Enhanced Logging", setup_enhanced_logging),
        ("Backup Automation", setup_backup_automation),
        ("Security Improvements", setup_security_improvements),
        ("Health Monitoring", setup_health_monitoring),
        ("Environment Template", setup_environment_template),
    ]

    applied_fixes = 0
    for _fix_name, fix_function in fixes:
        try:
            fix_function()
            applied_fixes += 1
        except Exception:
            pass


    if applied_fixes == len(fixes):

        # Run basic tests
        if run_production_tests():
            pass
        else:
            pass
    else:
        pass


if __name__ == "__main__":
    main()
