"""Unified Authentication Service.

This module provides a centralized authentication service that resolves
the parameter mismatch issues between EnhancedUserService and UserService.
"""

import json
import secrets
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from fastapi import HTTPException, Request, status
from loguru import logger
from sqlalchemy import update
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from app.core.security import security_service
from app.db.models.security import SecurityEvent
from app.db.models.user import Permission, Role, User, UserRole, UserSession
from app.db.schemas.user import UserCreate, UserRead, UserUpdate


class UnifiedAuthService:
    """Unified Authentication Service with consistent method signatures."""

    def __init__(self, security_service=None):
        self.security_service = security_service or security_service

    async def create_user(
        self, 
        db: AsyncSession, 
        user_create: UserCreate, 
        created_by: Optional[str] = None,
        request: Optional[Request] = None
    ) -> User:
        """Create a new user with enhanced security validation."""
        try:
            # Validate password
            password_validation = self.security_service.validate_password_strength(
                user_create.password
            )
            if not password_validation["valid"]:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={
                        "message": "Password does not meet security requirements",
                        "errors": password_validation["errors"],
                        "strength": password_validation["strength"],
                    },
                )

            # Check if user already exists
            existing_user = await self.get_by_username_or_email(
                db, user_create.username, user_create.email
            )
            if existing_user:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="User with this username or email already exists",
                )

            # Create user with hashed password
            hashed_password = self.security_service.hash_password(user_create.password)

            user = User(
                username=user_create.username,
                email=user_create.email,
                first_name=user_create.first_name,
                last_name=user_create.last_name,
                hashed_password=hashed_password,
                created_by=created_by,
                is_active=True,
                is_verified=False,  # Require email verification
                failed_login_attempts=0,
                login_ip_history="[]",
                passkey_enabled=False,
                mfa_enabled=False,
                max_sessions=5,
            )

            db.add(user)
            await db.flush()  # Get the user ID

            # Assign default role
            await self.assign_role(db, user.id, "user")

            await db.commit()
            await db.refresh(user)

            # Log security event if request provided
            if request:
                await self.log_security_event(
                    db, user, "user_registration", "authentication",
                    {"username": user.username, "email": user.email}, request
                )

            return user

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error creating user: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Registration failed"
            )

    async def get_by_username_or_email(
        self, 
        db: AsyncSession, 
        username: Optional[str] = None, 
        email: Optional[str] = None
    ) -> Optional[User]:
        """Get user by username or email."""
        query = select(User).options(selectinload(User.roles))

        if username and email:
            query = query.where((User.username == username) | (User.email == email))
        elif username:
            query = query.where(User.username == username)
        elif email:
            query = query.where(User.email == email)
        else:
            return None

        result = await db.execute(query)
        return result.scalar_one_or_none()

    async def get_by_id(self, db: AsyncSession, user_id: str) -> Optional[User]:
        """Get user by ID."""
        query = select(User).options(selectinload(User.roles)).where(User.id == user_id)
        result = await db.execute(query)
        return result.scalar_one_or_none()

    async def authenticate_user(
        self, 
        db: AsyncSession, 
        username_or_email: str, 
        password: str, 
        request: Optional[Request] = None
    ) -> Optional[User]:
        """Authenticate user with enhanced security features.
        
        This method has a consistent signature that handles both cases:
        - Enhanced authentication with Request object
        - Basic authentication without Request object
        """
        try:
            # Get user
            user = await self.get_by_username_or_email(
                db, username_or_email, username_or_email
            )
            if not user:
                return None

            # Check if account is locked
            if self.security_service.is_account_locked(user):
                raise HTTPException(
                    status_code=status.HTTP_423_LOCKED,
                    detail="Account is temporarily locked due to multiple failed login attempts",
                )

            # Verify password
            if not self.security_service.verify_password(password, user.hashed_password):
                # Handle failed login
                if request:
                    await self.security_service.handle_failed_login(db, user, request)
                else:
                    # Increment failed attempts without request context
                    user.failed_login_attempts += 1
                    await db.commit()
                return None

            # Check if account is active
            if not user.is_active:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST, 
                    detail="Account is disabled"
                )

            # Handle successful login
            if request:
                await self.security_service.handle_successful_login(db, user, request)
            else:
                # Reset failed attempts without request context
                user.failed_login_attempts = 0
                user.last_login = datetime.utcnow()
                await db.commit()

            return user

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            return None

    async def create_session(
        self, 
        db: AsyncSession, 
        user: User, 
        request: Request
    ) -> UserSession:
        """Create a new user session."""
        # Check if user has reached max sessions
        active_sessions = await self.get_active_sessions(db, user.id)
        if len(active_sessions) >= user.max_sessions:
            # Deactivate oldest session
            oldest_session = min(active_sessions, key=lambda s: s.last_activity)
            await self.deactivate_session(db, oldest_session.id)

        # Create new session
        session = UserSession(
            user_id=user.id,
            session_token=secrets.token_urlsafe(32),
            ip_address=request.client.host if request.client else "unknown",
            user_agent=request.headers.get("user-agent", "unknown"),
            device_fingerprint=self._generate_device_fingerprint(request),
            is_active=True,
            expires_at=datetime.utcnow() + timedelta(days=30),
        )

        db.add(session)
        await db.commit()
        await db.refresh(session)

        return session

    async def get_active_sessions(
        self, 
        db: AsyncSession, 
        user_id: str
    ) -> list[UserSession]:
        """Get all active sessions for a user."""
        query = select(UserSession).where(
            UserSession.user_id == user_id,
            UserSession.is_active,
            UserSession.expires_at > datetime.utcnow(),
        )
        result = await db.execute(query)
        return result.scalars().all()

    async def deactivate_session(self, db: AsyncSession, session_id: str) -> None:
        """Deactivate a session."""
        query = (
            update(UserSession)
            .where(UserSession.id == session_id)
            .values(is_active=False)
        )
        await db.execute(query)
        await db.commit()

    async def update_session_activity(
        self, 
        db: AsyncSession, 
        session: UserSession
    ) -> None:
        """Update session last activity."""
        session.last_activity = datetime.utcnow()
        await db.commit()

    async def assign_role(
        self, 
        db: AsyncSession, 
        user_id: str, 
        role_name: str, 
        granted_by: Optional[str] = None
    ) -> None:
        """Assign a role to a user."""
        # Get role
        role_query = select(Role).where(Role.name == role_name)
        role_result = await db.execute(role_query)
        role = role_result.scalar_one_or_none()

        if not role:
            # Create default role if it doesn't exist
            role = Role(
                name=role_name,
                description=f"Default {role_name} role",
                is_system_role=True,
            )
            db.add(role)
            await db.flush()

        # Check if user already has this role
        existing_query = select(UserRole).where(
            UserRole.user_id == user_id, UserRole.role_id == role.id
        )
        existing_result = await db.execute(existing_query)
        if existing_result.scalar_one_or_none():
            return  # User already has this role

        # Assign role
        user_role = UserRole(
            user_id=user_id, 
            role_id=role.id, 
            granted_by=granted_by
        )
        db.add(user_role)
        await db.commit()

    async def log_security_event(
        self,
        db: AsyncSession,
        user: User,
        event_type: str,
        category: str,
        details: Dict[str, Any],
        request: Request
    ) -> None:
        """Log a security event."""
        try:
            event = SecurityEvent(
                user_id=user.id,
                event_type=event_type,
                category=category,
                details=json.dumps(details),
                ip_address=request.client.host if request.client else "unknown",
                user_agent=request.headers.get("user-agent", "unknown"),
                created_at=datetime.utcnow()
            )
            db.add(event)
            await db.commit()
        except Exception as e:
            logger.error(f"Failed to log security event: {e}")

    def _generate_device_fingerprint(self, request: Request) -> str:
        """Generate a device fingerprint based on request headers."""
        fingerprint_data = {
            "user_agent": request.headers.get("user-agent", "unknown"),
            "accept_language": request.headers.get("accept-language", "unknown"),
            "accept_encoding": request.headers.get("accept-encoding", "unknown"),
        }

        # Create a simple hash of the data
        import hashlib
        fingerprint_string = json.dumps(fingerprint_data, sort_keys=True)
        return hashlib.sha256(fingerprint_string.encode()).hexdigest()[:16]


# Create unified auth service instance
unified_auth_service = UnifiedAuthService(security_service=security_service)


# Compatibility function for existing code
def get_enhanced_user_service():
    """Compatibility function that returns the unified auth service."""
    return unified_auth_service


# Update the enhanced_user_service import to use unified service
enhanced_user_service = unified_auth_service 