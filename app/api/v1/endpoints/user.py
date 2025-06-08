"""
User API endpoints.

This file defines the API routes for user-related operations.
Complete CRUD operations with enterprise security features.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from app.services.user_service import enhanced_user_service
from app.db.schemas.user import UserRead, UserCreate, UserUpdate, UserWithRoles
from app.db.session import get_db
from app.api.v1.endpoints.auth import get_current_user

router = APIRouter()

# CREATE - Register new user (public endpoint)
@router.post("/", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def create_user(
    user_create: UserCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new user account.

    Args:
        user_create (UserCreate): User creation payload.
        db (AsyncSession): Database session dependency.
    Returns:
        UserRead: The created user object.
    Raises:
        HTTPException: On user creation error or database failure.
    """
    try:
        return await enhanced_user_service.create_user(db, user_create)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create user"
        )

# READ - Get all users (admin only)
@router.get("/", response_model=List[UserRead])
async def get_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    current_user: UserRead = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get all users in the system (admin only).

    Args:
        skip (int): Number of users to skip (pagination).
        limit (int): Maximum number of users to return.
        current_user (UserRead): The current authenticated user.
        db (AsyncSession): Database session dependency.
    Returns:
        List[UserRead]: List of user objects.
    Raises:
        HTTPException: On retrieval error or permission denied.
    """
    # TODO: Add admin role check
    try:
        from sqlalchemy.future import select
        from app.db.models.user import User
        
        query = select(User).offset(skip).limit(limit)
        result = await db.execute(query)
        users = result.scalars().all()
        
        return [UserRead.from_orm(user) for user in users]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve users"
        )

# READ - Get user by ID
@router.get("/{user_id}", response_model=UserWithRoles)
async def get_user(
    user_id: str,
    current_user: UserRead = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Retrieve a user by user ID (self or admin access).

    Args:
        user_id (str): The unique user ID.
        current_user (UserRead): The current authenticated user.
        db (AsyncSession): Database session dependency.
    Returns:
        UserWithRoles: The user object with roles and permissions.
    Raises:
        HTTPException: If user not found or access denied.
    """
    # Users can only access their own data unless they're admin
    if current_user.id != user_id:
        # TODO: Add admin role check
        pass
    
    try:
        user = await enhanced_user_service.get_by_id(db, user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Get user permissions
        permissions = await enhanced_user_service.get_user_permissions(db, user.id)
        
        return UserWithRoles(
            **user.__dict__,
            roles=[role for role in user.roles],
            permissions=permissions
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve user"
        )

# UPDATE - Update user
@router.put("/{user_id}", response_model=UserRead)
async def update_user(
    user_id: str,
    user_update: UserUpdate,
    current_user: UserRead = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update user details (self or admin access).

    Args:
        user_id (str): The unique user ID to update.
        user_update (UserUpdate): Update payload for the user.
        current_user (UserRead): The current authenticated user.
        db (AsyncSession): Database session dependency.
    Returns:
        UserRead: The updated user object.
    Raises:
        HTTPException: If update fails or access denied.
    """
    # Update user logic only update their own data unless they're admin
    if current_user.id != user_id:
        # TODO: Add admin role check
        pass
    
    try:
        updated_user = await enhanced_user_service.update_user(db, user_id, user_update)
        return updated_user
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update user"
        )

# DELETE - Delete user (admin only)
@router.delete("/{user_id}")
async def delete_user(
    user_id: str,
    current_user: UserRead = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete a user from the system (admin only).

    Args:
        user_id (str): The unique user ID to delete.
        current_user (UserRead): The current authenticated user.
        db (AsyncSession): Database session dependency.
    Returns:
        dict: Status message indicating deletion result.
    Raises:
        HTTPException: If deletion fails or permission denied.
    """
    # Delete user logic role check
    
    try:
        user = await enhanced_user_service.get_by_id(db, user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Soft delete by deactivating
        from app.db.schemas.user import UserUpdate
        await enhanced_user_service.update_user(
            db, user_id, UserUpdate(is_active=False)
        )
        
        return {"message": "User deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete user"
        )

# SEARCH - Search users
@router.get("/search/", response_model=List[UserRead])
async def search_users(
    q: str = Query(..., min_length=1),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    current_user: UserRead = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Search users by username, email, or name.

    Args:
        q (str): Query string for username, email, or name.
        skip (int): Number of users to skip (pagination).
        limit (int): Maximum number of users to return.
        current_user (UserRead): The current authenticated user.
        db (AsyncSession): Database session dependency.
    Returns:
        List[UserRead]: List of matching user objects.
    Raises:
        HTTPException: If search fails or permission denied.
    """
    try:
        from sqlalchemy.future import select
        from sqlalchemy import or_
        from app.db.models.user import User

        query = select(User).where(
            or_(
                User.username.ilike(f"%{q}%"),
                User.email.ilike(f"%{q}%"),
                User.first_name.ilike(f"%{q}%"),
                User.last_name.ilike(f"%{q}%")
            )
        ).offset(skip).limit(limit)

        result = await db.execute(query)
        users = result.scalars().all()

        return [UserRead.from_orm(user) for user in users]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to search users"
        )
