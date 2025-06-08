from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
"""
Base CRUD API router factory for FastAPI.

This module provides a generic function `get_crud_router` that generates a FastAPI APIRouter
with standard CRUD endpoints for any SQLAlchemy model/service. This pattern is highly scalable
and maintainable for large codebases, as it avoids repetitive CRUD code for each model and keeps
your endpoint files clean and DRY.

Usage:
    from app.api.v1.endpoints.base import get_crud_router
    from app.services.book_service import BookService
    from app.db.schemas.book import BookRead, BookCreate
    from app.db.session import get_db

    router = get_crud_router(
        service=BookService(),
        schema_read=BookRead,
        schema_create=BookCreate,
        prefix="/books",
        get_db=get_db,
        tags=["Books"]
    )

You can then add custom endpoints to the same router if needed.
"""

from typing import Type, Any, List, Callable, Optional
from app.db.session import get_db

def get_crud_router(
    *,
    service,
    schema_read: Type,
    schema_create: Type,
    prefix: str,
    get_db: Callable = get_db,
    tags: Optional[List[str]] = None
) -> APIRouter:
    """
    Generate a FastAPI router with standard CRUD endpoints for a given service and schemas.
    
    Args:
        service: Service class instance that provides CRUD operations.
        schema_read (Type): Pydantic model for reading/returning objects.
        schema_create (Type): Pydantic model for creating/updating objects.
        prefix (str): URL prefix for all endpoints in this router.
        get_db (Callable): Function that provides a database session dependency.
        tags (Optional[List[str]]): Tags for API documentation grouping.
        
    Returns:
        APIRouter: FastAPI router with CRUD endpoints configured.
    """
    router = APIRouter(prefix=prefix, tags=tags or [])

    @router.post("/", response_model=schema_read)
    async def create(item: schema_create, db: AsyncSession = Depends(get_db)):
        """
        Create a new item.
        
        Args:
            item (schema_create): The item data to create.
            db (AsyncSession): Database session dependency.
            
        Returns:
            schema_read: The created item.
        """
        obj = await service.add(db, item.dict())
        return schema_read.from_orm(obj)

    @router.get("/", response_model=List[schema_read])
    async def list_all(db: AsyncSession = Depends(get_db)):
        """
        List all items.
        
        Args:
            db (AsyncSession): Database session dependency.
            
        Returns:
            List[schema_read]: List of all items.
        """
        objs = await service.all(db)
        return [schema_read.from_orm(obj) for obj in objs]

    @router.get("/{item_id}", response_model=schema_read)
    async def get_one(item_id: Any, db: AsyncSession = Depends(get_db)):
        """
        Get a specific item by ID.
        
        Args:
            item_id (Any): The ID of the item to retrieve.
            db (AsyncSession): Database session dependency.
            
        Returns:
            schema_read: The requested item.
            
        Raises:
            HTTPException: If the item is not found (404).
        """
        obj = await service.find_by_id(db, item_id)
        if not obj:
            raise HTTPException(status_code=404, detail="Not found")
        return schema_read.from_orm(obj)

    @router.put("/{item_id}", response_model=schema_read)
    async def update(item_id: Any, item: schema_create, db: AsyncSession = Depends(get_db)):
        """
        Update an existing item.
        
        Args:
            item_id (Any): The ID of the item to update.
            item (schema_create): The updated item data.
            db (AsyncSession): Database session dependency.
            
        Returns:
            schema_read: The updated item.
            
        Raises:
            HTTPException: If the item is not found (404).
        """
        db_obj = await service.find_by_id(db, item_id)
        if not db_obj:
            raise HTTPException(status_code=404, detail="Not found")
        obj = await service.update(db, db_obj, item.dict())
        return schema_read.from_orm(obj)

    @router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
    async def delete(item_id: Any, db: AsyncSession = Depends(get_db)):
        """
        Delete an item.
        
        Args:
            item_id (Any): The ID of the item to delete.
            db (AsyncSession): Database session dependency.
            
        Returns:
            None: Returns 204 No Content on success.
            
        Raises:
            HTTPException: If the item is not found (404).
        """
        db_obj = await service.find_by_id(db, item_id)
        if not db_obj:
            raise HTTPException(status_code=404, detail="Not found")
        await service.delete(db, db_obj)
        return

    return router
