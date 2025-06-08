# app/api/v1/endpoints/listing.py

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.listing_service import (
    BaseListingService,
    FilterCriteria,
    FilterOperator,
    ListingRequest,
    ListingResponse,
    ModelIntrospector,
    PaginationParams,
    SearchParams,
    SortCriteria,
    SortOrder,
)
from app.db.base import Base

# Import your models here for dynamic endpoint creation
from app.db.models.user import User
from app.db.session import get_db

# Product model not available yet - uncomment when created
# from app.db.models.product import Product


router = APIRouter()


class ModelListingEndpoint:
    """Dynamic listing endpoint creator for any SQLAlchemy model.

    This class provides a factory pattern for creating standardized listing endpoints
    for any SQLAlchemy model. It automatically generates POST and GET endpoints with
    advanced filtering, sorting, pagination, and search capabilities.
    """

    def __init__(self, model: type[Base], route_prefix: str) -> None:
        """Initialize a new ModelListingEndpoint instance.

        Args:
            model (Type[Base]): SQLAlchemy model class to create endpoints for.
            route_prefix (str): URL prefix for the endpoints (e.g., "users").

        """
        self.model = model
        self.route_prefix = route_prefix
        self.service = BaseListingService(model)
        self.introspector = ModelIntrospector()

    def create_listing_endpoint(self):
        """Create the listing endpoints for this model.

        Generates three endpoints:
        - POST /{route_prefix}/listing: Advanced filtering with request body
        - GET /{route_prefix}/listing: Simplified filtering with query parameters
        - GET /{route_prefix}/fields: Metadata about available fields

        Returns:
            tuple: The three endpoint functions (list_items, list_items_get, get_model_fields).

        """

        @router.post(f"/{self.route_prefix}/listing")
        async def list_items(
            request: ListingRequest, session: Annotated[AsyncSession, Depends(get_db)],
        ) -> ListingResponse:
            """Universal listing endpoint with advanced filtering, sorting, and search.

            This POST endpoint accepts a structured request body with advanced filtering,
            sorting, pagination, and search options. It provides maximum flexibility for
            complex queries.

            Args:
                request (ListingRequest): Structured request with filtering, sorting, and pagination options.
                session (AsyncSession): Database session dependency.

            Returns:
                ListingResponse: Paginated response with items matching the criteria.

            Raises:
                HTTPException: If an error occurs during the listing operation.

            """
            try:
                return await self.service.list_items(session, request)
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to list {self.model.__name__} items: {e!s}",
                )

        @router.get(f"/{self.route_prefix}/listing")
        async def list_items_get(
            # Pagination
            page: Annotated[int, Query(ge=1, description="Page number")] = 1,
            page_size: Annotated[int, Query(ge=1, le=100, description="Items per page")] = 20,
            # Search
            search: Annotated[str | None, Query(description="Search query")] = None,
            search_fields: Annotated[list[str] | None, Query(description="Fields to search in")] = None,
            # Sorting
            sort_by: Annotated[str | None, Query(description="Field to sort by")] = None,
            sort_order: Annotated[SortOrder | None, Query(description="Sort order")] = SortOrder.ASC,
            # Include relationships
            include: Annotated[list[str] | None, Query(description="Relationships to include")] = None,
            session: AsyncSession = Depends(get_db),
        ) -> ListingResponse:
            """GET version of listing endpoint with query parameters.

            This endpoint provides the same functionality as the POST version but uses
            query parameters instead of a request body. It's more convenient for simple
            queries and direct URL access.

            Args:
                page (int): Page number for pagination (starts at 1).
                page_size (int): Number of items per page (1-100).
                search (Optional[str]): General search query across searchable fields.
                search_fields (Optional[List[str]]): Specific fields to search within.
                sort_by (Optional[str]): Field to sort results by.
                sort_order (Optional[SortOrder]): Sort direction (ASC or DESC).
                include (Optional[List[str]]): Related entities to include in the response.
                session (AsyncSession): Database session dependency.

            Returns:
                ListingResponse: Paginated response with items matching the criteria.

            Raises:
                HTTPException: If an error occurs during the listing operation.

            """
            # Build request from query parameters
            request = ListingRequest(
                pagination=PaginationParams(page=page, page_size=page_size),
                search=SearchParams(query=search, fields=search_fields)
                if search
                else None,
                sort=[SortCriteria(field=sort_by, order=sort_order)] if sort_by else [],
                include_relations=include or [],
            )

            try:
                return await self.service.list_items(session, request)
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to list {self.model.__name__} items: {e!s}",
                )

        @router.get(f"/{self.route_prefix}/fields")
        async def get_model_fields() -> dict[str, Any]:
            """Get filterable and searchable fields for the model.

            This endpoint provides metadata about the model's fields that can be used
            for filtering and searching. It's useful for client applications that need
            to dynamically build filter interfaces.

            Returns:
                Dict[str, Any]: Dictionary containing:
                    - filterable_fields: List of fields that can be used for filtering
                    - searchable_fields: List of fields that can be used for text search
                    - model_name: Name of the model

            """
            return {
                "filterable_fields": self.service.get_filterable_fields(),
                "searchable_fields": self.service.get_searchable_fields(),
                "model_name": self.model.__name__,
            }

        return list_items, list_items_get, get_model_fields


# Create listing endpoints for all models
def setup_model_listings() -> None:
    """Set up listing endpoints for all registered models.

    This function initializes dynamic listing endpoints for each model in the application.
    It creates standardized endpoints with consistent filtering, sorting, and pagination
    capabilities for each registered model using the ModelListingEndpoint class.

    Currently configured models:
    - User: Creates /users/listing endpoints
    - Additional models can be added as they become available
    """
    # User listing endpoints
    user_endpoint = ModelListingEndpoint(User, "users")
    user_endpoint.create_listing_endpoint()

    # Product listing endpoints (uncomment when Product model is available)
    # product_endpoint = ModelListingEndpoint(Product, "products")
    # product_endpoint.create_listing_endpoint()

    # Add more models as needed
    # Example for future models:
    # order_endpoint = ModelListingEndpoint(Order, "orders")
    # order_endpoint.create_listing_endpoint()


# Initialize all model listings
setup_model_listings()


# Additional utility endpoints
@router.get("/filter-operators")
async def get_filter_operators() -> list[dict[str, str]]:
    """Get available filter operators for use in advanced filtering.

    Returns a list of all supported filter operators with their descriptions
    and examples of usage. Useful for client applications that need to build
    dynamic filtering interfaces.

    Returns:
        List[Dict[str, str]]: List of filter operators with descriptions.

    """
    return [
        {"value": op.value, "description": op.value.replace("_", " ").title()}
        for op in FilterOperator
    ]


@router.get("/sort-orders")
async def get_sort_orders() -> list[dict[str, str]]:
    """Get available sort orders for use in listing endpoints.

    Returns a list of all supported sort orders with their descriptions.
    Useful for client applications that need to build dynamic sorting interfaces.

    Returns:
        List[Dict[str, str]]: List of sort orders with descriptions.

    """
    return [
        {"value": order.value, "description": order.value.upper()}
        for order in SortOrder
    ]


# Example of advanced filtering endpoint
@router.post("/users/advanced-listing")
async def advanced_user_listing(
    # Basic filters - using actual User model field names
    username__contains: Annotated[str | None, Query(description="Username contains")] = None,
    email__contains: Annotated[str | None, Query(description="Email contains")] = None,
    first_name__contains: Annotated[str | None, Query(description="First name contains")] = None,
    last_name__contains: Annotated[str | None, Query(description="Last name contains")] = None,
    is_active__eq: Annotated[bool | None, Query(description="Is active equals")] = None,
    is_verified__eq: Annotated[bool | None, Query(description="Is verified equals")] = None,
    # Date range filters
    created_at__gte: Annotated[str | None, Query(description="Created after (ISO date)")] = None,
    created_at__lte: Annotated[str | None, Query(description="Created before (ISO date)")] = None,
    # Pagination
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    # Search
    search: Annotated[str | None, Query()] = None,
    # Sort
    sort_by: Annotated[str | None, Query()] = "created_at",
    sort_order: Annotated[SortOrder | None, Query()] = SortOrder.DESC,
    session: AsyncSession = Depends(get_db),
) -> ListingResponse:
    """Advanced user listing with pre-defined common filters.

    This endpoint provides a more user-friendly interface for filtering and sorting users
    compared to the generic listing endpoint. It exposes common filter fields directly
    as query parameters with strongly typed validation.

    Args:
        username__contains (Optional[str]): Filter by username containing this string.
        email__contains (Optional[str]): Filter by email containing this string.
        first_name__contains (Optional[str]): Filter by first name containing this string.
        last_name__contains (Optional[str]): Filter by last name containing this string.
        is_active__eq (Optional[bool]): Filter by active status.
        is_verified__eq (Optional[bool]): Filter by verification status.
        created_at__gte (Optional[str]): Filter by creation date after this ISO date.
        created_at__lte (Optional[str]): Filter by creation date before this ISO date.
        page (int): Page number for pagination (starts at 1).
        page_size (int): Number of items per page (1-100).
        search (Optional[str]): General search query across searchable fields.
        sort_by (Optional[str]): Field to sort results by.
        sort_order (Optional[SortOrder]): Sort direction (ASC or DESC).
        session (AsyncSession): Database session dependency.

    Returns:
        ListingResponse: Paginated list of users matching the filter criteria.

    """
    # Build filters dynamically
    filters = []

    if username__contains:
        filters.append(
            FilterCriteria(
                field="username",
                operator=FilterOperator.CONTAINS,
                value=username__contains,
            ),
        )

    if email__contains:
        filters.append(
            FilterCriteria(
                field="email", operator=FilterOperator.CONTAINS, value=email__contains,
            ),
        )

    if first_name__contains:
        filters.append(
            FilterCriteria(
                field="first_name",
                operator=FilterOperator.CONTAINS,
                value=first_name__contains,
            ),
        )

    if last_name__contains:
        filters.append(
            FilterCriteria(
                field="last_name",
                operator=FilterOperator.CONTAINS,
                value=last_name__contains,
            ),
        )

    if is_active__eq is not None:
        filters.append(
            FilterCriteria(
                field="is_active", operator=FilterOperator.EQUALS, value=is_active__eq,
            ),
        )

    if is_verified__eq is not None:
        filters.append(
            FilterCriteria(
                field="is_verified",
                operator=FilterOperator.EQUALS,
                value=is_verified__eq,
            ),
        )

    if created_at__gte:
        filters.append(
            FilterCriteria(
                field="created_at",
                operator=FilterOperator.GREATER_THAN_OR_EQUAL,
                value=created_at__gte,
            ),
        )

    if created_at__lte:
        filters.append(
            FilterCriteria(
                field="created_at",
                operator=FilterOperator.LESS_THAN_OR_EQUAL,
                value=created_at__lte,
            ),
        )

    # Build request
    request = ListingRequest(
        pagination=PaginationParams(page=page, page_size=page_size),
        filters=filters,
        sort=[SortCriteria(field=sort_by, order=sort_order)] if sort_by else [],
        search=SearchParams(query=search) if search else None,
    )

    # Use service
    service = BaseListingService(User)
    return await service.list_items(session, request)


# Export functionality for other modules
@router.get("/available-models")
async def list_available_models() -> list[dict[str, str]]:
    """List all models available for dynamic listing endpoints.

    Returns information about all registered models including their names,
    table names, and available fields for filtering and sorting.

    Returns:
        List[Dict[str, str]]: List of available models with their metadata.

    """
    return [
        {"name": "User", "endpoint": "/users/listing"},
        # {"name": "Product", "endpoint": "/products/listing"},  # Uncomment when Product model is available
        # Add more models as they're implemented
    ]
