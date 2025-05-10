from sqlalchemy.future import select
from sqlalchemy.exc import SQLAlchemyError
from app.db.models.user import User
from app.core.exception_handlers import AppException

async def get_users(db):
    try:
        result = await db.execute(select(User))
        return result.scalars().all()
    except SQLAlchemyError as e:
        raise AppException(message="Failed to retrieve users", details=str(e))

async def create_user(db, name: str, email: str):
    try:
        user = User(name=name, email=email)
        db.add(user)
        await db.commit()
        await db.refresh(user)
        return user
    except SQLAlchemyError as e:
        await db.rollback()
        if "unique constraint" in str(e).lower():
            raise AppException(message="Email already exists", details=str(e))
        raise AppException(message="Failed to create user", details=str(e))
    user = User(name=name, email=email)
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user
