from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models.user import User
from app.core.exception_handlers import AppException
from sqlalchemy.future import select
from sqlalchemy.exc import SQLAlchemyError
from app.db.schemas.user import UserRead
import asyncio
from loguru import logger

from app.services.enhanced_base_service import EnhancedBaseService
from app.utils.concurrent_utils import parallel_io, parallel_cpu, TaskType, execute_parallel

class UserService(EnhancedBaseService[User]):
    """
    Service class for user-related database operations.
    Inherits generic CRUD methods from BaseService, and adds user-specific logic.
    Use this service in endpoints and business logic to keep code DRY and maintainable.
    """
    def __init__(self):
        # Initialize with the User SQLAlchemy model
        super().__init__(User)

    async def get_by_username_or_email(self, db: AsyncSession, identifier: str):
        """
        Retrieve a user by username or email (supports login with either).
        Custom logic not covered by generic BaseService methods.
        """
        result = await db.execute(
            select(User).where((User.email == identifier) | (User.username == identifier))
        )
        user = result.scalars().first()
        if user:
            return user
        return None

    async def get_by_username(self, db: AsyncSession, username: str):
        """
        Retrieve a user by username only (simple wrapper for find_one).
        """
        result = await db.execute(select(User).where(User.username == username))
        user = result.scalars().first()
        if user:
            return user
        return None

    async def authenticate_user(self, db: AsyncSession, identifier: str, password: str):
        """
        Authenticate a user by username/email and password.
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
        """
        Get all users, returning a list of UserRead schemas.
        Uses the generic all() method from BaseService.
        """
        users = await self.all(db)
        if not users:
            raise AppException("No users found.", status_code=404)
        return [UserRead.from_orm(user) for user in users]

    async def create_user(self, db: AsyncSession, username: str, name: str, email: str, password: str, roles: str = "user", is_active: int = 1):
        """
        Create a new user, hashing the password before saving.
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
                raise AppException("Email or Username already exists.", status_code=400)
            raise AppException("Database error occurred while creating user.", status_code=500)

    # Enhanced methods with parallel processing

    async def bulk_create_users_parallel(
        self, 
        db: AsyncSession, 
        users_data: List[Dict[str, Any]],
        batch_size: Optional[int] = 50
    ) -> List[UserRead]:
        """
        Create multiple users in parallel with validation and password hashing.
        
        Args:
            db: Database session
            users_data: List of user data dictionaries
            batch_size: Batch size for processing
        
        Returns:
            List of created UserRead schemas
        """
        def validate_and_hash_user(user_data: Dict[str, Any]) -> Dict[str, Any]:
            """Validate user data and hash password (CPU-bound)"""
            try:
                from app.core.security import get_password_hash
                
                # Validation logic
                required_fields = ['username', 'name', 'email', 'password']
                for field in required_fields:
                    if field not in user_data:
                        raise ValueError(f"Missing required field: {field}")
                
                # Hash password
                validated_data = user_data.copy()
                validated_data['hashed_password'] = get_password_hash(user_data['password'])
                validated_data.pop('password')  # Remove plain password
                
                # Set defaults
                validated_data.setdefault('roles', 'user')
                validated_data.setdefault('is_active', 1)
                
                return validated_data
            except Exception as e:
                logger.error(f"Error validating user data: {e}")
                raise e

        # Create users in parallel with validation
        created_users = await self.bulk_create_parallel(
            db, users_data, batch_size, validate_and_hash_user
        )
        
        # Convert to UserRead schemas
        return [UserRead.from_orm(user) for user in created_users]

    async def bulk_update_users_parallel(
        self, 
        db: AsyncSession, 
        updates: List[Dict[str, Any]]
    ) -> List[UserRead]:
        """
        Update multiple users in parallel with password hashing if needed.
        
        Args:
            db: Database session
            updates: List of update dictionaries with 'id' field
        
        Returns:
            List of updated UserRead schemas
        """
        def process_user_update(update_data: Dict[str, Any]) -> Dict[str, Any]:
            """Process user update data (hash password if provided)"""
            try:
                processed_data = update_data.copy()
                
                # Hash password if provided
                if 'password' in processed_data:
                    from app.core.security import get_password_hash
                    processed_data['hashed_password'] = get_password_hash(processed_data['password'])
                    processed_data.pop('password')
                
                return processed_data
            except Exception as e:
                logger.error(f"Error processing user update: {e}")
                raise e

        # Update users in parallel
        updated_users = await self.bulk_update_parallel(
            db, updates, processor_func=process_user_update
        )
        
        # Convert to UserRead schemas
        return [UserRead.from_orm(user) for user in updated_users if user]

    async def authenticate_users_parallel(
        self, 
        db: AsyncSession, 
        credentials: List[Dict[str, str]]
    ) -> List[Optional[UserRead]]:
        """
        Authenticate multiple users in parallel.
        
        Args:
            db: Database session
            credentials: List of {'identifier': str, 'password': str} dicts
        
        Returns:
            List of authenticated users (None for failed authentication)
        """
        async def authenticate_single(cred: Dict[str, str]) -> Optional[UserRead]:
            """Authenticate a single user"""
            try:
                user = await self.authenticate_user(
                    db, cred['identifier'], cred['password']
                )
                return UserRead.from_orm(user) if user else None
            except Exception as e:
                logger.error(f"Authentication error: {e}")
                return None

        # Execute authentications in parallel
        results = await execute_parallel(
            authenticate_single, credentials, TaskType.IO_BOUND, max_workers=10
        )
        
        return [result for result in results if not isinstance(result, Exception)]

    async def search_users_parallel(
        self, 
        db: AsyncSession, 
        search_queries: List[Dict[str, Any]]
    ) -> List[List[UserRead]]:
        """
        Execute multiple user search queries in parallel.
        
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
        user_ids: List[int], 
        notification_data: Dict[str, Any],
        notification_func: callable = None
    ) -> List[Any]:
        """
        Send notifications to multiple users in parallel.
        
        Args:
            user_ids: List of user IDs
            notification_data: Notification content
            notification_func: Function to send notification
        
        Returns:
            List of notification results
        """
        if not notification_func:
            # Default notification function (placeholder)
            def default_notification(user_id: int) -> Dict[str, Any]:
                logger.info(f"Sending notification to user {user_id}")
                return {"user_id": user_id, "status": "sent", "data": notification_data}
            notification_func = default_notification

        # Send notifications in parallel
        return await execute_parallel(
            notification_func, user_ids, TaskType.IO_BOUND, max_workers=15
        )

    async def export_users_parallel(
        self, 
        db: AsyncSession, 
        filters: Optional[Dict[str, Any]] = None,
        export_format: str = "dict"
    ) -> List[Dict[str, Any]]:
        """
        Export users data in parallel with processing.
        
        Args:
            db: Database session
            filters: Optional filters for user selection
            export_format: Format for export data
        
        Returns:
            List of exported user data
        """
        # Get users based on filters
        users = await self.find(db, filters)
        
        def process_user_export(user: User) -> Dict[str, Any]:
            """Process user data for export (CPU-bound)"""
            try:
                user_data = {
                    'id': user.id,
                    'username': user.username,
                    'name': user.name,
                    'email': user.email,
                    'roles': user.roles,
                    'is_active': user.is_active,
                    'created_at': getattr(user, 'created_at', None),
                    'updated_at': getattr(user, 'updated_at', None)
                }
                
                # Add computed fields
                user_data['full_display_name'] = f"{user.name} ({user.username})"
                user_data['status'] = "Active" if user.is_active else "Inactive"
                
                return user_data
            except Exception as e:
                logger.error(f"Error processing user export: {e}")
                return {}

        # Process users in parallel
        return await execute_parallel(
            process_user_export, users, TaskType.CPU_BOUND, max_workers=4
        )

    async def generate_user_statistics_parallel(self, db: AsyncSession) -> Dict[str, Any]:
        """
        Generate comprehensive user statistics in parallel.
        
        Args:
            db: Database session
        
        Returns:
            Dictionary of user statistics
        """
        stat_configs = [
            {'name': 'total_users', 'type': 'count', 'filters': None},
            {'name': 'active_users', 'type': 'count', 'filters': {'is_active': 1}},
            {'name': 'inactive_users', 'type': 'count', 'filters': {'is_active': 0}},
            {'name': 'admin_users', 'type': 'count', 'filters': {'roles': 'admin'}},
            {'name': 'regular_users', 'type': 'count', 'filters': {'roles': 'user'}},
        ]
        
        return await self.generate_statistics_parallel(db, stat_configs)

    async def validate_users_parallel(
        self, 
        users_data: List[Dict[str, Any]],
        validation_rules: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Validate multiple users data in parallel.
        
        Args:
            users_data: List of user data to validate
            validation_rules: Optional custom validation rules
        
        Returns:
            List of validated user data
        """
        def validate_user_data(user_data: Dict[str, Any]) -> Dict[str, Any]:
            """Validate single user data (CPU-bound)"""
            try:
                # Basic validation
                required_fields = ['username', 'email', 'name']
                for field in required_fields:
                    if not user_data.get(field):
                        raise ValueError(f"Missing or empty field: {field}")
                
                # Email validation
                import re
                email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
                if not re.match(email_pattern, user_data['email']):
                    raise ValueError("Invalid email format")
                
                # Username validation
                if len(user_data['username']) < 3:
                    raise ValueError("Username must be at least 3 characters")
                
                # Custom validation rules
                if validation_rules:
                    for field, rule in validation_rules.items():
                        if field in user_data:
                            if 'min_length' in rule and len(str(user_data[field])) < rule['min_length']:
                                raise ValueError(f"{field} is too short")
                            if 'max_length' in rule and len(str(user_data[field])) > rule['max_length']:
                                raise ValueError(f"{field} is too long")
                
                return user_data
            except Exception as e:
                logger.error(f"Validation error for user data: {e}")
                raise e

        return await self.validate_data_parallel(users_data, validate_user_data)
