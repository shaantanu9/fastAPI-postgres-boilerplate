"""
TestItem FastAPI routes with enhanced timeout and error handling
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import JSONResponse

# Import timeout utilities
from app.core.timeouts import with_timeout, database_timeout_context, TimeoutException

from .schemas import (
    TestItemCreate, 
    TestItemUpdate, 
    TestItemResponse,
    TestItemSearch
)
from .services import TestItemService


class TestItemRoutes:
    """FastAPI routes for TestItem with enhanced timeouts"""
    
    def __init__(self):
        self.router = APIRouter()
        self.service = TestItemService()
        self.setup_routes()
    
    def setup_routes(self):
        """Setup CRUD routes for TestItem with appropriate timeouts"""
        
        @self.router.post("/test_items/", response_model=TestItemResponse, tags=["TestItem"])
        @with_timeout(timeout_seconds=10.0)
        async def create_test_item(item: TestItemCreate, request: Request):
            """Create a new test_item"""
            try:
                # Use database timeout context for data operations
                async with database_timeout_context(15.0):
                    result = await self.service.create(**item.dict())
                
                # Emit creation event
                self.emit_event("test_item_created", 
                              id=result.id, 
                              plugin="test_item_plugin")
                
                return result
                
            except TimeoutException as e:
                raise HTTPException(
                    status_code=504,
                    detail={
                        "error": "operation_timeout",
                        "message": "Create operation timed out",
                        "timeout_seconds": 10.0,
                        "operation": "create_test_item"
                    }
                )
            except Exception as e:
                raise HTTPException(status_code=400, detail=str(e))
        
        @self.router.get("/test_items/", response_model=List[TestItemResponse], tags=["TestItem"])
        @with_timeout(timeout_seconds=5.0)
        async def get_test_items(
            request: Request,
            skip: int = Query(0, ge=0),
            limit: int = Query(100, ge=1, le=1000)
        ):
            """Get all test_items with pagination"""
            try:
                async with database_timeout_context(15.0):
                    results = await self.service.get_all(skip=skip, limit=limit)
                return results
                
            except TimeoutException as e:
                raise HTTPException(
                    status_code=504,
                    detail={
                        "error": "database_timeout",
                        "message": "Database query timed out",
                        "timeout_seconds": 15.0,
                        "operation": "get_test_items",
                        "parameters": {"skip": skip, "limit": limit}
                    }
                )
            except Exception as e:
                raise HTTPException(status_code=400, detail=str(e))
        
        @self.router.get("/test_items/{item_id}", response_model=TestItemResponse, tags=["TestItem"])
        @with_timeout(timeout_seconds=5.0)
        async def get_test_item(item_id: int, request: Request):
            """Get a specific test_item by ID"""
            try:
                async with database_timeout_context(15.0):
                    result = await self.service.get(item_id)
                    
                if not result:
                    raise HTTPException(status_code=404, detail="TestItem not found")
                return result
                
            except HTTPException:
                raise
            except TimeoutException as e:
                raise HTTPException(
                    status_code=504,
                    detail={
                        "error": "database_timeout",
                        "message": "Database lookup timed out",
                        "timeout_seconds": 15.0,
                        "operation": "get_test_item",
                        "item_id": item_id
                    }
                )
            except Exception as e:
                raise HTTPException(status_code=400, detail=str(e))
        
        @self.router.put("/test_items/{item_id}", response_model=TestItemResponse, tags=["TestItem"])
        @with_timeout(timeout_seconds=10.0)
        async def update_test_item(item_id: int, item: TestItemUpdate, request: Request):
            """Update a test_item"""
            try:
                async with database_timeout_context(15.0):
                    result = await self.service.update(item_id, **item.dict(exclude_unset=True))
                    
                if not result:
                    raise HTTPException(status_code=404, detail="TestItem not found")
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
                        "operation": "update_test_item",
                        "item_id": item_id
                    }
                )
            except Exception as e:
                raise HTTPException(status_code=400, detail=str(e))
        
        @self.router.delete("/test_items/{item_id}", tags=["TestItem"])
        @with_timeout(timeout_seconds=5.0)
        async def delete_test_item(item_id: int, request: Request):
            """Delete a test_item"""
            try:
                async with database_timeout_context(15.0):
                    success = await self.service.delete(item_id)
                    
                if not success:
                    raise HTTPException(status_code=404, detail="TestItem not found")
                return {"message": "TestItem deleted successfully"}
                
            except HTTPException:
                raise
            except TimeoutException as e:
                raise HTTPException(
                    status_code=504,
                    detail={
                        "error": "operation_timeout",
                        "message": "Delete operation timed out",
                        "timeout_seconds": 5.0,
                        "operation": "delete_test_item",
                        "item_id": item_id
                    }
                )
            except Exception as e:
                raise HTTPException(status_code=400, detail=str(e))
        
        @self.router.get("/test_items/search/", response_model=List[TestItemResponse], tags=["TestItem"])
        @with_timeout(timeout_seconds=30.0)
        async def search_test_items(
            request: Request,
            q: str = Query(..., min_length=1),
            limit: int = Query(10, ge=1, le=100)
        ):
            """Search test_items"""
            try:
                async with database_timeout_context(15.0):
                    results = await self.service.search(q, limit=limit)
                return results
                
            except TimeoutException as e:
                raise HTTPException(
                    status_code=504,
                    detail={
                        "error": "search_timeout",
                        "message": "Search operation timed out",
                        "timeout_seconds": 30.0,
                        "operation": "search_test_items",
                        "query": q,
                        "limit": limit
                    }
                )
            except Exception as e:
                raise HTTPException(status_code=400, detail=str(e))
        
        
        
        @self.router.post("/test_items/bulk", response_model=List[TestItemResponse], tags=["TestItem"])
        @with_timeout(timeout_seconds=60.0)
        async def create_bulk_test_items(items: List[TestItemCreate], request: Request):
            """Create multiple test_items"""
            try:
                # Bulk operations use longer database timeouts
                async with database_timeout_context(48.0):
                    results = await self.service.bulk_create(items)
                    
                self.emit_event("test_item_bulk_created", count=len(results))
                return results
                
            except TimeoutException as e:
                raise HTTPException(
                    status_code=504,
                    detail={
                        "error": "bulk_operation_timeout",
                        "message": "Bulk create operation timed out",
                        "timeout_seconds": 60.0,
                        "operation": "bulk_create_test_items",
                        "item_count": len(items)
                    }
                )
            except Exception as e:
                raise HTTPException(status_code=400, detail=str(e))
        
        @self.router.put("/test_items/bulk", response_model=List[TestItemResponse], tags=["TestItem"])
        @with_timeout(timeout_seconds=60.0)
        async def update_bulk_test_items(updates: List[TestItemUpdate], request: Request):
            """Update multiple test_items"""
            try:
                async with database_timeout_context(48.0):
                    results = await self.service.bulk_update(updates)
                    
                self.emit_event("test_item_bulk_updated", count=len(results))
                return results
                
            except TimeoutException as e:
                raise HTTPException(
                    status_code=504,
                    detail={
                        "error": "bulk_operation_timeout",
                        "message": "Bulk update operation timed out",
                        "timeout_seconds": 60.0,
                        "operation": "bulk_update_test_items",
                        "update_count": len(updates)
                    }
                )
            except Exception as e:
                raise HTTPException(status_code=400, detail=str(e))
        
        @self.router.delete("/test_items/bulk", tags=["TestItem"])
        @with_timeout(timeout_seconds=30.0)
        async def delete_bulk_test_items(ids: List[int], request: Request):
            """Delete multiple test_items"""
            try:
                async with database_timeout_context(24.0):
                    deleted_count = await self.service.bulk_delete(ids)
                    
                self.emit_event("test_item_bulk_deleted", count=deleted_count)
                return {"message": f"Deleted {deleted_count} test_items successfully"}
                
            except TimeoutException as e:
                raise HTTPException(
                    status_code=504,
                    detail={
                        "error": "bulk_operation_timeout",
                        "message": "Bulk delete operation timed out",
                        "timeout_seconds": 30.0,
                        "operation": "bulk_delete_test_items",
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
