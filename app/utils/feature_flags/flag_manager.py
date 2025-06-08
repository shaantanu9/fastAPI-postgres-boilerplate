"""Feature Flag Manager.

This module provides feature flag management capabilities with:
- Subscription tier-based access control
- Tenant and user-specific overrides
- Percentage-based gradual rollouts
- A/B testing variants
- Time-scheduled activation/deactivation

Usage:
    # Get singleton instance
    flag_manager = await get_feature_flag_manager()

    # Check if feature is enabled in context
    is_enabled = await flag_manager.is_enabled(
        feature_key="premium_analytics",
        context=FeatureContext(
            tenant_id="tenant123",
            user_id="user456",
            subscription_tier="enterprise"
        )
    )
"""

import hashlib
import logging
import random
from datetime import datetime

import redis.asyncio as aioredis
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.session import get_db

from .models import Feature, FeatureContext, FeatureOverride, FeatureScope, FeatureState

# Configure logging
logger = logging.getLogger(__name__)


class FeatureFlagManager:
    """Manager for feature flag evaluation and administration.

    This class handles feature flag state, evaluation, and subscription-based access.
    """

    def __init__(
        self, redis_url: str | None = None, db_session: AsyncSession | None = None,
    ) -> None:
        """Initialize the feature flag manager.

        Args:
            redis_url: Optional Redis URL. If None, uses value from settings.
            db_session: Optional DB session for persistence

        """
        settings = get_settings()
        self.redis_url = redis_url or settings.REDIS_URL
        self.db_session = db_session
        self.redis_client: aioredis.Redis | None = None

        # In-memory feature cache
        self._features: dict[str, Feature] = {}
        self._overrides: dict[str, list[FeatureOverride]] = {}

        # Feature tier map (subscription tier -> list of feature keys)
        self._tier_features: dict[str, set[str]] = {}

        # Cache time-to-live (seconds)
        self.cache_ttl = 300  # 5 minutes

        # Feature definition defaults
        self.default_features: list[Feature] = [
            # Core features available on all tiers
            Feature(
                name="User Management",
                key="core:user_management",
                description="Basic user management capabilities",
                state=FeatureState.ENABLED,
                scope=FeatureScope.GLOBAL,
            ),
            # Free tier features
            Feature(
                name="Basic Dashboard",
                key="dashboard:basic",
                description="Basic metrics dashboard",
                state=FeatureState.ENABLED,
                scope=FeatureScope.GLOBAL,
            ),
            # Pro tier features
            Feature(
                name="Advanced Analytics",
                key="analytics:advanced",
                description="Advanced data analytics",
                state=FeatureState.ENABLED,
                scope=FeatureScope.SUBSCRIPTION,
                subscription_tiers=["pro", "enterprise"],
            ),
            # Enterprise tier features
            Feature(
                name="White Labeling",
                key="branding:white_label",
                description="White labeling and custom branding",
                state=FeatureState.ENABLED,
                scope=FeatureScope.SUBSCRIPTION,
                subscription_tiers=["enterprise"],
            ),
            # Beta features (percentage rollout)
            Feature(
                name="AI Recommendations",
                key="ai:recommendations",
                description="AI-powered content recommendations",
                state=FeatureState.PERCENTAGE,
                percentage=25,  # 25% of users
                scope=FeatureScope.SUBSCRIPTION,
                subscription_tiers=["pro", "enterprise"],
            ),
        ]

        logger.info("FeatureFlagManager initialized")

    async def connect(self) -> None:
        """Connect to Redis if not already connected."""
        if self.redis_client is None:
            try:
                self.redis_client = await aioredis.from_url(
                    self.redis_url, encoding="utf-8", decode_responses=True,
                )
                logger.info(f"Connected to Redis at {self.redis_url}")
            except Exception as e:
                logger.exception(f"Failed to connect to Redis: {e}")
                # Continue without Redis - will use in-memory cache only

    async def initialize(self) -> None:
        """Initialize the feature flag system with default features."""
        # Connect to Redis
        await self.connect()

        # Load default features
        for feature in self.default_features:
            await self.register_feature(feature)

        # Build tier -> features map
        await self._build_tier_feature_map()

    async def register_feature(self, feature: Feature) -> None:
        """Register a new feature flag or update an existing one.

        Args:
            feature: Feature configuration to register

        """
        # Update in-memory cache
        self._features[feature.key] = feature

        # Update Redis cache if connected
        if self.redis_client:
            try:
                await self.redis_client.set(
                    f"feature:{feature.key}", feature.json(), ex=self.cache_ttl,
                )
            except Exception as e:
                logger.exception(f"Failed to cache feature in Redis: {e}")

        # TODO: Persist to database if db_session is available

    async def get_feature(self, key: str) -> Feature | None:
        """Get a feature by its key.

        Args:
            key: Feature key identifier

        Returns:
            Feature object if found, None otherwise

        """
        # Check in-memory cache first
        if key in self._features:
            return self._features[key]

        # Try Redis cache
        if self.redis_client:
            try:
                feature_json = await self.redis_client.get(f"feature:{key}")
                if feature_json:
                    feature = Feature.parse_raw(feature_json)
                    self._features[key] = feature  # Update in-memory cache
                    return feature
            except Exception as e:
                logger.exception(f"Failed to get feature from Redis: {e}")

        # TODO: Fetch from database if available

        return None

    async def is_enabled(self, feature_key: str, context: FeatureContext) -> bool:
        """Check if a feature is enabled in the given context.

        Args:
            feature_key: Feature key to check
            context: Context containing tenant, user, subscription info

        Returns:
            Boolean indicating if feature is enabled

        """
        # Get feature definition
        feature = await self.get_feature(feature_key)
        if not feature:
            logger.warning(f"Feature {feature_key} not found")
            return False

        # Check overrides first (highest precedence)
        override = await self._get_active_override(feature_key, context)
        if override:
            return override.state == FeatureState.ENABLED

        # Check feature state
        if feature.state == FeatureState.DISABLED:
            return False

        # Handle different scopes
        if feature.scope == FeatureScope.SUBSCRIPTION:
            # Check subscription tier
            if not context.subscription_tier:
                return False

            if context.subscription_tier not in feature.subscription_tiers:
                return False

        # Check tenant restrictions if applicable
        if feature.tenant_ids and context.tenant_id:
            if context.tenant_id not in feature.tenant_ids:
                return False

        # Check user restrictions if applicable
        if feature.user_ids and context.user_id:
            if context.user_id not in feature.user_ids:
                return False

        # Handle percentage rollout
        if feature.state == FeatureState.PERCENTAGE:
            if not self._is_in_percentage_rollout(feature, context):
                return False

        # Handle scheduled activation
        if feature.state == FeatureState.SCHEDULED:
            now = datetime.utcnow()

            # Not yet activated
            if feature.scheduled_activation and now < feature.scheduled_activation:
                return False

            # Already deactivated
            if feature.scheduled_deactivation and now >= feature.scheduled_deactivation:
                return False

        # If we made it here, the feature is enabled
        return True

    async def _get_active_override(
        self, feature_key: str, context: FeatureContext,
    ) -> FeatureOverride | None:
        """Get active override for a feature in the given context.

        Args:
            feature_key: Feature key to check
            context: Context with tenant and user info

        Returns:
            Active override if found, None otherwise

        """
        # Check for tenant override
        if context.tenant_id:
            # TODO: Implement tenant override lookup
            pass

        # Check for user override
        if context.user_id:
            # TODO: Implement user override lookup
            pass

        return None

    def _is_in_percentage_rollout(
        self, feature: Feature, context: FeatureContext,
    ) -> bool:
        """Check if user/tenant is in the percentage rollout.
        Uses consistent hashing to ensure the same user always gets the same result.

        Args:
            feature: Feature with percentage rollout
            context: Context with user/tenant info

        Returns:
            Boolean indicating if in rollout group

        """
        if feature.percentage is None or feature.percentage == 0:
            return False

        if feature.percentage >= 100:
            return True

        # Get stable ID to hash (prefer user_id, fall back to tenant_id)
        stable_id = context.user_id or context.tenant_id
        if not stable_id:
            # Without a stable ID, use random chance
            return random.randint(1, 100) <= feature.percentage

        # Create hash of feature key + stable ID
        hash_input = f"{feature.key}:{stable_id}".encode()
        hash_val = int(hashlib.md5(hash_input).hexdigest(), 16) % 100

        # Check if hash value falls within percentage
        return hash_val < feature.percentage

    async def _build_tier_feature_map(self) -> None:
        """Build a mapping of subscription tiers to feature keys."""
        self._tier_features = {}

        for key, feature in self._features.items():
            if feature.scope == FeatureScope.SUBSCRIPTION:
                for tier in feature.subscription_tiers:
                    if tier not in self._tier_features:
                        self._tier_features[tier] = set()
                    self._tier_features[tier].add(key)

    async def get_features_for_tier(self, tier: str) -> list[str]:
        """Get all feature keys available for a subscription tier.

        Args:
            tier: Subscription tier name

        Returns:
            List of feature keys available for the tier

        """
        # Ensure tier map is built
        if not self._tier_features:
            await self._build_tier_feature_map()

        return list(self._tier_features.get(tier, set()))

    async def get_all_features(self) -> list[Feature]:
        """Get all registered features.

        Returns:
            List of all feature definitions

        """
        return list(self._features.values())

    async def register_tenant_override(
        self,
        feature_key: str,
        tenant_id: str,
        state: FeatureState,
        expires_at: datetime | None = None,
    ) -> FeatureOverride:
        """Register a tenant-specific feature override.

        Args:
            feature_key: Feature key to override
            tenant_id: Tenant identifier
            state: New state for the feature
            expires_at: Optional expiration date

        Returns:
            Created override object

        """
        return FeatureOverride(
            feature_key=feature_key,
            tenant_id=tenant_id,
            state=state,
            expires_at=expires_at,
        )

        # TODO: Store override in Redis and/or database



# Global instance for application-wide use
_feature_flag_manager = None


async def get_feature_flag_manager() -> FeatureFlagManager:
    """Get or create the global feature flag manager instance.

    Returns:
        Feature flag manager instance

    """
    global _feature_flag_manager
    if _feature_flag_manager is None:
        _feature_flag_manager = FeatureFlagManager()
        await _feature_flag_manager.initialize()
    return _feature_flag_manager


# Dependency for FastAPI endpoints
async def get_feature_manager(db: AsyncSession = Depends(get_db)) -> FeatureFlagManager:
    """FastAPI dependency for feature flag manager."""
    manager = await get_feature_flag_manager()
    manager.db_session = db
    return manager
