from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models.user import User
from app.core.exception_handlers import AppException
from sqlalchemy.future import select
from sqlalchemy.exc import SQLAlchemyError

class UserService:
    @staticmethod
    async def get_users(db: AsyncSession):
        try:
            result = await db.execute(select(User))
            users = result.scalars().all()
            if not users:
                raise AppException("No users found.", status_code=404)
            return users
        except SQLAlchemyError as e:
            raise AppException("Database error occurred while fetching users.", status_code=500)

    @staticmethod
    async def create_user(db: AsyncSession, name: str, email: str):
        try:
            user = User(name=name, email=email)
            db.add(user)
            await db.commit()
            await db.refresh(user)
            return user
        except SQLAlchemyError as e:
            await db.rollback()
            if "unique constraint" in str(e).lower():
                raise AppException("Email already exists.", status_code=400)
            raise AppException("Database error occurred while creating user.", status_code=500)
