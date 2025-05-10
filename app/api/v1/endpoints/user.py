"""
User API endpoints.

This file defines the API routes for user-related operations.
- All CRUD operations (create, read, update, delete) are provided by the generic get_crud_router factory.
- To add custom endpoints (e.g., search, advanced filters), use the same `router` object below.
- This pattern is scalable and maintainable for large codebases, as it keeps endpoint files clean and DRY.

How to extend:
    @router.get("/users/by_email/{email}")
    async def get_user_by_email(email: str, ...):
        ...
"""

from app.api.v1.endpoints.base import get_crud_router
from app.services.user_service import UserService
from app.db.schemas.user import UserRead, UserCreate
from app.db.session import get_db

# Main CRUD router for users
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.user_service import UserService
from app.db.schemas.user import UserRead, UserCreate
from app.db.session import get_db

router = APIRouter(prefix="/users", tags=["Users"])

@router.post("/", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def create_user(user: UserCreate, db: AsyncSession = Depends(get_db)):
    try:
        return await UserService().create_user(
            db=db,
            username=user.username,
            name=user.name,
            email=user.email,
            password=user.password,
            roles=user.roles,
            is_active=user.is_active
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# Example custom endpoint with OpenAPI tag and description
def example_custom_endpoint():
    """
    Example custom endpoint for users by email.
    Shows how to add OpenAPI tags and descriptions for better docs.
    """
    from fastapi import Depends, HTTPException
    @router.get("/users/by_email/{email}", response_model=UserRead, tags=["Users"], description="Get a user by their email address.")
    async def get_user_by_email(email: str, db=Depends(get_db)):
        user = await UserService().get_by_username_or_email(db, email)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        return UserRead.from_orm(user)

# Add more custom endpoints below using @router.get/post/... with tags and description as needed.
