"""
Enhanced FastAPI routes template with timeout integration
"""
from typing import List, Dict, Any
import re


class EnhancedRoutesTemplate:
    """Generates FastAPI routes templates with timeout support"""
    
    def generate(self, model_name: str, fields: List[Dict[str, Any]], with_bulk: bool = False) -> str:
        """Generate FastAPI routes file content with timeout integration"""
        snake_name = re.sub(r'(?<!^)(?=[A-Z])', '_', model_name).lower()
        pascal_name = model_name
        
        # Determine appropriate timeouts based on operation complexity
        timeouts = self._get_operation_timeouts(fields, with_bulk)
        
        bulk_routes = ""
        if with_bulk:
            bulk_routes = self._generate_bulk_routes(pascal_name, snake_name, timeouts)
        
        template = f'''"""
{pascal_name} FastAPI routes with enhanced timeout and error handling
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import JSONResponse

# Import timeout utilities
from app.core.timeouts import with_timeout, database_timeout_context, TimeoutException

from .schemas import (
    {pascal_name}Create, 
    {pascal_name}Update, 
    {pascal_name}Response,
    {pascal_name}Search
)
from .services import {pascal_name}Service


class {pascal_name}Routes:
    """FastAPI routes for {pascal_name} with enhanced timeouts"""
    
    def __init__(self):
        self.router = APIRouter()
        self.service = {pascal_name}Service()
        self.setup_routes()
    
    def setup_routes(self):
        """Setup CRUD routes for {pascal_name} with appropriate timeouts"""
        
        @self.router.post("/{snake_name}s/", response_model={pascal_name}Response, tags=["{pascal_name}"])
        @with_timeout(timeout_seconds={timeouts['create']})
        async def create_{snake_name}(item: {pascal_name}Create, request: Request):
            \"\"\"Create a new {snake_name}\"\"\"
            try:
                # Use database timeout context for data operations
                async with database_timeout_context({timeouts['database']}):
                    result = await self.service.create(**item.dict())
                
                # Emit creation event
                self.emit_event("{snake_name}_created", 
                              id=result.id, 
                              plugin="{snake_name}_plugin")
                
                return result
                
            except TimeoutException as e:
                raise HTTPException(
                    status_code=504,
                    detail={{
                        "error": "operation_timeout",
                        "message": "Create operation timed out",
                        "timeout_seconds": {timeouts['create']},
                        "operation": "create_{snake_name}"
                    }}
                )
            except Exception as e:
                raise HTTPException(status_code=400, detail=str(e))
        
        @self.router.get("/{snake_name}s/", response_model=List[{pascal_name}Response], tags=["{pascal_name}"])
        @with_timeout(timeout_seconds={timeouts['read']})
        async def get_{snake_name}s(
            skip: int = Query(0, ge=0),
            limit: int = Query(100, ge=1, le=1000),
            request: Request
        ):
            \"\"\"Get all {snake_name}s with pagination\"\"\"
            try:
                async with database_timeout_context({timeouts['database']}):
                    results = await self.service.get_all(skip=skip, limit=limit)
                return results
                
            except TimeoutException as e:
                raise HTTPException(
                    status_code=504,
                    detail={{
                        "error": "database_timeout",
                        "message": "Database query timed out",
                        "timeout_seconds": {timeouts['database']},
                        "operation": "get_{snake_name}s",
                        "parameters": {{"skip": skip, "limit": limit}}
                    }}
                )
            except Exception as e:
                raise HTTPException(status_code=400, detail=str(e))
        
        @self.router.get("/{snake_name}s/{{item_id}}", response_model={pascal_name}Response, tags=["{pascal_name}"])
        @with_timeout(timeout_seconds={timeouts['read']})
        async def get_{snake_name}(item_id: int, request: Request):
            \"\"\"Get a specific {snake_name} by ID\"\"\"
            try:
                async with database_timeout_context({timeouts['database']}):
                    result = await self.service.get(item_id)
                    
                if not result:
                    raise HTTPException(status_code=404, detail="{pascal_name} not found")
                return result
                
            except HTTPException:
                raise
            except TimeoutException as e:
                raise HTTPException(
                    status_code=504,
                    detail={{
                        "error": "database_timeout",
                        "message": "Database lookup timed out",
                        "timeout_seconds": {timeouts['database']},
                        "operation": "get_{snake_name}",
                        "item_id": item_id
                    }}
                )
            except Exception as e:
                raise HTTPException(status_code=400, detail=str(e))
        
        @self.router.put("/{snake_name}s/{{item_id}}", response_model={pascal_name}Response, tags=["{pascal_name}"])
        @with_timeout(timeout_seconds={timeouts['update']})
        async def update_{snake_name}(item_id: int, item: {pascal_name}Update, request: Request):
            \"\"\"Update a {snake_name}\"\"\"
            try:
                async with database_timeout_context({timeouts['database']}):
                    result = await self.service.update(item_id, **item.dict(exclude_unset=True))
                    
                if not result:
                    raise HTTPException(status_code=404, detail="{pascal_name} not found")
                return result
                
            except HTTPException:
                raise
            except TimeoutException as e:
                raise HTTPException(
                    status_code=504,
                    detail={{
                        "error": "operation_timeout",
                        "message": "Update operation timed out",
                        "timeout_seconds": {timeouts['update']},
                        "operation": "update_{snake_name}",
                        "item_id": item_id
                    }}
                )
            except Exception as e:
                raise HTTPException(status_code=400, detail=str(e))
        
        @self.router.delete("/{snake_name}s/{{item_id}}", tags=["{pascal_name}"])
        @with_timeout(timeout_seconds={timeouts['delete']})
        async def delete_{snake_name}(item_id: int, request: Request):
            \"\"\"Delete a {snake_name}\"\"\"
            try:
                async with database_timeout_context({timeouts['database']}):
                    success = await self.service.delete(item_id)
                    
                if not success:
                    raise HTTPException(status_code=404, detail="{pascal_name} not found")
                return {{"message": "{pascal_name} deleted successfully"}}
                
            except HTTPException:
                raise
            except TimeoutException as e:
                raise HTTPException(
                    status_code=504,
                    detail={{
                        "error": "operation_timeout",
                        "message": "Delete operation timed out",
                        "timeout_seconds": {timeouts['delete']},
                        "operation": "delete_{snake_name}",
                        "item_id": item_id
                    }}
                )
            except Exception as e:
                raise HTTPException(status_code=400, detail=str(e))
        
        @self.router.get("/{snake_name}s/search/", response_model=List[{pascal_name}Response], tags=["{pascal_name}"])
        @with_timeout(timeout_seconds={timeouts['search']})
        async def search_{snake_name}s(
            q: str = Query(..., min_length=1),
            limit: int = Query(10, ge=1, le=100),
            request: Request
        ):
            \"\"\"Search {snake_name}s\"\"\"
            try:
                async with database_timeout_context({timeouts['database']}):
                    results = await self.service.search(q, limit=limit)
                return results
                
            except TimeoutException as e:
                raise HTTPException(
                    status_code=504,
                    detail={{
                        "error": "search_timeout",
                        "message": "Search operation timed out",
                        "timeout_seconds": {timeouts['search']},
                        "operation": "search_{snake_name}s",
                        "query": q,
                        "limit": limit
                    }}
                )
            except Exception as e:
                raise HTTPException(status_code=400, detail=str(e))
        
        {bulk_routes}
    
    def get_router(self) -> APIRouter:
        \"\"\"Get the FastAPI router\"\"\"
        return self.router
    
    def emit_event(self, event_name: str, **kwargs):
        \"\"\"Emit plugin events for monitoring and integration\"\"\"
        try:
            # Try to use the plugin system's event emitter
            from app.core.plugin_system import get_plugin_manager
            plugin_manager = get_plugin_manager()
            if plugin_manager and hasattr(plugin_manager, 'emit_event'):
                plugin_manager.emit_event(event_name, **kwargs)
        except ImportError:
            # Fallback: just log the event
            print(f"📡 Event: {{event_name}} - {{kwargs}}")
        except Exception as e:
            # Don't let event emission break the main functionality
            print(f"⚠️ Event emission failed: {{e}}")
'''
        
        return template
    
    def _get_operation_timeouts(self, fields: List[Dict[str, Any]], with_bulk: bool) -> Dict[str, float]:
        """Determine appropriate timeouts based on model complexity"""
        # Analyze field complexity
        has_text_search = any(
            field.get('type') in ['text', 'longtext', 'json'] 
            for field in fields
        )
        has_relations = any(
            field.get('type') in ['foreignkey', 'manytomany'] 
            for field in fields
        )
        field_count = len(fields)
        
        # Base timeouts
        timeouts = {
            'create': 10.0,
            'read': 5.0,
            'update': 10.0,
            'delete': 5.0,
            'search': 15.0,
            'database': 8.0
        }
        
        # Adjust based on complexity
        if field_count > 20:
            # Large models need more time
            timeouts.update({
                'create': 15.0,
                'update': 15.0,
                'search': 25.0,
                'database': 12.0
            })
        
        if has_text_search:
            # Text search operations are slower
            timeouts.update({
                'search': 30.0,
                'database': 15.0
            })
        
        if has_relations:
            # Related data fetching takes longer
            timeouts.update({
                'read': 10.0,
                'create': 15.0,
                'update': 15.0,
                'database': 12.0
            })
        
        if with_bulk:
            # Bulk operations need much longer timeouts
            timeouts.update({
                'bulk_create': 60.0,
                'bulk_update': 60.0,
                'bulk_delete': 30.0
            })
        
        return timeouts
    
    def _generate_bulk_routes(self, pascal_name: str, snake_name: str, timeouts: Dict[str, float]) -> str:
        """Generate bulk operation routes with appropriate timeouts"""
        return f'''
        
        @self.router.post("/{snake_name}s/bulk", response_model=List[{pascal_name}Response], tags=["{pascal_name}"])
        @with_timeout(timeout_seconds={timeouts.get('bulk_create', 60.0)})
        async def create_bulk_{snake_name}s(items: List[{pascal_name}Create], request: Request):
            \"\"\"Create multiple {snake_name}s\"\"\"
            try:
                # Bulk operations use longer database timeouts
                async with database_timeout_context({timeouts.get('bulk_create', 60.0) * 0.8}):
                    results = await self.service.bulk_create(items)
                    
                self.emit_event("{snake_name}_bulk_created", count=len(results))
                return results
                
            except TimeoutException as e:
                raise HTTPException(
                    status_code=504,
                    detail={{
                        "error": "bulk_operation_timeout",
                        "message": "Bulk create operation timed out",
                        "timeout_seconds": {timeouts.get('bulk_create', 60.0)},
                        "operation": "bulk_create_{snake_name}s",
                        "item_count": len(items)
                    }}
                )
            except Exception as e:
                raise HTTPException(status_code=400, detail=str(e))
        
        @self.router.put("/{snake_name}s/bulk", response_model=List[{pascal_name}Response], tags=["{pascal_name}"])
        @with_timeout(timeout_seconds={timeouts.get('bulk_update', 60.0)})
        async def update_bulk_{snake_name}s(updates: List[{pascal_name}Update], request: Request):
            \"\"\"Update multiple {snake_name}s\"\"\"
            try:
                async with database_timeout_context({timeouts.get('bulk_update', 60.0) * 0.8}):
                    results = await self.service.bulk_update(updates)
                    
                self.emit_event("{snake_name}_bulk_updated", count=len(results))
                return results
                
            except TimeoutException as e:
                raise HTTPException(
                    status_code=504,
                    detail={{
                        "error": "bulk_operation_timeout",
                        "message": "Bulk update operation timed out",
                        "timeout_seconds": {timeouts.get('bulk_update', 60.0)},
                        "operation": "bulk_update_{snake_name}s",
                        "update_count": len(updates)
                    }}
                )
            except Exception as e:
                raise HTTPException(status_code=400, detail=str(e))
        
        @self.router.delete("/{snake_name}s/bulk", tags=["{pascal_name}"])
        @with_timeout(timeout_seconds={timeouts.get('bulk_delete', 30.0)})
        async def delete_bulk_{snake_name}s(ids: List[int], request: Request):
            \"\"\"Delete multiple {snake_name}s\"\"\"
            try:
                async with database_timeout_context({timeouts.get('bulk_delete', 30.0) * 0.8}):
                    deleted_count = await self.service.bulk_delete(ids)
                    
                self.emit_event("{snake_name}_bulk_deleted", count=deleted_count)
                return {{"message": f"Deleted {{deleted_count}} {snake_name}s successfully"}}
                
            except TimeoutException as e:
                raise HTTPException(
                    status_code=504,
                    detail={{
                        "error": "bulk_operation_timeout",
                        "message": "Bulk delete operation timed out",
                        "timeout_seconds": {timeouts.get('bulk_delete', 30.0)},
                        "operation": "bulk_delete_{snake_name}s",
                        "id_count": len(ids)
                    }}
                )
            except Exception as e:
                raise HTTPException(status_code=400, detail=str(e))''' 