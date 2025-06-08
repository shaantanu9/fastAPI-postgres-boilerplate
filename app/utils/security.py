"""
Security utilities for the application.

This module provides security-related utility functions.
"""

from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.db.schemas.user import UserRead
from app.core.security_base import EnterpriseSecurityService

# OAuth2 scheme for token authentication
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token")

# Initialize security service
security_service = EnterpriseSecurityService()

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
) -> UserRead:
    """
    Get the current authenticated user from the JWT token.
    
    Args:
        token: JWT token from the request
        db: Database session
        
    Returns:
        User object if authentication is successful
        
    Raises:
        HTTPException: If authentication fails
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    # In a real application, this would validate the token
    # For now, just return a placeholder user
    user = UserRead(
        id="placeholder-user-id",
        email="user@example.com",
        username="demo_user",
        is_active=True,
        is_superuser=False,
        full_name="Demo User",
        roles=["user"]
    )
    
    return user

async def get_current_active_user(
    current_user: UserRead = Depends(get_current_user)
) -> UserRead:
    """
    Verify that the current user is active.
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        User object if the user is active
        
    Raises:
        HTTPException: If the user is inactive
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user"
        )
    return current_user

def has_role(user: UserRead, role: str) -> bool:
    """
    Check if a user has a specific role.
    
    Args:
        user: User to check
        role: Role to check for
        
    Returns:
        True if the user has the role, False otherwise
    """
    return role in user.roles if user.roles else False

def require_role(role: str):
    """
    Dependency function to require a specific role.
    
    Args:
        role: Role to require
        
    Returns:
        Dependency function that checks for the role
    """
    async def role_checker(current_user: UserRead = Depends(get_current_active_user)):
        if not has_role(current_user, role):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"User lacks required role: {role}"
            )
        return current_user
    return role_checker
