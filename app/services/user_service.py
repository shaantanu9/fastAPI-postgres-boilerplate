from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models.user import User
from app.core.exception_handlers import AppException
from sqlalchemy.future import select
from sqlalchemy.exc import SQLAlchemyError
from app.db.schemas.user import UserRead

from app.services.base_service import BaseService
from app.db.models.user import User

class UserService(BaseService[User]):
    """
    Service class for user-related database operations.
    Inherits generic CRUD methods from BaseService, and adds user-specific logic.
    Use this service in endpoints and business logic to keep code DRY and maintainable.
    """
    def __init__(self):
        # Initialize with the User SQLAlchemy model
        super().__init__(User)

    async def get_by_username_or_email(self, db: AsyncSession, identifier: str):
        """
        Retrieve a user by username or email (supports login with either).
        Custom logic not covered by generic BaseService methods.
        """
        result = await db.execute(
            select(User).where((User.email == identifier) | (User.username == identifier))
        )
        user = result.scalars().first()
        if user:
            return user
        return None

    async def get_by_username(self, db: AsyncSession, username: str):
        """
        Retrieve a user by username only (simple wrapper for find_one).
        """
        result = await db.execute(select(User).where(User.username == username))
        user = result.scalars().first()
        if user:
            return user
        return None

    async def authenticate_user(self, db: AsyncSession, identifier: str, password: str):
        """
        Authenticate a user by username/email and password.
        Custom logic for authentication, not generic CRUD.
        """
        from app.core.security import verify_password
        user = await self.get_by_username_or_email(db, identifier)
        if not user:
            return None
        if not verify_password(password, user.hashed_password):
            return None
        return user

    async def get_users(self, db: AsyncSession):
        """
        Get all users, returning a list of UserRead schemas.
        Uses the generic all() method from BaseService.
        """
        users = await self.all(db)
        if not users:
            raise AppException("No users found.", status_code=404)
        return [UserRead.from_orm(user) for user in users]

    async def create_user(self, db: AsyncSession, username: str, name: str, email: str, password: str, roles: str = "user", is_active: int = 1):
        """
        Create a new user, hashing the password before saving.
        Uses the generic add() method from BaseService for DB insert.
        """
        from app.core.security import get_password_hash
        try:
            hashed_password = get_password_hash(password)
            user_dict = {
                "username": username,
                "name": name,
                "email": email,
                "hashed_password": hashed_password,
                "roles": roles,
                "is_active": is_active,
            }
            user = await self.add(db, user_dict)
            return UserRead.from_orm(user)
        except SQLAlchemyError as e:
            await db.rollback()
            if "unique constraint" in str(e).lower():
                raise AppException("Email or Username already exists.", status_code=400)
            raise AppException("Database error occurred while creating user.", status_code=500)
