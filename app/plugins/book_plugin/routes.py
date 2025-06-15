"""
Book FastAPI routes with enhanced timeout and error handling
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import JSONResponse

# Import timeout utilities
from app.core.timeouts import with_timeout, database_timeout_context, TimeoutException

from .schemas import (
    BookCreate, 
    BookUpdate, 
    BookResponse,
    BookSearch
)
from .services import BookService


class BookRoutes:
    """FastAPI routes for Book with enhanced timeouts"""
    
    def __init__(self):
        self.router = APIRouter()
        self.service = BookService()
        self.setup_routes()
    
    def setup_routes(self):
        """Setup CRUD routes for Book with appropriate timeouts"""
        
        @self.router.post("/books/", response_model=BookResponse, tags=["Book"])
        @with_timeout(timeout_seconds=10.0)
        async def create_book(item: BookCreate, request: Request):
            """Create a new book"""
            try:
                # Use database timeout context for data operations
                async with database_timeout_context(8.0):
                    result = await self.service.create(**item.dict())
                
                # Emit creation event
                self.emit_event("book_created", 
                              id=result.id, 
                              plugin="book_plugin")
                
                return result
                
            except TimeoutException as e:
                raise HTTPException(
                    status_code=504,
                    detail={
                        "error": "operation_timeout",
                        "message": "Create operation timed out",
                        "timeout_seconds": 10.0,
                        "operation": "create_book"
                    }
                )
            except Exception as e:
                raise HTTPException(status_code=400, detail=str(e))
        
        @self.router.get("/books/", response_model=List[BookResponse], tags=["Book"])
        @with_timeout(timeout_seconds=5.0)
        async def get_books(
            request: Request,
            skip: int = Query(0, ge=0),
            limit: int = Query(100, ge=1, le=1000)
        ):
            """Get all books with pagination"""
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
                        "operation": "get_books",
                        "parameters": {"skip": skip, "limit": limit}
                    }
                )
            except Exception as e:
                raise HTTPException(status_code=400, detail=str(e))
        
        @self.router.get("/books/{item_id}", response_model=BookResponse, tags=["Book"])
        @with_timeout(timeout_seconds=5.0)
        async def get_book(item_id: int, request: Request):
            """Get a specific book by ID"""
            try:
                async with database_timeout_context(8.0):
                    result = await self.service.get(item_id)
                    
                if not result:
                    raise HTTPException(status_code=404, detail="Book not found")
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
                        "operation": "get_book",
                        "item_id": item_id
                    }
                )
            except Exception as e:
                raise HTTPException(status_code=400, detail=str(e))
        
        @self.router.put("/books/{item_id}", response_model=BookResponse, tags=["Book"])
        @with_timeout(timeout_seconds=10.0)
        async def update_book(item_id: int, item: BookUpdate, request: Request):
            """Update a book"""
            try:
                async with database_timeout_context(8.0):
                    result = await self.service.update(item_id, **item.dict(exclude_unset=True))
                    
                if not result:
                    raise HTTPException(status_code=404, detail="Book not found")
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
                        "operation": "update_book",
                        "item_id": item_id
                    }
                )
            except Exception as e:
                raise HTTPException(status_code=400, detail=str(e))
        
        @self.router.delete("/books/{item_id}", tags=["Book"])
        @with_timeout(timeout_seconds=5.0)
        async def delete_book(item_id: int, request: Request):
            """Delete a book"""
            try:
                async with database_timeout_context(8.0):
                    success = await self.service.delete(item_id)
                    
                if not success:
                    raise HTTPException(status_code=404, detail="Book not found")
                return {"message": "Book deleted successfully"}
                
            except HTTPException:
                raise
            except TimeoutException as e:
                raise HTTPException(
                    status_code=504,
                    detail={
                        "error": "operation_timeout",
                        "message": "Delete operation timed out",
                        "timeout_seconds": 5.0,
                        "operation": "delete_book",
                        "item_id": item_id
                    }
                )
            except Exception as e:
                raise HTTPException(status_code=400, detail=str(e))
        
        @self.router.get("/books/search/", response_model=List[BookResponse], tags=["Book"])
        @with_timeout(timeout_seconds=15.0)
        async def search_books(
            request: Request,
            q: str = Query(..., min_length=1),
            limit: int = Query(10, ge=1, le=100)
        ):
            """Search books"""
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
                        "operation": "search_books",
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
