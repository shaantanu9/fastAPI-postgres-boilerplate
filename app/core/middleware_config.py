"""Comprehensive Middleware Configuration.

This module provides a centralized configuration for all middleware components
in the FastAPI application, ensuring proper order and dependency management.
"""

import logging
from typing import Any, Dict, List

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from starlette.middleware.sessions import SessionMiddleware

from app.core.config import get_settings

# Import available middleware with error handling
try:
    from slowapi import Limiter, _rate_limit_exceeded_handler
    from slowapi.errors import RateLimitExceeded
    from slowapi.util import get_remote_address
    SLOWAPI_AVAILABLE = True
except ImportError:
    SLOWAPI_AVAILABLE = False

# Import custom middleware
from app.middleware import __available__ as available_middleware

logger = logging.getLogger(__name__)
settings = get_settings()


class MiddlewareManager:
    """Manages all middleware configuration and setup."""
    
    def __init__(self, app: FastAPI):
        self.app = app
        self.settings = settings
        
    def setup_all_middleware(self) -> None:
        """Setup all middleware in the correct order."""
        # Order matters! Middleware is applied in reverse order
        # (last added = first executed)
        
        # 1. Core FastAPI middleware (applied last, executed first)
        self._setup_core_middleware()
        
        # 2. Security middleware
        self._setup_security_middleware()
        
        # 3. Monitoring and logging
        self._setup_monitoring_middleware()
        
        # 4. Rate limiting (if available)
        if SLOWAPI_AVAILABLE:
            self._setup_rate_limiting()
        
        # 5. Custom application middleware
        self._setup_application_middleware()
        
        logger.info(f"✅ Middleware configured successfully (Available: {available_middleware})")
    
    def _setup_core_middleware(self) -> None:
        """Setup core FastAPI middleware."""
        # CORS - must be last to execute first
        cors_origins = getattr(self.settings, 'cors_origins', ["*"])
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=cors_origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        # GZip compression
        self.app.add_middleware(GZipMiddleware, minimum_size=1000)
        
        # Trusted hosts (production only)
        if self.settings.ENVIRONMENT.lower() == "production":
            allowed_hosts = getattr(self.settings, 'allowed_hosts', ["*"])
            self.app.add_middleware(
                TrustedHostMiddleware,
                allowed_hosts=allowed_hosts
            )
        
        # Session middleware
        self.app.add_middleware(
            SessionMiddleware,
            secret_key=self.settings.jwt_secret_token,
            max_age=86400,  # 24 hours
        )
        
        logger.info("✅ Core middleware configured")
    
    def _setup_security_middleware(self) -> None:
        """Setup security-related middleware."""
        # Security headers (if available)
        if "SecurityHeadersMiddleware" in available_middleware:
            from app.middleware import SecurityHeadersMiddleware
            self.app.add_middleware(SecurityHeadersMiddleware)
            logger.info("✅ Security headers middleware added")
        
        # Multi-tenancy support (if available and enabled)
        if ("TenantMiddleware" in available_middleware and 
            hasattr(self.settings, 'multi_tenant_enabled') and 
            self.settings.multi_tenant_enabled):
            from app.middleware import TenantMiddleware
            self.app.add_middleware(TenantMiddleware)
            logger.info("✅ Tenant middleware added")
        
        logger.info("✅ Security middleware configured")
    
    def _setup_monitoring_middleware(self) -> None:
        """Setup monitoring and logging middleware."""
        # Error tracking (if available)
        if "SimpleErrorTracker" in available_middleware:
            from app.middleware import SimpleErrorTracker
            self.app.add_middleware(SimpleErrorTracker)
            logger.info("✅ Error tracker middleware added")
        
        # Request/response logging (if available)
        if "LoggingMiddleware" in available_middleware:
            from app.middleware import LoggingMiddleware
            self.app.add_middleware(LoggingMiddleware)
            logger.info("✅ Logging middleware added")
        
        logger.info("✅ Monitoring middleware configured")
    
    def _setup_rate_limiting(self) -> None:
        """Setup rate limiting (if SlowAPI is available)."""
        if not SLOWAPI_AVAILABLE:
            logger.warning("⚠️ SlowAPI not available, skipping rate limiting")
            return
            
        try:
            # Create limiter
            limiter = Limiter(
                key_func=get_remote_address,
                default_limits=["100/minute", "1000/hour"]
            )
            
            # Add to app state
            self.app.state.limiter = limiter
            
            # Add exception handler
            self.app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
            
            logger.info("✅ Rate limiting configured")
        except Exception as e:
            logger.warning(f"⚠️ Failed to setup rate limiting: {e}")
    
    def _setup_application_middleware(self) -> None:
        """Setup custom application middleware."""
        # Timeout middleware (if available)
        if "TimeoutMiddleware" in available_middleware:
            from app.middleware import TimeoutMiddleware
            timeout_seconds = getattr(self.settings, 'request_timeout', 30.0)
            self.app.add_middleware(
                TimeoutMiddleware,
                timeout_seconds=timeout_seconds
            )
            logger.info("✅ Timeout middleware added")
        
        logger.info("✅ Application middleware configured")


def setup_middleware(app: FastAPI) -> None:
    """Setup all middleware for the FastAPI application."""
    middleware_manager = MiddlewareManager(app)
    middleware_manager.setup_all_middleware()


# Middleware configuration for different environments
MIDDLEWARE_CONFIG = {
    "development": {
        "cors_debug": True,
        "log_requests": True,
        "rate_limit_enabled": False,
        "security_headers": True,
    },
    "staging": {
        "cors_debug": False,
        "log_requests": True,
        "rate_limit_enabled": True,
        "security_headers": True,
    },
    "production": {
        "cors_debug": False,
        "log_requests": False,  # Use structured logging instead
        "rate_limit_enabled": True,
        "security_headers": True,
    }
}


def get_middleware_config() -> Dict[str, Any]:
    """Get middleware configuration for current environment."""
    env = settings.ENVIRONMENT.lower()
    config = MIDDLEWARE_CONFIG.get(env, MIDDLEWARE_CONFIG["development"])
    
    # Add availability information
    config["available_middleware"] = available_middleware
    config["slowapi_available"] = SLOWAPI_AVAILABLE
    
    return config 