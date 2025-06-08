"""
Core dependencies for FastAPI application.

This module provides common dependency functions used across the application.
"""

from typing import Dict, Optional
from fastapi import Depends, HTTPException, Header, status
from app.core.security import security_service
from app.db.schemas.user import UserRead

async def get_current_user(
    authorization: Optional[str] = Header(None)
) -> str:
    """
    Dependency to extract and verify the current authenticated user ID from the request.

    Args:
        authorization (Optional[str]): The Authorization header from the request.
    Returns:
        str: The user ID if authenticated.
    Raises:
        HTTPException: If no authorization header is provided or authentication fails.
    """
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )
    # In a real application, this would validate the token
    # For now, just return a placeholder user ID
    return "current-user-id"

async def get_current_tenant(
    tenant_id: Optional[str] = Header(None, alias="X-Tenant-ID")
) -> str:
    """
    Dependency to extract the current tenant ID from the request headers.

    Args:
        tenant_id (Optional[str]): The X-Tenant-ID header from the request.
    Returns:
        str: The tenant ID if provided, otherwise a default tenant ID.
    """
    if not tenant_id:
        # Default tenant for single-tenant mode or when no tenant is specified
        return "default-tenant"
    return tenant_id

async def get_current_admin_user(
    user_id: str = Depends(get_current_user),
) -> Dict:
    """
    Dependency to verify that the current user has admin privileges.

    Args:
        user_id (str): The user ID extracted from authentication.
    Returns:
        Dict: A dictionary representing the admin user if authorized.
    Raises:
        HTTPException: If the user is not an admin.
    """
    # In a real application, this would check if the user has admin role
    # For now, just return a placeholder admin user
    admin_user = {
        "id": user_id,
        "is_admin": True,
        "roles": ["admin"]
    }
    if not admin_user.get("is_admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized as admin"
        )
    return admin_user
