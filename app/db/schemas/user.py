from datetime import datetime

from pydantic import BaseModel, EmailStr, constr, field_validator


class UserBase(BaseModel):
    username: constr(min_length=3, max_length=50)
    email: EmailStr
    first_name: constr(min_length=1, max_length=50)
    last_name: constr(min_length=1, max_length=50)


class UserCreate(UserBase):
    password: constr(min_length=12, max_length=128)  # Enhanced password requirements

    @field_validator("password")
    @classmethod
    def validate_password_complexity(cls, v):
        """Basic client-side password validation."""
        if not any(c.isupper() for c in v):
            msg = "Password must contain at least one uppercase letter"
            raise ValueError(msg)
        if not any(c.islower() for c in v):
            msg = "Password must contain at least one lowercase letter"
            raise ValueError(msg)
        if not any(c.isdigit() for c in v):
            msg = "Password must contain at least one digit"
            raise ValueError(msg)
        if not any(c in '!@#$%^&*(),.?":{}|<>' for c in v):
            msg = "Password must contain at least one special character"
            raise ValueError(msg)
        return v


class UserUpdate(BaseModel):
    first_name: constr(min_length=1, max_length=50) | None = None
    last_name: constr(min_length=1, max_length=50) | None = None
    email: EmailStr | None = None
    password: constr(min_length=12, max_length=128) | None = None
    is_active: bool | None = None

    @field_validator("password")
    @classmethod
    def validate_password_complexity(cls, v):
        """Basic client-side password validation."""
        if v is None:
            return v
        if not any(c.isupper() for c in v):
            msg = "Password must contain at least one uppercase letter"
            raise ValueError(msg)
        if not any(c.islower() for c in v):
            msg = "Password must contain at least one lowercase letter"
            raise ValueError(msg)
        if not any(c.isdigit() for c in v):
            msg = "Password must contain at least one digit"
            raise ValueError(msg)
        if not any(c in '!@#$%^&*(),.?":{}|<>' for c in v):
            msg = "Password must contain at least one special character"
            raise ValueError(msg)
        return v


class UserRead(UserBase):
    id: str
    is_active: bool
    is_verified: bool
    email_verified_at: datetime | None = None
    last_login: datetime | None = None
    failed_login_attempts: int
    passkey_enabled: bool
    mfa_enabled: bool
    max_sessions: int
    created_at: datetime
    updated_at: datetime
    created_by: str | None = None

    class Config:
        from_attributes = True


class UserInDB(UserRead):
    hashed_password: str
    account_locked_until: datetime | None = None
    password_changed_at: datetime
    login_ip_history: str | None = None
    mfa_secret: str | None = None
    backup_codes: str | None = None
    device_fingerprints: str | None = None

    class Config:
        from_attributes = True


# Role and Permission Schemas
class RoleBase(BaseModel):
    name: constr(min_length=1, max_length=50)
    description: str | None = None
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
    conditions: str | None = None  # JSON string for ABAC conditions
    description: str | None = None
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
    ip_address: str | None = None
    user_agent: str | None = None
    device_fingerprint: str | None = None
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
    event_data: str | None = None  # JSON string
    ip_address: str | None = None
    user_agent: str | None = None
    risk_score: int
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


# Authentication Schemas
class LoginRequest(BaseModel):
    username_or_email: str
    password: str
    mfa_token: str | None = None


class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserRead
    requires_mfa: bool = False


class RefreshTokenRequest(BaseModel):
    refresh_token: str


# Email verification schemas
class EmailVerificationRequest(BaseModel):
    email: str


# Password reset schemas
class PasswordResetRequest(BaseModel):
    email: str


class PasswordResetConfirm(BaseModel):
    user_id: str
    token: str
    new_password: str


class BackupCodePasswordReset(BaseModel):
    """Schema for password reset using backup code."""

    username_or_email: str
    backup_code: str
    new_password: constr(min_length=12, max_length=128)

    @field_validator("new_password")
    @classmethod
    def validate_password_complexity(cls, v):
        """Basic client-side password validation."""
        if v is None:
            return v
        if not any(c.isupper() for c in v):
            msg = "Password must contain at least one uppercase letter"
            raise ValueError(msg)
        if not any(c.islower() for c in v):
            msg = "Password must contain at least one lowercase letter"
            raise ValueError(msg)
        if not any(c.isdigit() for c in v):
            msg = "Password must contain at least one digit"
            raise ValueError(msg)
        if not any(c in '!@#$%^&*(),.?":{}|<>' for c in v):
            msg = "Password must contain at least one special character"
            raise ValueError(msg)
        return v


# User invitation schemas
class UserInvitationRequest(BaseModel):
    email: str
    organization_name: str | None = None
    role: str | None = "user"


# Profile management schemas
class UserProfileUpdate(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    username: str | None = None
    # Note: email changes require verification


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


class MFASetupResponse(BaseModel):
    secret: str
    qr_code: str  # Base64 encoded QR code image
    backup_codes: list[str]


class MFAVerifyRequest(BaseModel):
    token: str


class PasswordStrengthResponse(BaseModel):
    valid: bool
    errors: list[str]
    strength: str
    score: int


# Enhanced User with Roles
class UserWithRoles(UserRead):
    roles: list[RoleRead] = []
    permissions: list[PermissionRead] = []

    class Config:
        from_attributes = True
