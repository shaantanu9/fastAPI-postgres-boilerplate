from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.schemas.user import UserCreate, UserRead
from app.db.crud.user import get_users, create_user
from app.db.session import get_db
from typing import List

router = APIRouter()

@router.get("/users", response_model=List[UserRead])
async def read_users(db: AsyncSession = Depends(get_db)):
    return await get_users(db)

@router.post("/users", response_model=UserRead)
async def create_new_user(user: UserCreate, db: AsyncSession = Depends(get_db)):
    return await create_user(db, name=user.name, email=user.email)
