"""
Logging Middleware for FastAPI
- Automatic request/response logging
- Correlation ID tracking
- Performance monitoring
- Security event logging
"""
import time
import uuid
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.logging import (
    get_logger, 
    set_correlation_id, 
    set_user_context, 
    clear_context,
    perf_logger,
    security_logger
)

logger = get_logger(__name__)

class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for comprehensive request/response logging"""
    
    def __init__(self, app, skip_paths: list = None):
        super().__init__(app)
        self.skip_paths = skip_paths or ['/health', '/metrics', '/docs', '/openapi.json']
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip logging for certain paths
        if any(request.url.path.startswith(path) for path in self.skip_paths):
            return await call_next(request)
        
        # Set correlation ID
        correlation_id = request.headers.get('X-Correlation-ID') or str(uuid.uuid4())
        set_correlation_id(correlation_id)
        
        # Get client info
        client_ip = self._get_client_ip(request)
        user_agent = request.headers.get('User-Agent', 'Unknown')
        
        # Start timing
        start_time = time.time()
        
        # Log request
        logger.info(
            f"Request started: {request.method} {request.url.path}",
            extra={
                "event_type": "request_start",
                "method": request.method,
                "path": request.url.path,
                "query_params": dict(request.query_params),
                "client_ip": client_ip,
                "user_agent": user_agent,
                "correlation_id": correlation_id,
            }
        )
        
        response = None
        error = None
        
        try:
            # Process request
            response = await call_next(request)
            
            # Extract user ID from response if available
            user_id = getattr(request.state, 'user_id', None)
            if user_id:
                set_user_context(str(user_id))
            
        except Exception as e:
            error = e
            logger.error(
                f"Request error: {request.method} {request.url.path}",
                extra={
                    "event_type": "request_error",
                    "method": request.method,
                    "path": request.url.path,
                    "error": str(e),
                    "client_ip": client_ip,
                },
                exc_info=True
            )
            raise
        
        finally:
            # Calculate duration
            duration = time.time() - start_time
            status_code = response.status_code if response else 500
            
            # Log performance
            perf_logger.log_request(
                method=request.method,
                path=request.url.path,
                status_code=status_code,
                duration=duration,
                user_id=getattr(request.state, 'user_id', None)
            )
            
            # Log response
            logger.info(
                f"Request completed: {request.method} {request.url.path} - {status_code}",
                extra={
                    "event_type": "request_end",
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": status_code,
                    "duration_ms": round(duration * 1000, 2),
                    "client_ip": client_ip,
                    "error": str(error) if error else None,
                }
            )
            
            # Add correlation ID to response headers
            if response:
                response.headers['X-Correlation-ID'] = correlation_id
            
            # Clear context
            clear_context()
        
        return response
    
    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP address"""
        # Check for forwarded headers first (for reverse proxies)
        forwarded_for = request.headers.get('X-Forwarded-For')
        if forwarded_for:
            return forwarded_for.split(',')[0].strip()
        
        real_ip = request.headers.get('X-Real-IP')
        if real_ip:
            return real_ip
        
        # Fallback to direct client
        return request.client.host if request.client else 'unknown'

class SecurityLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for security event logging"""
    
    def __init__(self, app):
        super().__init__(app)
        self.sensitive_paths = ['/auth', '/login', '/register', '/password']
        self.admin_paths = ['/admin', '/management']
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        client_ip = self._get_client_ip(request)
        user_agent = request.headers.get('User-Agent', 'Unknown')
        
        # Check for suspicious activity
        await self._check_suspicious_activity(request, client_ip, user_agent)
        
        response = await call_next(request)
        
        # Log security-relevant events
        await self._log_security_events(request, response, client_ip, user_agent)
        
        return response
    
    async def _check_suspicious_activity(self, request: Request, client_ip: str, user_agent: str):
        """Check for suspicious activity patterns"""
        path = request.url.path.lower()
        
        # Check for common attack patterns
        suspicious_patterns = [
            'script', 'javascript:', 'onload=', 'onerror=',  # XSS attempts
            'union', 'select', 'drop', 'insert', 'update',   # SQL injection attempts
            '../', '..\\', '/etc/passwd', '/etc/shadow',      # Path traversal
            'cmd=', 'exec=', 'system=', 'eval=',             # Command injection
        ]
        
        query_string = str(request.query_params).lower()
        
        for pattern in suspicious_patterns:
            if pattern in path or pattern in query_string:
                security_logger.log_suspicious_activity(
                    user_id=getattr(request.state, 'user_id', 'anonymous'),
                    activity='suspicious_request_pattern',
                    details={
                        'pattern': pattern,
                        'path': request.url.path,
                        'query_params': dict(request.query_params),
                        'method': request.method,
                    },
                    ip=client_ip
                )
                break
    
    async def _log_security_events(self, request: Request, response: Response, 
                                 client_ip: str, user_agent: str):
        """Log security-relevant events"""
        path = request.url.path.lower()
        
        # Log access to sensitive endpoints
        if any(sensitive in path for sensitive in self.sensitive_paths):
            logger.info(
                f"Sensitive endpoint access: {request.method} {request.url.path}",
                extra={
                    "event_type": "sensitive_access",
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code,
                    "client_ip": client_ip,
                    "user_agent": user_agent,
                    "user_id": getattr(request.state, 'user_id', None),
                }
            )
        
        # Log admin endpoint access
        if any(admin in path for admin in self.admin_paths):
            logger.warning(
                f"Admin endpoint access: {request.method} {request.url.path}",
                extra={
                    "event_type": "admin_access",
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code,
                    "client_ip": client_ip,
                    "user_agent": user_agent,
                    "user_id": getattr(request.state, 'user_id', None),
                }
            )
        
        # Log failed authentication attempts
        if response.status_code == 401:
            security_logger.log_permission_denied(
                user_id=getattr(request.state, 'user_id', 'anonymous'),
                resource=request.url.path,
                action=request.method,
                ip=client_ip
            )
    
    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP address"""
        forwarded_for = request.headers.get('X-Forwarded-For')
        if forwarded_for:
            return forwarded_for.split(',')[0].strip()
        
        real_ip = request.headers.get('X-Real-IP')
        if real_ip:
            return real_ip
        
        return request.client.host if request.client else 'unknown' 