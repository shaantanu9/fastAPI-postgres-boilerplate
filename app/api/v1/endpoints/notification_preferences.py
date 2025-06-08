"""API endpoints for managing notification preferences."""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.user import User
from app.db.session import get_db
from app.models.notification import (
    NotificationPreference,
)
from app.schemas.notification import (
    NotificationPreferenceRead,
    NotificationPreferenceUpdate,
)
from app.utils.security import get_current_active_user

router = APIRouter()


@router.get("/preferences", response_model=list[NotificationPreferenceRead])
async def get_notification_preferences(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    """Retrieve the notification preferences for the current authenticated user.

    Args:
        db (AsyncSession): Database session dependency.
        current_user (User): The current authenticated user.

    Returns:
        List[NotificationPreferenceRead]: List of notification preferences for the user.

    Raises:
        HTTPException: If retrieval fails (rare, e.g., DB error).

    """
    preferences = await db.execute(
        select(NotificationPreference).where(
            NotificationPreference.user_id == current_user.id,
        ),
    )
    return preferences.scalars().all()


@router.put("/preferences", response_model=list[NotificationPreferenceRead])
async def update_notification_preferences(
    notification_preferences: list[NotificationPreferenceUpdate],
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    """Update the notification preferences for the current authenticated user.

    Args:
        notification_preferences (List[NotificationPreferenceUpdate]): List of notification preference updates.
        db (AsyncSession): Database session dependency.
        current_user (User): The current authenticated user.

    Returns:
        List[NotificationPreferenceRead]: List of updated notification preferences for the user.

    Raises:
        HTTPException: If update fails (rare, e.g., DB error).

    """
    updated_preferences: list[NotificationPreference] = []
    for preference_update in notification_preferences:
        preference = await db.execute(
            select(NotificationPreference).where(
                NotificationPreference.user_id == current_user.id,
                NotificationPreference.category == preference_update.category,
                NotificationPreference.channel == preference_update.channel,
            ),
        ).scalar_one_or_none()
        if preference:
            # Update existing preference
            preference.enabled = preference_update.enabled
            # ... update other fields as needed
            await db.commit()
            await db.refresh(preference)
            updated_preferences.append(preference)
        else:
            # Create new preference
            preference = NotificationPreference(
                user_id=current_user.id,
                category=preference_update.category,
                channel=preference_update.channel,
                enabled=preference_update.enabled,
                # ... set other fields as needed
            )
            db.add(preference)
            await db.commit()
            await db.refresh(preference)
            updated_preferences.append(preference)
    return updated_preferences
