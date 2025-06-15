"""
Customer FastAPI routes with enhanced timeout and error handling
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import JSONResponse

# Import timeout utilities
from app.core.timeouts import with_timeout, database_timeout_context, TimeoutException

from .schemas import (
    CustomerCreate, 
    CustomerUpdate, 
    CustomerResponse,
    CustomerSearch
)
from .services import CustomerService


class CustomerRoutes:
    """FastAPI routes for Customer with enhanced timeouts"""
    
    def __init__(self):
        self.router = APIRouter()
        self.service = CustomerService()
        self.setup_routes()
    
    def setup_routes(self):
        """Setup CRUD routes for Customer with appropriate timeouts"""
        
        @self.router.post("/customers/", response_model=CustomerResponse, tags=["Customer"])
        @with_timeout(timeout_seconds=10.0)
        async def create_customer(item: CustomerCreate, request: Request):
            """Create a new customer"""
            try:
                # Use database timeout context for data operations
                async with database_timeout_context(8.0):
                    result = await self.service.create(**item.dict())
                
                # Emit creation event
                self.emit_event("customer_created", 
                              id=result.id, 
                              plugin="customer_plugin")
                
                return result
                
            except TimeoutException as e:
                raise HTTPException(
                    status_code=504,
                    detail={
                        "error": "operation_timeout",
                        "message": "Create operation timed out",
                        "timeout_seconds": 10.0,
                        "operation": "create_customer"
                    }
                )
            except Exception as e:
                raise HTTPException(status_code=400, detail=str(e))
        
        @self.router.get("/customers/", response_model=List[CustomerResponse], tags=["Customer"])
        @with_timeout(timeout_seconds=5.0)
        async def get_customers(
            request: Request,
            skip: int = Query(0, ge=0),
            limit: int = Query(100, ge=1, le=1000)
        ):
            """Get all customers with pagination"""
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
                        "operation": "get_customers",
                        "parameters": {"skip": skip, "limit": limit}
                    }
                )
            except Exception as e:
                raise HTTPException(status_code=400, detail=str(e))
        
        @self.router.get("/customers/{item_id}", response_model=CustomerResponse, tags=["Customer"])
        @with_timeout(timeout_seconds=5.0)
        async def get_customer(item_id: int, request: Request):
            """Get a specific customer by ID"""
            try:
                async with database_timeout_context(8.0):
                    result = await self.service.get(item_id)
                    
                if not result:
                    raise HTTPException(status_code=404, detail="Customer not found")
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
                        "operation": "get_customer",
                        "item_id": item_id
                    }
                )
            except Exception as e:
                raise HTTPException(status_code=400, detail=str(e))
        
        @self.router.put("/customers/{item_id}", response_model=CustomerResponse, tags=["Customer"])
        @with_timeout(timeout_seconds=10.0)
        async def update_customer(item_id: int, item: CustomerUpdate, request: Request):
            """Update a customer"""
            try:
                async with database_timeout_context(8.0):
                    result = await self.service.update(item_id, **item.dict(exclude_unset=True))
                    
                if not result:
                    raise HTTPException(status_code=404, detail="Customer not found")
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
                        "operation": "update_customer",
                        "item_id": item_id
                    }
                )
            except Exception as e:
                raise HTTPException(status_code=400, detail=str(e))
        
        @self.router.delete("/customers/{item_id}", tags=["Customer"])
        @with_timeout(timeout_seconds=5.0)
        async def delete_customer(item_id: int, request: Request):
            """Delete a customer"""
            try:
                async with database_timeout_context(8.0):
                    success = await self.service.delete(item_id)
                    
                if not success:
                    raise HTTPException(status_code=404, detail="Customer not found")
                return {"message": "Customer deleted successfully"}
                
            except HTTPException:
                raise
            except TimeoutException as e:
                raise HTTPException(
                    status_code=504,
                    detail={
                        "error": "operation_timeout",
                        "message": "Delete operation timed out",
                        "timeout_seconds": 5.0,
                        "operation": "delete_customer",
                        "item_id": item_id
                    }
                )
            except Exception as e:
                raise HTTPException(status_code=400, detail=str(e))
        
        @self.router.get("/customers/search/", response_model=List[CustomerResponse], tags=["Customer"])
        @with_timeout(timeout_seconds=15.0)
        async def search_customers(
            request: Request,
            q: str = Query(..., min_length=1),
            limit: int = Query(10, ge=1, le=100)
        ):
            """Search customers"""
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
                        "operation": "search_customers",
                        "query": q,
                        "limit": limit
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
