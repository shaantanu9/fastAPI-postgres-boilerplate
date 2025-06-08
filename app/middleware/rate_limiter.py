"""Enterprise Rate Limiting Middleware
Advanced rate limiting with IP restrictions, user-based limits, and Redis backend.
"""

import ipaddress
from collections.abc import Callable
from datetime import datetime, timedelta
from enum import Enum

import geoip2.database
import geoip2.errors
from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
from loguru import logger
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.core.config import get_settings
from app.core.redis_manager import RedisNamespace, redis_manager


class RateLimitType(str, Enum):
    """Types of rate limits."""

    PER_IP = "per_ip"
    PER_USER = "per_user"
    PER_ENDPOINT = "per_endpoint"
    GLOBAL = "global"


class RiskLevel(str, Enum):
    """IP risk assessment levels."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RateLimitRule:
    """Rate limit rule configuration."""

    def __init__(
        self,
        limit: int,
        window: int,
        rule_type: RateLimitType,
        path_pattern: str = "*",
        methods: list[str] | None = None,
        user_roles: list[str] | None = None,
        ip_whitelist: list[str] | None = None,
        ip_blacklist: list[str] | None = None,
        country_whitelist: list[str] | None = None,
        country_blacklist: list[str] | None = None,
    ) -> None:
        self.limit = limit
        self.window = window
        self.rule_type = rule_type
        self.path_pattern = path_pattern
        self.methods = methods or ["GET", "POST", "PUT", "DELETE"]
        self.user_roles = user_roles or []
        self.ip_whitelist = ip_whitelist or []
        self.ip_blacklist = ip_blacklist or []
        self.country_whitelist = country_whitelist or []
        self.country_blacklist = country_blacklist or []


class IPGeolocationService:
    """IP geolocation and risk assessment service."""

    def __init__(self) -> None:
        self.geoip_db = None
        self.risk_cache = {}
        self.settings = get_settings()

    async def initialize(self) -> None:
        """Initialize GeoIP database."""
        try:
            # Try to load GeoIP database (requires GeoLite2-City.mmdb)
            geoip_path = getattr(self.settings, "geoip_db_path", "GeoLite2-City.mmdb")
            self.geoip_db = geoip2.database.Reader(geoip_path)
            logger.info("GeoIP database loaded successfully")
        except Exception as e:
            logger.warning(f"GeoIP database not available: {e}")

    def get_ip_info(self, ip_address: str) -> dict[str, str]:
        """Get geographic information for IP address."""
        if not self.geoip_db:
            return {
                "country": "unknown",
                "city": "unknown",
                "risk_level": RiskLevel.LOW.value,
            }

        try:
            response = self.geoip_db.city(ip_address)
            return {
                "country": response.country.iso_code or "unknown",
                "city": response.city.name or "unknown",
                "continent": response.continent.code or "unknown",
                "is_eu": response.country.is_in_european_union,
                "latitude": float(response.location.latitude or 0),
                "longitude": float(response.location.longitude or 0),
            }
        except geoip2.errors.AddressNotFoundError:
            return {"country": "unknown", "city": "unknown"}
        except Exception as e:
            logger.error(f"GeoIP lookup error for {ip_address}: {e}")
            return {"country": "unknown", "city": "unknown"}

    def assess_ip_risk(self, ip_address: str, request: Request) -> RiskLevel:
        """Assess risk level of IP address based on various factors."""
        # Check cache first
        if ip_address in self.risk_cache:
            cached_result = self.risk_cache[ip_address]
            if cached_result["expires"] > datetime.utcnow():
                return RiskLevel(cached_result["risk_level"])

        risk_score = 0
        risk_factors = []

        # Check if IP is private/local
        try:
            ip_obj = ipaddress.ip_address(ip_address)
            if ip_obj.is_private or ip_obj.is_loopback:
                risk_level = RiskLevel.LOW
            else:
                # Public IP - assess further
                geo_info = self.get_ip_info(ip_address)

                # Country-based risk (configurable)
                high_risk_countries = getattr(self.settings, "high_risk_countries", [])
                if geo_info.get("country") in high_risk_countries:
                    risk_score += 30
                    risk_factors.append("high_risk_country")

                # Check for rapid requests from same IP
                # This would be implemented with Redis tracking

                # User agent analysis
                user_agent = request.headers.get("user-agent", "").lower()
                if not user_agent or len(user_agent) < 10:
                    risk_score += 20
                    risk_factors.append("suspicious_user_agent")

                # Determine risk level
                if risk_score >= 50:
                    risk_level = RiskLevel.CRITICAL
                elif risk_score >= 30:
                    risk_level = RiskLevel.HIGH
                elif risk_score >= 15:
                    risk_level = RiskLevel.MEDIUM
                else:
                    risk_level = RiskLevel.LOW

        except ValueError:
            # Invalid IP address
            risk_level = RiskLevel.HIGH
            risk_factors.append("invalid_ip")

        # Cache result for 1 hour
        self.risk_cache[ip_address] = {
            "risk_level": risk_level.value,
            "risk_factors": risk_factors,
            "expires": datetime.utcnow() + timedelta(hours=1),
        }

        return risk_level


class EnterpriseRateLimiter:
    """Enterprise rate limiter with advanced features."""

    def __init__(self) -> None:
        self.rules: list[RateLimitRule] = []
        self.ip_service = IPGeolocationService()
        self.settings = get_settings()
        self._setup_default_rules()

    async def initialize(self) -> None:
        """Initialize rate limiter."""
        await self.ip_service.initialize()
        await redis_manager.initialize()

    def _setup_default_rules(self) -> None:
        """Setup default rate limiting rules."""
        # API endpoints - stricter limits
        self.rules.append(
            RateLimitRule(
                limit=100,
                window=3600,
                rule_type=RateLimitType.PER_IP,
                path_pattern="/api/*",
                methods=["GET"],
            ),
        )

        self.rules.append(
            RateLimitRule(
                limit=50,
                window=3600,
                rule_type=RateLimitType.PER_IP,
                path_pattern="/api/*",
                methods=["POST", "PUT", "DELETE"],
            ),
        )

        # Authentication endpoints - very strict
        self.rules.append(
            RateLimitRule(
                limit=5,
                window=300,
                rule_type=RateLimitType.PER_IP,
                path_pattern="/api/v1/auth/login",
                methods=["POST"],
            ),
        )

        self.rules.append(
            RateLimitRule(
                limit=3,
                window=3600,
                rule_type=RateLimitType.PER_IP,
                path_pattern="/api/v1/auth/register",
                methods=["POST"],
            ),
        )

        # Password reset - strict
        self.rules.append(
            RateLimitRule(
                limit=3,
                window=3600,
                rule_type=RateLimitType.PER_IP,
                path_pattern="/api/v1/user-management/forgot-password",
                methods=["POST"],
            ),
        )

        # Global rate limit per IP
        self.rules.append(
            RateLimitRule(
                limit=1000,
                window=3600,
                rule_type=RateLimitType.PER_IP,
                path_pattern="*",
            ),
        )

    def add_rule(self, rule: RateLimitRule) -> None:
        """Add custom rate limiting rule."""
        self.rules.append(rule)

    def _match_rule(self, rule: RateLimitRule, request: Request) -> bool:
        """Check if rule matches current request."""
        # Check method
        if request.method not in rule.methods:
            return False

        # Check path pattern
        if rule.path_pattern != "*":
            path = str(request.url.path)
            if rule.path_pattern.endswith("*"):
                prefix = rule.path_pattern[:-1]
                if not path.startswith(prefix):
                    return False
            elif rule.path_pattern != path:
                return False

        return True

    def _get_rate_limit_key(self, rule: RateLimitRule, request: Request) -> str:
        """Generate rate limit key for rule and request."""
        client_ip = self._get_client_ip(request)

        if rule.rule_type == RateLimitType.PER_IP:
            return f"ip:{client_ip}"
        if rule.rule_type == RateLimitType.PER_ENDPOINT:
            return f"endpoint:{request.url.path}:{client_ip}"
        if rule.rule_type == RateLimitType.GLOBAL:
            return "global"
        if rule.rule_type == RateLimitType.PER_USER:
            # Would need user ID from JWT token
            user_id = getattr(request.state, "user_id", None)
            return f"user:{user_id}" if user_id else f"ip:{client_ip}"

        return f"default:{client_ip}"

    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP address from request."""
        # Check X-Forwarded-For header first (for load balancers/proxies)
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            # Take the first IP in the chain
            return forwarded_for.split(",")[0].strip()

        # Check X-Real-IP header
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip.strip()

        # Fall back to direct connection IP
        return request.client.host if request.client else "unknown"

    def _is_ip_whitelisted(self, ip: str, rule: RateLimitRule) -> bool:
        """Check if IP is in whitelist."""
        if not rule.ip_whitelist:
            return False

        try:
            ip_obj = ipaddress.ip_address(ip)
            for whitelisted in rule.ip_whitelist:
                if "/" in whitelisted:  # CIDR notation
                    network = ipaddress.ip_network(whitelisted, strict=False)
                    if ip_obj in network:
                        return True
                elif ip == whitelisted:
                    return True
        except ValueError:
            pass

        return False

    def _is_ip_blacklisted(self, ip: str, rule: RateLimitRule) -> bool:
        """Check if IP is in blacklist."""
        if not rule.ip_blacklist:
            return False

        try:
            ip_obj = ipaddress.ip_address(ip)
            for blacklisted in rule.ip_blacklist:
                if "/" in blacklisted:  # CIDR notation
                    network = ipaddress.ip_network(blacklisted, strict=False)
                    if ip_obj in network:
                        return True
                elif ip == blacklisted:
                    return True
        except ValueError:
            pass

        return False

    def _is_country_allowed(self, ip: str, rule: RateLimitRule) -> bool:
        """Check if country is allowed based on geo-restrictions."""
        if not rule.country_whitelist and not rule.country_blacklist:
            return True

        geo_info = self.ip_service.get_ip_info(ip)
        country = geo_info.get("country", "unknown")

        # Check blacklist first
        if rule.country_blacklist and country in rule.country_blacklist:
            return False

        # Check whitelist
        return not (rule.country_whitelist and country not in rule.country_whitelist)

    async def check_rate_limit(self, request: Request) -> tuple[bool, dict]:
        """Check if request should be rate limited."""
        client_ip = self._get_client_ip(request)

        # Check each rule
        for rule in self.rules:
            if not self._match_rule(rule, request):
                continue

            # Check IP whitelist first
            if self._is_ip_whitelisted(client_ip, rule):
                continue

            # Check IP blacklist
            if self._is_ip_blacklisted(client_ip, rule):
                return False, {
                    "error": "IP address is blacklisted",
                    "ip": client_ip,
                    "rule_type": rule.rule_type.value,
                }

            # Check country restrictions
            if not self._is_country_allowed(client_ip, rule):
                geo_info = self.ip_service.get_ip_info(client_ip)
                return False, {
                    "error": "Country not allowed",
                    "country": geo_info.get("country"),
                    "rule_type": rule.rule_type.value,
                }

            # Check rate limit
            key = self._get_rate_limit_key(rule, request)
            result = await redis_manager.rate_limit_check(
                key, rule.limit, rule.window, f"rate_limit:{rule.rule_type.value}",
            )

            if not result["allowed"]:
                return False, {
                    "error": "Rate limit exceeded",
                    "limit": result["limit"],
                    "remaining": result["remaining"],
                    "reset_time": result["reset_time"].isoformat(),
                    "rule_type": rule.rule_type.value,
                    "window_seconds": rule.window,
                }

        return True, {}

    async def log_security_event(
        self, request: Request, event_type: str, details: dict,
    ) -> None:
        """Log security-related events."""
        client_ip = self._get_client_ip(request)
        risk_level = self.ip_service.assess_ip_risk(client_ip, request)
        geo_info = self.ip_service.get_ip_info(client_ip)

        event_data = {
            "event_type": event_type,
            "ip_address": client_ip,
            "user_agent": request.headers.get("user-agent"),
            "path": str(request.url.path),
            "method": request.method,
            "geo_info": geo_info,
            "risk_level": risk_level.value,
            "timestamp": datetime.utcnow().isoformat(),
            **details,
        }

        # Store in Redis for real-time monitoring
        await redis_manager.cache_set(
            f"security_event:{datetime.utcnow().timestamp()}",
            event_data,
            ttl=86400,  # 24 hours
            namespace=RedisNamespace.SECURITY,
        )

        logger.warning(
            f"Security event: {event_type} from {client_ip} ({risk_level.value})",
        )


class RateLimitMiddleware(BaseHTTPMiddleware):
    """FastAPI middleware for rate limiting."""

    def __init__(self, app: ASGIApp, rate_limiter: EnterpriseRateLimiter) -> None:
        super().__init__(app)
        self.rate_limiter = rate_limiter

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request through rate limiter."""
        try:
            # Skip rate limiting for health checks
            if request.url.path in ["/health", "/metrics"]:
                return await call_next(request)

            # Check rate limit
            allowed, details = await self.rate_limiter.check_rate_limit(request)

            if not allowed:
                # Log the event
                await self.rate_limiter.log_security_event(
                    request, "rate_limit_exceeded", details,
                )

                # Return rate limit error
                return JSONResponse(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    content={
                        "detail": details.get("error", "Rate limit exceeded"),
                        **details,
                    },
                    headers={
                        "X-RateLimit-Limit": str(details.get("limit", "")),
                        "X-RateLimit-Remaining": str(details.get("remaining", "")),
                        "X-RateLimit-Reset": str(details.get("reset_time", "")),
                        "Retry-After": str(details.get("window_seconds", 60)),
                    },
                )

            # Process request normally
            response = await call_next(request)

            # Add rate limit headers to successful responses
            if hasattr(request.state, "rate_limit_info"):
                info = request.state.rate_limit_info
                response.headers["X-RateLimit-Limit"] = str(info.get("limit", ""))
                response.headers["X-RateLimit-Remaining"] = str(
                    info.get("remaining", ""),
                )
                response.headers["X-RateLimit-Reset"] = str(info.get("reset_time", ""))

            return response

        except Exception as e:
            logger.error(f"Rate limiting middleware error: {e}")
            # Continue processing on middleware errors
            return await call_next(request)


# Global rate limiter instance
enterprise_rate_limiter = EnterpriseRateLimiter()
