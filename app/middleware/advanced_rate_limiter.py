"""
Advanced Rate Limiting Middleware with IP restrictions and Redis backend
"""

from datetime import datetime, timedelta
from typing import Dict, List, Tuple
from enum import Enum
from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
from loguru import logger
from app.core.redis_manager import redis_manager


class RateLimitType(str, Enum):
    PER_IP = "per_ip"
    PER_USER = "per_user"
    PER_ENDPOINT = "per_endpoint"


class RateLimitRule:
    def __init__(self, limit: int, window: int, rule_type: RateLimitType, path_pattern: str = "*"):
        self.limit = limit
        self.window = window
        self.rule_type = rule_type
        self.path_pattern = path_pattern


class AdvancedRateLimiter:
    def __init__(self):
        self.rules: List[RateLimitRule] = []
        self._setup_default_rules()
        
    def _setup_default_rules(self):
        # Authentication endpoints - very strict
        self.rules.append(RateLimitRule(5, 300, RateLimitType.PER_IP, "/api/v1/auth/login"))
        self.rules.append(RateLimitRule(3, 3600, RateLimitType.PER_IP, "/api/v1/auth/register"))
        self.rules.append(RateLimitRule(3, 3600, RateLimitType.PER_IP, "/api/v1/user-management/forgot-password"))
        
        # API endpoints - moderate
        self.rules.append(RateLimitRule(100, 3600, RateLimitType.PER_IP, "/api/"))
        
        # Global limit per IP
        self.rules.append(RateLimitRule(1000, 3600, RateLimitType.PER_IP, "*"))
    
    def _get_client_ip(self, request: Request) -> str:
        # Check X-Forwarded-For header first (for load balancers)
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        # Check X-Real-IP header
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip.strip()
        
        # Fall back to direct connection IP
        return request.client.host if request.client else "unknown"
    
    def _is_suspicious_ip(self, ip: str, request: Request) -> bool:
        """Basic IP risk assessment"""
        # Check for missing or suspicious user agent
        user_agent = request.headers.get("user-agent", "").lower()
        if not user_agent or len(user_agent) < 10:
            return True
        
        # Add more checks as needed
        suspicious_patterns = ["bot", "crawler", "spider", "scraper"]
        if any(pattern in user_agent for pattern in suspicious_patterns):
            return True
        
        return False
    
    async def check_rate_limit(self, request: Request) -> Tuple[bool, Dict]:
        client_ip = self._get_client_ip(request)
        path = str(request.url.path)
        
        # Apply stricter limits for suspicious IPs
        multiplier = 0.5 if self._is_suspicious_ip(client_ip, request) else 1.0
        
        for rule in self.rules:
            # Check if rule applies to this path
            if rule.path_pattern != "*":
                if rule.path_pattern.endswith("/"):
                    if not path.startswith(rule.path_pattern):
                        continue
                elif rule.path_pattern != path:
                    continue
            
            # Generate rate limit key
            key = f"{rule.rule_type.value}:{rule.path_pattern}:{client_ip}"
            adjusted_limit = int(rule.limit * multiplier)
            
            # Check rate limit using Redis
            result = await redis_manager.rate_limit_check(
                key, adjusted_limit, rule.window, f"rate_limit:{rule.rule_type.value}"
            )
            
            if not result["allowed"]:
                logger.warning(f"Rate limit exceeded for IP {client_ip} on {path}")
                return False, {
                    "error": "Rate limit exceeded",
                    "limit": result["limit"],
                    "remaining": result["remaining"],
                    "reset_time": result["reset_time"].isoformat(),
                    "rule_type": rule.rule_type.value,
                    "window_seconds": rule.window,
                    "path": path
                }
        
        return True, {}


class AdvancedRateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.rate_limiter = AdvancedRateLimiter()
        
    async def dispatch(self, request: Request, call_next) -> Response:
        # Skip rate limiting for health check endpoints
        if request.url.path in ["/health", "/metrics", "/docs", "/redoc", "/openapi.json"]:
            return await call_next(request)
        
        try:
            # Check rate limit
            allowed, details = await self.rate_limiter.check_rate_limit(request)
            
            if not allowed:
                # Return rate limit error with appropriate headers
                return JSONResponse(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    content={
                        "detail": details.get("error", "Rate limit exceeded"),
                        "limit": details.get("limit"),
                        "remaining": details.get("remaining"),
                        "reset_time": details.get("reset_time")
                    },
                    headers={
                        "X-RateLimit-Limit": str(details.get("limit", "")),
                        "X-RateLimit-Remaining": str(details.get("remaining", "")),
                        "X-RateLimit-Reset": str(details.get("reset_time", "")),
                        "Retry-After": str(details.get("window_seconds", 60))
                    }
                )
            
            # Process request normally
            response = await call_next(request)
            return response
            
        except Exception as e:
            logger.error(f"Rate limiting middleware error: {e}")
            # Continue processing on middleware errors (fail open)
            return await call_next(request)


# Factory function for easy integration
def create_rate_limit_middleware(app: ASGIApp) -> AdvancedRateLimitMiddleware:
    return AdvancedRateLimitMiddleware(app) 