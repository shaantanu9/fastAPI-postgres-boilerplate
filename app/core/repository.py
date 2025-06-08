"""Base repository pattern implementation.
Provides consistent data access interface following best practices.
"""

from typing import Any, Generic, TypeVar

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

ModelType = TypeVar("ModelType")


class BaseRepository(Generic[ModelType]):
    """Base repository providing common data access patterns.

    Following the repository pattern to abstract database operations
    and provide a consistent interface for data access.
    """

    def __init__(self, model: type[ModelType]) -> None:
        self.model = model

    async def find_by_id(self, db: AsyncSession, id: Any) -> ModelType | None:
        """Find a single record by ID."""
        return await db.get(self.model, id)

    async def find_all(
        self, db: AsyncSession, skip: int = 0, limit: int = 100,
    ) -> list[ModelType]:
        """Find all records with pagination."""
        stmt = select(self.model).offset(skip).limit(limit)
        result = await db.execute(stmt)
        return result.scalars().all()

    async def find_by_conditions(
        self, db: AsyncSession, conditions: dict[str, Any],
    ) -> list[ModelType]:
        """Find records matching conditions."""
        stmt = select(self.model)
        for key, value in conditions.items():
            field = getattr(self.model, key)
            stmt = stmt.where(field == value)

        result = await db.execute(stmt)
        return result.scalars().all()

    async def count(
        self, db: AsyncSession, conditions: dict[str, Any] | None = None,
    ) -> int:
        """Count records matching conditions."""
        stmt = select(func.count(self.model.id))

        if conditions:
            for key, value in conditions.items():
                field = getattr(self.model, key)
                stmt = stmt.where(field == value)

        result = await db.execute(stmt)
        return result.scalar()

    async def exists(self, db: AsyncSession, conditions: dict[str, Any]) -> bool:
        """Check if record exists with conditions."""
        count = await self.count(db, conditions)
        return count > 0

    async def create(self, db: AsyncSession, data: dict[str, Any]) -> ModelType:
        """Create a new record."""
        instance = self.model(**data)
        db.add(instance)
        await db.commit()
        await db.refresh(instance)
        return instance

    async def update(
        self, db: AsyncSession, instance: ModelType, data: dict[str, Any],
    ) -> ModelType:
        """Update an existing record."""
        for key, value in data.items():
            setattr(instance, key, value)

        db.add(instance)
        await db.commit()
        await db.refresh(instance)
        return instance

    async def delete(self, db: AsyncSession, instance: ModelType) -> None:
        """Delete a record."""
        await db.delete(instance)
        await db.commit()
