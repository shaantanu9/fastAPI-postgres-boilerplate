from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.security import (
    verify_password, create_access_token, Token, get_current_active_user, get_password_hash
)
from app.services.user_service import UserService
from app.db.session import get_db
from app.db.models.user import User
from datetime import timedelta

router = APIRouter()

@router.post("/token")
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    user = await UserService.authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username/email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    # user is SQLAlchemy model, convert to UserRead for response
    from app.db.schemas.user import UserRead
    user_data = UserRead.from_orm(user)
    # Ensure roles is a list for JWT
    roles_value = user.roles
    if isinstance(roles_value, str):
        roles_list = [r.strip() for r in roles_value.split(',') if r.strip()]
    elif isinstance(roles_value, list):
        roles_list = roles_value
    else:
        roles_list = []
    access_token = create_access_token(
        data={"sub": user.email, "roles": roles_list},
        expires_delta=timedelta(minutes=30),
    )
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": user_data
    }

from app.db.schemas.user import UserRead, UserCreate

@router.post("/register", response_model=UserRead)
async def register_user(user: UserCreate, db: AsyncSession = Depends(get_db)):
    created_user = await UserService.create_user(
        db,
        username=user.username,
        name=user.name,
        email=user.email,
        password=user.password,
        roles=user.roles,
        is_active=user.is_active
    )
    return created_user

@router.get("/me", response_model=UserRead)
async def read_users_me(current_user: UserRead = Depends(get_current_active_user)):
    return current_user
