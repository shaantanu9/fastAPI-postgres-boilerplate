"""
Log Aggregation Module for FastAPI with ELK Stack Integration

This module provides comprehensive log aggregation capabilities including:
- Enhanced structured logging with JSON formatting
- Elasticsearch integration for log storage and search
- Logstash pipeline configuration for log processing
- Kibana dashboard setup for log visualization
- Correlation ID tracking across distributed services
- Sensitive data filtering and log sanitization

Based on ELK stack best practices and enterprise logging requirements.
"""

import json
import logging
import logging.handlers
import os
import socket
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

try:
    import elasticsearch
    from elasticsearch import Elasticsearch
    ELASTICSEARCH_AVAILABLE = True
except ImportError:
    ELASTICSEARCH_AVAILABLE = False

try:
    import logstash
    LOGSTASH_AVAILABLE = True
except ImportError:
    LOGSTASH_AVAILABLE = False

from app.core.config import get_settings
from app.core.logging import correlation_id, user_id

logger = logging.getLogger(__name__)
settings = get_settings()


class ElasticsearchHandler(logging.Handler):
    """
    Custom logging handler that sends logs directly to Elasticsearch.
    
    This handler formats logs as JSON and sends them to Elasticsearch
    for indexing and search capabilities.
    """
    
    def __init__(
        self,
        host: str = "localhost",
        port: int = 9200,
        index_prefix: str = "fastapi-logs",
        doc_type: str = "_doc",
        timeout: int = 30,
        max_retries: int = 3
    ):
        super().__init__()
        self.host = host
        self.port = port
        self.index_prefix = index_prefix
        self.doc_type = doc_type
        self.timeout = timeout
        self.max_retries = max_retries
        
        if ELASTICSEARCH_AVAILABLE:
            try:
                self.es_client = Elasticsearch(
                    [{"host": host, "port": port}],
                    timeout=timeout,
                    max_retries=max_retries,
                    retry_on_timeout=True
                )
                # Test connection
                self.es_client.ping()
                logger.info(f"Elasticsearch handler connected to {host}:{port}")
            except Exception as e:
                logger.error(f"Failed to connect to Elasticsearch: {e}")
                self.es_client = None
        else:
            logger.warning("Elasticsearch not available - handler disabled")
            self.es_client = None
    
    def emit(self, record: logging.LogRecord) -> None:
        """Send log record to Elasticsearch."""
        if not self.es_client:
            return
            
        try:
            # Format the log record
            log_entry = self._format_record(record)
            
            # Generate index name with date
            index_name = f"{self.index_prefix}-{datetime.utcnow().strftime('%Y.%m.%d')}"
            
            # Send to Elasticsearch
            self.es_client.index(
                index=index_name,
                doc_type=self.doc_type,
                body=log_entry
            )
            
        except Exception as e:
            # Don't let logging errors break the application
            print(f"Failed to send log to Elasticsearch: {e}")
    
    def _format_record(self, record: logging.LogRecord) -> Dict[str, Any]:
        """Format log record for Elasticsearch."""
        log_entry = {
            "@timestamp": datetime.utcfromtimestamp(record.created).isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "thread": record.thread,
            "thread_name": record.threadName,
            "process": record.process,
            "process_name": record.processName,
            "host": socket.gethostname(),
            "service": settings.OTEL_SERVICE_NAME,
            "environment": settings.OTEL_ENVIRONMENT,
            "version": settings.OTEL_SERVICE_VERSION,
        }
        
        # Add correlation ID if available
        if correlation_id.get():
            log_entry["correlation_id"] = correlation_id.get()
        
        # Add user ID if available
        if user_id.get():
            log_entry["user_id"] = user_id.get()
        
        # Add exception info if present
        if record.exc_info:
            log_entry["exception"] = {
                "type": record.exc_info[0].__name__ if record.exc_info[0] else None,
                "message": str(record.exc_info[1]) if record.exc_info[1] else None,
                "traceback": self.formatException(record.exc_info)
            }
        
        # Add extra fields from record
        extra_fields = {}
        for key, value in record.__dict__.items():
            if key not in [
                "name", "msg", "args", "levelname", "levelno", "pathname",
                "filename", "module", "lineno", "funcName", "created", "msecs",
                "relativeCreated", "thread", "threadName", "processName",
                "process", "getMessage", "exc_info", "exc_text", "stack_info"
            ]:
                extra_fields[key] = value
        
        if extra_fields:
            log_entry["extra"] = extra_fields
        
        return log_entry


class LogstashHandler(logging.Handler):
    """
    Custom logging handler that sends logs to Logstash via TCP.
    
    This handler formats logs as JSON and sends them to Logstash
    for processing and forwarding to Elasticsearch.
    """
    
    def __init__(
        self,
        host: str = "localhost",
        port: int = 5044,
        timeout: int = 5
    ):
        super().__init__()
        self.host = host
        self.port = port
        self.timeout = timeout
        
        if LOGSTASH_AVAILABLE:
            try:
                self.handler = logstash.TCPLogstashHandler(
                    host=host,
                    port=port,
                    version=1,
                    message_type="fastapi"
                )
                logger.info(f"Logstash handler connected to {host}:{port}")
            except Exception as e:
                logger.error(f"Failed to connect to Logstash: {e}")
                self.handler = None
        else:
            logger.warning("Logstash library not available - handler disabled")
            self.handler = None
    
    def emit(self, record: logging.LogRecord) -> None:
        """Send log record to Logstash."""
        if self.handler:
            try:
                # Add correlation ID and user ID to record
                if correlation_id.get():
                    record.correlation_id = correlation_id.get()
                if user_id.get():
                    record.user_id = user_id.get()
                
                # Add service information
                record.service = settings.OTEL_SERVICE_NAME
                record.environment = settings.OTEL_ENVIRONMENT
                record.version = settings.OTEL_SERVICE_VERSION
                record.host = socket.gethostname()
                
                self.handler.emit(record)
            except Exception as e:
                print(f"Failed to send log to Logstash: {e}")


class SensitiveDataFilter(logging.Filter):
    """
    Filter to remove or mask sensitive data from log records.
    
    This filter scans log messages and extra fields for sensitive
    information and masks or removes it before logging.
    """
    
    def __init__(self, sensitive_fields: Optional[List[str]] = None):
        super().__init__()
        self.sensitive_fields = sensitive_fields or settings.LOG_SENSITIVE_DATA_FIELDS
        self.mask_value = "***MASKED***"
    
    def filter(self, record: logging.LogRecord) -> bool:
        """Filter sensitive data from log record."""
        try:
            # Mask sensitive data in message
            record.msg = self._mask_sensitive_data(str(record.msg))
            
            # Mask sensitive data in extra fields
            for key, value in record.__dict__.items():
                if key.lower() in [field.lower() for field in self.sensitive_fields]:
                    setattr(record, key, self.mask_value)
                elif isinstance(value, (dict, str)):
                    setattr(record, key, self._mask_sensitive_data(value))
            
            return True
        except Exception as e:
            # Don't let filtering errors break logging
            print(f"Error filtering sensitive data: {e}")
            return True
    
    def _mask_sensitive_data(self, data: Union[str, Dict[str, Any]]) -> Union[str, Dict[str, Any]]:
        """Mask sensitive data in strings or dictionaries."""
        if isinstance(data, str):
            # Simple pattern matching for common sensitive data
            import re
            
            # Mask potential passwords, tokens, keys
            patterns = [
                (r'password["\s]*[:=]["\s]*[^"\s,}]+', 'password":"***MASKED***"'),
                (r'token["\s]*[:=]["\s]*[^"\s,}]+', 'token":"***MASKED***"'),
                (r'key["\s]*[:=]["\s]*[^"\s,}]+', 'key":"***MASKED***"'),
                (r'secret["\s]*[:=]["\s]*[^"\s,}]+', 'secret":"***MASKED***"'),
                (r'authorization["\s]*[:=]["\s]*[^"\s,}]+', 'authorization":"***MASKED***"'),
            ]
            
            for pattern, replacement in patterns:
                data = re.sub(pattern, replacement, data, flags=re.IGNORECASE)
            
            return data
        
        elif isinstance(data, dict):
            masked_data = {}
            for key, value in data.items():
                if key.lower() in [field.lower() for field in self.sensitive_fields]:
                    masked_data[key] = self.mask_value
                else:
                    masked_data[key] = self._mask_sensitive_data(value)
            return masked_data
        
        return data


class StructuredJSONFormatter(logging.Formatter):
    """
    Enhanced JSON formatter for structured logging.
    
    This formatter creates consistent JSON log entries with
    all necessary fields for log aggregation and analysis.
    """
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_entry = {
            "@timestamp": datetime.utcfromtimestamp(record.created).isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "thread": record.thread,
            "thread_name": record.threadName,
            "process": record.process,
            "process_name": record.processName,
            "host": socket.gethostname(),
            "service": settings.OTEL_SERVICE_NAME,
            "environment": settings.OTEL_ENVIRONMENT,
            "version": settings.OTEL_SERVICE_VERSION,
        }
        
        # Add correlation ID if available
        if correlation_id.get():
            log_entry["correlation_id"] = correlation_id.get()
        
        # Add user ID if available
        if user_id.get():
            log_entry["user_id"] = user_id.get()
        
        # Add exception info if present
        if record.exc_info:
            log_entry["exception"] = {
                "type": record.exc_info[0].__name__ if record.exc_info[0] else None,
                "message": str(record.exc_info[1]) if record.exc_info[1] else None,
                "traceback": self.formatException(record.exc_info)
            }
        
        # Add extra fields from record
        extra_fields = {}
        for key, value in record.__dict__.items():
            if key not in [
                "name", "msg", "args", "levelname", "levelno", "pathname",
                "filename", "module", "lineno", "funcName", "created", "msecs",
                "relativeCreated", "thread", "threadName", "processName",
                "process", "getMessage", "exc_info", "exc_text", "stack_info"
            ]:
                extra_fields[key] = value
        
        if extra_fields:
            log_entry["extra"] = extra_fields
        
        return json.dumps(log_entry, default=str, ensure_ascii=False)


class LogAggregationManager:
    """
    Centralized log aggregation management for the FastAPI application.
    
    Handles setup of log handlers, formatters, and filters for
    comprehensive log aggregation with ELK stack integration.
    """
    
    def __init__(self):
        self.is_initialized = False
        self.handlers = []
        
    def initialize(self) -> None:
        """Initialize log aggregation with configured handlers."""
        if self.is_initialized:
            logger.warning("Log aggregation already initialized")
            return
            
        if not settings.LOG_AGGREGATION_ENABLED:
            logger.info("Log aggregation disabled in configuration")
            return
            
        try:
            # Setup root logger
            root_logger = logging.getLogger()
            root_logger.setLevel(getattr(logging, settings.LOG_LEVEL.upper()))
            
            # Remove existing handlers
            for handler in root_logger.handlers[:]:
                root_logger.removeHandler(handler)
            
            # Setup formatters and filters
            json_formatter = StructuredJSONFormatter()
            sensitive_filter = SensitiveDataFilter()
            
            # Console handler with JSON formatting
            if settings.LOG_FORMAT == "json":
                console_handler = logging.StreamHandler()
                console_handler.setFormatter(json_formatter)
                console_handler.addFilter(sensitive_filter)
                root_logger.addHandler(console_handler)
                self.handlers.append(console_handler)
                logger.info("JSON console handler configured")
            
            # File handler with rotation
            self._setup_file_handler(json_formatter, sensitive_filter)
            
            # Elasticsearch handler
            if ELASTICSEARCH_AVAILABLE and settings.ELASTICSEARCH_HOST:
                self._setup_elasticsearch_handler(sensitive_filter)
            
            # Logstash handler
            if LOGSTASH_AVAILABLE and settings.LOGSTASH_HOST:
                self._setup_logstash_handler(sensitive_filter)
            
            # Configure specific loggers
            self._configure_specific_loggers()
            
            self.is_initialized = True
            
            logger.info(
                "Log aggregation initialized successfully",
                extra={
                    "handlers_count": len(self.handlers),
                    "elasticsearch_enabled": ELASTICSEARCH_AVAILABLE and bool(settings.ELASTICSEARCH_HOST),
                    "logstash_enabled": LOGSTASH_AVAILABLE and bool(settings.LOGSTASH_HOST),
                    "log_format": settings.LOG_FORMAT
                }
            )
            
        except Exception as e:
            logger.error(f"Failed to initialize log aggregation: {e}", exc_info=True)
    
    def _setup_file_handler(self, formatter: logging.Formatter, log_filter: logging.Filter) -> None:
        """Setup rotating file handler."""
        try:
            # Create logs directory
            log_dir = Path("logs")
            log_dir.mkdir(exist_ok=True)
            
            # Rotating file handler
            file_handler = logging.handlers.RotatingFileHandler(
                filename="logs/app.log",
                maxBytes=100 * 1024 * 1024,  # 100MB
                backupCount=10,
                encoding="utf-8"
            )
            file_handler.setFormatter(formatter)
            file_handler.addFilter(log_filter)
            
            root_logger = logging.getLogger()
            root_logger.addHandler(file_handler)
            self.handlers.append(file_handler)
            
            logger.info("Rotating file handler configured")
        except Exception as e:
            logger.warning(f"Failed to setup file handler: {e}")
    
    def _setup_elasticsearch_handler(self, log_filter: logging.Filter) -> None:
        """Setup Elasticsearch handler."""
        try:
            es_handler = ElasticsearchHandler(
                host=settings.ELASTICSEARCH_HOST,
                port=settings.ELASTICSEARCH_PORT,
                index_prefix=settings.ELASTICSEARCH_INDEX_PREFIX
            )
            es_handler.addFilter(log_filter)
            
            root_logger = logging.getLogger()
            root_logger.addHandler(es_handler)
            self.handlers.append(es_handler)
            
            logger.info("Elasticsearch handler configured")
        except Exception as e:
            logger.warning(f"Failed to setup Elasticsearch handler: {e}")
    
    def _setup_logstash_handler(self, log_filter: logging.Filter) -> None:
        """Setup Logstash handler."""
        try:
            logstash_handler = LogstashHandler(
                host=settings.LOGSTASH_HOST,
                port=settings.LOGSTASH_PORT
            )
            logstash_handler.addFilter(log_filter)
            
            root_logger = logging.getLogger()
            root_logger.addHandler(logstash_handler)
            self.handlers.append(logstash_handler)
            
            logger.info("Logstash handler configured")
        except Exception as e:
            logger.warning(f"Failed to setup Logstash handler: {e}")
    
    def _configure_specific_loggers(self) -> None:
        """Configure specific loggers for better log management."""
        # Disable uvicorn access logs (we handle them ourselves)
        logging.getLogger("uvicorn.access").disabled = True
        
        # Reduce SQLAlchemy noise
        logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
        
        # Reduce HTTP client noise
        logging.getLogger("httpx").setLevel(logging.WARNING)
        logging.getLogger("urllib3").setLevel(logging.WARNING)
    
    def shutdown(self) -> None:
        """Shutdown log aggregation and flush handlers."""
        for handler in self.handlers:
            try:
                handler.flush()
                handler.close()
            except Exception as e:
                print(f"Error closing handler: {e}")
        
        logger.info("Log aggregation shutdown completed")


# Global log aggregation manager instance
log_aggregation_manager = LogAggregationManager()


def initialize_log_aggregation() -> None:
    """Initialize log aggregation for the application."""
    log_aggregation_manager.initialize()


def shutdown_log_aggregation() -> None:
    """Shutdown log aggregation."""
    log_aggregation_manager.shutdown()


def get_structured_logger(name: str) -> logging.Logger:
    """Get a logger configured for structured logging."""
    return logging.getLogger(name)


# Utility functions for common logging patterns
def log_api_request(
    method: str,
    path: str,
    status_code: int,
    duration: float,
    user_id: Optional[str] = None,
    correlation_id: Optional[str] = None
) -> None:
    """Log API request with structured data."""
    logger = get_structured_logger("api.requests")
    logger.info(
        f"{method} {path} - {status_code}",
        extra={
            "event_type": "api_request",
            "http_method": method,
            "http_path": path,
            "http_status_code": status_code,
            "duration_ms": round(duration * 1000, 2),
            "user_id": user_id,
            "correlation_id": correlation_id
        }
    )


def log_database_operation(
    operation: str,
    table: str,
    duration: float,
    rows_affected: Optional[int] = None
) -> None:
    """Log database operation with structured data."""
    logger = get_structured_logger("database.operations")
    logger.info(
        f"DB {operation} on {table}",
        extra={
            "event_type": "database_operation",
            "db_operation": operation,
            "db_table": table,
            "duration_ms": round(duration * 1000, 2),
            "rows_affected": rows_affected
        }
    )


def log_security_event(
    event_type: str,
    user_id: Optional[str] = None,
    ip_address: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None
) -> None:
    """Log security event with structured data."""
    logger = get_structured_logger("security.events")
    logger.warning(
        f"Security event: {event_type}",
        extra={
            "event_type": "security_event",
            "security_event_type": event_type,
            "user_id": user_id,
            "ip_address": ip_address,
            "details": details or {}
        }
    )


def log_business_event(
    event_name: str,
    user_id: Optional[str] = None,
    **attributes
) -> None:
    """Log business event with structured data."""
    logger = get_structured_logger("business.events")
    logger.info(
        f"Business event: {event_name}",
        extra={
            "event_type": "business_event",
            "business_event_name": event_name,
            "user_id": user_id,
            **attributes
        }
    ) 