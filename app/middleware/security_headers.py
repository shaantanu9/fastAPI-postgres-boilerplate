"""
Enhanced Security Headers Middleware for FastAPI

Implements comprehensive OWASP-compliant security headers including:
- Content Security Policy (CSP)
- HTTP Strict Transport Security (HSTS)
- X-Frame-Options, X-Content-Type-Options
- Referrer Policy, Permissions Policy
- And more security headers for production use

Based on OWASP Security Headers recommendations and enterprise best practices.
"""

import logging
from typing import Optional

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class EnhancedSecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Comprehensive security headers middleware following OWASP guidelines.
    
    Features:
    - Content Security Policy (CSP) with customizable policies
    - HTTP Strict Transport Security (HSTS) with configurable options
    - X-Frame-Options for clickjacking protection
    - X-Content-Type-Options to prevent MIME sniffing
    - X-XSS-Protection for legacy browser protection
    - Referrer Policy for privacy protection
    - Permissions Policy for feature control
    - Cross-Origin policies for API security
    """
    
    def __init__(self, app, enable_csp: bool = True, enable_hsts: bool = True):
        super().__init__(app)
        self.enable_csp = enable_csp
        self.enable_hsts = enable_hsts
        self.settings = settings
        
        # Log initialization
        logger.info(
            "Enhanced Security Headers Middleware initialized",
            extra={
                "csp_enabled": enable_csp,
                "hsts_enabled": enable_hsts,
                "environment": self.settings.ENVIRONMENT
            }
        )

    async def dispatch(self, request: Request, call_next):
        """Apply security headers to all responses."""
        response = await call_next(request)
        
        if not self.settings.SECURITY_HEADERS_ENABLED:
            return response
        
        # Core security headers (always applied)
        self._apply_core_headers(response, request)
        
        # Content Security Policy
        if self.enable_csp:
            self._apply_csp_headers(response)
        
        # HSTS (only for HTTPS)
        if self.enable_hsts and request.url.scheme == "https":
            self._apply_hsts_headers(response)
        
        # Additional security headers
        self._apply_additional_headers(response)
        
        # Log security headers application (debug level)
        logger.debug(
            "Security headers applied",
            extra={
                "path": request.url.path,
                "method": request.method,
                "scheme": request.url.scheme,
                "headers_count": len([h for h in response.headers.keys() if h.lower().startswith(('x-', 'content-security', 'strict-transport'))])
            }
        )
        
        return response
    
    def _apply_core_headers(self, response: Response, request: Request) -> None:
        """Apply core security headers."""
        # Prevent MIME type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"
        
        # Clickjacking protection
        response.headers["X-Frame-Options"] = "DENY"
        
        # XSS protection for legacy browsers
        response.headers["X-XSS-Protection"] = "1; mode=block"
        
        # Referrer policy for privacy
        response.headers["Referrer-Policy"] = self.settings.REFERRER_POLICY
        
        # Remove server information
        response.headers["Server"] = ""
        
        # Prevent caching of sensitive content
        if request.url.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, private"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
    
    def _apply_csp_headers(self, response: Response) -> None:
        """Apply Content Security Policy headers."""
        # Main CSP policy
        response.headers["Content-Security-Policy"] = self.settings.CSP_POLICY
        
        # CSP reporting (if needed)
        # response.headers["Content-Security-Policy-Report-Only"] = self.settings.CSP_POLICY
    
    def _apply_hsts_headers(self, response: Response) -> None:
        """Apply HTTP Strict Transport Security headers."""
        hsts_value = f"max-age={self.settings.HSTS_MAX_AGE}"
        
        if self.settings.HSTS_INCLUDE_SUBDOMAINS:
            hsts_value += "; includeSubDomains"
        
        if self.settings.HSTS_PRELOAD:
            hsts_value += "; preload"
        
        response.headers["Strict-Transport-Security"] = hsts_value
    
    def _apply_additional_headers(self, response: Response) -> None:
        """Apply additional security headers."""
        # Permissions Policy (formerly Feature Policy)
        response.headers["Permissions-Policy"] = self.settings.PERMISSIONS_POLICY
        
        # Cross-Origin policies
        response.headers["Cross-Origin-Embedder-Policy"] = "require-corp"
        response.headers["Cross-Origin-Opener-Policy"] = "same-origin"
        response.headers["Cross-Origin-Resource-Policy"] = "same-origin"
        
        # Additional security headers
        response.headers["X-Permitted-Cross-Domain-Policies"] = "none"
        response.headers["X-Download-Options"] = "noopen"
        
        # DNS prefetch control
        response.headers["X-DNS-Prefetch-Control"] = "off"


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Legacy security headers middleware for backward compatibility.
    Use EnhancedSecurityHeadersMiddleware for new implementations.
    """
    
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        
        # Essential security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        # Only add HSTS if HTTPS is enabled
        if request.url.scheme == "https":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        
        return response


# Factory function for easy middleware creation
def create_security_headers_middleware(
    enhanced: bool = True,
    enable_csp: bool = True,
    enable_hsts: bool = True
) -> BaseHTTPMiddleware:
    """
    Factory function to create security headers middleware.
    
    Args:
        enhanced: Use enhanced middleware with full OWASP compliance
        enable_csp: Enable Content Security Policy
        enable_hsts: Enable HTTP Strict Transport Security
    
    Returns:
        Configured security headers middleware
    """
    if enhanced:
        return EnhancedSecurityHeadersMiddleware(
            app=None,  # Will be set by FastAPI
            enable_csp=enable_csp,
            enable_hsts=enable_hsts
        )
    else:
        return SecurityHeadersMiddleware(app=None)


# Utility functions for CSP management
def build_csp_policy(**policies) -> str:
    """
    Build a Content Security Policy string from keyword arguments.
    
    Example:
        build_csp_policy(
            default_src="'self'",
            script_src="'self' 'unsafe-inline'",
            style_src="'self' 'unsafe-inline'"
        )
    """
    return "; ".join([f"{key.replace('_', '-')} {value}" for key, value in policies.items()])


def validate_csp_policy(policy: str) -> bool:
    """
    Basic validation of CSP policy format.
    
    Args:
        policy: CSP policy string to validate
    
    Returns:
        True if policy appears valid, False otherwise
    """
    try:
        # Basic validation - check for required directives
        required_directives = ['default-src']
        policy_lower = policy.lower()
        
        for directive in required_directives:
            if directive not in policy_lower:
                logger.warning(f"CSP policy missing required directive: {directive}")
                return False
        
        return True
    except Exception as e:
        logger.error(f"Error validating CSP policy: {e}")
        return False
