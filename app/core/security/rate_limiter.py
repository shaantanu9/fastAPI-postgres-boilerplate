"""
Enhanced Rate Limiting module with tiered rate limits and Redis backend.
Provides sophisticated rate limiting based on user tiers and endpoint sensitivity.
"""

from enum import Enum
from typing import Optional, Dict, Tuple
import time
from datetime import datetime
import json
from fastapi import Request, HTTPException, Depends
from redis.asyncio import Redis
from app.core.config import get_settings
from app.db.session import get_db, get_redis
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.security import APIKey
from app.utils.crypto import hash_api_key
from app.db.models.user import User
from app.db.models.organization import Organization, OrganizationMembership

settings = get_settings()

class RateLimitTier(str, Enum):
    """Rate limit tiers for different user levels"""
    FREE = "free"
    BASIC = "basic"
    PREMIUM = "premium"
    ENTERPRISE = "enterprise"

class RateLimitScope(str, Enum):
    """Rate limit scopes for different types of operations"""
    READ = "read"
    WRITE = "write"
    DELETE = "delete"
    ADMIN = "admin"

# Rate limit configurations per tier (requests per minute)
TIER_LIMITS = {
    RateLimitTier.FREE: {
        RateLimitScope.READ: 60,
        RateLimitScope.WRITE: 30,
        RateLimitScope.DELETE: 10,
        RateLimitScope.ADMIN: 0
    },
    RateLimitTier.BASIC: {
        RateLimitScope.READ: 300,
        RateLimitScope.WRITE: 100,
        RateLimitScope.DELETE: 20,
        RateLimitScope.ADMIN: 0
    },
    RateLimitTier.PREMIUM: {
        RateLimitScope.READ: 1000,
        RateLimitScope.WRITE: 500,
        RateLimitScope.DELETE: 100,
        RateLimitScope.ADMIN: 10
    },
    RateLimitTier.ENTERPRISE: {
        RateLimitScope.READ: 5000,
        RateLimitScope.WRITE: 1000,
        RateLimitScope.DELETE: 200,
        RateLimitScope.ADMIN: 50
    }
}

class RateLimiter:
    """
    Sophisticated rate limiter with Redis backend and tier-based limits.
    """
    
    def __init__(
        self,
        scope: RateLimitScope,
        override_limit: Optional[int] = None,
        override_window: Optional[int] = None
    ):
        self.scope = scope
        self.override_limit = override_limit
        self.override_window = override_window or 60  # Default 1-minute window
        
    async def __call__(
        self,
        request: Request,
        redis: Redis = Depends(get_redis),
        db: AsyncSession = Depends(get_db)
    ):
        """
        Rate limit middleware implementation.
        
        Args:
            request: FastAPI request
            redis: Redis connection
            db: Database session
            
        Raises:
            HTTPException: If rate limit is exceeded
        """
        # Get client identifier (API key or user ID)
        client_id = await self._get_client_id(request)
        
        # Get client's rate limit tier
        tier = await self._get_client_tier(db, client_id)
        
        # Calculate rate limit for this tier and scope
        limit = self.override_limit or TIER_LIMITS[tier][self.scope]
        
        # Check rate limit
        await self._check_rate_limit(redis, client_id, limit)
    
    async def _get_client_id(self, request: Request) -> str:
        """Get unique identifier for the client."""
        # Try API key first
        api_key = request.headers.get("X-API-Key")
        if api_key:
            return f"api_{api_key}"
        
        # Fall back to user ID if authenticated
        user = request.state.user if hasattr(request.state, "user") else None
        if user and user.id:
            return f"user_{user.id}"
        
        # Last resort: IP address
        return f"ip_{request.client.host}"
    
    async def _get_client_tier(
        self,
        db: AsyncSession,
        client_id: str
    ) -> RateLimitTier:
        """Get rate limit tier for the client."""
        if client_id.startswith("api_"):
            return await self._get_api_key_tier(db, client_id[4:])
        elif client_id.startswith("user_"):
            return await self._get_user_tier(db, client_id[5:])
        return RateLimitTier.FREE  # Default tier for IP-based limits
    
    async def _check_rate_limit(
        self,
        redis: Redis,
        client_id: str,
        limit: int
    ):
        """
        Check if client has exceeded their rate limit.
        Uses Redis sorted set for accurate sliding window rate limiting.
        """
        now = time.time()
        key = f"ratelimit:{self.scope}:{client_id}"
        
        pipeline = redis.pipeline()
        
        # Remove old entries outside the window
        pipeline.zremrangebyscore(
            key,
            0,
            now - self.override_window
        )
        
        # Add current request
        pipeline.zadd(key, {str(now): now})
        
        # Count requests in window
        pipeline.zcard(key)
        
        # Set key expiration
        pipeline.expire(key, self.override_window)
        
        # Execute pipeline
        results = await pipeline.execute()
        request_count = results[2]
        
        if request_count > limit:
            raise HTTPException(
                status_code=429,
                detail={
                    "error": "Rate limit exceeded",
                    "limit": limit,
                    "window_seconds": self.override_window,
                    "retry_after": self.override_window - (now % self.override_window)
                }
            )
    
    async def _get_api_key_tier(
        self,
        db: AsyncSession,
        api_key: str
    ) -> RateLimitTier:
        """Get rate limit tier for an API key."""
        stmt = select(APIKey).where(APIKey.key_hash == hash_api_key(api_key))
        result = await db.execute(stmt)
        api_key_data = result.scalar_one_or_none()
        
        if not api_key_data:
            return RateLimitTier.FREE
            
        # Get organization's tier if API key belongs to an organization
        if api_key_data.organization_id:
            return await self._get_organization_tier(
                db,
                api_key_data.organization_id
            )
            
        # Get user's tier
        return await self._get_user_tier(db, api_key_data.user_id)
    
    async def _get_user_tier(
        self,
        db: AsyncSession,
        user_id: str
    ) -> RateLimitTier:
        """Get rate limit tier for a user."""
        stmt = select(User).where(User.id == user_id)
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()
        
        if not user:
            return RateLimitTier.FREE
            
        # Get organization's tier if user belongs to an organization
        org_membership = await self._get_primary_organization(db, user_id)
        if org_membership:
            return await self._get_organization_tier(
                db,
                org_membership.organization_id
            )
            
        return RateLimitTier.FREE
    
    async def _get_organization_tier(
        self,
        db: AsyncSession,
        org_id: str
    ) -> RateLimitTier:
        """Get rate limit tier for an organization."""
        stmt = select(Organization).where(Organization.id == org_id)
        result = await db.execute(stmt)
        org = result.scalar_one_or_none()
        
        if not org:
            return RateLimitTier.FREE
            
        # Map organization plan to rate limit tier
        plan_tier_map = {
            "free": RateLimitTier.FREE,
            "starter": RateLimitTier.BASIC,
            "professional": RateLimitTier.PREMIUM,
            "enterprise": RateLimitTier.ENTERPRISE
        }
        
        return plan_tier_map.get(org.plan, RateLimitTier.FREE)
    
    async def _get_primary_organization(
        self,
        db: AsyncSession,
        user_id: str
    ) -> Optional[OrganizationMembership]:
        """Get user's primary organization membership."""
        stmt = (
            select(OrganizationMembership)
            .where(
                OrganizationMembership.user_id == user_id,
                OrganizationMembership.is_active == True
            )
            .order_by(OrganizationMembership.joined_at)
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()
