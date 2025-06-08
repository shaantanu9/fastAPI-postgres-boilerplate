"""API Key Authentication module.
Provides secure API key generation, validation, and management for machine-to-machine communication.
"""

import secrets
from datetime import datetime, timedelta

from fastapi import Depends, HTTPException, Security
from fastapi.security.api_key import APIKeyHeader
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.session import get_db
from app.models.security import APIKey
from app.utils.crypto import hash_api_key

settings = get_settings()

# API Key header configuration
API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=True)


class APIKeyAuth:
    """API Key Authentication handler with role-based access control."""

    def __init__(self, scopes: list[str] | None = None, rate_limit: int | None = None) -> None:
        self.scopes = scopes or []
        self.rate_limit = rate_limit

    async def __call__(
        self,
        api_key: str = Security(API_KEY_HEADER),
        db: AsyncSession = Depends(get_db),
    ) -> dict:
        """Validate API key and check permissions.

        Args:
            api_key: The API key from request header
            db: Database session

        Returns:
            Dict containing API key metadata

        Raises:
            HTTPException: If API key is invalid or lacks required permissions

        """
        if not api_key:
            raise HTTPException(status_code=401, detail="API key is required")

        # Get hashed API key
        hashed_key = hash_api_key(api_key)

        # Validate API key
        api_key_data = await self._validate_api_key(db, hashed_key)

        # Check scopes if specified
        if self.scopes:
            await self._check_scopes(api_key_data)

        # Update last used timestamp
        await self._update_last_used(db, api_key_data["id"])

        return api_key_data

    async def _validate_api_key(self, db: AsyncSession, hashed_key: str) -> dict:
        """Validate API key against database."""
        stmt = select(APIKey).where(
            APIKey.hashed_key == hashed_key,
            APIKey.is_active,
            or_(APIKey.expires_at.is_(None), APIKey.expires_at > datetime.utcnow()),
        )
        result = await db.execute(stmt)
        api_key = result.scalar_one_or_none()

        if not api_key:
            raise HTTPException(status_code=401, detail="Invalid or expired API key")

        return {
            "id": api_key.id,
            "name": api_key.name,
            "scopes": api_key.scopes,
            "user_id": api_key.user_id,
            "organization_id": api_key.organization_id,
        }

    async def _check_scopes(self, api_key_data: dict) -> None:
        """Check if API key has required scopes."""
        api_key_scopes = set(api_key_data.get("scopes", []))
        required_scopes = set(self.scopes)

        if not required_scopes.issubset(api_key_scopes):
            raise HTTPException(
                status_code=403, detail="API key lacks required permissions",
            )

    async def _update_last_used(self, db: AsyncSession, api_key_id: str) -> None:
        """Update last used timestamp for API key."""
        stmt = (
            update(APIKey)
            .where(APIKey.id == api_key_id)
            .values(last_used_at=datetime.utcnow())
        )
        await db.execute(stmt)
        await db.commit()


async def create_api_key(
    db: AsyncSession,
    name: str,
    user_id: str,
    organization_id: str | None = None,
    scopes: list[str] | None = None,
    expires_in_days: int | None = None,
) -> dict[str, str]:
    """Create a new API key.

    Args:
        db: Database session
        name: Name/description for the API key
        user_id: User ID who owns this key
        organization_id: Optional organization ID
        scopes: List of permission scopes
        expires_in_days: Optional expiration in days

    Returns:
        Dict containing the raw API key (to be shown once) and key ID

    """
    # Generate secure random API key
    api_key = f"sk_{secrets.token_urlsafe(32)}"
    hashed_key = hash_api_key(api_key)

    # Calculate expiration
    expires_at = None
    if expires_in_days:
        expires_at = datetime.utcnow() + timedelta(days=expires_in_days)

    # Create API key record
    db_api_key = APIKey(
        hashed_key=hashed_key,
        name=name,
        user_id=user_id,
        organization_id=organization_id,
        scopes=scopes or [],
        expires_at=expires_at,
    )

    db.add(db_api_key)
    await db.commit()
    await db.refresh(db_api_key)

    return {
        "api_key": api_key,  # Raw key - shown only once
        "key_id": db_api_key.id,
    }


async def validate_api_key(db: AsyncSession, api_key: str) -> bool:
    """Validate an API key without checking scopes.

    Args:
        db: Database session
        api_key: The API key to validate

    Returns:
        bool indicating if the key is valid

    """
    hashed_key = hash_api_key(api_key)

    stmt = select(APIKey).where(
        APIKey.hashed_key == hashed_key,
        APIKey.is_active,
        or_(APIKey.expires_at.is_(None), APIKey.expires_at > datetime.utcnow()),
    )

    result = await db.execute(stmt)
    return bool(result.scalar_one_or_none())
