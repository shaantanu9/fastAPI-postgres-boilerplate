from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.base import Base
import uuid


class User(Base):
    __tablename__ = "users"

    # Basic Identity (Updated for 2025)
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    first_name = Column(String(50), nullable=False)
    last_name = Column(String(50), nullable=False)

    # Security (Enhanced for 2025)
    hashed_password = Column(String(255), nullable=False)
    # REMOVED: password field (security fix)
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    email_verified_at = Column(DateTime, nullable=True)

    # Account Security (2025 Standards)
    failed_login_attempts = Column(Integer, default=0)
    account_locked_until = Column(DateTime, nullable=True)
    last_login = Column(DateTime, nullable=True)
    password_changed_at = Column(DateTime, server_default=func.now())
    login_ip_history = Column(Text)  # JSON array of recent IPs

    # Passkey Support (2025 Feature)
    passkey_enabled = Column(Boolean, default=False)
    passkey_counter = Column(Integer, default=0)

    # MFA Support (2025 Feature)
    mfa_enabled = Column(Boolean, default=False)
    mfa_secret = Column(String(32), nullable=True)
    backup_codes = Column(Text)  # JSON array of backup codes

    # Session Management (2025 Feature)
    max_sessions = Column(Integer, default=5)
    device_fingerprints = Column(Text)  # JSON array

    # Audit Trail
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    created_by = Column(String, nullable=True)

    # Relationships
    roles = relationship(
        "Role", 
        secondary="user_roles", 
        back_populates="users",
        primaryjoin="User.id == UserRole.user_id",
        secondaryjoin="Role.id == UserRole.role_id"
    )
    sessions = relationship("UserSession", back_populates="user")
    # security_events relationship moved to app.db.models.security.SecurityEvent
    passkeys = relationship("UserPasskey", back_populates="user")


# Enhanced RBAC Tables (2025 Standards)
class Role(Base):
    __tablename__ = "roles"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(50), unique=True, nullable=False)
    description = Column(Text)
    is_system_role = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())

    # Relationships
    users = relationship(
        "User", 
        secondary="user_roles", 
        back_populates="roles",
        primaryjoin="Role.id == UserRole.role_id",
        secondaryjoin="User.id == UserRole.user_id"
    )
    permissions = relationship("Permission", secondary="role_permissions", back_populates="roles")


class Permission(Base):
    __tablename__ = "permissions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(100), unique=True, nullable=False)
    resource = Column(String(100), nullable=False)
    action = Column(String(50), nullable=False)
    conditions = Column(Text)  # JSON for ABAC conditions
    description = Column(Text)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())

    # Relationships
    roles = relationship("Role", secondary="role_permissions", back_populates="permissions")


# Association Tables
class UserRole(Base):
    __tablename__ = "user_roles"

    user_id = Column(String, ForeignKey("users.id"), primary_key=True)
    role_id = Column(String, ForeignKey("roles.id"), primary_key=True)
    granted_at = Column(DateTime, server_default=func.now())
    granted_by = Column(String, ForeignKey("users.id"), nullable=True)
    expires_at = Column(DateTime, nullable=True)


class RolePermission(Base):
    __tablename__ = "role_permissions"

    role_id = Column(String, ForeignKey("roles.id"), primary_key=True)
    permission_id = Column(String, ForeignKey("permissions.id"), primary_key=True)


# Passkey Support (2025 Feature)
class UserPasskey(Base):
    __tablename__ = "user_passkeys"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    credential_id = Column(String(255), unique=True, nullable=False)
    public_key = Column(Text, nullable=False)
    sign_count = Column(Integer, default=0)
    name = Column(String(100), nullable=True)  # User-defined name
    created_at = Column(DateTime, server_default=func.now())
    last_used = Column(DateTime, nullable=True)

    # Relationships
    user = relationship("User", back_populates="passkeys")


# Enhanced Session Management (2025 Feature)
class UserSession(Base):
    __tablename__ = "user_sessions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    session_token = Column(String(255), unique=True, nullable=False)
    refresh_token = Column(Text, unique=True, nullable=True)
    ip_address = Column(String(45))
    user_agent = Column(Text)
    device_fingerprint = Column(Text)
    is_active = Column(Boolean, default=True)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    last_activity = Column(DateTime, server_default=func.now())

    # Relationships
    user = relationship("User", back_populates="sessions")


# SecurityEvent model moved to app.db.models.security to avoid duplication
