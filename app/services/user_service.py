import json
import secrets
from datetime import datetime, timedelta
from typing import Any, Callable

from fastapi import HTTPException, Request, status
from loguru import logger
from sqlalchemy import update
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from app.core.exception_handlers import AppException
from app.db.models.security import SecurityEvent
from app.db.models.user import Permission, Role, User, UserSession
from app.db.schemas.user import UserCreate, UserRead, UserUpdate
from app.services.enhanced_base_service import EnhancedBaseService
from app.utils.concurrent_utils import (
    TaskType,
    execute_parallel,
)


class EnhancedUserService:
    """Enhanced User Service with 2025 enterprise features."""

    def __init__(self, security_service) -> None:
        self.security_service = security_service

    async def create_user(
        self, db: AsyncSession, user_create: UserCreate, created_by: str | None = None,
    ) -> User:
        """Create a new user with enhanced security validation."""
        # Validate password
        password_validation = self.security_service.validate_password_strength(
            user_create.password,
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
            db, user_create.username, user_create.email,
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

        return user

    async def get_by_username_or_email(
        self, db: AsyncSession, username: str | None = None, email: str | None = None,
    ) -> User | None:
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

    async def get_by_id(self, db: AsyncSession, user_id: str) -> User | None:
        """Get user by ID."""
        query = select(User).options(selectinload(User.roles)).where(User.id == user_id)
        result = await db.execute(query)
        return result.scalar_one_or_none()

    async def authenticate_user(
        self, db: AsyncSession, username_or_email: str, password: str, request: Request,
    ) -> User | None:
        """Authenticate user with enhanced security features."""
        # Get user
        user = await self.get_by_username_or_email(
            db, username_or_email, username_or_email,
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
            await self.security_service.handle_failed_login(db, user, request)
            return None

        # Check if account is active
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Account is disabled",
            )

        # Handle successful login
        await self.security_service.handle_successful_login(db, user, request)

        return user

    async def create_session(
        self, db: AsyncSession, user: User, request: Request,
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
            ip_address=request.client.host,
            user_agent=request.headers.get("user-agent"),
            device_fingerprint=self._generate_device_fingerprint(request),
            is_active=True,
            expires_at=datetime.utcnow() + timedelta(days=30),
        )

        db.add(session)
        await db.commit()
        await db.refresh(session)

        return session

    async def get_active_sessions(
        self, db: AsyncSession, user_id: str,
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

    async def update_session_activity(self, db: AsyncSession, session: UserSession) -> None:
        """Update session last activity."""
        session.last_activity = datetime.utcnow()
        await db.commit()

    async def assign_role(
        self, db: AsyncSession, user_id: str, role_name: str, granted_by: str | None = None,
    ) -> None:
        """Assign a role to a user."""
        from app.db.models.user import UserRole

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
            UserRole.user_id == user_id, UserRole.role_id == role.id,
        )
        existing_result = await db.execute(existing_query)
        if existing_result.scalar_one_or_none():
            return  # User already has this role

        # Assign role
        user_role = UserRole(user_id=user_id, role_id=role.id, granted_by=granted_by)
        db.add(user_role)
        await db.commit()

    async def get_user_permissions(
        self, db: AsyncSession, user_id: str,
    ) -> list[Permission]:
        """Get all permissions for a user through their roles."""
        from app.db.models.user import RolePermission

        query = (
            select(Permission)
            .join(RolePermission)
            .join(Role)
            .join(UserRole)
            .where(
                UserRole.user_id == user_id,
                Role.is_active,
                Permission.is_active,
            )
            .distinct()
        )

        result = await db.execute(query)
        return result.scalars().all()

    async def update_user(
        self, db: AsyncSession, user_id: str, user_update: UserUpdate,
    ) -> User:
        """Update user information."""
        user = await self.get_by_id(db, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Update fields
        for field, value in user_update.dict(exclude_unset=True).items():
            if field == "password" and value:
                # Validate and hash new password
                password_validation = self.security_service.validate_password_strength(
                    value,
                )
                if not password_validation["valid"]:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail={
                            "message": "Password does not meet security requirements",
                            "errors": password_validation["errors"],
                        },
                    )
                user.hashed_password = self.security_service.hash_password(value)
                user.password_changed_at = datetime.utcnow()
            else:
                setattr(user, field, value)

        user.updated_at = datetime.utcnow()
        await db.commit()
        await db.refresh(user)

        return user

    async def enable_mfa(self, db: AsyncSession, user_id: str) -> dict[str, Any]:
        """Enable MFA for a user."""
        user = await self.get_by_id(db, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        if user.mfa_enabled:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="MFA is already enabled for this user",
            )

        # Generate MFA secret and backup codes
        mfa_secret = self.security_service.generate_mfa_secret()
        backup_codes = self.security_service.generate_backup_codes()

        user.mfa_secret = mfa_secret
        user.backup_codes = json.dumps(backup_codes)
        user.mfa_enabled = True

        await db.commit()

        # Generate QR code for setup
        qr_code = self.security_service.generate_mfa_qr_code(user.email, mfa_secret)

        return {"secret": mfa_secret, "qr_code": qr_code, "backup_codes": backup_codes}

    async def verify_mfa_setup(
        self, db: AsyncSession, user_id: str, token: str,
    ) -> bool:
        """Verify MFA setup with a token."""
        user = await self.get_by_id(db, user_id)
        if not user or not user.mfa_secret:
            return False

        return self.security_service.verify_mfa_token(user.mfa_secret, token)

    async def get_security_events(
        self, db: AsyncSession, user_id: str, limit: int = 50,
    ) -> list[SecurityEvent]:
        """Get security events for a user."""
        query = (
            select(SecurityEvent)
            .where(SecurityEvent.user_id == user_id)
            .order_by(SecurityEvent.created_at.desc())
            .limit(limit)
        )

        result = await db.execute(query)
        return result.scalars().all()

    def _generate_device_fingerprint(self, request: Request) -> str:
        """Generate a device fingerprint based on request headers."""
        fingerprint_data = {
            "user_agent": request.headers.get("user-agent"),
            "accept_language": request.headers.get("accept-language"),
            "accept_encoding": request.headers.get("accept-encoding"),
        }

        # Create a simple hash of the data
        import hashlib

        fingerprint_string = json.dumps(fingerprint_data, sort_keys=True)
        return hashlib.sha256(fingerprint_string.encode()).hexdigest()[:16]


# Initialize service - import here to avoid circular import
def get_enhanced_user_service():
    from app.core.security import security_service

    return EnhancedUserService(security_service=security_service)


enhanced_user_service = get_enhanced_user_service()


class UserService(EnhancedBaseService[User]):
    """Service class for user-related database operations.
    Inherits generic CRUD methods from BaseService, and adds user-specific logic.
    Use this service in endpoints and business logic to keep code DRY and maintainable.
    """

    def __init__(self) -> None:
        # Initialize with the User SQLAlchemy model
        super().__init__(User)

    async def get_by_username_or_email(self, db: AsyncSession, identifier: str):
        """Retrieve a user by username or email (supports login with either).
        Custom logic not covered by generic BaseService methods.
        """
        result = await db.execute(
            select(User).where(
                (User.email == identifier) | (User.username == identifier),
            ),
        )
        user = result.scalars().first()
        if user:
            return user
        return None

    async def get_by_username(self, db: AsyncSession, username: str):
        """Retrieve a user by username only (simple wrapper for find_one)."""
        result = await db.execute(select(User).where(User.username == username))
        user = result.scalars().first()
        if user:
            return user
        return None

    async def authenticate_user(self, db: AsyncSession, identifier: str, password: str):
        """Authenticate a user by username/email and password.
        Custom logic for authentication, not generic CRUD.
        """
        from app.core.security import verify_password

        user = await self.get_by_username_or_email(db, identifier)
        if not user:
            return None
        if not verify_password(password, user.hashed_password):
            return None
        return user

    async def get_users(self, db: AsyncSession):
        """Get all users, returning a list of UserRead schemas.
        Uses the generic all() method from BaseService.
        """
        users = await self.all(db)
        if not users:
            msg = "No users found."
            raise AppException(msg, status_code=404)
        return [UserRead.from_orm(user) for user in users]

    async def create_user(
        self,
        db: AsyncSession,
        username: str,
        name: str,
        email: str,
        password: str,
        roles: str = "user",
        is_active: int = 1,
    ):
        """Create a new user, hashing the password before saving.
        Uses the generic add() method from BaseService for DB insert.
        """
        from app.core.security import get_password_hash

        try:
            hashed_password = get_password_hash(password)
            user_dict = {
                "username": username,
                "name": name,
                "email": email,
                "hashed_password": hashed_password,
                "roles": roles,
                "is_active": is_active,
            }
            user = await self.add(db, user_dict)
            return UserRead.from_orm(user)
        except SQLAlchemyError as e:
            await db.rollback()
            if "unique constraint" in str(e).lower():
                msg = "Email or Username already exists."
                raise AppException(msg, status_code=400)
            msg = "Database error occurred while creating user."
            raise AppException(
                msg, status_code=500,
            )

    # Enhanced methods with parallel processing

    async def bulk_create_users_parallel(
        self,
        db: AsyncSession,
        users_data: list[dict[str, Any]],
        batch_size: int | None = 50,
    ) -> list[UserRead]:
        """Create multiple users in parallel with validation and password hashing.

        Args:
            db: Database session
            users_data: List of user data dictionaries
            batch_size: Batch size for processing

        Returns:
            List of created UserRead schemas

        """

        def validate_and_hash_user(user_data: dict[str, Any]) -> dict[str, Any]:
            """Validate user data and hash password (CPU-bound)."""
            try:
                from app.core.security import get_password_hash

                # Validation logic
                required_fields = ["username", "name", "email", "password"]
                for field in required_fields:
                    if field not in user_data:
                        msg = f"Missing required field: {field}"
                        raise ValueError(msg)

                # Hash password
                validated_data = user_data.copy()
                validated_data["hashed_password"] = get_password_hash(
                    user_data["password"],
                )
                validated_data.pop("password")  # Remove plain password

                # Set defaults
                validated_data.setdefault("roles", "user")
                validated_data.setdefault("is_active", 1)

                return validated_data
            except Exception as e:
                logger.error(f"Error validating user data: {e}")
                raise

        # Create users in parallel with validation
        created_users = await self.bulk_create_parallel(
            db, users_data, batch_size, validate_and_hash_user,
        )

        # Convert to UserRead schemas
        return [UserRead.from_orm(user) for user in created_users]

    async def bulk_update_users_parallel(
        self, db: AsyncSession, updates: list[dict[str, Any]],
    ) -> list[UserRead]:
        """Update multiple users in parallel with password hashing if needed.

        Args:
            db: Database session
            updates: List of update dictionaries with 'id' field

        Returns:
            List of updated UserRead schemas

        """

        def process_user_update(update_data: dict[str, Any]) -> dict[str, Any]:
            """Process user update data (hash password if provided)."""
            try:
                processed_data = update_data.copy()

                # Hash password if provided
                if "password" in processed_data:
                    from app.core.security import get_password_hash

                    processed_data["hashed_password"] = get_password_hash(
                        processed_data["password"],
                    )
                    processed_data.pop("password")

                return processed_data
            except Exception as e:
                logger.error(f"Error processing user update: {e}")
                raise

        # Update users in parallel
        updated_users = await self.bulk_update_parallel(
            db, updates, processor_func=process_user_update,
        )

        # Convert to UserRead schemas
        return [UserRead.from_orm(user) for user in updated_users if user]

    async def authenticate_users_parallel(
        self, db: AsyncSession, credentials: list[dict[str, str]],
    ) -> list[UserRead | None]:
        """Authenticate multiple users in parallel.

        Args:
            db: Database session
            credentials: List of {'identifier': str, 'password': str} dicts

        Returns:
            List of authenticated users (None for failed authentication)

        """

        async def authenticate_single(cred: dict[str, str]) -> UserRead | None:
            """Authenticate a single user."""
            try:
                user = await self.authenticate_user(
                    db, cred["identifier"], cred["password"],
                )
                return UserRead.from_orm(user) if user else None
            except Exception as e:
                logger.error(f"Authentication error: {e}")
                return None

        # Execute authentications in parallel
        results = await execute_parallel(
            authenticate_single, credentials, TaskType.IO_BOUND, max_workers=10,
        )

        return [result for result in results if not isinstance(result, Exception)]

    async def search_users_parallel(
        self, db: AsyncSession, search_queries: list[dict[str, Any]],
    ) -> list[list[UserRead]]:
        """Execute multiple user search queries in parallel.

        Args:
            db: Database session
            search_queries: List of search condition dictionaries

        Returns:
            List of search results for each query

        """
        # Execute searches in parallel
        search_results = await self.find_parallel_with_conditions(db, search_queries)

        # Convert to UserRead schemas
        return [
            [UserRead.from_orm(user) for user in users]
            for users in search_results
            if not isinstance(users, Exception)
        ]

    async def send_user_notifications_parallel(
        self,
        user_ids: list[int],
        notification_data: dict[str, Any],
        notification_func: Callable | None = None,
    ) -> list[Any]:
        """Send notifications to multiple users in parallel.

        Args:
            user_ids: List of user IDs
            notification_data: Notification content
            notification_func: Function to send notification

        Returns:
            List of notification results

        """
        if not notification_func:
            # Default notification function (placeholder)
            def default_notification(user_id: int) -> dict[str, Any]:
                logger.info(f"Sending notification to user {user_id}")
                return {"user_id": user_id, "status": "sent", "data": notification_data}

            notification_func = default_notification

        # Send notifications in parallel
        return await execute_parallel(
            notification_func, user_ids, TaskType.IO_BOUND, max_workers=15,
        )

    async def export_users_parallel(
        self,
        db: AsyncSession,
        filters: dict[str, Any] | None = None,
        export_format: str = "dict",
    ) -> list[dict[str, Any]]:
        """Export users data in parallel with processing.

        Args:
            db: Database session
            filters: Optional filters for user selection
            export_format: Format for export data

        Returns:
            List of exported user data

        """
        # Get users based on filters
        users = await self.find(db, filters)

        def process_user_export(user: User) -> dict[str, Any]:
            """Process user data for export (CPU-bound)."""
            try:
                user_data = {
                    "id": user.id,
                    "username": user.username,
                    "name": user.name,
                    "email": user.email,
                    "roles": user.roles,
                    "is_active": user.is_active,
                    "created_at": getattr(user, "created_at", None),
                    "updated_at": getattr(user, "updated_at", None),
                }

                # Add computed fields
                user_data["full_display_name"] = f"{user.name} ({user.username})"
                user_data["status"] = "Active" if user.is_active else "Inactive"

                return user_data
            except Exception as e:
                logger.error(f"Error processing user export: {e}")
                return {}

        # Process users in parallel
        return await execute_parallel(
            process_user_export, users, TaskType.CPU_BOUND, max_workers=4,
        )

    async def generate_user_statistics_parallel(
        self, db: AsyncSession,
    ) -> dict[str, Any]:
        """Generate comprehensive user statistics in parallel.

        Args:
            db: Database session

        Returns:
            Dictionary of user statistics

        """
        stat_configs = [
            {"name": "total_users", "type": "count", "filters": None},
            {"name": "active_users", "type": "count", "filters": {"is_active": 1}},
            {"name": "inactive_users", "type": "count", "filters": {"is_active": 0}},
            {"name": "admin_users", "type": "count", "filters": {"roles": "admin"}},
            {"name": "regular_users", "type": "count", "filters": {"roles": "user"}},
        ]

        return await self.generate_statistics_parallel(db, stat_configs)

    async def validate_users_parallel(
        self,
        users_data: list[dict[str, Any]],
        validation_rules: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Validate multiple users data in parallel.

        Args:
            users_data: List of user data to validate
            validation_rules: Optional custom validation rules

        Returns:
            List of validated user data

        """

        def validate_user_data(user_data: dict[str, Any]) -> dict[str, Any]:
            """Validate single user data (CPU-bound)."""
            try:
                # Basic validation
                required_fields = ["username", "email", "name"]
                for field in required_fields:
                    if not user_data.get(field):
                        msg = f"Missing or empty field: {field}"
                        raise ValueError(msg)

                # Email validation
                import re

                email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
                if not re.match(email_pattern, user_data["email"]):
                    msg = "Invalid email format"
                    raise ValueError(msg)

                # Username validation
                if len(user_data["username"]) < 3:
                    msg = "Username must be at least 3 characters"
                    raise ValueError(msg)

                # Custom validation rules
                if validation_rules:
                    for field, rule in validation_rules.items():
                        if field in user_data:
                            if (
                                "min_length" in rule
                                and len(str(user_data[field])) < rule["min_length"]
                            ):
                                msg = f"{field} is too short"
                                raise ValueError(msg)
                            if (
                                "max_length" in rule
                                and len(str(user_data[field])) > rule["max_length"]
                            ):
                                msg = f"{field} is too long"
                                raise ValueError(msg)

                return user_data
            except Exception as e:
                logger.error(f"Validation error for user data: {e}")
                raise

        return await self.validate_data_parallel(users_data, validate_user_data)
