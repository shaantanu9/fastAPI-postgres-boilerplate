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
    from .security_headers import SecurityHeadersMiddleware
    available_middleware.append("SecurityHeadersMiddleware")
except ImportError as e:
    SecurityHeadersMiddleware = None

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

__all__ = [name for name in [
    "AdvancedRateLimiter",
    "LoggingMiddleware", 
    "SecurityLoggingMiddleware",
    "RateLimiter",
    "SecurityHeadersMiddleware",
    "SimpleErrorTracker",
    "TenantIsolationMiddleware",
    "TenantMiddleware",
    "TimeoutMiddleware",
] if globals().get(name) is not None]

# Add available middleware list for debugging
__available__ = available_middleware 