"""
API Versioning System for FastAPI.

This module provides comprehensive API versioning strategies:
- Header-based versioning
- URL path versioning
- Query parameter versioning
- Content negotiation versioning
"""
from enum import Enum
from typing import Optional, Dict, Any, Callable
from fastapi import Request, HTTPException, Header, Query
from fastapi.routing import APIRouter
from dataclasses import dataclass
import re


class VersioningStrategy(Enum):
    """API versioning strategies."""
    HEADER = "header"
    PATH = "path"
    QUERY = "query"
    CONTENT_TYPE = "content_type"


@dataclass
class APIVersion:
    """API version information."""
    major: int
    minor: int
    patch: int = 0
    
    def __str__(self) -> str:
        return f"{self.major}.{self.minor}.{self.patch}"
    
    def __eq__(self, other) -> bool:
        if isinstance(other, str):
            return str(self) == other
        return (
            self.major == other.major and
            self.minor == other.minor and
            self.patch == other.patch
        )
    
    def __lt__(self, other) -> bool:
        return (self.major, self.minor, self.patch) < (other.major, other.minor, other.patch)
    
    def __gt__(self, other) -> bool:
        return (self.major, self.minor, self.patch) > (other.major, other.minor, other.patch)
    
    @classmethod
    def from_string(cls, version_str: str) -> "APIVersion":
        """Create APIVersion from string like '1.2.3'."""
        match = re.match(r"^(\d+)\.(\d+)(?:\.(\d+))?$", version_str)
        if not match:
            raise ValueError(f"Invalid version format: {version_str}")
        
        major, minor, patch = match.groups()
        return cls(
            major=int(major),
            minor=int(minor),
            patch=int(patch) if patch else 0
        )


class VersionedAPIRouter(APIRouter):
    """
    Extended APIRouter with versioning support.
    """
    
    def __init__(
        self,
        version: str,
        deprecated: bool = False,
        sunset_date: Optional[str] = None,
        **kwargs
    ):
        super().__init__(**kwargs)
        self.version = APIVersion.from_string(version)
        self.deprecated = deprecated
        self.sunset_date = sunset_date
    
    def add_api_route(self, *args, **kwargs):
        """Override to add version info to route metadata."""
        route = super().add_api_route(*args, **kwargs)
        
        # Add version metadata to the route
        if hasattr(route, 'endpoint'):
            if not hasattr(route.endpoint, '__version_info__'):
                route.endpoint.__version_info__ = {
                    'version': str(self.version),
                    'deprecated': self.deprecated,
                    'sunset_date': self.sunset_date
                }
        
        return route


class APIVersionManager:
    """
    Manages API versions and routing.
    """
    
    def __init__(self, default_version: str = "1.0.0"):
        self.default_version = APIVersion.from_string(default_version)
        self.versions: Dict[str, VersionedAPIRouter] = {}
        self.deprecated_versions: Dict[str, str] = {}  # version -> sunset_date
    
    def add_version(
        self,
        version: str,
        router: VersionedAPIRouter,
        deprecated: bool = False,
        sunset_date: Optional[str] = None
    ):
        """Add a new API version."""
        self.versions[version] = router
        if deprecated:
            self.deprecated_versions[version] = sunset_date
    
    def get_version_from_header(self, request: Request) -> APIVersion:
        """Extract version from Accept header."""
        accept_header = request.headers.get("accept", "")
        
        # Look for version in Accept header like: application/vnd.api+json;version=1.2
        version_match = re.search(r"version=(\d+\.\d+(?:\.\d+)?)", accept_header)
        if version_match:
            return APIVersion.from_string(version_match.group(1))
        
        # Look for custom version header
        version_header = request.headers.get("api-version") or request.headers.get("x-api-version")
        if version_header:
            return APIVersion.from_string(version_header)
        
        return self.default_version
    
    def get_version_from_query(self, version: Optional[str] = Query(None)) -> APIVersion:
        """Extract version from query parameter."""
        if version:
            return APIVersion.from_string(version)
        return self.default_version
    
    def get_supported_versions(self) -> list:
        """Get list of supported versions."""
        return list(self.versions.keys())
    
    def is_version_supported(self, version: APIVersion) -> bool:
        """Check if version is supported."""
        return str(version) in self.versions
    
    def is_version_deprecated(self, version: APIVersion) -> bool:
        """Check if version is deprecated."""
        return str(version) in self.deprecated_versions


# Global version manager
version_manager = APIVersionManager(default_version="1.0.0")

# Initialize supported versions
version_manager.add_version("1.0.0", None, deprecated=False)
version_manager.add_version("1.1.0", None, deprecated=False)


def versioned_route(
    versions: list,
    deprecated_versions: list = None,
    min_version: str = None,
    max_version: str = None
):
    """
    Decorator for versioned routes.
    
    Args:
        versions: List of supported versions
        deprecated_versions: List of deprecated versions (still supported but warned)
        min_version: Minimum supported version
        max_version: Maximum supported version
    """
    def decorator(func: Callable):
        def wrapper(*args, **kwargs):
            # This would be implemented based on your versioning strategy
            return func(*args, **kwargs)
        
        # Add version metadata
        wrapper.__version_info__ = {
            'supported_versions': versions,
            'deprecated_versions': deprecated_versions or [],
            'min_version': min_version,
            'max_version': max_version
        }
        
        return wrapper
    return decorator


def get_api_version(
    request: Request,
    strategy: VersioningStrategy = VersioningStrategy.HEADER
) -> APIVersion:
    """
    Get API version based on strategy.
    """
    if strategy == VersioningStrategy.HEADER:
        return version_manager.get_version_from_header(request)
    elif strategy == VersioningStrategy.QUERY:
        version_param = request.query_params.get("version")
        if version_param:
            return APIVersion.from_string(version_param)
    elif strategy == VersioningStrategy.PATH:
        # Extract from path - assumes format like /api/v1/...
        path_match = re.search(r"/v(\d+(?:\.\d+)?)", request.url.path)
        if path_match:
            version_str = path_match.group(1)
            if "." not in version_str:
                version_str += ".0"  # Convert v1 to v1.0
            return APIVersion.from_string(version_str)
    
    return version_manager.default_version


def validate_api_version(version: APIVersion) -> None:
    """
    Validate API version and raise appropriate exceptions.
    """
    if not version_manager.is_version_supported(version):
        raise HTTPException(
            status_code=400,
            detail={
                "error": "Unsupported API version",
                "requested_version": str(version),
                "supported_versions": version_manager.get_supported_versions()
            }
        )


def add_version_headers(response, version: APIVersion) -> None:
    """
    Add version-related headers to response.
    """
    response.headers["API-Version"] = str(version)
    response.headers["API-Supported-Versions"] = ",".join(version_manager.get_supported_versions())
    
    if version_manager.is_version_deprecated(version):
        response.headers["API-Deprecation"] = "true"
        sunset_date = version_manager.deprecated_versions.get(str(version))
        if sunset_date:
            response.headers["API-Sunset"] = sunset_date


# Version-specific routers
def create_v1_router() -> VersionedAPIRouter:
    """Create version 1.0 router."""
    return VersionedAPIRouter(
        version="1.0.0",
        prefix="/api/v1",
        tags=["v1.0"],
        deprecated=False
    )


def create_v2_router() -> VersionedAPIRouter:
    """Create version 2.0 router."""
    return VersionedAPIRouter(
        version="2.0.0",
        prefix="/api/v2",
        tags=["v2.0"],
        deprecated=False
    )


def create_legacy_v1_router() -> VersionedAPIRouter:
    """Create legacy version 1.0 router (deprecated)."""
    return VersionedAPIRouter(
        version="1.0.0",
        prefix="/api/v1",
        tags=["v1.0", "deprecated"],
        deprecated=True,
        sunset_date="2024-12-31"
    )


# Content negotiation helpers
def get_content_version(accept_header: str) -> Optional[APIVersion]:
    """
    Extract version from Accept header content negotiation.
    
    Examples:
    - application/vnd.myapi.v1+json
    - application/vnd.myapi+json;version=1.2
    """
    # Check for version in media type
    version_match = re.search(r"\.v(\d+(?:\.\d+)?)\+", accept_header)
    if version_match:
        version_str = version_match.group(1)
        if "." not in version_str:
            version_str += ".0"
        return APIVersion.from_string(version_str)
    
    # Check for version parameter
    version_match = re.search(r"version=(\d+\.\d+(?:\.\d+)?)", accept_header)
    if version_match:
        return APIVersion.from_string(version_match.group(1))
    
    return None 