"""Security Headers module.
Implements comprehensive security headers for HTTP responses.
"""

from fastapi import FastAPI
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.config import get_settings

settings = get_settings()


class SecurityHeaders(BaseHTTPMiddleware):
    """Middleware to add security headers to all responses.
    Implements best practices for web security headers.
    """

    def __init__(
        self,
        app: FastAPI,
        csp_config: dict | None = None,
        hsts_max_age: int = 31536000,  # 1 year
        enable_hsts: bool = True,
        enable_csp: bool = True,
        enable_permissions_policy: bool = True,
    ) -> None:
        super().__init__(app)
        self.csp_config = csp_config or self._default_csp_config()
        self.hsts_max_age = hsts_max_age
        self.enable_hsts = enable_hsts
        self.enable_csp = enable_csp
        self.enable_permissions_policy = enable_permissions_policy

    async def dispatch(self, request: Request, call_next) -> Response:
        """Add security headers to response.

        Args:
            request: The incoming request
            call_next: The next middleware/route handler

        Returns:
            Response with added security headers

        """
        response = await call_next(request)

        # Basic security headers (always enabled)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Cache control for sensitive routes
        if self._is_sensitive_route(request.url.path):
            response.headers["Cache-Control"] = "no-store, max-age=0"
            response.headers["Pragma"] = "no-cache"

        # HSTS (HTTP Strict Transport Security)
        if self.enable_hsts and request.url.scheme == "https":
            response.headers["Strict-Transport-Security"] = (
                f"max-age={self.hsts_max_age}; includeSubDomains; preload"
            )

        # Content Security Policy (CSP)
        if self.enable_csp:
            response.headers["Content-Security-Policy"] = self._build_csp_header()

        # Permissions Policy
        if self.enable_permissions_policy:
            response.headers["Permissions-Policy"] = self._build_permissions_policy()

        return response

    def _default_csp_config(self) -> dict:
        """Default Content Security Policy configuration."""
        return {
            "default-src": ["'self'"],
            "script-src": ["'self'", "'unsafe-inline'", "'unsafe-eval'"],
            "style-src": ["'self'", "'unsafe-inline'"],
            "img-src": ["'self'", "data:", "https:"],
            "font-src": ["'self'", "https:", "data:"],
            "connect-src": ["'self'"],
            "media-src": ["'self'"],
            "object-src": ["'none'"],
            "frame-src": ["'self'"],
            "worker-src": ["'self'"],
            "frame-ancestors": ["'none'"],
            "form-action": ["'self'"],
            "base-uri": ["'self'"],
            "manifest-src": ["'self'"],
            "upgrade-insecure-requests": [],
        }

    def _build_csp_header(self) -> str:
        """Build Content Security Policy header value."""
        csp_parts = []

        for directive, sources in self.csp_config.items():
            if not sources:  # Directive without sources
                if directive == "upgrade-insecure-requests":
                    csp_parts.append(directive)
                continue

            sources_str = " ".join(sources)
            csp_parts.append(f"{directive} {sources_str}")

        return "; ".join(csp_parts)

    def _build_permissions_policy(self) -> str:
        """Build Permissions Policy header value."""
        # Restrictive permissions policy by default
        permissions = {
            "accelerometer": "()",
            "ambient-light-sensor": "()",
            "autoplay": "()",
            "battery": "()",
            "camera": "()",
            "display-capture": "()",
            "document-domain": "()",
            "encrypted-media": "()",
            "execution-while-not-rendered": "()",
            "execution-while-out-of-viewport": "()",
            "fullscreen": "(self)",
            "geolocation": "()",
            "gyroscope": "()",
            "magnetometer": "()",
            "microphone": "()",
            "midi": "()",
            "navigation-override": "()",
            "payment": "()",
            "picture-in-picture": "()",
            "publickey-credentials-get": "()",
            "screen-wake-lock": "()",
            "sync-xhr": "()",
            "usb": "()",
            "web-share": "()",
            "xr-spatial-tracking": "()",
        }

        return ", ".join(f"{k}={v}" for k, v in permissions.items())

    def _is_sensitive_route(self, path: str) -> bool:
        """Determine if a route should be considered sensitive.
        Sensitive routes include authentication, user data, and admin paths.
        """
        sensitive_prefixes = [
            "/api/v1/auth",
            "/api/v1/users",
            "/api/v1/admin",
            "/api/v1/organizations",
        ]

        return any(path.startswith(prefix) for prefix in sensitive_prefixes)

    def update_csp_config(self, new_config: dict) -> None:
        """Update CSP configuration dynamically.

        Args:
            new_config: New CSP configuration to merge with existing

        """
        self.csp_config.update(new_config)

    def add_csp_source(self, directive: str, source: str) -> None:
        """Add a new source to a CSP directive.

        Args:
            directive: CSP directive to update
            source: New source to add

        """
        if directive not in self.csp_config:
            self.csp_config[directive] = []

        if source not in self.csp_config[directive]:
            self.csp_config[directive].append(source)
