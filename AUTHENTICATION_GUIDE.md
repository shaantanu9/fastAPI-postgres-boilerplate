# 🔐 FastAPI Enterprise Authentication System Guide

## Table of Contents

1. [System Overview](#system-overview)
2. [User Registration Flow](#user-registration-flow)
3. [User Login Flow](#user-login-flow)
4. [JWT Token System](#jwt-token-system)
5. [Protected Endpoints](#protected-endpoints)
6. [Session Management](#session-management)
7. [Role-Based Access Control (RBAC)](#role-based-access-control-rbac)
8. [Permission System](#permission-system)
9. [Security Features](#security-features)
10. [API Examples](#api-examples)
11. [Implementation Guide](#implementation-guide)

---

## System Overview

Our FastAPI authentication system provides enterprise-grade security with:

- **JWT Tokens** with 2025 security standards
- **Multi-session management** with device tracking
- **Role-based access control (RBAC)**
- **Permission-based authorization**
- **Session tracking and management**
- **Security event logging**
- **Password policies and validation**

### Architecture Diagram

```mermaid
graph TD
    A[Client] -->|1. Register/Login| B[Auth API]
    B -->|2. Validate Credentials| C[User Service]
    C -->|3. Create Session| D[Session Manager]
    D -->|4. Generate JWT| E[JWT Service]
    E -->|5. Return Tokens| B
    B -->|6. Access Token + Refresh Token| A

    A -->|7. API Requests + Bearer Token| F[Protected Endpoints]
    F -->|8. Verify Token| E
    E -->|9. Extract User Info| G[Authorization]
    G -->|10. Check Roles/Permissions| H[RBAC Service]
    H -->|11. Allow/Deny| F
    F -->|12. Response| A
```

---

## User Registration Flow

### Step 1: Register New User

**Endpoint:** `POST /api/v1/auth/register`

**Request Body:**

```json
{
  "username": "john_doe",
  "email": "john@example.com",
  "first_name": "John",
  "last_name": "Doe",
  "password": "MyStr0ng!P@ssw0rd2025"
}
```

**Response:**

```json
{
  "id": "abc123-def456-ghi789",
  "username": "john_doe",
  "email": "john@example.com",
  "first_name": "John",
  "last_name": "Doe",
  "is_active": true,
  "is_verified": false,
  "created_at": "2025-06-01T19:00:00Z"
}
```

**What Happens:**

1. Password is validated against strength policies
2. User data is validated (unique username/email)
3. Password is hashed using bcrypt
4. User record is created in database
5. Default "user" role is assigned
6. Security event is logged

### Step 2: Email Verification (Future Enhancement)

```json
{
  "message": "Verification email sent to john@example.com",
  "verification_required": true
}
```

---

## User Login Flow

### Step 1: User Login

**Endpoint:** `POST /api/v1/auth/login`

**Request Body:**

```json
{
  "username_or_email": "john_doe",
  "password": "MyStr0ng!P@ssw0rd2025"
}
```

**Successful Response:**

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 900,
  "user": {
    "id": "abc123-def456-ghi789",
    "username": "john_doe",
    "email": "john@example.com",
    "first_name": "John",
    "last_name": "Doe",
    "is_active": true,
    "is_verified": false,
    "mfa_enabled": false,
    "last_login": "2025-06-01T19:00:00Z"
  },
  "requires_mfa": false
}
```

**What Happens:**

1. User credentials are validated
2. Account status is checked (active, not locked)
3. Login attempt is logged
4. New session is created with device fingerprinting
5. JWT access token (15 min) and refresh token (30 days) are generated
6. Session is stored with tokens
7. Security event is logged

### Step 2: Failed Login Handling

**Failed Response:**

```json
{
  "detail": "Invalid credentials"
}
```

**Account Lockout (after 5 failed attempts):**

```json
{
  "detail": "Account temporarily locked due to too many failed attempts",
  "locked_until": "2025-06-01T20:00:00Z"
}
```

---

## JWT Token System

### Access Token Structure

Our JWT tokens follow 2025 security standards:

```json
{
  "sub": "john_doe",
  "user_id": "abc123-def456-ghi789",
  "session_id": "session-uuid-here",
  "exp": 1748785928,
  "iat": 1748785028,
  "nbf": 1748785028,
  "type": "access",
  "jti": "unique-token-id",
  "aud": "api",
  "iss": "fastapi-app",
  "scope": ["read", "write"]
}
```

**Token Fields Explained:**

- `sub`: Subject (username)
- `user_id`: Unique user identifier
- `session_id`: Session identifier for tracking
- `exp`: Expiration time (15 minutes)
- `iat`: Issued at time
- `nbf`: Not before time
- `type`: Token type (access/refresh)
- `jti`: JWT ID for blacklisting
- `aud`: Audience validation
- `iss`: Issuer validation
- `scope`: User permissions/scopes

### Refresh Token Structure

```json
{
  "sub": "abc123-def456-ghi789",
  "session_id": "session-uuid-here",
  "exp": 1751377020,
  "iat": 1748785020,
  "type": "refresh",
  "jti": "unique-refresh-token-id"
}
```

### Token Refresh Flow

**Endpoint:** `POST /api/v1/auth/refresh`

**Request:**

```json
{
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**Response:**

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 900
}
```

---

## Protected Endpoints

### Making Authenticated Requests

**Header Format:**

```http
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**Example Request:**

```bash
curl -X GET "http://localhost:8000/api/v1/auth/me" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### Current User Information

**Endpoint:** `GET /api/v1/auth/me`

**Response:**

```json
{
  "id": "abc123-def456-ghi789",
  "username": "john_doe",
  "email": "john@example.com",
  "first_name": "John",
  "last_name": "Doe",
  "is_active": true,
  "is_verified": false,
  "mfa_enabled": false,
  "last_login": "2025-06-01T19:00:00Z",
  "created_at": "2025-06-01T18:00:00Z"
}
```

### Authentication Middleware

```python
from fastapi import Depends, HTTPException, Request
from app.core.jwt import jwt_service
from app.services.user_service import enhanced_user_service

async def get_current_user(request: Request, db: AsyncSession = Depends(get_db)):
    """Extract and validate user from JWT token"""

    # Extract token from Authorization header
    auth_header = request.headers.get("authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing authorization header")

    token = auth_header.split(" ")[1]

    # Verify JWT token
    payload = jwt_service.verify_token(token)
    user_id = payload.get("user_id")

    # Get user from database
    user = await enhanced_user_service.get_by_id(db, user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="Invalid user")

    return user
```

---

## Session Management

### View Active Sessions

**Endpoint:** `GET /api/v1/auth/me/sessions`

**Response:**

```json
[
  {
    "id": "session-uuid-1",
    "session_token": "session-token-hash",
    "ip_address": "192.168.1.100",
    "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "device_fingerprint": "device-hash",
    "is_active": true,
    "expires_at": "2025-07-01T19:00:00Z",
    "created_at": "2025-06-01T19:00:00Z",
    "last_activity": "2025-06-01T19:30:00Z"
  }
]
```

### Revoke Specific Session

**Endpoint:** `DELETE /api/v1/auth/me/sessions/{session_id}`

**Response:**

```json
{
  "message": "Session revoked successfully"
}
```

### Logout (Current Session)

**Endpoint:** `POST /api/v1/auth/logout`

**What Happens:**

1. Current session is deactivated
2. JWT token is blacklisted
3. Security event is logged

---

## Role-Based Access Control (RBAC)

### Database Schema

```sql
-- Roles table
CREATE TABLE roles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(50) UNIQUE NOT NULL,
    description TEXT,
    is_system_role BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- User-Role association
CREATE TABLE user_roles (
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    role_id UUID REFERENCES roles(id) ON DELETE CASCADE,
    granted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    granted_by UUID REFERENCES users(id),
    expires_at TIMESTAMP,
    PRIMARY KEY (user_id, role_id)
);
```

### Default Roles

```sql
INSERT INTO roles (name, description, is_system_role) VALUES
('admin', 'System Administrator', TRUE),
('user', 'Standard User', TRUE),
('moderator', 'Content Moderator', TRUE),
('viewer', 'Read-only Access', TRUE);
```

### Role Management API

#### Assign Role to User

**Endpoint:** `POST /api/v1/admin/users/{user_id}/roles`

**Request:**

```json
{
  "role_name": "moderator",
  "expires_at": "2025-12-31T23:59:59Z"
}
```

**Implementation:**

```python
@router.post("/admin/users/{user_id}/roles")
async def assign_role(
    user_id: str,
    role_data: RoleAssignment,
    current_user: UserRead = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db)
):
    await enhanced_user_service.assign_role(
        db, user_id, role_data.role_name, current_user.id
    )
    return {"message": "Role assigned successfully"}
```

#### Remove Role from User

**Endpoint:** `DELETE /api/v1/admin/users/{user_id}/roles/{role_name}`

### Role-Based Endpoint Protection

```python
from functools import wraps
from fastapi import HTTPException, status

def require_role(required_role: str):
    """Decorator to require specific role"""
    def role_checker(current_user: UserRead = Depends(get_current_user)):
        user_roles = [role.name for role in current_user.roles]
        if required_role not in user_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Required role: {required_role}"
            )
        return current_user
    return role_checker

# Usage in endpoints
@router.get("/admin/users")
async def list_users(
    current_user: UserRead = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db)
):
    """Admin-only endpoint"""
    return await enhanced_user_service.list_users(db)
```

---

## Permission System

### Database Schema

```sql
-- Permissions table
CREATE TABLE permissions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) UNIQUE NOT NULL,
    resource VARCHAR(100) NOT NULL,
    action VARCHAR(50) NOT NULL,
    conditions JSONB,
    description TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Role-Permission association
CREATE TABLE role_permissions (
    role_id UUID REFERENCES roles(id) ON DELETE CASCADE,
    permission_id UUID REFERENCES permissions(id) ON DELETE CASCADE,
    PRIMARY KEY (role_id, permission_id)
);
```

### Default Permissions

```sql
INSERT INTO permissions (name, resource, action, description) VALUES
-- User management
('users.create', 'users', 'create', 'Create new users'),
('users.read', 'users', 'read', 'View user information'),
('users.update', 'users', 'update', 'Update user information'),
('users.delete', 'users', 'delete', 'Delete users'),

-- Product management
('products.create', 'products', 'create', 'Create new products'),
('products.read', 'products', 'read', 'View products'),
('products.update', 'products', 'update', 'Update products'),
('products.delete', 'products', 'delete', 'Delete products'),

-- System administration
('system.admin', 'system', 'admin', 'System administration'),
('roles.manage', 'roles', 'manage', 'Manage roles and permissions');
```

### Permission-Based Authorization

```python
def require_permission(resource: str, action: str):
    """Decorator to require specific permission"""
    def permission_checker(
        current_user: UserRead = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
    ):
        # Check if user has required permission
        user_permissions = enhanced_user_service.get_user_permissions(db, current_user.id)
        required_permission = f"{resource}.{action}"

        if not any(perm.name == required_permission for perm in user_permissions):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Required permission: {required_permission}"
            )
        return current_user
    return permission_checker

# Usage in endpoints
@router.post("/products")
async def create_product(
    product_data: ProductCreate,
    current_user: UserRead = Depends(require_permission("products", "create")),
    db: AsyncSession = Depends(get_db)
):
    """Create product with permission check"""
    return await product_service.create(db, product_data, current_user.id)
```

### Advanced Permission System

```python
class PermissionService:
    @staticmethod
    async def has_permission(
        db: AsyncSession,
        user: UserRead,
        resource: str,
        action: str,
        context: dict = None
    ) -> bool:
        """Check if user has permission with context"""

        # Get user permissions through roles
        permissions = await enhanced_user_service.get_user_permissions(db, user.id)

        for permission in permissions:
            if permission.resource == resource and permission.action == action:
                # Check conditions if any
                if permission.conditions:
                    return await evaluate_conditions(permission.conditions, context)
                return True

        return False

    @staticmethod
    async def evaluate_conditions(conditions: dict, context: dict) -> bool:
        """Evaluate permission conditions"""
        # Example: Only allow access to own resources
        if conditions.get("owner_only"):
            return context.get("resource_owner_id") == context.get("user_id")

        # Example: Time-based access
        if conditions.get("business_hours"):
            current_hour = datetime.now().hour
            return 9 <= current_hour <= 17

        return True
```

---

## Security Features

### Password Policies

**Endpoint:** `POST /api/v1/auth/password/check`

**Request:**

```bash
curl -X POST "http://localhost:8000/api/v1/auth/password/check?password=MyPassword123"
```

**Response:**

```json
{
  "score": 8,
  "strength": "strong",
  "suggestions": ["Add special characters for better security"],
  "meets_policy": true
}
```

### Security Events

**Endpoint:** `GET /api/v1/auth/me/security-events`

**Response:**

```json
[
  {
    "id": "event-uuid",
    "event_type": "successful_login",
    "event_category": "authentication",
    "event_data": {
      "ip": "192.168.1.100",
      "user_agent": "Mozilla/5.0..."
    },
    "ip_address": "192.168.1.100",
    "risk_score": 0,
    "status": "success",
    "created_at": "2025-06-01T19:00:00Z"
  }
]
```

### Account Lockout

```python
class SecurityService:
    @staticmethod
    async def handle_failed_login(db: AsyncSession, user: User, ip_address: str):
        """Handle failed login attempt"""
        user.failed_login_attempts += 1

        if user.failed_login_attempts >= 5:
            # Lock account for 30 minutes
            user.account_locked_until = datetime.utcnow() + timedelta(minutes=30)

        # Log security event
        await log_security_event(
            db, user, "failed_login", "authentication",
            {"ip": ip_address, "attempts": user.failed_login_attempts}
        )

        await db.commit()
```

---

## API Examples

### Complete Authentication Flow Example

```python
import requests
import json

BASE_URL = "http://localhost:8000"

# 1. Register new user
def register_user():
    data = {
        "username": "john_doe",
        "email": "john@example.com",
        "first_name": "John",
        "last_name": "Doe",
        "password": "MyStr0ng!P@ssw0rd2025"
    }
    response = requests.post(f"{BASE_URL}/api/v1/auth/register", json=data)
    return response.json()

# 2. Login user
def login_user():
    data = {
        "username_or_email": "john_doe",
        "password": "MyStr0ng!P@ssw0rd2025"
    }
    response = requests.post(f"{BASE_URL}/api/v1/auth/login", json=data)
    return response.json()

# 3. Access protected endpoint
def get_user_profile(access_token):
    headers = {"Authorization": f"Bearer {access_token}"}
    response = requests.get(f"{BASE_URL}/api/v1/auth/me", headers=headers)
    return response.json()

# 4. Refresh token
def refresh_token(refresh_token):
    data = {"refresh_token": refresh_token}
    response = requests.post(f"{BASE_URL}/api/v1/auth/refresh", json=data)
    return response.json()

# 5. Create product (with permission check)
def create_product(access_token, product_data):
    headers = {"Authorization": f"Bearer {access_token}"}
    response = requests.post(f"{BASE_URL}/api/v1/products",
                           json=product_data, headers=headers)
    return response.json()

# Example usage
if __name__ == "__main__":
    # Register and login
    user = register_user()
    login_result = login_user()

    access_token = login_result["access_token"]
    refresh_token = login_result["refresh_token"]

    # Get user profile
    profile = get_user_profile(access_token)
    print(f"User: {profile['username']}")

    # Create product (requires permission)
    product_data = {
        "name": "Test Product",
        "price": 99.99,
        "description": "A test product"
    }
    product = create_product(access_token, product_data)
    print(f"Product created: {product['id']}")
```

### Frontend Integration (JavaScript)

```javascript
class AuthService {
  constructor(baseURL) {
    this.baseURL = baseURL;
    this.accessToken = localStorage.getItem("access_token");
    this.refreshToken = localStorage.getItem("refresh_token");
  }

  async login(username, password) {
    const response = await fetch(`${this.baseURL}/api/v1/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        username_or_email: username,
        password: password,
      }),
    });

    if (response.ok) {
      const data = await response.json();
      this.accessToken = data.access_token;
      this.refreshToken = data.refresh_token;

      localStorage.setItem("access_token", this.accessToken);
      localStorage.setItem("refresh_token", this.refreshToken);

      return data;
    }

    throw new Error("Login failed");
  }

  async makeAuthenticatedRequest(url, options = {}) {
    const headers = {
      Authorization: `Bearer ${this.accessToken}`,
      "Content-Type": "application/json",
      ...options.headers,
    };

    let response = await fetch(url, { ...options, headers });

    // If token expired, try to refresh
    if (response.status === 401) {
      await this.refreshAccessToken();
      headers["Authorization"] = `Bearer ${this.accessToken}`;
      response = await fetch(url, { ...options, headers });
    }

    return response;
  }

  async refreshAccessToken() {
    const response = await fetch(`${this.baseURL}/api/v1/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: this.refreshToken }),
    });

    if (response.ok) {
      const data = await response.json();
      this.accessToken = data.access_token;
      localStorage.setItem("access_token", this.accessToken);
    } else {
      this.logout();
      throw new Error("Session expired");
    }
  }

  logout() {
    this.accessToken = null;
    this.refreshToken = null;
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
  }
}

// Usage
const auth = new AuthService("http://localhost:8000");

// Login
await auth.login("john_doe", "MyStr0ng!P@ssw0rd2025");

// Make authenticated requests
const response = await auth.makeAuthenticatedRequest("/api/v1/auth/me");
const userProfile = await response.json();
```

---

## Implementation Guide

### Step 1: Set Up RBAC Tables

```sql
-- Run these migrations to set up RBAC
-- Create roles table
CREATE TABLE roles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(50) UNIQUE NOT NULL,
    description TEXT,
    is_system_role BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create permissions table
CREATE TABLE permissions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) UNIQUE NOT NULL,
    resource VARCHAR(100) NOT NULL,
    action VARCHAR(50) NOT NULL,
    conditions JSONB,
    description TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create user_roles association table
CREATE TABLE user_roles (
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    role_id UUID REFERENCES roles(id) ON DELETE CASCADE,
    granted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    granted_by UUID REFERENCES users(id),
    expires_at TIMESTAMP,
    PRIMARY KEY (user_id, role_id)
);

-- Create role_permissions association table
CREATE TABLE role_permissions (
    role_id UUID REFERENCES roles(id) ON DELETE CASCADE,
    permission_id UUID REFERENCES permissions(id) ON DELETE CASCADE,
    PRIMARY KEY (role_id, permission_id)
);
```

### Step 2: Create Default Data

```python
# app/scripts/create_default_rbac.py
async def create_default_roles_and_permissions():
    """Create default roles and permissions"""

    # Create default roles
    roles = [
        {"name": "admin", "description": "System Administrator", "is_system_role": True},
        {"name": "user", "description": "Standard User", "is_system_role": True},
        {"name": "moderator", "description": "Content Moderator", "is_system_role": True},
    ]

    # Create default permissions
    permissions = [
        {"name": "users.create", "resource": "users", "action": "create"},
        {"name": "users.read", "resource": "users", "action": "read"},
        {"name": "users.update", "resource": "users", "action": "update"},
        {"name": "users.delete", "resource": "users", "action": "delete"},
        {"name": "products.create", "resource": "products", "action": "create"},
        {"name": "products.read", "resource": "products", "action": "read"},
        {"name": "products.update", "resource": "products", "action": "update"},
        {"name": "products.delete", "resource": "products", "action": "delete"},
    ]

    # Assign permissions to roles
    admin_permissions = [p["name"] for p in permissions]  # Admin gets all
    user_permissions = ["users.read", "products.read"]    # User gets read-only

    # Implementation here...
```

### Step 3: Update User Service

```python
# app/services/user_service.py
class EnhancedUserService:
    async def get_user_permissions(self, db: AsyncSession, user_id: str) -> List[Permission]:
        """Get all permissions for a user through their roles"""
        query = select(Permission).join(RolePermission).join(Role).join(UserRole).where(
            UserRole.user_id == user_id,
            Role.is_active == True,
            Permission.is_active == True
        ).distinct()

        result = await db.execute(query)
        return result.scalars().all()

    async def assign_role(self, db: AsyncSession, user_id: str, role_name: str, granted_by: str = None):
        """Assign a role to a user"""
        # Get role
        role = await self.get_role_by_name(db, role_name)
        if not role:
            raise HTTPException(status_code=404, detail="Role not found")

        # Check if user already has this role
        existing = await self.get_user_role(db, user_id, role.id)
        if existing:
            return  # User already has this role

        # Assign role
        user_role = UserRole(
            user_id=user_id,
            role_id=role.id,
            granted_by=granted_by
        )
        db.add(user_role)
        await db.commit()
```

### Step 4: Create Authorization Decorators

```python
# app/core/authorization.py
from functools import wraps
from fastapi import Depends, HTTPException, status
from app.services.user_service import enhanced_user_service

def require_role(required_role: str):
    """Decorator to require specific role"""
    async def role_checker(
        current_user: UserRead = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
    ):
        user_roles = await enhanced_user_service.get_user_roles(db, current_user.id)
        role_names = [role.name for role in user_roles]

        if required_role not in role_names:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Required role: {required_role}"
            )
        return current_user
    return role_checker

def require_permission(resource: str, action: str):
    """Decorator to require specific permission"""
    async def permission_checker(
        current_user: UserRead = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
    ):
        permissions = await enhanced_user_service.get_user_permissions(db, current_user.id)
        required_permission = f"{resource}.{action}"

        if not any(perm.name == required_permission for perm in permissions):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Required permission: {required_permission}"
            )
        return current_user
    return permission_checker
```

### Step 5: Apply to Endpoints

```python
# app/api/v1/endpoints/users.py
@router.get("/", response_model=List[UserRead])
async def list_users(
    current_user: UserRead = Depends(require_permission("users", "read")),
    db: AsyncSession = Depends(get_db)
):
    """List users - requires users.read permission"""
    return await enhanced_user_service.list_users(db)

@router.post("/", response_model=UserRead)
async def create_user(
    user_data: UserCreate,
    current_user: UserRead = Depends(require_permission("users", "create")),
    db: AsyncSession = Depends(get_db)
):
    """Create user - requires users.create permission"""
    return await enhanced_user_service.create_user(db, user_data)

@router.delete("/{user_id}")
async def delete_user(
    user_id: str,
    current_user: UserRead = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db)
):
    """Delete user - requires admin role"""
    return await enhanced_user_service.delete_user(db, user_id)
```

---

## Testing Your Implementation

### Test Script

```python
# test_rbac.py
import asyncio
import pytest
from app.services.user_service import enhanced_user_service
from app.core.authorization import require_permission

async def test_rbac_flow():
    """Test complete RBAC flow"""

    # 1. Create user with default role
    user_data = UserCreate(
        username="testuser",
        email="test@example.com",
        password="TestPassword123!",
        first_name="Test",
        last_name="User"
    )
    user = await enhanced_user_service.create_user(db, user_data)

    # 2. Check default permissions
    permissions = await enhanced_user_service.get_user_permissions(db, user.id)
    assert any(p.name == "products.read" for p in permissions)

    # 3. Assign admin role
    await enhanced_user_service.assign_role(db, user.id, "admin")

    # 4. Check new permissions
    permissions = await enhanced_user_service.get_user_permissions(db, user.id)
    assert any(p.name == "users.delete" for p in permissions)

    print("✅ RBAC test passed!")

if __name__ == "__main__":
    asyncio.run(test_rbac_flow())
```

---

## Summary

This authentication system provides:

1. **Secure User Registration** with password policies
2. **JWT-based Authentication** with 2025 security standards
3. **Multi-session Management** with device tracking
4. **Role-based Access Control** with flexible permissions
5. **Comprehensive Security Features** including audit logging
6. **Production-ready Implementation** with proper error handling

The system is designed to be scalable, secure, and maintainable for enterprise applications. You can extend it further with features like:

- Multi-factor authentication (MFA)
- OAuth2 integration (Google, GitHub)
- Passkey/WebAuthn support
- Advanced permission conditions
- Real-time security monitoring

For any questions or additional features, feel free to ask!
