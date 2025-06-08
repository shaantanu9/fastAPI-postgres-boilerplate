"""Core security module for FastAPI PostgreSQL application.
This module provides centralized security features and utilities.
"""

# Re-export EnterpriseSecurityService from security_base to maintain compatibility
from app.core.security_base import EnterpriseSecurityService

from .api_key import APIKeyAuth, create_api_key, validate_api_key
from .audit import SecurityAuditLog
from .input_validation import InputValidator, ValidationRule
from .rate_limiter import RateLimiter, RateLimitTier
from .security_headers import SecurityHeaders

# Import security_service last to avoid circular imports
from .security_service import security_service

__all__ = [
    "APIKeyAuth",
    "EnterpriseSecurityService",
    "InputValidator",
    "RateLimitTier",
    "RateLimiter",
    "SecurityAuditLog",
    "SecurityHeaders",
    "ValidationRule",
    "create_api_key",
    "security_service",
    "validate_api_key",
]
