from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.schemas.user import UserCreate, UserRead
from app.services.user_service import UserService
from app.db.session import get_db
from app.core.exception_handlers import AppException
from sqlalchemy.exc import SQLAlchemyError
from typing import List

router = APIRouter()

@router.get("/users", response_model=List[UserRead])
async def read_users(db: AsyncSession = Depends(get_db)):
    try:
        users = await UserService.get_users(db)
        return users
    except AppException as ae:
        raise ae
    except SQLAlchemyError as se:
        raise AppException("Database error occurred while fetching users.", status_code=500)

@router.post("/users", response_model=UserRead)
async def create_new_user(user: UserCreate, db: AsyncSession = Depends(get_db)):
    try:
        return await UserService.create_user(db, name=user.name, email=user.email)
    except AppException as ae:
        raise ae
    except SQLAlchemyError as se:
        raise AppException("Database error occurred while creating user.", status_code=500)
