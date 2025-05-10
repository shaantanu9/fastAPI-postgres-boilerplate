from typing import Type, TypeVar, Generic, Optional, List, Any, Dict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import func
from sqlalchemy import delete as sqlalchemy_delete
from sqlalchemy import update as sqlalchemy_update

ModelType = TypeVar("ModelType")

class BaseService(Generic[ModelType]):
    """
    Generic base service for SQLAlchemy models.
    Provides reusable async CRUD methods for any SQLAlchemy model.
    Inherit from this class and pass your model to enable DRY, scalable service logic.

    Example:
        class BookService(BaseService[Book]):
            def __init__(self):
                super().__init__(Book)
    """
    model: Type[ModelType]

    def __init__(self, model: Type[ModelType]):
        """
        Initialize the service with the SQLAlchemy model class.
        """
        self.model = model

    async def find(self, db: AsyncSession, filters: Optional[Dict[str, Any]] = None) -> List[ModelType]:
        try:
            stmt = select(self.model)
            if filters:
                for key, value in filters.items():
                    stmt = stmt.where(getattr(self.model, key) == value)
            result = await db.execute(stmt)
            return result.scalars().all()
        except SQLAlchemyError as e:
            raise

    async def find_one(self, db: AsyncSession, filters: Dict[str, Any]) -> Optional[ModelType]:
        try:
            stmt = select(self.model)
            for key, value in filters.items():
                stmt = stmt.where(getattr(self.model, key) == value)
            result = await db.execute(stmt)
            return result.scalars().first()
        except SQLAlchemyError as e:
            raise

    async def add(self, db: AsyncSession, obj_in: Dict[str, Any]) -> ModelType:
        try:
            db_obj = self.model(**obj_in)
            db.add(db_obj)
            await db.commit()
            await db.refresh(db_obj)
            return db_obj
        except SQLAlchemyError as e:
            await db.rollback()
            raise

    async def update(self, db: AsyncSession, db_obj: ModelType, obj_in: Dict[str, Any]) -> ModelType:
        try:
            for key, value in obj_in.items():
                setattr(db_obj, key, value)
            db.add(db_obj)
            await db.commit()
            await db.refresh(db_obj)
            return db_obj
        except SQLAlchemyError as e:
            await db.rollback()
            raise

    async def update_one(self, db: AsyncSession, filters: Dict[str, Any], obj_in: Dict[str, Any]) -> Optional[ModelType]:
        db_obj = await self.find_one(db, filters)
        if not db_obj:
            return None
        return await self.update(db, db_obj, obj_in)

    async def delete(self, db: AsyncSession, db_obj: ModelType) -> None:
        try:
            await db.delete(db_obj)
            await db.commit()
        except SQLAlchemyError as e:
            await db.rollback()
            raise

    async def delete_one(self, db: AsyncSession, filters: Dict[str, Any]) -> bool:
        db_obj = await self.find_one(db, filters)
        if not db_obj:
            return False
        await self.delete(db, db_obj)
        return True

    async def find_by_id(self, db: AsyncSession, id: Any) -> Optional[ModelType]:
        try:
            result = await db.get(self.model, id)
            return result
        except SQLAlchemyError as e:
            raise

    async def count(self, db: AsyncSession, filters: Optional[Dict[str, Any]] = None) -> int:
        try:
            stmt = select(func.count()).select_from(self.model)
            if filters:
                for key, value in filters.items():
                    stmt = stmt.where(getattr(self.model, key) == value)
            result = await db.execute(stmt)
            return result.scalar_one()
        except SQLAlchemyError as e:
            raise

    async def exists(self, db: AsyncSession, filters: Dict[str, Any]) -> bool:
        try:
            stmt = select(self.model)
            for key, value in filters.items():
                stmt = stmt.where(getattr(self.model, key) == value)
            result = await db.execute(stmt)
            return result.scalars().first() is not None
        except SQLAlchemyError as e:
            raise

    async def bulk_add(self, db: AsyncSession, objs_in: List[Dict[str, Any]]) -> List[ModelType]:
        try:
            db_objs = [self.model(**obj_in) for obj_in in objs_in]
            db.add_all(db_objs)
            await db.commit()
            for obj in db_objs:
                await db.refresh(obj)
            return db_objs
        except SQLAlchemyError as e:
            await db.rollback()
            raise

    async def bulk_add(self, db: AsyncSession, objs_in: List[Dict[str, Any]]) -> List[ModelType]:
        try:
            db_objs = [self.model(**obj_in) for obj_in in objs_in]
            db.add_all(db_objs)
            await db.commit()
            for obj in db_objs:
                await db.refresh(obj)
            return db_objs
        except SQLAlchemyError as e:
            await db.rollback()
            raise

    async def bulk_delete(self, db: AsyncSession, filters: Dict[str, Any]) -> int:
        try:
            stmt = sqlalchemy_delete(self.model)
            for key, value in filters.items():
                stmt = stmt.where(getattr(self.model, key) == value)
            result = await db.execute(stmt)
            await db.commit()
            return result.rowcount
        except SQLAlchemyError as e:
            await db.rollback()
            raise

    async def aggregate(self, db: AsyncSession, aggregates: Dict[str, Any], filters: Optional[Dict[str, Any]] = None):
        try:
            stmt = select(*aggregates.values())
            if filters:
                for key, value in filters.items():
                    stmt = stmt.where(getattr(self.model, key) == value)
            result = await db.execute(stmt)
            return result.all()
        except SQLAlchemyError as e:
            raise

    async def paginate(self, db: AsyncSession, page: int = 1, page_size: int = 20, filters: Optional[Dict[str, Any]] = None) -> List[ModelType]:
        try:
            stmt = select(self.model)
            if filters:
                for key, value in filters.items():
                    stmt = stmt.where(getattr(self.model, key) == value)
            stmt = stmt.offset((page - 1) * page_size).limit(page_size)
            result = await db.execute(stmt)
            return result.scalars().all()
        except SQLAlchemyError as e:
            raise

    async def upsert(self, db: AsyncSession, obj_in: Dict[str, Any], unique_fields: List[str]) -> ModelType:
        filters = {field: obj_in[field] for field in unique_fields}
        db_obj = await self.find_one(db, filters)
        if db_obj:
            return await self.update(db, db_obj, obj_in)
        else:
            return await self.add(db, obj_in)

    async def find_projection(self, db: AsyncSession, fields: List[str], filters: Optional[Dict[str, Any]] = None):
        try:
            cols = [getattr(self.model, f) for f in fields]
            stmt = select(*cols)
            if filters:
                for key, value in filters.items():
                    stmt = stmt.where(getattr(self.model, key) == value)
            result = await db.execute(stmt)
            return result.all()
        except SQLAlchemyError as e:
            raise

    async def first_or_create(self, db: AsyncSession, filters: Dict[str, Any], defaults: Dict[str, Any] = {}) -> ModelType:
        db_obj = await self.find_one(db, filters)
        if db_obj:
            return db_obj
        data = {**filters, **defaults}
        return await self.add(db, data)

    async def bulk_update(self, db: AsyncSession, filters: Dict[str, Any], update_data: Dict[str, Any]) -> int:
        try:
            stmt = sqlalchemy_update(self.model)
            for key, value in filters.items():
                stmt = stmt.where(getattr(self.model, key) == value)
            stmt = stmt.values(**update_data)
            result = await db.execute(stmt)
            await db.commit()
            return result.rowcount
        except SQLAlchemyError as e:
            await db.rollback()
            raise

    async def all(self, db: AsyncSession, filters: Optional[Dict[str, Any]] = None) -> List[ModelType]:
        return await self.find(db, filters)