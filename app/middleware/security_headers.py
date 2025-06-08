"""Enterprise Security Headers Middleware
Implements comprehensive security headers for protection against common web vulnerabilities.
"""

from collections.abc import Callable

from fastapi import Request, Response
from loguru import logger
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.core.config import get_settings


class SecurityHeadersConfig:
    """Configuration for security headers."""

    def __init__(self) -> None:
        self.settings = get_settings()

        # Content Security Policy
        self.csp_policy = self._build_csp_policy()

        # HSTS (HTTP Strict Transport Security)
        self.hsts_max_age = 31536000  # 1 year
        self.hsts_include_subdomains = True
        self.hsts_preload = True

        # Feature Policy / Permissions Policy
        self.permissions_policy = self._build_permissions_policy()

        # CORS settings
        self.cors_origins = getattr(self.settings, "cors_origins", ["*"])
        self.cors_methods = ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
        self.cors_headers = ["*"]

    def _build_csp_policy(self) -> str:
        """Build Content Security Policy."""
        # Base CSP policy - adjust based on your needs
        csp_directives = [
            "default-src 'self'",
            "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net https://unpkg.com",
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://cdn.jsdelivr.net",
            "font-src 'self' https://fonts.gstatic.com https://cdn.jsdelivr.net",
            "img-src 'self' data: https: blob:",
            "connect-src 'self' wss: ws:",
            "media-src 'self'",
            "object-src 'none'",
            "base-uri 'self'",
            "form-action 'self'",
            "frame-ancestors 'none'",
            "upgrade-insecure-requests",
        ]

        # Add report URI if configured
        report_uri = getattr(self.settings, "csp_report_uri", None)
        if report_uri:
            csp_directives.append(f"report-uri {report_uri}")

        return "; ".join(csp_directives)

    def _build_permissions_policy(self) -> str:
        """Build Permissions Policy (formerly Feature Policy)."""
        policies = [
            "geolocation=()",
            "microphone=()",
            "camera=()",
            "magnetometer=()",
            "gyroscope=()",
            "speaker=()",
            "vibrate=()",
            "fullscreen=(self)",
            "payment=()",
        ]
        return ", ".join(policies)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Comprehensive security headers middleware
    Adds essential security headers to all responses.
    """

    def __init__(self, app: ASGIApp, config: SecurityHeadersConfig | None = None) -> None:
        super().__init__(app)
        self.config = config or SecurityHeadersConfig()

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Add security headers to response."""
        try:
            response = await call_next(request)

            # Add security headers
            self._add_security_headers(response, request)
            self._add_cors_headers(response, request)

            return response

        except Exception as e:
            logger.error(f"Security headers middleware error: {e}")
            return await call_next(request)

    def _add_security_headers(self, response: Response, request: Request) -> None:
        """Add comprehensive security headers."""
        # Content Security Policy
        response.headers["Content-Security-Policy"] = self.config.csp_policy

        # X-Content-Type-Options
        response.headers["X-Content-Type-Options"] = "nosniff"

        # X-Frame-Options
        response.headers["X-Frame-Options"] = "DENY"

        # X-XSS-Protection (legacy, but still useful for older browsers)
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # Referrer Policy
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Permissions Policy
        response.headers["Permissions-Policy"] = self.config.permissions_policy

        # HSTS (only for HTTPS)
        if request.url.scheme == "https":
            hsts_value = f"max-age={self.config.hsts_max_age}"
            if self.config.hsts_include_subdomains:
                hsts_value += "; includeSubDomains"
            if self.config.hsts_preload:
                hsts_value += "; preload"
            response.headers["Strict-Transport-Security"] = hsts_value

        # Cache Control for sensitive endpoints
        if self._is_sensitive_endpoint(request.url.path):
            response.headers["Cache-Control"] = (
                "no-store, no-cache, must-revalidate, max-age=0"
            )
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"

        # Server header removal (don't reveal server info)
        response.headers.pop("Server", None)

        # Add custom security identifier
        response.headers["X-Security-Framework"] = "FastAPI-Enterprise"

        # Cross-Origin Embedder Policy
        response.headers["Cross-Origin-Embedder-Policy"] = "require-corp"

        # Cross-Origin Opener Policy
        response.headers["Cross-Origin-Opener-Policy"] = "same-origin"

        # Cross-Origin Resource Policy
        response.headers["Cross-Origin-Resource-Policy"] = "same-origin"

    def _add_cors_headers(self, response: Response, request: Request) -> None:
        """Add CORS headers if needed."""
        origin = request.headers.get("Origin")

        # Handle CORS
        if origin:
            if "*" in self.config.cors_origins or origin in self.config.cors_origins:
                response.headers["Access-Control-Allow-Origin"] = origin
            else:
                # If specific origins are configured and this isn't one of them
                response.headers["Access-Control-Allow-Origin"] = (
                    self.config.cors_origins[0] if self.config.cors_origins else "*"
                )
        else:
            response.headers["Access-Control-Allow-Origin"] = "*"

        response.headers["Access-Control-Allow-Methods"] = ", ".join(
            self.config.cors_methods,
        )
        response.headers["Access-Control-Allow-Headers"] = ", ".join(
            self.config.cors_headers,
        )
        response.headers["Access-Control-Allow-Credentials"] = "true"
        response.headers["Access-Control-Max-Age"] = "86400"  # 24 hours

    def _is_sensitive_endpoint(self, path: str) -> bool:
        """Check if endpoint contains sensitive data that shouldn't be cached."""
        sensitive_patterns = [
            "/api/v1/auth/",
            "/api/v1/user-management/",
            "/admin/",
            "/dashboard/",
            "/profile/",
            "/settings/",
        ]

        return any(pattern in path for pattern in sensitive_patterns)


class CSPViolationHandler:
    """Handle CSP violation reports."""

    @staticmethod
    async def handle_violation(request: Request) -> Response:
        """Process CSP violation report."""
        try:
            violation_data = await request.json()

            # Log the violation
            logger.warning(f"CSP Violation: {violation_data}")

            # Here you could:
            # - Store violations in database
            # - Send alerts for critical violations
            # - Update CSP policy based on violations

            return Response(status_code=204)

        except Exception as e:
            logger.error(f"Error handling CSP violation: {e}")
            return Response(status_code=400)


# Factory function for easy integration
def create_security_middleware(
    app: ASGIApp, custom_config: SecurityHeadersConfig | None = None,
) -> SecurityHeadersMiddleware:
    """Create security headers middleware with optional custom configuration."""
    return SecurityHeadersMiddleware(app, custom_config)


# Default configuration instance
default_security_config = SecurityHeadersConfig()
