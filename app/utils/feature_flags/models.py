"""Feature Flag Models.

This module defines the data structures for feature flags and their states.

Classes:
    FeatureScope: Enum for feature flag scope.
    FeatureState: Enum for feature flag state.
    Feature: Model for feature flag configuration.
    FeatureOverride: Model for tenant/user-specific overrides.
    FeatureContext: Model for evaluation context.
"""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator


class FeatureScope(str, Enum):
    """Scopes defining who can access a feature."""

    GLOBAL = "global"  # Available to all tenants
    TENANT = "tenant"  # Available to specific tenants
    USER = "user"  # Available to specific users
    SUBSCRIPTION = "subscription"  # Available to specific subscription tiers


class FeatureState(str, Enum):
    """Possible states of a feature flag."""

    ENABLED = "enabled"  # Feature is fully enabled
    DISABLED = "disabled"  # Feature is disabled
    PERCENTAGE = "percentage"  # Feature is enabled for % of users
    SCHEDULED = "scheduled"  # Feature is scheduled for future activation


class Feature(BaseModel):
    """Model representing a feature flag configuration.

    Attributes:
        name (str): Human-readable name of the feature.
        key (str): Unique key for the feature flag.
        description (str): Description of the feature.
        scope (FeatureScope): Scope of the feature (global, tenant, user, etc.).
        state (FeatureState): Current state of the feature (enabled, disabled, etc.).
        subscription_tiers (List[str]): Subscription tiers with access.
        tenant_ids (List[str]): Tenant IDs with access.
        user_ids (List[str]): User IDs with access.
        percentage (Optional[int]): Percentage rollout (0-100) if applicable.
        scheduled_activation (Optional[datetime]): When the feature is scheduled to activate.
        scheduled_deactivation (Optional[datetime]): When the feature is scheduled to deactivate.
        is_experiment (bool): Whether this is an experiment/A-B test.
        experiment_id (Optional[str]): ID for the experiment.
        variant (Optional[str]): Variant name for A-B testing.
        custom_rules (Optional[Dict[str, Any]]): Custom rules in JSON logic format.
        created_at (datetime): Creation timestamp.
        updated_at (datetime): Last update timestamp.
        created_by (Optional[str]): Creator user ID.

    """

    # Core properties
    name: str
    key: str
    description: str
    scope: FeatureScope = FeatureScope.GLOBAL
    state: FeatureState = FeatureState.DISABLED

    # Access controls
    subscription_tiers: list[str] = Field(default_factory=list)
    tenant_ids: list[str] = Field(default_factory=list)
    user_ids: list[str] = Field(default_factory=list)

    # Gradual rollout configuration
    percentage: int | None = None

    # Scheduling
    scheduled_activation: datetime | None = None
    scheduled_deactivation: datetime | None = None

    # A/B testing
    is_experiment: bool = False
    experiment_id: str | None = None
    variant: str | None = None

    # Custom rules (JSON logic format)
    custom_rules: dict[str, Any] | None = None

    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: str | None = None

    @field_validator("percentage")
    @classmethod
    def validate_percentage(cls, v):
        """Validate that the percentage value is between 0 and 100.

        Args:
            v (int): The percentage value to validate.

        Returns:
            int: The validated percentage value.

        Raises:
            ValueError: If the percentage is not between 0 and 100.

        """
        if v is not None and (v < 0 or v > 100):
            msg = "Percentage must be between 0 and 100"
            raise ValueError(msg)
        return v

    @field_validator("state", "scheduled_activation")
    @classmethod
    def validate_scheduled_state(cls, v, info):
        """Validate that scheduled features have a scheduled_activation time.

        Args:
            v: The value being validated.
            values: The dictionary of field values.

        Returns:
            The validated value.

        Raises:
            ValueError: If a scheduled feature does not have an activation time.

        """
        if info.data.get("state") == FeatureState.SCHEDULED and not values.get(
            "scheduled_activation",
        ):
            msg = "Scheduled features must have a scheduled_activation time"
            raise ValueError(msg)
        return v

    @field_validator("state", "percentage")
    @classmethod
    def validate_percentage_state(cls, v, info):
        """Validate that percentage-based features have a percentage value.

        Args:
            v: The value being validated.
            values: The dictionary of field values.

        Returns:
            The validated value.

        Raises:
            ValueError: If a percentage-based feature does not have a percentage value.

        """
        if (
            info.data.get("state") == FeatureState.PERCENTAGE
            and info.data.get("percentage") is None
        ):
            msg = "Percentage-based features must have a percentage value"
            raise ValueError(msg)
        return v


class FeatureOverride(BaseModel):
    """Model for tenant-specific or user-specific feature overrides.

    Attributes:
        feature_key (str): The key of the feature to override.
        state (FeatureState): The override state.
        tenant_id (Optional[str]): Tenant ID for the override.
        user_id (Optional[str]): User ID for the override.
        expires_at (Optional[datetime]): Expiration time for the override.
        created_at (datetime): When the override was created.

    """

    feature_key: str
    state: FeatureState
    tenant_id: str | None = None
    user_id: str | None = None
    expires_at: datetime | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

    @field_validator("tenant_id", "user_id")
    @classmethod
    def validate_scope(cls, v, info):
        """Validate that either tenant_id or user_id is provided, but not both.

        Args:
            v: The value being validated.
            info: Validation info containing field data.

        Returns:
            The validated value.

        Raises:
            ValueError: If both tenant_id and user_id are specified, or if neither is specified.

        """
        if not info.data:
            return v

        field_name = info.field_name
        tenant_id = info.data.get("tenant_id") if field_name == "user_id" else v
        user_id = info.data.get("user_id") if field_name == "tenant_id" else v

        if tenant_id and user_id:
            msg = "Cannot specify both tenant_id and user_id"
            raise ValueError(msg)
        if not tenant_id and not user_id:
            msg = "Must specify either tenant_id or user_id"
            raise ValueError(msg)

        return v


class FeatureContext(BaseModel):
    """Evaluation context for feature flag decisions.

    Attributes:
        tenant_id (Optional[str]): Tenant ID for evaluation.
        user_id (Optional[str]): User ID for evaluation.
        subscription_tier (Optional[str]): Subscription tier for evaluation.
        attributes (Dict[str, Any]): Additional arbitrary attributes for evaluation.

    """

    tenant_id: str | None = None
    user_id: str | None = None
    subscription_tier: str | None = None
    attributes: dict[str, Any] = Field(default_factory=dict)
