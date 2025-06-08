"""ProductTest FastAPI routes with enhanced timeout and error handling."""

from fastapi import APIRouter, HTTPException, Query, Request

# Import timeout utilities
from app.core.timeouts import TimeoutException, database_timeout_context, with_timeout

from .schemas import (
    ProductTestCreate,
    ProductTestResponse,
    ProductTestUpdate,
)
from .services import ProductTestService


class ProductTestRoutes:
    """FastAPI routes for ProductTest with enhanced timeouts."""

    def __init__(self) -> None:
        self.router = APIRouter()
        self.service = ProductTestService()
        self.setup_routes()

    def setup_routes(self) -> None:
        """Setup CRUD routes for ProductTest with appropriate timeouts."""

        @self.router.post(
            "/product_tests/", response_model=ProductTestResponse, tags=["ProductTest"],
        )
        @with_timeout(timeout_seconds=10.0)
        async def create_product_test(item: ProductTestCreate, request: Request):
            """Create a new product_test."""
            try:
                # Use database timeout context for data operations
                async with database_timeout_context(8.0):
                    result = await self.service.create(**item.dict())

                # Emit creation event
                self.emit_event(
                    "product_test_created", id=result.id, plugin="product_test_plugin",
                )

                return result

            except TimeoutException:
                raise HTTPException(
                    status_code=504,
                    detail={
                        "error": "operation_timeout",
                        "message": "Create operation timed out",
                        "timeout_seconds": 10.0,
                        "operation": "create_product_test",
                    },
                )
            except Exception as e:
                raise HTTPException(status_code=400, detail=str(e))

        @self.router.get(
            "/product_tests/",
            response_model=list[ProductTestResponse],
            tags=["ProductTest"],
        )
        @with_timeout(timeout_seconds=5.0)
        async def get_product_tests(
            request: Request,
            skip: int = Query(0, ge=0),
            limit: int = Query(100, ge=1, le=1000),
        ):
            """Get all product_tests with pagination."""
            try:
                async with database_timeout_context(8.0):
                    return await self.service.get_all(skip=skip, limit=limit)

            except TimeoutException:
                raise HTTPException(
                    status_code=504,
                    detail={
                        "error": "database_timeout",
                        "message": "Database query timed out",
                        "timeout_seconds": 8.0,
                        "operation": "get_product_tests",
                        "parameters": {"skip": skip, "limit": limit},
                    },
                )
            except Exception as e:
                raise HTTPException(status_code=400, detail=str(e))

        @self.router.get(
            "/product_tests/{item_id}",
            response_model=ProductTestResponse,
            tags=["ProductTest"],
        )
        @with_timeout(timeout_seconds=5.0)
        async def get_product_test(item_id: int, request: Request):
            """Get a specific product_test by ID."""
            try:
                async with database_timeout_context(8.0):
                    result = await self.service.get(item_id)

                if not result:
                    raise HTTPException(status_code=404, detail="ProductTest not found")
                return result

            except HTTPException:
                raise
            except TimeoutException:
                raise HTTPException(
                    status_code=504,
                    detail={
                        "error": "database_timeout",
                        "message": "Database lookup timed out",
                        "timeout_seconds": 8.0,
                        "operation": "get_product_test",
                        "item_id": item_id,
                    },
                )
            except Exception as e:
                raise HTTPException(status_code=400, detail=str(e))

        @self.router.put(
            "/product_tests/{item_id}",
            response_model=ProductTestResponse,
            tags=["ProductTest"],
        )
        @with_timeout(timeout_seconds=10.0)
        async def update_product_test(
            item_id: int, item: ProductTestUpdate, request: Request,
        ):
            """Update a product_test."""
            try:
                async with database_timeout_context(8.0):
                    result = await self.service.update(
                        item_id, **item.dict(exclude_unset=True),
                    )

                if not result:
                    raise HTTPException(status_code=404, detail="ProductTest not found")
                return result

            except HTTPException:
                raise
            except TimeoutException:
                raise HTTPException(
                    status_code=504,
                    detail={
                        "error": "operation_timeout",
                        "message": "Update operation timed out",
                        "timeout_seconds": 10.0,
                        "operation": "update_product_test",
                        "item_id": item_id,
                    },
                )
            except Exception as e:
                raise HTTPException(status_code=400, detail=str(e))

        @self.router.delete("/product_tests/{item_id}", tags=["ProductTest"])
        @with_timeout(timeout_seconds=5.0)
        async def delete_product_test(item_id: int, request: Request):
            """Delete a product_test."""
            try:
                async with database_timeout_context(8.0):
                    success = await self.service.delete(item_id)

                if not success:
                    raise HTTPException(status_code=404, detail="ProductTest not found")
                return {"message": "ProductTest deleted successfully"}

            except HTTPException:
                raise
            except TimeoutException:
                raise HTTPException(
                    status_code=504,
                    detail={
                        "error": "operation_timeout",
                        "message": "Delete operation timed out",
                        "timeout_seconds": 5.0,
                        "operation": "delete_product_test",
                        "item_id": item_id,
                    },
                )
            except Exception as e:
                raise HTTPException(status_code=400, detail=str(e))

        @self.router.get(
            "/product_tests/search/",
            response_model=list[ProductTestResponse],
            tags=["ProductTest"],
        )
        @with_timeout(timeout_seconds=15.0)
        async def search_product_tests(
            request: Request,
            q: str = Query(..., min_length=1),
            limit: int = Query(10, ge=1, le=100),
        ):
            """Search product_tests."""
            try:
                async with database_timeout_context(8.0):
                    return await self.service.search(q, limit=limit)

            except TimeoutException:
                raise HTTPException(
                    status_code=504,
                    detail={
                        "error": "search_timeout",
                        "message": "Search operation timed out",
                        "timeout_seconds": 15.0,
                        "operation": "search_product_tests",
                        "query": q,
                        "limit": limit,
                    },
                )
            except Exception as e:
                raise HTTPException(status_code=400, detail=str(e))

    def get_router(self) -> APIRouter:
        """Get the FastAPI router."""
        return self.router

    def emit_event(self, event_name: str, **kwargs) -> None:
        """Emit plugin events for monitoring and integration."""
        try:
            # Try to use the plugin system's event emitter
            from app.core.plugin_system import get_plugin_manager

            plugin_manager = get_plugin_manager()
            if plugin_manager and hasattr(plugin_manager, "emit_event"):
                plugin_manager.emit_event(event_name, **kwargs)
        except ImportError:
            # Fallback: just log the event
            pass
        except Exception:
            # Don't let event emission break the main functionality
            pass
