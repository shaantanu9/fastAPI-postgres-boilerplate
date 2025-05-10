from datetime import datetime, timedelta
from typing import Optional
import jwt
from jwt import PyJWTError
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel
from app.db.schemas.user import UserRead

from app.db.models.user import User
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
import os

# Settings
# Secret key and algorithm for JWT
from app.core.config import get_settings
SECRET_KEY = get_settings().jwt_secret_token  # Loaded from .env via Settings
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

# OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token")

# Pydantic models for token and user output
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None
    roles: Optional[list] = []

# JWT utils

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Generate a JWT access token using pyjwt.
    """
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    # pyjwt returns a string in v2+, bytes in v1. Ensure string output
    if isinstance(encoded_jwt, bytes):
        encoded_jwt = encoded_jwt.decode('utf-8')
    return encoded_jwt

async def get_current_user(token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)) -> User:
    # Import inside function to avoid circular import
    from app.services.user_service import UserService
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username, roles=payload.get("roles", []))
    except PyJWTError:
        raise credentials_exception
    user = await UserService.get_by_username_or_email(db, token_data.username)
    if not user:
        raise credentials_exception
    return UserRead.from_orm(user)

async def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

# Role/permission helpers

def has_role(user: User, role: str) -> bool:
    return role in getattr(user, "roles", [])

def require_role(role: str):
    def role_checker(user: User = Depends(get_current_active_user)):
        if not has_role(user, role):
            raise HTTPException(status_code=403, detail=f"User lacks required role: {role}")
        return user
    return role_checker

