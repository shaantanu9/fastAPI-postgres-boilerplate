# Complete Current System Analysis & Enhancement Plan

## 🚨 **CRITICAL FINDINGS**

### **Current State:**

- ❌ **Users table DOES NOT EXIST** in database (dropped by migration)
- ✅ **User model exists** in code but mismatched with DB
- ✅ **User schemas exist** but incomplete for enterprise use
- ✅ **Authentication system partially implemented**
- ⚠️ **Migration state is broken** - model vs DB mismatch

### **Database Reality Check:**

```sql
-- Current tables in database:
- alembic_version
- procrastinate_events
- procrastinate_jobs
- procrastinate_periodic_defers
- procrastinate_workers

-- MISSING: users table (was dropped!)
```

### **Code Reality Check:**

```python
# Current User Model (app/db/models/user.py):
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    name = Column(String, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String, nullable=False)
    password = Column(String, nullable=True)  # 🚨 SECURITY RISK
    is_active = Column(Integer, default=1)
    roles = Column(String, default="user")  # 🚨 Not scalable

# Current User Schema (app/db/schemas/user.py):
class UserBase(BaseModel):
    username: constr(min_length=3, max_length=50)
    name: constr(min_length=1, max_length=100)
    email: EmailStr
    roles: str = "user"
    is_active: int = 1

class UserCreate(UserBase):
    password: constr(min_length=8, max_length=128)
```

## 🛠️ **ENHANCEMENT STRATEGY**

### **Phase 1: Fix Broken State (CRITICAL)**

#### **1.1 Clean Migration State**

```bash
# Reset to clean state
alembic downgrade base
# Remove broken migrations
rm alembic/versions/59e065da9fc5_add_user_model.py
rm alembic/versions/78d24fe72405_fix_user_table_creation.py
rm alembic/versions/224f348c5f78_add_user_model.py
```

#### **1.2 Enhanced User Model**

```python
# app/db/models/user.py
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.base import Base

class User(Base):
    __tablename__ = "users"

    # Basic Identity
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    first_name = Column(String(50), nullable=False)
    last_name = Column(String(50), nullable=False)

    # Security
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)

    # Account Security
    failed_login_attempts = Column(Integer, default=0)
    account_locked_until = Column(DateTime, nullable=True)
    last_login = Column(DateTime, nullable=True)
    password_changed_at = Column(DateTime, server_default=func.now())

    # MFA Support
    mfa_enabled = Column(Boolean, default=False)
    mfa_secret = Column(String(32), nullable=True)

    # Audit
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationships (will be added in Phase 2)
    # roles = relationship("Role", secondary="user_roles", back_populates="users")

class Role(Base):
    __tablename__ = "roles"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, nullable=False)
    description = Column(Text)
    is_system_role = Column(Boolean, default=False)
    created_at = Column(DateTime, server_default=func.now())

class Permission(Base):
    __tablename__ = "permissions"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)
    resource = Column(String(100), nullable=False)
    action = Column(String(50), nullable=False)
    description = Column(Text)
    created_at = Column(DateTime, server_default=func.now())

class UserRole(Base):
    __tablename__ = "user_roles"

    user_id = Column(Integer, ForeignKey("users.id"), primary_key=True)
    role_id = Column(Integer, ForeignKey("roles.id"), primary_key=True)
    granted_at = Column(DateTime, server_default=func.now())
    granted_by = Column(Integer, ForeignKey("users.id"), nullable=True)

class RolePermission(Base):
    __tablename__ = "role_permissions"

    role_id = Column(Integer, ForeignKey("roles.id"), primary_key=True)
    permission_id = Column(Integer, ForeignKey("permissions.id"), primary_key=True)

class SecurityEvent(Base):
    __tablename__ = "security_events"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    event_type = Column(String(50), nullable=False)
    event_data = Column(Text)  # JSON as text for now
    ip_address = Column(String(45))
    user_agent = Column(Text)
    risk_score = Column(Integer, default=0)
    created_at = Column(DateTime, server_default=func.now())
```

#### **1.3 Enhanced User Schemas**

```python
# app/db/schemas/user.py
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime

class UserBase(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    first_name: str = Field(..., min_length=1, max_length=50)
    last_name: str = Field(..., min_length=1, max_length=50)
    is_active: bool = True

class UserCreate(UserBase):
    password: str = Field(..., min_length=12, max_length=128,
                         description="Password must be at least 12 characters")

class UserUpdate(BaseModel):
    first_name: Optional[str] = Field(None, min_length=1, max_length=50)
    last_name: Optional[str] = Field(None, min_length=1, max_length=50)
    email: Optional[EmailStr] = None
    is_active: Optional[bool] = None

class UserRead(UserBase):
    id: int
    is_verified: bool
    mfa_enabled: bool
    last_login: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class UserSecurity(BaseModel):
    id: int
    username: str
    email: str
    is_active: bool
    is_verified: bool
    mfa_enabled: bool
    failed_login_attempts: int
    account_locked_until: Optional[datetime]
    last_login: Optional[datetime]
    roles: List[str] = []

    class Config:
        from_attributes = True

class PasswordChange(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=12, max_length=128)

class PasswordReset(BaseModel):
    token: str
    new_password: str = Field(..., min_length=12, max_length=128)

# Role Schemas
class RoleBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=50)
    description: Optional[str] = None

class RoleCreate(RoleBase):
    pass

class RoleRead(RoleBase):
    id: int
    is_system_role: bool
    created_at: datetime

    class Config:
        from_attributes = True

# Permission Schemas
class PermissionBase(BaseModel):
    name: str = Field(..., min_length=3, max_length=100)
    resource: str = Field(..., min_length=2, max_length=100)
    action: str = Field(..., min_length=2, max_length=50)
    description: Optional[str] = None

class PermissionCreate(PermissionBase):
    pass

class PermissionRead(PermissionBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True
```

### **Phase 2: Enhanced Authentication (HIGH PRIORITY)**

#### **2.1 Enhanced Security Service**

```python
# app/core/security.py
import re
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from passlib.context import CryptContext
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

class EnhancedSecurityService:
    def __init__(self):
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        self.MAX_LOGIN_ATTEMPTS = 5
        self.LOCKOUT_DURATION = timedelta(minutes=30)

    def validate_password_strength(self, password: str) -> bool:
        """Enforce enterprise password policy"""
        errors = []

        if len(password) < 12:
            errors.append("Password must be at least 12 characters long")

        if not re.search(r"[A-Z]", password):
            errors.append("Password must contain at least one uppercase letter")

        if not re.search(r"[a-z]", password):
            errors.append("Password must contain at least one lowercase letter")

        if not re.search(r"\d", password):
            errors.append("Password must contain at least one digit")

        if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
            errors.append("Password must contain at least one special character")

        if errors:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"message": "Password does not meet requirements", "errors": errors}
            )
        return True

    def hash_password(self, password: str) -> str:
        return self.pwd_context.hash(password)

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        return self.pwd_context.verify(plain_password, hashed_password)

    def is_account_locked(self, user) -> bool:
        if user.account_locked_until and user.account_locked_until > datetime.utcnow():
            return True
        return False

    def handle_failed_login(self, db: Session, user, ip_address: str):
        user.failed_login_attempts += 1

        if user.failed_login_attempts >= self.MAX_LOGIN_ATTEMPTS:
            user.account_locked_until = datetime.utcnow() + self.LOCKOUT_DURATION
            # TODO: Log security event

        db.commit()

    def handle_successful_login(self, db: Session, user, ip_address: str):
        user.failed_login_attempts = 0
        user.account_locked_until = None
        user.last_login = datetime.utcnow()
        # TODO: Log security event
        db.commit()

security_service = EnhancedSecurityService()
```

#### **2.2 Enhanced User Service**

```python
# app/services/user_service.py (enhanced)
from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models.user import User, Role
from app.db.schemas.user import UserCreate, UserUpdate, UserRead
from app.core.security import security_service
from app.services.base_service import EnhancedBaseService

class EnhancedUserService(EnhancedBaseService[User]):

    async def create_user(self, db: AsyncSession, user_data: UserCreate) -> User:
        """Create a new user with enhanced security"""

        # Validate password strength
        security_service.validate_password_strength(user_data.password)

        # Check if user already exists
        existing_user = await self.get_by_email(db, user_data.email)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already registered"
            )

        existing_username = await self.get_by_username(db, user_data.username)
        if existing_username:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Username already taken"
            )

        # Create user
        hashed_password = security_service.hash_password(user_data.password)
        user_dict = {
            "username": user_data.username,
            "email": user_data.email,
            "first_name": user_data.first_name,
            "last_name": user_data.last_name,
            "hashed_password": hashed_password,
            "is_active": user_data.is_active
        }

        user = await self.add(db, user_dict)

        # Assign default role
        # TODO: Implement role assignment

        return user

    async def authenticate_user(self, db: AsyncSession, identifier: str, password: str) -> Optional[User]:
        """Authenticate user with enhanced security checks"""

        user = await self.get_by_username_or_email(db, identifier)
        if not user:
            return None

        # Check account lockout
        if security_service.is_account_locked(user):
            raise HTTPException(
                status_code=status.HTTP_423_LOCKED,
                detail="Account temporarily locked due to too many failed attempts"
            )

        # Verify password
        if not security_service.verify_password(password, user.hashed_password):
            security_service.handle_failed_login(db, user, "0.0.0.0")  # TODO: Get real IP
            return None

        # Success
        security_service.handle_successful_login(db, user, "0.0.0.0")  # TODO: Get real IP
        return user

    async def get_by_username(self, db: AsyncSession, username: str) -> Optional[User]:
        result = await db.execute(
            select(User).where(User.username == username)
        )
        return result.scalar_one_or_none()

    async def get_by_email(self, db: AsyncSession, email: str) -> Optional[User]:
        result = await db.execute(
            select(User).where(User.email == email)
        )
        return result.scalar_one_or_none()

    async def get_by_username_or_email(self, db: AsyncSession, identifier: str) -> Optional[User]:
        result = await db.execute(
            select(User).where(
                (User.username == identifier) | (User.email == identifier)
            )
        )
        return result.scalar_one_or_none()
```

### **Phase 3: Protected Routes Example**

#### **3.1 Authentication Dependencies**

```python
# app/core/auth_dependencies.py
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.services.user_service import EnhancedUserService
from app.core.jwt import verify_access_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = verify_access_token(token)
        user_id: int = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except:
        raise credentials_exception

    user_service = EnhancedUserService()
    user = await user_service.get(db, user_id)
    if user is None:
        raise credentials_exception

    return user

async def get_current_active_user(current_user = Depends(get_current_user)):
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

def require_role(role_name: str):
    async def role_dependency(current_user = Depends(get_current_active_user)):
        # TODO: Implement proper role checking with RBAC
        user_roles = []  # Get from user.roles relationship
        if role_name not in user_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required role: {role_name}"
            )
        return current_user
    return role_dependency

def require_permission(resource: str, action: str):
    async def permission_dependency(current_user = Depends(get_current_active_user)):
        # TODO: Implement ABAC permission checking
        # Check if user has permission to perform action on resource
        has_permission = True  # Placeholder
        if not has_permission:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required permission: {action} on {resource}"
            )
        return current_user
    return permission_dependency
```

#### **3.2 Protected User Routes**

```python
# app/api/v1/endpoints/users.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.db.session import get_db
from app.db.schemas.user import UserRead, UserCreate, UserUpdate
from app.services.user_service import EnhancedUserService
from app.core.auth_dependencies import (
    get_current_active_user,
    require_role,
    require_permission
)

router = APIRouter(prefix="/users", tags=["Users"])

# Public endpoint (registration)
@router.post("/", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def create_user(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db)
):
    """Public user registration"""
    user_service = EnhancedUserService()
    return await user_service.create_user(db, user_data)

# Protected endpoints
@router.get("/me", response_model=UserRead)
async def get_current_user_profile(
    current_user = Depends(get_current_active_user)
):
    """Get current user's profile"""
    return current_user

@router.put("/me", response_model=UserRead)
async def update_current_user_profile(
    user_update: UserUpdate,
    current_user = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Update current user's profile"""
    user_service = EnhancedUserService()
    return await user_service.update(db, current_user.id, user_update.dict(exclude_unset=True))

# Admin-only endpoints
@router.get("/", response_model=List[UserRead])
async def list_all_users(
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_role("admin"))
):
    """List all users (admin only)"""
    user_service = EnhancedUserService()
    return await user_service.all(db)

@router.get("/{user_id}", response_model=UserRead)
async def get_user_by_id(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_permission("users", "read"))
):
    """Get user by ID (requires permission)"""
    user_service = EnhancedUserService()
    user = await user_service.get(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@router.delete("/{user_id}")
async def delete_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_permission("users", "delete"))
):
    """Delete user (requires permission)"""
    user_service = EnhancedUserService()
    deleted = await user_service.delete(db, user_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="User not found")
    return {"message": "User deleted successfully"}
```

## 🚀 **IMPLEMENTATION STEPS**

### **Step 1: Clean Current State**

```bash
# 1. Reset migrations
alembic downgrade base

# 2. Remove broken migrations
rm alembic/versions/59e065da9fc5_add_user_model.py
rm alembic/versions/78d24fe72405_fix_user_table_creation.py
rm alembic/versions/224f348c5f78_add_user_model.py

# 3. Update models with enhanced version
# 4. Create new migration
alembic revision --autogenerate -m "Create enhanced user management system"

# 5. Apply migration
alembic upgrade head
```

### **Step 2: Test Enhanced System**

```bash
# 1. Create test user via API
curl -X POST "http://localhost:8000/api/v1/users/" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "email": "test@example.com",
    "first_name": "Test",
    "last_name": "User",
    "password": "SecurePassword123!"
  }'

# 2. Login and get token
curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=testuser&password=SecurePassword123!"

# 3. Access protected route
curl -X GET "http://localhost:8000/api/v1/users/me" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

This plan addresses your current broken state and provides a clear path to enterprise-grade user management with proper authentication and authorization!
