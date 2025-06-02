"""
Structured Logging System for FastAPI
- JSON formatted logs for easy parsing
- Correlation ID tracking
- Performance monitoring
- Security event logging
"""
import json
import time
import uuid
import logging
from typing import Dict, Any, Optional
from datetime import datetime
from contextvars import ContextVar
from pathlib import Path

# Context variables for request tracking
correlation_id: ContextVar[Optional[str]] = ContextVar('correlation_id', default=None)
user_id: ContextVar[Optional[str]] = ContextVar('user_id', default=None)

class StructuredFormatter(logging.Formatter):
    """Custom JSON formatter for structured logging"""
    
    def format(self, record: logging.LogRecord) -> str:
        # Base log structure
        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # Add correlation ID if available
        if correlation_id.get():
            log_entry["correlation_id"] = correlation_id.get()
            
        # Add user ID if available
        if user_id.get():
            log_entry["user_id"] = user_id.get()
        
        # Add exception info if present
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
        
        # Add extra fields from record
        extra_fields = {}
        for key, value in record.__dict__.items():
            if key not in ['name', 'msg', 'args', 'levelname', 'levelno', 'pathname',
                          'filename', 'module', 'lineno', 'funcName', 'created',
                          'msecs', 'relativeCreated', 'thread', 'threadName',
                          'processName', 'process', 'getMessage', 'exc_info',
                          'exc_text', 'stack_info']:
                extra_fields[key] = value
        
        if extra_fields:
            log_entry["extra"] = extra_fields
            
        return json.dumps(log_entry, default=str)

class PerformanceLogger:
    """Track performance metrics for API endpoints"""
    
    def __init__(self, logger_name: str = "performance"):
        self.logger = logging.getLogger(logger_name)
    
    def log_request(self, method: str, path: str, status_code: int, 
                   duration: float, user_id: str = None):
        """Log API request performance"""
        self.logger.info(
            f"{method} {path} - {status_code}",
            extra={
                "event_type": "api_request",
                "method": method,
                "path": path,
                "status_code": status_code,
                "duration_ms": round(duration * 1000, 2),
                "user_id": user_id,
            }
        )
    
    def log_database_query(self, query_type: str, table: str, duration: float):
        """Log database query performance"""
        self.logger.info(
            f"DB {query_type} on {table}",
            extra={
                "event_type": "database_query",
                "query_type": query_type,
                "table": table,
                "duration_ms": round(duration * 1000, 2),
            }
        )

class SecurityLogger:
    """Log security-related events"""
    
    def __init__(self, logger_name: str = "security"):
        self.logger = logging.getLogger(logger_name)
    
    def log_login_attempt(self, username: str, success: bool, ip: str, user_agent: str = None):
        """Log login attempts"""
        self.logger.info(
            f"Login {'successful' if success else 'failed'} for {username}",
            extra={
                "event_type": "login_attempt",
                "username": username,
                "success": success,
                "ip_address": ip,
                "user_agent": user_agent,
            }
        )
    
    def log_permission_denied(self, user_id: str, resource: str, action: str, ip: str):
        """Log permission denied events"""
        self.logger.warning(
            f"Permission denied: user {user_id} tried to {action} on {resource}",
            extra={
                "event_type": "permission_denied",
                "user_id": user_id,
                "resource": resource,
                "action": action,
                "ip_address": ip,
            }
        )
    
    def log_suspicious_activity(self, user_id: str, activity: str, details: Dict[str, Any], ip: str):
        """Log suspicious activities"""
        self.logger.warning(
            f"Suspicious activity: {activity}",
            extra={
                "event_type": "suspicious_activity",
                "user_id": user_id,
                "activity": activity,
                "details": details,
                "ip_address": ip,
            }
        )

def setup_logging(
    log_level: str = "INFO",
    log_file: str = "logs/app.log",
    enable_console: bool = True,
    enable_file: bool = True
):
    """Set up structured logging for the application"""
    
    # Create logs directory
    log_path = Path(log_file).parent
    log_path.mkdir(parents=True, exist_ok=True)
    
    # Create formatter
    formatter = StructuredFormatter()
    
    # Root logger configuration
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))
    
    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Console handler
    if enable_console:
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)
    
    # File handler
    if enable_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
    
    # Configure specific loggers
    logging.getLogger("uvicorn.access").disabled = True  # We'll handle this ourselves
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)  # Reduce SQL noise
    
    return root_logger

def get_logger(name: str) -> logging.Logger:
    """Get a logger with the specified name"""
    return logging.getLogger(name)

# Convenience instances
perf_logger = PerformanceLogger()
security_logger = SecurityLogger()

# Utility functions
def set_correlation_id(cid: str = None) -> str:
    """Set correlation ID for request tracking"""
    if cid is None:
        cid = str(uuid.uuid4())
    correlation_id.set(cid)
    return cid

def get_correlation_id() -> Optional[str]:
    """Get current correlation ID"""
    return correlation_id.get()

def set_user_context(uid: str):
    """Set user ID for logging context"""
    user_id.set(uid)

def clear_context():
    """Clear logging context"""
    correlation_id.set(None)
    user_id.set(None)
