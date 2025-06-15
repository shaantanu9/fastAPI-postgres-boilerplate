"""
Order FastAPI routes with enhanced timeout and error handling
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import JSONResponse

# Import timeout utilities
from app.core.timeouts import with_timeout, database_timeout_context, TimeoutException

from .schemas import (
    OrderCreate, 
    OrderUpdate, 
    OrderResponse,
    OrderSearch
)
from .services import OrderService


class OrderRoutes:
    """FastAPI routes for Order with enhanced timeouts"""
    
    def __init__(self):
        self.router = APIRouter()
        self.service = OrderService()
        self.setup_routes()
    
    def setup_routes(self):
        """Setup CRUD routes for Order with appropriate timeouts"""
        
        @self.router.post("/orders/", response_model=OrderResponse, tags=["Order"])
        @with_timeout(timeout_seconds=10.0)
        async def create_order(item: OrderCreate, request: Request):
            """Create a new order"""
            try:
                # Use database timeout context for data operations
                async with database_timeout_context(8.0):
                    result = await self.service.create(**item.dict())
                
                # Emit creation event
                self.emit_event("order_created", 
                              id=result.id, 
                              plugin="order_plugin")
                
                return result
                
            except TimeoutException as e:
                raise HTTPException(
                    status_code=504,
                    detail={
                        "error": "operation_timeout",
                        "message": "Create operation timed out",
                        "timeout_seconds": 10.0,
                        "operation": "create_order"
                    }
                )
            except Exception as e:
                raise HTTPException(status_code=400, detail=str(e))
        
        @self.router.get("/orders/", response_model=List[OrderResponse], tags=["Order"])
        @with_timeout(timeout_seconds=5.0)
        async def get_orders(
            request: Request,
            skip: int = Query(0, ge=0),
            limit: int = Query(100, ge=1, le=1000)
        ):
            """Get all orders with pagination"""
            try:
                async with database_timeout_context(8.0):
                    results = await self.service.get_all(skip=skip, limit=limit)
                return results
                
            except TimeoutException as e:
                raise HTTPException(
                    status_code=504,
                    detail={
                        "error": "database_timeout",
                        "message": "Database query timed out",
                        "timeout_seconds": 8.0,
                        "operation": "get_orders",
                        "parameters": {"skip": skip, "limit": limit}
                    }
                )
            except Exception as e:
                raise HTTPException(status_code=400, detail=str(e))
        
        @self.router.get("/orders/{item_id}", response_model=OrderResponse, tags=["Order"])
        @with_timeout(timeout_seconds=5.0)
        async def get_order(item_id: int, request: Request):
            """Get a specific order by ID"""
            try:
                async with database_timeout_context(8.0):
                    result = await self.service.get(item_id)
                    
                if not result:
                    raise HTTPException(status_code=404, detail="Order not found")
                return result
                
            except HTTPException:
                raise
            except TimeoutException as e:
                raise HTTPException(
                    status_code=504,
                    detail={
                        "error": "database_timeout",
                        "message": "Database lookup timed out",
                        "timeout_seconds": 8.0,
                        "operation": "get_order",
                        "item_id": item_id
                    }
                )
            except Exception as e:
                raise HTTPException(status_code=400, detail=str(e))
        
        @self.router.put("/orders/{item_id}", response_model=OrderResponse, tags=["Order"])
        @with_timeout(timeout_seconds=10.0)
        async def update_order(item_id: int, item: OrderUpdate, request: Request):
            """Update a order"""
            try:
                async with database_timeout_context(8.0):
                    result = await self.service.update(item_id, **item.dict(exclude_unset=True))
                    
                if not result:
                    raise HTTPException(status_code=404, detail="Order not found")
                return result
                
            except HTTPException:
                raise
            except TimeoutException as e:
                raise HTTPException(
                    status_code=504,
                    detail={
                        "error": "operation_timeout",
                        "message": "Update operation timed out",
                        "timeout_seconds": 10.0,
                        "operation": "update_order",
                        "item_id": item_id
                    }
                )
            except Exception as e:
                raise HTTPException(status_code=400, detail=str(e))
        
        @self.router.delete("/orders/{item_id}", tags=["Order"])
        @with_timeout(timeout_seconds=5.0)
        async def delete_order(item_id: int, request: Request):
            """Delete a order"""
            try:
                async with database_timeout_context(8.0):
                    success = await self.service.delete(item_id)
                    
                if not success:
                    raise HTTPException(status_code=404, detail="Order not found")
                return {"message": "Order deleted successfully"}
                
            except HTTPException:
                raise
            except TimeoutException as e:
                raise HTTPException(
                    status_code=504,
                    detail={
                        "error": "operation_timeout",
                        "message": "Delete operation timed out",
                        "timeout_seconds": 5.0,
                        "operation": "delete_order",
                        "item_id": item_id
                    }
                )
            except Exception as e:
                raise HTTPException(status_code=400, detail=str(e))
        
        @self.router.get("/orders/search/", response_model=List[OrderResponse], tags=["Order"])
        @with_timeout(timeout_seconds=15.0)
        async def search_orders(
            request: Request,
            q: str = Query(..., min_length=1),
            limit: int = Query(10, ge=1, le=100)
        ):
            """Search orders"""
            try:
                async with database_timeout_context(8.0):
                    results = await self.service.search(q, limit=limit)
                return results
                
            except TimeoutException as e:
                raise HTTPException(
                    status_code=504,
                    detail={
                        "error": "search_timeout",
                        "message": "Search operation timed out",
                        "timeout_seconds": 15.0,
                        "operation": "search_orders",
                        "query": q,
                        "limit": limit
                    }
                )
            except Exception as e:
                raise HTTPException(status_code=400, detail=str(e))
        
        
        
        @self.router.post("/orders/bulk", response_model=List[OrderResponse], tags=["Order"])
        @with_timeout(timeout_seconds=60.0)
        async def create_bulk_orders(items: List[OrderCreate], request: Request):
            """Create multiple orders"""
            try:
                # Bulk operations use longer database timeouts
                async with database_timeout_context(48.0):
                    results = await self.service.bulk_create(items)
                    
                self.emit_event("order_bulk_created", count=len(results))
                return results
                
            except TimeoutException as e:
                raise HTTPException(
                    status_code=504,
                    detail={
                        "error": "bulk_operation_timeout",
                        "message": "Bulk create operation timed out",
                        "timeout_seconds": 60.0,
                        "operation": "bulk_create_orders",
                        "item_count": len(items)
                    }
                )
            except Exception as e:
                raise HTTPException(status_code=400, detail=str(e))
        
        @self.router.put("/orders/bulk", response_model=List[OrderResponse], tags=["Order"])
        @with_timeout(timeout_seconds=60.0)
        async def update_bulk_orders(updates: List[OrderUpdate], request: Request):
            """Update multiple orders"""
            try:
                async with database_timeout_context(48.0):
                    results = await self.service.bulk_update(updates)
                    
                self.emit_event("order_bulk_updated", count=len(results))
                return results
                
            except TimeoutException as e:
                raise HTTPException(
                    status_code=504,
                    detail={
                        "error": "bulk_operation_timeout",
                        "message": "Bulk update operation timed out",
                        "timeout_seconds": 60.0,
                        "operation": "bulk_update_orders",
                        "update_count": len(updates)
                    }
                )
            except Exception as e:
                raise HTTPException(status_code=400, detail=str(e))
        
        @self.router.delete("/orders/bulk", tags=["Order"])
        @with_timeout(timeout_seconds=30.0)
        async def delete_bulk_orders(ids: List[int], request: Request):
            """Delete multiple orders"""
            try:
                async with database_timeout_context(24.0):
                    deleted_count = await self.service.bulk_delete(ids)
                    
                self.emit_event("order_bulk_deleted", count=deleted_count)
                return {"message": f"Deleted {deleted_count} orders successfully"}
                
            except TimeoutException as e:
                raise HTTPException(
                    status_code=504,
                    detail={
                        "error": "bulk_operation_timeout",
                        "message": "Bulk delete operation timed out",
                        "timeout_seconds": 30.0,
                        "operation": "bulk_delete_orders",
                        "id_count": len(ids)
                    }
                )
            except Exception as e:
                raise HTTPException(status_code=400, detail=str(e))
    
    def get_router(self) -> APIRouter:
        """Get the FastAPI router"""
        return self.router
    
    def emit_event(self, event_name: str, **kwargs):
        """Emit plugin events for monitoring and integration"""
        try:
            # Try to use the plugin system's event emitter
            from app.core.plugin_system import get_plugin_manager
            plugin_manager = get_plugin_manager()
            if plugin_manager and hasattr(plugin_manager, 'emit_event'):
                plugin_manager.emit_event(event_name, **kwargs)
        except ImportError:
            # Fallback: just log the event
            print(f"📡 Event: {event_name} - {kwargs}")
        except Exception as e:
            # Don't let event emission break the main functionality
            print(f"⚠️ Event emission failed: {e}")
