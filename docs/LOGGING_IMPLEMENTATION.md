# Logging Implementation Guide

This document outlines the logging strategy and implementation details for the FastAPI PostgreSQL application.

## Table of Contents
1. [Current Implementation](#current-implementation)
2. [Enhancements](#enhancements)
   - [Log Sampling](#1-log-sampling)
   - [Sensitive Data Redaction](#2-sensitive-data-redaction)
   - [Enhanced Logging Middleware](#3-enhanced-logging-middleware)
   - [Log Retention and Rotation](#4-log-retention-and-rotation)
   - [Performance Monitoring](#5-performance-monitoring)
3. [Implementation Plan](#implementation-plan)
4. [Usage Examples](#usage-examples)

## Current Implementation

### What's Working Well

- **Structured Logging** with Loguru
- **Correlation IDs** for request tracing
- **Request/Response** logging middleware
- **Security Event** logging

### Areas Needing Improvement

1. No log sampling for high-volume logs
2. Limited sensitive data redaction
3. Basic log rotation and retention
4. Limited performance metrics
5. No centralized log aggregation

## Enhancements

### 1. Log Sampling

```python
# app/core/logging.py
from loguru import logger
import random
from functools import wraps

def sample_log(probability: float = 0.1):
    """Sample logs based on probability."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if random.random() < probability:
                return func(*args, **kwargs)
        return wrapper
    return decorator

# Usage
@sample_log(probability=0.1)
def log_debug(message: str, **kwargs):
    logger.debug(message, **kwargs)
```

### 2. Sensitive Data Redaction

```python
# app/core/redaction.py
import re
from typing import Any, Dict

class Redactor:
    SENSITIVE_KEYS = {
        "password", "token", "secret", "api_key", "ssn", "credit_card"
    }
    
    SENSITIVE_PATTERNS = [
        r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b",  # SSN
        r"\b(?:\d[ -]*?){13,16}\b",  # Credit card
        r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",  # Email
    ]
    
    @classmethod
    def redact(cls, data: Any) -> Any:
        if isinstance(data, dict):
            return {k: cls.redact(v) if k.lower() not in cls.SENSITIVE_KEYS 
                   else "[REDACTED]" for k, v in data.items()}
        elif isinstance(data, list):
            return [cls.redact(item) for item in data]
        elif isinstance(data, str):
            for pattern in cls.SENSITIVE_PATTERNS:
                data = re.sub(pattern, "[REDACTED]", data)
        return data
```

### 3. Enhanced Logging Middleware

```python
# app/middleware/enhanced_logging.py
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
import time
from loguru import logger
from app.core.redaction import Redactor

class EnhancedLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        
        # Log request
        logger.info(
            "Request received",
            method=request.method,
            path=request.url.path,
            query_params=Redactor.redact(dict(request.query_params)),
            headers=Redactor.redact(dict(request.headers))
        )
        
        try:
            response = await call_next(request)
            duration = time.time() - start_time
            
            # Log response
            logger.info(
                "Request completed",
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
                duration=f"{duration:.3f}s",
                response_size=response.headers.get("content-length", 0)
            )
            
            return response
            
        except Exception as e:
            logger.opt(exception=e).error(
                "Request failed",
                method=request.method,
                path=request.url.path,
                error=str(e)
            )
            raise
```

### 4. Log Retention and Rotation

```python
# app/core/logging.py
from loguru import logger
import os
from datetime import datetime

def configure_logging():
    log_dir = "logs"
    os.makedirs(log_dir, exist_ok=True)
    
    # Rotate logs daily, keep 7 days, compress old logs
    logger.add(
        f"{log_dir}/app_{time.strftime('%Y%m%d')}.log",
        rotation="1 day",
        retention="7 days",
        compression="zip",
        enqueue=True,  # Async logging
        backtrace=True,  # Include stack traces
        diagnose=True,  # Include variable values in stack traces
    )
    
    # Add error log with different retention
    logger.add(
        f"{log_dir}/error.log",
        rotation="100 MB",
        retention="30 days",
        level="ERROR",
        compression="zip",
        enqueue=True
    )
```

### 5. Performance Monitoring

```python
# app/core/metrics.py
from prometheus_client import Counter, Histogram
from functools import wraps
import time

# Request metrics
REQUEST_COUNT = Counter(
    'http_requests_total',
    'Total HTTP Requests',
    ['method', 'endpoint', 'status_code']
)

REQUEST_LATENCY = Histogram(
    'http_request_duration_seconds',
    'HTTP Request Latency',
    ['method', 'endpoint']
)

# Database metrics
DB_QUERY_COUNT = Counter(
    'db_queries_total',
    'Total Database Queries',
    ['operation', 'table']
)

DB_QUERY_DURATION = Histogram(
    'db_query_duration_seconds',
    'Database Query Duration',
    ['operation', 'table']
)

def track_db_query(operation: str, table: str):
    """Decorator to track database query metrics."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            DB_QUERY_COUNT.labels(operation=operation, table=table).inc()
            
            try:
                result = await func(*args, **kwargs)
                return result
            finally:
                duration = time.time() - start_time
                DB_QUERY_DURATION.labels(
                    operation=operation,
                    table=table
                ).observe(duration)
        return wrapper
    return decorator
```

## Implementation Plan

### Phase 1: Core Enhancements (Week 1)
- [ ] Add sensitive data redaction
- [ ] Implement log sampling
- [ ] Set up log rotation and retention

### Phase 2: Monitoring (Week 2)
- [ ] Add performance metrics
- [ ] Set up Prometheus integration
- [ ] Create Grafana dashboards

### Phase 3: Scaling (Week 3)
- [ ] Implement centralized logging (ELK/Loki)
- [ ] Set up log aggregation
- [ ] Configure alerts

## Usage Examples

### Basic Logging
```python
from loguru import logger

logger.info("User logged in", user_id=123, ip="192.168.1.1")
```

### Database Query with Metrics
```python
@track_db_query(operation="select", table="users")
async def get_user(user_id: int):
    return await db.execute("SELECT * FROM users WHERE id = :id", {"id": user_id})
```

### Request Logging
```python
# In FastAPI route
@app.get("/users/{user_id}")
async def get_user(user_id: int, request: Request):
    logger.info("Fetching user", user_id=user_id, path=request.url.path)
    # ...
```

## Monitoring Endpoints

- `/metrics` - Prometheus metrics
- `/health` - Service health check
- `/logs` - Log viewer (if implemented)

## Alerting

Set up alerts for:
- Error rate > 1% of requests
- P95 latency > 500ms
- Database query duration > 1s

---

*Last Updated: June 2, 2025*
