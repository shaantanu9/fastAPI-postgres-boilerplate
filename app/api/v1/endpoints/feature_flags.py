"""Feature Flags API endpoints.

This module provides endpoints for:
- Retrieving available features for a tenant
- Admin management of feature flags
- Feature override management
"""

from datetime import datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Body, Depends, HTTPException, Path, Query, status
from pydantic import BaseModel

from app.core.dependencies import (
    get_current_admin_user,
    get_current_tenant,
    get_current_user,
)
from app.utils.feature_flags import (
    Feature,
    FeatureContext,
    FeatureFlagManager,
    FeatureState,
)
from app.utils.feature_flags.flag_manager import get_feature_manager

router = APIRouter()


class FeatureResponse(BaseModel):
    """Response model for feature information returned by feature flag endpoints.

    Attributes:
        key (str): Unique key of the feature.
        name (str): Human-readable name of the feature.
        description (str): Description of the feature.
        enabled (bool): Whether the feature is enabled for the context.
        subscription_tiers (List[str]): Subscription tiers for which the feature is available.

    """

    key: str
    name: str
    description: str
    enabled: bool
    subscription_tiers: list[str] = []


class FeatureOverrideRequest(BaseModel):
    """Request model for creating feature flag overrides for tenants.

    Attributes:
        feature_key (str): The key of the feature to override.
        state (FeatureState): The desired state for the override.
        expires_in_days (Optional[int]): Days until the override expires.

    """

    feature_key: str
    state: FeatureState
    expires_in_days: int | None = None


@router.get("/features", response_model=list[FeatureResponse])
async def get_available_features(
    tenant_id: Annotated[str, Depends(get_current_tenant)],
    user_id: Annotated[str | None, Depends(get_current_user)],
    subscription_tier: Annotated[str | None, Query(description="Subscription tier to check features for")] = None,
    feature_manager: FeatureFlagManager = Depends(get_feature_manager),
):
    """Get all features available to the current tenant based on their subscription tier.

    Args:
        tenant_id (str): The current tenant's ID.
        user_id (Optional[str]): The current user's ID.
        subscription_tier (Optional[str]): Subscription tier to check features for.
        feature_manager (FeatureFlagManager): The feature flag manager dependency.

    Returns:
        List[FeatureResponse]: List of features with their enabled status.

    """
    # Create feature context
    context = FeatureContext(
        tenant_id=tenant_id, user_id=user_id, subscription_tier=subscription_tier,
    )

    # Get all features
    all_features = await feature_manager.get_all_features()

    # Build response with enabled status
    results = []
    for feature in all_features:
        # Skip internal/system features that shouldn't be exposed to clients
        if feature.key.startswith("system:"):
            continue

        # Check if feature is enabled in this context
        is_enabled = await feature_manager.is_enabled(
            feature_key=feature.key, context=context,
        )

        results.append(
            FeatureResponse(
                key=feature.key,
                name=feature.name,
                description=feature.description,
                enabled=is_enabled,
                subscription_tiers=feature.subscription_tiers,
            ),
        )

    return results


@router.get("/admin/features", response_model=list[Feature])
async def admin_list_all_features(
    feature_manager: Annotated[FeatureFlagManager, Depends(get_feature_manager)],
    _: Annotated[dict, Depends(get_current_admin_user)],  # Ensure admin access
):
    """Admin endpoint to list all feature flags in the system.

    Args:
        feature_manager (FeatureFlagManager): The feature flag manager dependency.
        _ (Dict): Placeholder for admin access dependency.

    Returns:
        List[Feature]: List of all feature flag configurations.

    """
    return await feature_manager.get_all_features()


@router.post(
    "/admin/features", response_model=Feature, status_code=status.HTTP_201_CREATED,
)
async def admin_create_feature(
    feature: Feature,
    feature_manager: Annotated[FeatureFlagManager, Depends(get_feature_manager)],
    _: Annotated[dict, Depends(get_current_admin_user)],  # Ensure admin access
):
    """Admin endpoint to create a new feature flag.

    Args:
        feature (Feature): The feature flag configuration to create.
        feature_manager (FeatureFlagManager): The feature flag manager dependency.
        _ (Dict): Placeholder for admin access dependency.

    Returns:
        Feature: The created feature flag.

    Raises:
        HTTPException: If the feature already exists.

    """
    # Check if feature already exists
    existing = await feature_manager.get_feature(feature.key)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Feature with key '{feature.key}' already exists",
        )

    # Register the feature
    await feature_manager.register_feature(feature)

    return feature


@router.post(
    "/admin/tenants/{tenant_id}/overrides", status_code=status.HTTP_201_CREATED,
)
async def create_tenant_override(
    tenant_id: Annotated[str, Path(description="Tenant ID to create override for")],
    override: Annotated[FeatureOverrideRequest, Body()],
    feature_manager: FeatureFlagManager = Depends(get_feature_manager),
    _: dict = Depends(get_current_admin_user),  # Ensure admin access
):
    """Create a tenant-specific feature override.

    This allows enabling or disabling specific features for individual tenants, regardless of their subscription tier.

    Args:
        tenant_id (str): The tenant ID for which to create the override.
        override (FeatureOverrideRequest): The override request payload.
        feature_manager (FeatureFlagManager): The feature flag manager dependency.
        _ (Dict): Placeholder for admin access dependency.

    Returns:
        dict: A message indicating successful override creation.

    Raises:
        HTTPException: If the feature does not exist.

    """
    # Check if feature exists
    feature = await feature_manager.get_feature(override.feature_key)
    if not feature:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Feature '{override.feature_key}' not found",
        )

    # Calculate expiration if provided
    expires_at = None
    if override.expires_in_days:
        expires_at = datetime.utcnow() + timedelta(days=override.expires_in_days)

    # Create the override
    await feature_manager.register_tenant_override(
        feature_key=override.feature_key,
        tenant_id=tenant_id,
        state=override.state,
        expires_at=expires_at,
    )

    return {"message": "Override created successfully"}
