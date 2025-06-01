from pydantic import BaseModel, EmailStr, Field, constr, validator
from typing import Optional, List, Dict, Any
from datetime import datetime


class UserBase(BaseModel):
    username: constr(min_length=3, max_length=50)
    email: EmailStr
    first_name: constr(min_length=1, max_length=50)
    last_name: constr(min_length=1, max_length=50)


class UserCreate(UserBase):
    password: constr(min_length=12, max_length=128)  # Enhanced password requirements
    
    @validator('password')
    def validate_password_complexity(cls, v):
        """Basic client-side password validation"""
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one digit')
        if not any(c in '!@#$%^&*(),.?":{}|<>' for c in v):
            raise ValueError('Password must contain at least one special character')
        return v


class UserUpdate(BaseModel):
    first_name: Optional[constr(min_length=1, max_length=50)] = None
    last_name: Optional[constr(min_length=1, max_length=50)] = None
    email: Optional[EmailStr] = None
    password: Optional[constr(min_length=12, max_length=128)] = None
    is_active: Optional[bool] = None
    
    @validator('password')
    def validate_password_complexity(cls, v):
        """Basic client-side password validation"""
        if v is None:
            return v
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one digit')
        if not any(c in '!@#$%^&*(),.?":{}|<>' for c in v):
            raise ValueError('Password must contain at least one special character')
        return v


class UserRead(UserBase):
    id: str
    is_active: bool
    is_verified: bool
    email_verified_at: Optional[datetime] = None
    last_login: Optional[datetime] = None
    failed_login_attempts: int
    passkey_enabled: bool
    mfa_enabled: bool
    max_sessions: int
    created_at: datetime
    updated_at: datetime
    created_by: Optional[str] = None

    class Config:
        from_attributes = True


class UserInDB(UserRead):
    hashed_password: str
    account_locked_until: Optional[datetime] = None
    password_changed_at: datetime
    login_ip_history: Optional[str] = None
    mfa_secret: Optional[str] = None
    backup_codes: Optional[str] = None
    device_fingerprints: Optional[str] = None
    
    class Config:
        from_attributes = True


# Role and Permission Schemas
class RoleBase(BaseModel):
    name: constr(min_length=1, max_length=50)
    description: Optional[str] = None
    is_system_role: bool = False
    is_active: bool = True


class RoleCreate(RoleBase):
    pass


class RoleRead(RoleBase):
    id: str
    created_at: datetime
    
    class Config:
        from_attributes = True


class PermissionBase(BaseModel):
    name: constr(min_length=1, max_length=100)
    resource: constr(min_length=1, max_length=100)
    action: constr(min_length=1, max_length=50)
    conditions: Optional[str] = None  # JSON string for ABAC conditions
    description: Optional[str] = None
    is_active: bool = True


class PermissionCreate(PermissionBase):
    pass


class PermissionRead(PermissionBase):
    id: str
    created_at: datetime
    
    class Config:
        from_attributes = True


# Session Schemas
class UserSessionRead(BaseModel):
    id: str
    session_token: str
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    device_fingerprint: Optional[str] = None
    is_active: bool
    expires_at: datetime
    created_at: datetime
    last_activity: datetime
    
    class Config:
        from_attributes = True


# Security Event Schemas
class SecurityEventRead(BaseModel):
    id: str
    event_type: str
    event_category: str
    event_data: Optional[str] = None  # JSON string
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    risk_score: int
    status: str
    created_at: datetime
    
    class Config:
        from_attributes = True


# Authentication Schemas
class LoginRequest(BaseModel):
    username_or_email: str
    password: str
    mfa_token: Optional[str] = None


class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserRead
    requires_mfa: bool = False


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class MFASetupResponse(BaseModel):
    secret: str
    qr_code: str  # Base64 encoded QR code image
    backup_codes: List[str]


class MFAVerifyRequest(BaseModel):
    token: str


class PasswordStrengthResponse(BaseModel):
    valid: bool
    errors: List[str]
    strength: str
    score: int


# Enhanced User with Roles
class UserWithRoles(UserRead):
    roles: List[RoleRead] = []
    permissions: List[PermissionRead] = []
    
    class Config:
        from_attributes = True
