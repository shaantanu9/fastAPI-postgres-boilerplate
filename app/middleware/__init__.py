"""Comprehensive Middleware Package.

This module consolidates all middleware components for the FastAPI application.
"""

# Import available middleware components
available_middleware = []

try:
    from .logging_middleware import LoggingMiddleware, SecurityLoggingMiddleware
    available_middleware.extend(["LoggingMiddleware", "SecurityLoggingMiddleware"])
except ImportError as e:
    LoggingMiddleware = None
    SecurityLoggingMiddleware = None

try:
    from .security_headers import SecurityHeadersMiddleware, EnhancedSecurityHeadersMiddleware, create_security_headers_middleware
    available_middleware.extend(["SecurityHeadersMiddleware", "EnhancedSecurityHeadersMiddleware", "create_security_headers_middleware"])
except ImportError as e:
    SecurityHeadersMiddleware = None
    EnhancedSecurityHeadersMiddleware = None
    create_security_headers_middleware = None

try:
    from .simple_error_tracker import SimpleErrorTracker
    available_middleware.append("SimpleErrorTracker")
except ImportError as e:
    SimpleErrorTracker = None

try:
    from .tenant_middleware import TenantIsolationMiddleware, TenantMiddleware
    available_middleware.extend(["TenantIsolationMiddleware", "TenantMiddleware"])
except ImportError as e:
    TenantIsolationMiddleware = None
    TenantMiddleware = None

try:
    from .timeout_middleware import TimeoutMiddleware
    available_middleware.append("TimeoutMiddleware")
except ImportError as e:
    TimeoutMiddleware = None

try:
    from .advanced_rate_limiter import AdvancedRateLimiter
    available_middleware.append("AdvancedRateLimiter")
except ImportError as e:
    AdvancedRateLimiter = None

try:
    from .rate_limiter import RateLimiter
    available_middleware.append("RateLimiter")
except ImportError as e:
    # Rate limiter might have optional dependencies
    RateLimiter = None

try:
    from .cors import CORSMiddleware
    available_middleware.append("CORSMiddleware")
except ImportError as e:
    CORSMiddleware = None

try:
    from .rate_limiting import RateLimitingMiddleware
    available_middleware.append("RateLimitingMiddleware")
except ImportError as e:
    RateLimitingMiddleware = None

__all__ = [name for name in [
    "AdvancedRateLimiter",
    "LoggingMiddleware", 
    "SecurityLoggingMiddleware",
    "RateLimiter",
    "SecurityHeadersMiddleware",
    "EnhancedSecurityHeadersMiddleware",
    "create_security_headers_middleware",
    "SimpleErrorTracker",
    "TenantIsolationMiddleware",
    "TenantMiddleware",
    "TimeoutMiddleware",
    "CORSMiddleware",
    "RateLimitingMiddleware"
] if globals().get(name) is not None]

# Add available middleware list for debugging
__available__ = available_middleware 