"""FastAPI routes template generator."""

import re
from typing import Any


class RoutesTemplate:
    """Generates FastAPI routes templates."""

    def generate(
        self, model_name: str, fields: list[dict[str, Any]], with_bulk: bool = False,
    ) -> str:
        """Generate FastAPI routes file content."""
        snake_name = re.sub(r"(?<!^)(?=[A-Z])", "_", model_name).lower()
        pascal_name = model_name

        bulk_routes = ""
        if with_bulk:
            bulk_routes = f"""

        @self.router.post("/{snake_name}s/bulk", response_model=List[{pascal_name}Response], tags=["{pascal_name}"])
        async def create_bulk_{snake_name}s(items: List[{pascal_name}Create]):
            \"\"\"Create multiple {snake_name}s\"\"\"
            try:
                results = await self.service.bulk_create(items)
                self.emit_event("{snake_name}_bulk_created", count=len(results))
                return results
            except Exception as e:
                raise HTTPException(status_code=400, detail=str(e))

        @self.router.put("/{snake_name}s/bulk", response_model=List[{pascal_name}Response], tags=["{pascal_name}"])
        async def update_bulk_{snake_name}s(updates: List[{pascal_name}Update]):
            \"\"\"Update multiple {snake_name}s\"\"\"
            try:
                results = await self.service.bulk_update(updates)
                self.emit_event("{snake_name}_bulk_updated", count=len(results))
                return results
            except Exception as e:
                raise HTTPException(status_code=400, detail=str(e))"""

        return f'''"""
{pascal_name} FastAPI routes
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query, status

from .schemas import (
    {pascal_name}Create,
    {pascal_name}Update,
    {pascal_name}Response,
    {pascal_name}Search
)
from .services import {pascal_name}Service


class {pascal_name}Routes:
    """FastAPI routes for {pascal_name}"""

    def __init__(self):
        self.router = APIRouter()
        self.service = {pascal_name}Service()
        self.setup_routes()

    def setup_routes(self):
        """Setup CRUD routes for {pascal_name}"""

        @self.router.post("/{snake_name}s/", response_model={pascal_name}Response, tags=["{pascal_name}"])
        async def create_{snake_name}(item: {pascal_name}Create):
            \"\"\"Create a new {snake_name}\"\"\"
            try:
                result = await self.service.create(**item.dict())

                # Emit creation event
                self.emit_event("{snake_name}_created",
                              id=result.id,
                              plugin="{snake_name}_plugin")

                return result
            except Exception as e:
                raise HTTPException(status_code=400, detail=str(e))

        @self.router.get("/{snake_name}s/", response_model=List[{pascal_name}Response], tags=["{pascal_name}"])
        async def get_{snake_name}s(
            skip: int = Query(0, ge=0),
            limit: int = Query(100, ge=1, le=1000)
        ):
            \"\"\"Get all {snake_name}s with pagination\"\"\"
            try:
                results = await self.service.get_all(skip=skip, limit=limit)
                return results
            except Exception as e:
                raise HTTPException(status_code=400, detail=str(e))

        @self.router.get("/{snake_name}s/{{item_id}}", response_model={pascal_name}Response, tags=["{pascal_name}"])
        async def get_{snake_name}(item_id: int):
            \"\"\"Get a specific {snake_name} by ID\"\"\"
            try:
                result = await self.service.get(item_id)
                if not result:
                    raise HTTPException(status_code=404, detail="{pascal_name} not found")
                return result
            except HTTPException:
                raise
            except Exception as e:
                raise HTTPException(status_code=400, detail=str(e))

        @self.router.put("/{snake_name}s/{{item_id}}", response_model={pascal_name}Response, tags=["{pascal_name}"])
        async def update_{snake_name}(item_id: int, item: {pascal_name}Update):
            \"\"\"Update a {snake_name}\"\"\"
            try:
                result = await self.service.update(item_id, **item.dict(exclude_unset=True))
                if not result:
                    raise HTTPException(status_code=404, detail="{pascal_name} not found")
                return result
            except HTTPException:
                raise
            except Exception as e:
                raise HTTPException(status_code=400, detail=str(e))

        @self.router.delete("/{snake_name}s/{{item_id}}", tags=["{pascal_name}"])
        async def delete_{snake_name}(item_id: int):
            \"\"\"Delete a {snake_name}\"\"\"
            try:
                success = await self.service.delete(item_id)
                if not success:
                    raise HTTPException(status_code=404, detail="{pascal_name} not found")
                return {{"message": "{pascal_name} deleted successfully"}}
            except HTTPException:
                raise
            except Exception as e:
                raise HTTPException(status_code=400, detail=str(e))

        @self.router.get("/{snake_name}s/search/", response_model=List[{pascal_name}Response], tags=["{pascal_name}"])
        async def search_{snake_name}s(
            q: str = Query(..., min_length=1),
            limit: int = Query(10, ge=1, le=100)
        ):
            \"\"\"Search {snake_name}s\"\"\"
            try:
                results = await self.service.search(q, limit=limit)
                return results
            except Exception as e:
                raise HTTPException(status_code=400, detail=str(e)){bulk_routes}

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

