"""Feature Flag System.

This package provides a flexible feature flag system that:
- Controls access to premium features based on subscription tier
- Enables gradual rollouts of new functionality
- Supports A/B testing
- Allows tenant-specific feature configuration
"""

from .flag_manager import FeatureFlagManager, get_feature_flag_manager
from .models import Feature, FeatureContext, FeatureState

__all__ = [
    "Feature",
    "FeatureContext",
    "FeatureFlagManager",
    "FeatureState",
    "get_feature_flag_manager",
]
