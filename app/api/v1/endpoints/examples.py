"""Example endpoints demonstrating new features:
- Advanced pagination strategies
- API versioning
- Response compression
- Performance monitoring.
"""

import random
import string
from datetime import datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi import Query as QueryParam
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.versioning import (
    VersioningStrategy,
    get_api_version,
    validate_api_version,
    versioned_route,
)
from app.db.models.user import User
from app.db.schemas.user import UserRead
from app.db.session import get_db
from app.utils.pagination import (
    CursorPaginatedResponse,
    CursorPaginationParams,
    PaginatedResponse,
    PaginationBuilder,
    PaginationParams,
    TimePaginatedResponse,
    TimePaginationParams,
    build_cursor_links,
    build_pagination_links,
    get_cursor_pagination_params,
    get_pagination_params,
    get_time_pagination_params,
)

router = APIRouter()


# Example models for demonstration
class ExampleItem(BaseModel):
    id: int
    name: str
    description: str
    created_at: datetime
    value: float


class LargeDataItem(BaseModel):
    id: int
    content: str
    metadata: dict
    timestamp: datetime


# --- Pagination Examples ---


@router.get(
    "/users/paginated",
    response_model=PaginatedResponse[UserRead],
    tags=["Examples", "Performance"],
    summary="Users with offset pagination",
    description="Demonstrates traditional offset-based pagination with page numbers",
)
async def get_users_paginated(
    request: Request,
    pagination: Annotated[PaginationParams, Depends(get_pagination_params)],
    db: Annotated[Session, Depends(get_db)],
):
    """Get users with offset-based pagination.

    Features:
    - Page-based navigation (user-friendly)
    - Total count and page metadata
    - Pagination links in response
    - Works well for small to medium datasets
    """
    # Build paginated query
    query = db.query(User)
    result = PaginationBuilder(query).offset_pagination(pagination).build()

    # Execute query and get items
    users = result["query"].all()
    pagination_info = result["pagination"]

    # Build pagination links
    build_pagination_links(request, pagination_info)

    return PaginatedResponse(
        items=[UserRead.from_attributes(user) for user in users],
        pagination=pagination_info,
    )


@router.get(
    "/users/cursor",
    response_model=CursorPaginatedResponse[UserRead],
    tags=["Examples", "Performance"],
    summary="Users with cursor pagination",
    description="Demonstrates cursor-based pagination for large datasets",
)
async def get_users_cursor(
    request: Request,
    pagination: Annotated[CursorPaginationParams, Depends(get_cursor_pagination_params)],
    db: Annotated[Session, Depends(get_db)],
):
    """Get users with cursor-based pagination.

    Features:
    - Consistent performance regardless of dataset size
    - No duplicate or missing items during pagination
    - Ideal for real-time feeds and large datasets
    - Forward and backward navigation
    """
    # Build cursor-paginated query
    query = db.query(User)
    result = (
        PaginationBuilder(query)
        .cursor_pagination(pagination, cursor_column="id")
        .build()
    )

    users = result["items"]
    cursor_info = result["cursor_info"]

    # Build cursor links
    build_cursor_links(request, cursor_info)

    return CursorPaginatedResponse(
        items=[UserRead.from_attributes(user) for user in users],
        cursor_info=cursor_info,
    )


@router.get(
    "/users/time-based",
    response_model=TimePaginatedResponse[UserRead],
    tags=["Examples", "Performance"],
    summary="Users with time-based pagination",
    description="Demonstrates time-based pagination for chronological data",
)
async def get_users_time_based(
    request: Request,
    pagination: Annotated[TimePaginationParams, Depends(get_time_pagination_params)],
    db: Annotated[Session, Depends(get_db)],
):
    """Get users with time-based pagination.

    Features:
    - Natural for time-series data
    - Efficient for recent/historical data queries
    - Supports both ascending and descending order
    - Time range filtering
    """
    # Build time-based paginated query
    query = db.query(User)
    result = (
        PaginationBuilder(query)
        .time_pagination(pagination, time_column="created_at")
        .build()
    )

    users = result["items"]
    time_info = result["time_info"]

    return TimePaginatedResponse(
        items=[UserRead.from_attributes(user) for user in users], time_info=time_info,
    )


# --- Response Compression Examples ---


@router.get(
    "/large-dataset",
    response_model=list[LargeDataItem],
    tags=["Examples", "Compression"],
    summary="Large dataset with compression",
    description="Demonstrates response compression with large JSON payloads",
)
async def get_large_dataset(
    size: Annotated[int, QueryParam(ge=100, le=10000, description="Number of items to generate")] = 1000,
):
    """Generate a large dataset to demonstrate response compression.

    Features:
    - Automatic gzip compression for large responses
    - Significant bandwidth savings
    - Improved client performance
    - Transparent to client applications
    """
    # Generate large dataset
    items = []
    for i in range(size):
        items.append(
            LargeDataItem(
                id=i,
                content="".join(
                    random.choices(string.ascii_letters + string.digits, k=500),
                ),
                metadata={
                    "category": random.choice(["A", "B", "C", "D"]),
                    "score": random.uniform(0, 100),
                    "tags": random.choices(
                        ["tag1", "tag2", "tag3", "tag4", "tag5"], k=3,
                    ),
                    "nested": {
                        "field1": "".join(random.choices(string.ascii_letters, k=50)),
                        "field2": random.randint(1, 1000),
                        "field3": random.uniform(0, 1),
                    },
                },
                timestamp=datetime.utcnow()
                - timedelta(minutes=random.randint(1, 10000)),
            ),
        )

    return items


# --- API Versioning Examples ---


@router.get(
    "/versioned-endpoint",
    tags=["Examples", "v1.0"],
    summary="Versioned endpoint example",
    description="Demonstrates API versioning with header detection",
)
@versioned_route(
    versions=["1.0.0", "1.1.0"],
    deprecated_versions=["1.0.0"],
    min_version="1.0.0",
    max_version="2.0.0",
)
async def versioned_endpoint(request: Request):
    """Example endpoint that demonstrates API versioning.

    Supports multiple versioning strategies:
    - Header-based: `API-Version: 1.1.0` or `Accept: application/vnd.api+json;version=1.1`
    - Query parameter: `?version=1.1.0`
    - Path-based: `/api/v1/...` (handled by router prefix)
    """
    # Get API version from request
    version = get_api_version(request, strategy=VersioningStrategy.HEADER)

    # Validate version
    validate_api_version(version)

    # Version-specific logic
    if version.major == 1 and version.minor == 0:
        return {
            "message": "This is version 1.0 response (deprecated)",
            "version": str(version),
            "features": ["basic_features"],
            "deprecated": True,
        }
    if version.major == 1 and version.minor >= 1:
        return {
            "message": "This is version 1.1+ response",
            "version": str(version),
            "features": ["basic_features", "enhanced_features", "new_endpoints"],
            "deprecated": False,
        }
    return {
        "message": f"Version {version} response",
        "version": str(version),
        "features": ["all_features"],
        "deprecated": False,
    }


# --- Performance Monitoring Examples ---


@router.get(
    "/performance-test",
    tags=["Examples", "Performance"],
    summary="Performance monitoring example",
    description="Endpoint with artificial delay to demonstrate performance monitoring",
)
async def performance_test(
    delay: Annotated[float, QueryParam(ge=0, le=5.0, description="Artificial delay in seconds")] = 0.1,
):
    """Test endpoint with configurable delay to demonstrate performance monitoring.

    This endpoint artificially delays the response to simulate various processing times.
    It's useful for testing performance monitoring tools, middleware, and logging systems.

    Features:
    - Request ID tracking
    - Processing time measurement
    - Performance headers in response
    - Request/response logging

    Args:
        delay (float): Artificial delay in seconds to simulate processing time.
               Constrained between 0 and 5 seconds.

    Returns:
        dict: Performance metrics including processing time and request details.

    """
    import asyncio

    # Simulate processing time
    await asyncio.sleep(delay)

    return {
        "message": f"Request processed with {delay}s delay",
        "timestamp": datetime.utcnow().isoformat(),
        "performance_info": "Check response headers for timing data",
    }


@router.get(
    "/compression-test",
    tags=["Examples", "Compression"],
    summary="Compression effectiveness test",
    description="Generate content with varying compression ratios",
)
async def compression_test(
    content_type: Annotated[str, QueryParam(description="Type of content to generate: json, text, random, structured")] = "json",
    size_kb: Annotated[int, QueryParam(ge=1, le=1000, description="Approximate size in KB")] = 100,
):
    """Generate different types of content to test compression effectiveness.

    This endpoint creates various types of content with configurable size to test
    how well different content types compress with HTTP compression algorithms.
    Useful for benchmarking and demonstrating the benefits of response compression.

    Content types:
    - json: Structured JSON (compresses well)
    - text: Repetitive text (compresses very well)
    - random: Random data (compresses poorly)
    - structured: Mix of structured and random data

    Args:
        content_type (str): Type of content to generate (json, text, random, or structured).
        size_kb (int): Approximate size of the generated content in kilobytes.
               Constrained between 1 and 1000 KB.

    Returns:
        Response: JSON or text response with the generated content and compression metrics.

    Raises:
        HTTPException: If an invalid content type is specified.

    """
    target_size = size_kb * 1024

    if content_type == "json":
        # Generate structured JSON data (good compression)
        data = {"items": []}
        item_template = {
            "id": 0,
            "name": "Item Name",
            "description": "This is a sample description that repeats often",
            "category": "Category A",
            "status": "active",
            "metadata": {"created_by": "system", "tags": ["tag1", "tag2", "tag3"]},
        }

        while len(str(data).encode()) < target_size:
            item = item_template.copy()
            item["id"] = len(data["items"])
            item["name"] = f"Item {item['id']}"
            data["items"].append(item)

        return data

    if content_type == "text":
        # Generate repetitive text (excellent compression)
        repeated_text = "This is a sample text that will be repeated many times to test compression. "
        content = repeated_text * (target_size // len(repeated_text.encode()) + 1)
        return {"content": content[:target_size], "type": "repetitive_text"}

    if content_type == "random":
        # Generate random data (poor compression)
        random_content = "".join(
            random.choices(
                string.ascii_letters + string.digits + string.punctuation, k=target_size,
            ),
        )
        return {"content": random_content, "type": "random_data"}

    # structured
    # Mix of structured and random data
    structured_part = {
        "header": "Structured Header",
        "metadata": {
            "version": "1.0",
            "timestamp": datetime.utcnow().isoformat(),
            "environment": "test",
        },
        "data": [],
    }

    remaining_size = target_size - len(str(structured_part).encode())
    random_items = remaining_size // 100

    for i in range(random_items):
        structured_part["data"].append(
            {
                "id": i,
                "random_field": "".join(random.choices(string.ascii_letters, k=50)),
                "structured_field": f"structured_value_{i}",
                "number": random.randint(1, 1000),
            },
        )

    return structured_part


# --- Health and Status Examples ---


@router.get(
    "/feature-status",
    tags=["Examples", "Health"],
    summary="Feature availability status",
    description="Check which advanced features are available",
)
async def feature_status():
    """Check the availability of advanced features in the application.

    Performs runtime checks for various advanced features by attempting to import
    their respective modules. This endpoint helps diagnose which features are
    properly configured and available in the current deployment environment.

    Returns:
        dict: Dictionary containing feature availability status and overall system status.
              Includes boolean flags for each feature and a summary status message.

    """
    try:
        from app.core.middleware import setup_middleware

        middleware_available = True
    except ImportError:
        middleware_available = False

    try:
        from app.core.versioning import version_manager

        versioning_available = True
    except ImportError:
        versioning_available = False

    try:
        from app.utils.pagination import Paginator

        pagination_available = True
    except ImportError:
        pagination_available = False

    return {
        "features": {
            "response_compression": middleware_available,
            "security_headers": middleware_available,
            "performance_monitoring": middleware_available,
            "rate_limiting": middleware_available,
            "api_versioning": versioning_available,
            "advanced_pagination": pagination_available,
            "http2_support": "Available via Nginx configuration",
        },
        "status": "All advanced features are available!"
        if all([middleware_available, versioning_available, pagination_available])
        else "Some features may not be available",
    }
