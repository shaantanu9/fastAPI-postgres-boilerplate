# FastAPI Enterprise Authentication Implementation Roadmap

## 🎯 **Project Overview**

Transform the current basic JWT authentication system into an enterprise-grade authentication and authorization platform with proper user management, RBAC, and security features.

## 🔍 **Current State Assessment**

### **✅ What's Working**

- Basic JWT authentication with PyJWT
- bcrypt password hashing
- FastAPI OAuth2 password bearer scheme
- Basic user registration and login
- Database connectivity with PostgreSQL

### **🚨 Critical Issues to Fix**

1. **SECURITY VULNERABILITY**: Plain password field stored in database
2. **Missing Features**: No refresh tokens, account lockout, or audit logging
3. **Poor Scalability**: String-based roles instead of normalized tables
4. **No Enterprise Features**: Missing MFA, OAuth2, rate limiting

## 📋 **Implementation Phases**

## **Phase 1: Critical Security Hardening (Week 1-2)**

### **1.1 Database Schema Updates**

**Priority: CRITICAL**

```sql
-- Step 1: Remove dangerous plain password field
ALTER TABLE users DROP COLUMN password;

-- Step 2: Add security fields
ALTER TABLE users ADD COLUMN is_verified BOOLEAN DEFAULT FALSE;
ALTER TABLE users ADD COLUMN mfa_enabled BOOLEAN DEFAULT FALSE;
ALTER TABLE users ADD COLUMN mfa_secret VARCHAR(32);
ALTER TABLE users ADD COLUMN last_login TIMESTAMP;
ALTER TABLE users ADD COLUMN failed_login_attempts INTEGER DEFAULT 0;
ALTER TABLE users ADD COLUMN account_locked_until TIMESTAMP;
ALTER TABLE users ADD COLUMN password_changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE users ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE users ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;

-- Step 3: Create proper RBAC tables
CREATE TABLE roles (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) UNIQUE NOT NULL,
    description TEXT,
    is_system_role BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE permissions (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,
    resource VARCHAR(100) NOT NULL,
    action VARCHAR(50) NOT NULL,
    conditions JSONB,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE user_roles (
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    role_id INTEGER REFERENCES roles(id) ON DELETE CASCADE,
    granted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    granted_by INTEGER REFERENCES users(id),
    expires_at TIMESTAMP,
    PRIMARY KEY (user_id, role_id)
);

CREATE TABLE role_permissions (
    role_id INTEGER REFERENCES roles(id) ON DELETE CASCADE,
    permission_id INTEGER REFERENCES permissions(id) ON DELETE CASCADE,
    PRIMARY KEY (role_id, permission_id)
);

-- Step 4: Security audit table
CREATE TABLE security_events (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    event_type VARCHAR(50) NOT NULL,
    event_data JSONB,
    ip_address INET,
    user_agent TEXT,
    risk_score INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### **1.2 Enhanced User Model**

**File: `app/db/models/user.py`**

```python
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.base_class import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    mfa_enabled = Column(Boolean, default=False)
    mfa_secret = Column(String(32), nullable=True)
    last_login = Column(DateTime, nullable=True)
    failed_login_attempts = Column(Integer, default=0)
    account_locked_until = Column(DateTime, nullable=True)
    password_changed_at = Column(DateTime, server_default=func.now())
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationships
    roles = relationship("Role", secondary="user_roles", back_populates="users")
    security_events = relationship("SecurityEvent", back_populates="user")

class Role(Base):
    __tablename__ = "roles"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, nullable=False)
    description = Column(Text)
    is_system_role = Column(Boolean, default=False)
    created_at = Column(DateTime, server_default=func.now())

    # Relationships
    users = relationship("User", secondary="user_roles", back_populates="roles")
    permissions = relationship("Permission", secondary="role_permissions", back_populates="roles")

class Permission(Base):
    __tablename__ = "permissions"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)
    resource = Column(String(100), nullable=False)
    action = Column(String(50), nullable=False)
    conditions = Column(JSON)
    description = Column(Text)
    created_at = Column(DateTime, server_default=func.now())

    # Relationships
    roles = relationship("Role", secondary="role_permissions", back_populates="permissions")

class SecurityEvent(Base):
    __tablename__ = "security_events"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    event_type = Column(String(50), nullable=False)
    event_data = Column(JSON)
    ip_address = Column(String(45))
    user_agent = Column(Text)
    risk_score = Column(Integer, default=0)
    created_at = Column(DateTime, server_default=func.now())

    # Relationships
    user = relationship("User", back_populates="security_events")
```

### **1.3 Enhanced Security Service**

**File: `app/core/security.py`**

```python
import re
import secrets
from datetime import datetime, timedelta
from typing import Any, Dict, Optional, Union
from fastapi import HTTPException, status
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from app.db.models.user import User, SecurityEvent
from app.core.config import get_settings

settings = get_settings()

class AccountSecurityService:
    def __init__(self):
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        self.MAX_LOGIN_ATTEMPTS = 5
        self.LOCKOUT_DURATION = timedelta(minutes=30)

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        return self.pwd_context.verify(plain_password, hashed_password)

    def get_password_hash(self, password: str) -> str:
        return self.pwd_context.hash(password)

    def validate_password_strength(self, password: str) -> bool:
        """Enforce enterprise password policy"""
        if len(password) < 12:
            raise HTTPException(
                status_code=400,
                detail="Password must be at least 12 characters long"
            )

        if not re.search(r"[A-Z]", password):
            raise HTTPException(
                status_code=400,
                detail="Password must contain at least one uppercase letter"
            )

        if not re.search(r"[a-z]", password):
            raise HTTPException(
                status_code=400,
                detail="Password must contain at least one lowercase letter"
            )

        if not re.search(r"\d", password):
            raise HTTPException(
                status_code=400,
                detail="Password must contain at least one digit"
            )

        if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
            raise HTTPException(
                status_code=400,
                detail="Password must contain at least one special character"
            )

        return True

    def check_account_lockout(self, user: User) -> bool:
        if user.account_locked_until and user.account_locked_until > datetime.utcnow():
            return True
        return False

    def handle_failed_login(self, db: Session, user: User, ip_address: str) -> None:
        user.failed_login_attempts += 1

        if user.failed_login_attempts >= self.MAX_LOGIN_ATTEMPTS:
            user.account_locked_until = datetime.utcnow() + self.LOCKOUT_DURATION

            # Log security event
            self.log_security_event(
                db=db,
                user_id=user.id,
                event_type="account_locked",
                event_data={"attempts": user.failed_login_attempts},
                ip_address=ip_address,
                risk_score=8
            )

        db.commit()

    def handle_successful_login(self, db: Session, user: User, ip_address: str) -> None:
        user.failed_login_attempts = 0
        user.account_locked_until = None
        user.last_login = datetime.utcnow()

        self.log_security_event(
            db=db,
            user_id=user.id,
            event_type="login_success",
            event_data={"ip_address": ip_address},
            ip_address=ip_address,
            risk_score=1
        )

        db.commit()

    def log_security_event(
        self,
        db: Session,
        user_id: Optional[int],
        event_type: str,
        event_data: Dict[str, Any],
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        risk_score: int = 1
    ) -> SecurityEvent:
        security_event = SecurityEvent(
            user_id=user_id,
            event_type=event_type,
            event_data=event_data,
            ip_address=ip_address,
            user_agent=user_agent,
            risk_score=risk_score
        )

        db.add(security_event)
        db.commit()
        db.refresh(security_event)

        return security_event

# Initialize security service
security_service = AccountSecurityService()
```

### **1.4 Enhanced JWT Service**

**File: `app/core/jwt.py`**

```python
import jwt
import secrets
from datetime import datetime, timedelta
from typing import Any, Dict, Optional
from fastapi import HTTPException, status
from app.core.config import get_settings

settings = get_settings()

class JWTService:
    def __init__(self):
        self.SECRET_KEY = settings.jwt_secret_token
        self.ALGORITHM = "HS256"
        self.ACCESS_TOKEN_EXPIRE_MINUTES = 15  # Short-lived for security
        self.REFRESH_TOKEN_EXPIRE_DAYS = 30

    def create_access_token(self, data: Dict[str, Any]) -> str:
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(minutes=self.ACCESS_TOKEN_EXPIRE_MINUTES)

        # Enhanced claims for security
        to_encode.update({
            "exp": expire,
            "iat": datetime.utcnow(),
            "type": "access",
            "jti": secrets.token_urlsafe(32),  # JWT ID for blacklisting
            "aud": "api",  # Audience
            "iss": "fastapi-app"  # Issuer
        })

        return jwt.encode(to_encode, self.SECRET_KEY, algorithm=self.ALGORITHM)

    def create_refresh_token(self, user_id: int) -> str:
        to_encode = {
            "sub": str(user_id),
            "exp": datetime.utcnow() + timedelta(days=self.REFRESH_TOKEN_EXPIRE_DAYS),
            "iat": datetime.utcnow(),
            "type": "refresh",
            "jti": secrets.token_urlsafe(32)
        }

        return jwt.encode(to_encode, self.SECRET_KEY, algorithm=self.ALGORITHM)

    def verify_token(self, token: str, token_type: str = "access") -> Dict[str, Any]:
        try:
            payload = jwt.decode(token, self.SECRET_KEY, algorithms=[self.ALGORITHM])

            if payload.get("type") != token_type:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token type"
                )

            return payload
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token expired"
            )
        except jwt.JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )

# Initialize JWT service
jwt_service = JWTService()
```

### **1.5 Rate Limiting Implementation**

**File: `app/core/rate_limit.py`**

```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import FastAPI

limiter = Limiter(key_func=get_remote_address)

def setup_rate_limiting(app: FastAPI):
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
```

## **Phase 2: Enhanced Authentication Features (Week 3-4)**

### **2.1 Enhanced User Registration**

**File: `app/api/v1/endpoints/auth.py`**

```python
from fastapi import APIRouter, Depends, HTTPException, status, Request, BackgroundTasks
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from app.core.security import security_service
from app.core.jwt import jwt_service
from app.core.rate_limit import limiter
from app.db.session import get_db
from app.schemas.user import UserCreate, UserResponse, Token
from app.services.user_service import UserService

router = APIRouter()

@router.post("/register", response_model=UserResponse)
@limiter.limit("3/hour")
async def register_user(
    request: Request,
    user_data: UserCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    # Validate password strength
    security_service.validate_password_strength(user_data.password)

    # Check if user exists
    existing_user = UserService.get_by_email(db, user_data.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered"
        )

    # Create user
    hashed_password = security_service.get_password_hash(user_data.password)
    user = UserService.create(
        db=db,
        username=user_data.username,
        email=user_data.email,
        hashed_password=hashed_password
    )

    # Log registration event
    security_service.log_security_event(
        db=db,
        user_id=user.id,
        event_type="user_registered",
        event_data={"email": user.email},
        ip_address=request.client.host,
        risk_score=2
    )

    # TODO: Send email verification in background
    # background_tasks.add_task(send_verification_email, user.email)

    return user

@router.post("/login", response_model=Token)
@limiter.limit("5/minute")
async def login(
    request: Request,
    credentials: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    # Get user
    user = UserService.get_by_username_or_email(db, credentials.username)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )

    # Check account lockout
    if security_service.check_account_lockout(user):
        raise HTTPException(
            status_code=status.HTTP_423_LOCKED,
            detail="Account temporarily locked due to too many failed attempts"
        )

    # Verify password
    if not security_service.verify_password(credentials.password, user.hashed_password):
        security_service.handle_failed_login(db, user, request.client.host)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )

    # Check if user is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )

    # Success - handle login
    security_service.handle_successful_login(db, user, request.client.host)

    # Create tokens
    access_token = jwt_service.create_access_token({"sub": str(user.id)})
    refresh_token = jwt_service.create_refresh_token(user.id)

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }

@router.post("/refresh", response_model=Token)
async def refresh_token(
    refresh_token: str,
    db: Session = Depends(get_db)
):
    # Verify refresh token
    payload = jwt_service.verify_token(refresh_token, "refresh")
    user_id = int(payload.get("sub"))

    # Get user
    user = UserService.get(db, user_id)
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )

    # Create new access token
    access_token = jwt_service.create_access_token({"sub": str(user.id)})

    return {
        "access_token": access_token,
        "token_type": "bearer"
    }
```

### **2.2 Enhanced User Service**

**File: `app/services/user_service.py`**

```python
from typing import Optional
from sqlalchemy.orm import Session
from app.db.models.user import User, Role
from app.core.security import security_service

class UserService:
    @staticmethod
    def get(db: Session, user_id: int) -> Optional[User]:
        return db.query(User).filter(User.id == user_id).first()

    @staticmethod
    def get_by_email(db: Session, email: str) -> Optional[User]:
        return db.query(User).filter(User.email == email).first()

    @staticmethod
    def get_by_username(db: Session, username: str) -> Optional[User]:
        return db.query(User).filter(User.username == username).first()

    @staticmethod
    def get_by_username_or_email(db: Session, identifier: str) -> Optional[User]:
        return db.query(User).filter(
            (User.username == identifier) | (User.email == identifier)
        ).first()

    @staticmethod
    def create(
        db: Session,
        username: str,
        email: str,
        hashed_password: str,
        name: Optional[str] = None
    ) -> User:
        user = User(
            username=username,
            email=email,
            name=name,
            hashed_password=hashed_password
        )

        db.add(user)
        db.commit()
        db.refresh(user)

        # Assign default role
        default_role = db.query(Role).filter(Role.name == "user").first()
        if default_role:
            user.roles.append(default_role)
            db.commit()

        return user

    @staticmethod
    def update_password(db: Session, user: User, new_password: str) -> User:
        # Validate password strength
        security_service.validate_password_strength(new_password)

        # Update password
        user.hashed_password = security_service.get_password_hash(new_password)
        user.password_changed_at = datetime.utcnow()

        db.commit()
        db.refresh(user)
        return user

    @staticmethod
    def assign_role(db: Session, user: User, role_name: str) -> User:
        role = db.query(Role).filter(Role.name == role_name).first()
        if role and role not in user.roles:
            user.roles.append(role)
            db.commit()
            db.refresh(user)
        return user
```

## **Phase 3: Advanced Permission System (Week 5-6)**

### **3.1 Permission Management**

**File: `app/services/permission_service.py`**

```python
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from app.db.models.user import User, Permission, Role

class PermissionService:
    @staticmethod
    def has_permission(
        user: User,
        resource: str,
        action: str,
        context: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Check if user has permission with ABAC support"""
        context = context or {}

        # Get all user permissions (direct + role-based)
        all_permissions = list(user.direct_permissions) if hasattr(user, 'direct_permissions') else []

        # Add role-based permissions
        for role in user.roles:
            all_permissions.extend(role.permissions)

        # Check each permission
        for permission in all_permissions:
            if (permission.resource == resource and
                permission.action == action):

                # Evaluate conditions
                if PermissionService._evaluate_conditions(permission.conditions, user, context):
                    return True

        return False

    @staticmethod
    def _evaluate_conditions(
        conditions: Optional[Dict[str, Any]],
        user: User,
        context: Dict[str, Any]
    ) -> bool:
        """Evaluate ABAC conditions"""
        if not conditions:
            return True

        # Time-based conditions
        if "time_range" in conditions:
            from datetime import datetime
            current_time = datetime.now().time()
            start_time = datetime.strptime(conditions["time_range"]["start"], "%H:%M").time()
            end_time = datetime.strptime(conditions["time_range"]["end"], "%H:%M").time()

            if not (start_time <= current_time <= end_time):
                return False

        # IP-based conditions
        if "allowed_ips" in conditions:
            client_ip = context.get("ip_address")
            if client_ip not in conditions["allowed_ips"]:
                return False

        # Custom conditions can be added here

        return True

    @staticmethod
    def create_permission(
        db: Session,
        name: str,
        resource: str,
        action: str,
        description: Optional[str] = None,
        conditions: Optional[Dict[str, Any]] = None
    ) -> Permission:
        permission = Permission(
            name=name,
            resource=resource,
            action=action,
            description=description,
            conditions=conditions
        )

        db.add(permission)
        db.commit()
        db.refresh(permission)
        return permission
```

### **3.2 Permission Dependencies**

**File: `app/core/dependencies.py`**

```python
from typing import Callable
from fastapi import Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.core.jwt import jwt_service
from app.services.user_service import UserService
from app.services.permission_service import PermissionService

def get_current_user(
    request: Request,
    db: Session = Depends(get_db)
) -> User:
    """Get current authenticated user"""
    # Extract token from Authorization header
    authorization = request.headers.get("Authorization")
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid authorization header"
        )

    token = authorization.split(" ")[1]

    # Verify token
    payload = jwt_service.verify_token(token)
    user_id = int(payload.get("sub"))

    # Get user
    user = UserService.get(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )

    return user

def require_permission(resource: str, action: str) -> Callable:
    """Dependency to require specific permission"""
    def permission_dependency(
        request: Request,
        current_user: User = Depends(get_current_user)
    ) -> User:
        context = {
            "ip_address": request.client.host,
            "user_agent": request.headers.get("user-agent"),
            "timestamp": datetime.utcnow()
        }

        if not PermissionService.has_permission(current_user, resource, action, context):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions: {action} on {resource}"
            )

        return current_user

    return permission_dependency

def require_role(role_name: str) -> Callable:
    """Dependency to require specific role"""
    def role_dependency(
        current_user: User = Depends(get_current_user)
    ) -> User:
        user_roles = [role.name for role in current_user.roles]

        if role_name not in user_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Required role: {role_name}"
            )

        return current_user

    return role_dependency
```

## **Phase 4: Additional Security Features (Week 7-8)**

### **4.1 Security Headers Middleware**

**File: `app/middleware/security.py`**

```python
from fastapi import Request, Response
from fastapi.middleware.base import BaseHTTPMiddleware

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)

        # Security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Content-Security-Policy"] = "default-src 'self'"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"

        return response
```

### **4.2 Data Migration Script**

**File: `scripts/migrate_auth_data.py`**

```python
#!/usr/bin/env python3
"""
Migration script to convert existing data to new authentication system
"""

import sys
from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.db.models.user import User, Role, Permission
from app.core.security import security_service

def create_default_roles_permissions(db: Session):
    """Create default roles and permissions"""

    # Create default roles
    admin_role = Role(name="admin", description="Administrator role")
    user_role = Role(name="user", description="Standard user role")

    db.add(admin_role)
    db.add(user_role)
    db.commit()

    # Create default permissions
    permissions = [
        Permission(name="users.create", resource="users", action="create"),
        Permission(name="users.read", resource="users", action="read"),
        Permission(name="users.update", resource="users", action="update"),
        Permission(name="users.delete", resource="users", action="delete"),
        Permission(name="roles.manage", resource="roles", action="manage"),
        Permission(name="permissions.manage", resource="permissions", action="manage"),
    ]

    for perm in permissions:
        db.add(perm)

    db.commit()

    # Assign permissions to admin role
    admin_role.permissions = permissions
    db.commit()

    print("✅ Default roles and permissions created")

def migrate_existing_users(db: Session):
    """Migrate existing users to new security model"""

    users = db.query(User).all()
    user_role = db.query(Role).filter(Role.name == "user").first()

    for user in users:
        # Remove plain password field if it exists
        if hasattr(user, 'password'):
            delattr(user, 'password')

        # Assign default role if no roles
        if not user.roles:
            user.roles.append(user_role)

        # Set security defaults
        if user.failed_login_attempts is None:
            user.failed_login_attempts = 0

        if user.is_active is None:
            user.is_active = True

    db.commit()
    print(f"✅ Migrated {len(users)} users")

def main():
    db = SessionLocal()
    try:
        print("🚀 Starting authentication system migration...")

        # Step 1: Create default roles and permissions
        create_default_roles_permissions(db)

        # Step 2: Migrate existing users
        migrate_existing_users(db)

        print("✅ Migration completed successfully!")

    except Exception as e:
        print(f"❌ Migration failed: {e}")
        db.rollback()
        sys.exit(1)
    finally:
        db.close()

if __name__ == "__main__":
    main()
```

## **📈 Implementation Timeline**

| Phase       | Duration | Deliverables                              | Risk Level |
| ----------- | -------- | ----------------------------------------- | ---------- |
| **Phase 1** | 2 weeks  | Critical security fixes, enhanced models  | 🔴 High    |
| **Phase 2** | 2 weeks  | JWT refresh, rate limiting, audit logging | 🟡 Medium  |
| **Phase 3** | 2 weeks  | RBAC system, permission dependencies      | 🟡 Medium  |
| **Phase 4** | 2 weeks  | Security middleware, migration scripts    | 🟢 Low     |

## **🧪 Testing Strategy**

### **Security Testing Checklist**

- [ ] Password policy enforcement
- [ ] Account lockout functionality
- [ ] JWT token validation
- [ ] Permission checking
- [ ] Rate limiting effectiveness
- [ ] SQL injection prevention
- [ ] XSS protection
- [ ] CSRF protection

### **Load Testing**

- [ ] Authentication endpoints under load
- [ ] Permission checking performance
- [ ] Database query optimization
- [ ] Token refresh behavior

## **🚀 Deployment Strategy**

### **Pre-deployment**

1. Database schema backup
2. User data export
3. Test environment validation
4. Security audit

### **Deployment**

1. Database migration during maintenance window
2. Application deployment with feature flags
3. Gradual rollout to user groups
4. Real-time monitoring

### **Post-deployment**

1. Security event monitoring
2. Performance metrics
3. User feedback collection
4. Incident response readiness

This roadmap transforms your basic authentication system into an enterprise-grade security platform while maintaining backward compatibility and minimal downtime.
