# app/db/models/organization.py

from sqlalchemy import Column, String, Text, Boolean, DateTime, Integer, ForeignKey, Enum as SQLEnum, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.db.base import Base
from datetime import datetime
import uuid
import enum


class OrganizationPlan(str, enum.Enum):
    FREE = "free"
    STARTER = "starter"
    PROFESSIONAL = "professional"
    ENTERPRISE = "enterprise"


class OrganizationStatus(str, enum.Enum):
    ACTIVE = "active"
    SUSPENDED = "suspended"
    TRIAL = "trial"
    EXPIRED = "expired"


class MemberRole(str, enum.Enum):
    OWNER = "owner"
    ADMIN = "admin"
    MANAGER = "manager"
    MEMBER = "member"
    VIEWER = "viewer"


class Organization(Base):
    """Organization model for multi-tenancy"""
    __tablename__ = "organizations"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False, index=True)
    slug = Column(String(100), unique=True, nullable=False, index=True)
    description = Column(Text)
    
    # Organization status and plan
    status = Column(SQLEnum(OrganizationStatus), default=OrganizationStatus.TRIAL, nullable=False)
    plan = Column(SQLEnum(OrganizationPlan), default=OrganizationPlan.FREE, nullable=False)
    
    # Contact and billing information
    email = Column(String(255))
    phone = Column(String(50))
    website = Column(String(255))
    
    # Address information
    address_line1 = Column(String(255))
    address_line2 = Column(String(255))
    city = Column(String(100))
    state = Column(String(100))
    postal_code = Column(String(20))
    country = Column(String(100))
    
    # Business information
    tax_id = Column(String(100))  # Tax ID, VAT number, etc.
    industry = Column(String(100))
    company_size = Column(String(50))  # "1-10", "11-50", "51-200", etc.
    
    # Feature limits and usage
    max_users = Column(Integer, default=5)
    max_projects = Column(Integer, default=3)
    max_storage_gb = Column(Integer, default=1)
    max_api_calls_per_month = Column(Integer, default=10000)
    
    # Current usage tracking
    current_users = Column(Integer, default=0)
    current_projects = Column(Integer, default=0)
    current_storage_gb = Column(Integer, default=0)
    current_api_calls_this_month = Column(Integer, default=0)
    
    # Trial and subscription information
    trial_ends_at = Column(DateTime)
    subscription_starts_at = Column(DateTime)
    subscription_ends_at = Column(DateTime)
    
    # Settings and configuration
    settings = Column(JSON, default=dict)  # Organization-specific settings
    features = Column(JSON, default=dict)  # Enabled features
    
    # Branding
    logo_url = Column(String(255))
    primary_color = Column(String(7))  # Hex color code
    
    # Audit fields
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    created_by = Column(String, ForeignKey("users.id"))
    
    # Relationships
    memberships = relationship("OrganizationMembership", back_populates="organization", cascade="all, delete-orphan")
    projects = relationship("Project", back_populates="organization", cascade="all, delete-orphan")
    invitations = relationship("OrganizationInvitation", back_populates="organization", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Organization(id={self.id}, name={self.name}, plan={self.plan})>"
    
    @property
    def owner(self):
        """Get the organization owner"""
        owner_membership = next(
            (m for m in self.memberships if m.role == MemberRole.OWNER and m.is_active), 
            None
        )
        return owner_membership.user if owner_membership else None
    
    def is_feature_enabled(self, feature_name: str) -> bool:
        """Check if a feature is enabled for this organization"""
        return self.features.get(feature_name, False)
    
    def get_usage_percentage(self, resource: str) -> float:
        """Get usage percentage for a resource"""
        usage_map = {
            'users': (self.current_users, self.max_users),
            'projects': (self.current_projects, self.max_projects),
            'storage': (self.current_storage_gb, self.max_storage_gb),
            'api_calls': (self.current_api_calls_this_month, self.max_api_calls_per_month)
        }
        
        current, maximum = usage_map.get(resource, (0, 1))
        if maximum == 0:
            return 0.0
        return (current / maximum) * 100
    
    def can_add_user(self) -> bool:
        """Check if organization can add another user"""
        return self.current_users < self.max_users
    
    def can_create_project(self) -> bool:
        """Check if organization can create another project"""
        return self.current_projects < self.max_projects


class OrganizationMembership(Base):
    """Membership of users in organizations"""
    __tablename__ = "organization_memberships"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Foreign keys
    organization_id = Column(String, ForeignKey("organizations.id"), nullable=False)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    
    # Membership details
    role = Column(SQLEnum(MemberRole), nullable=False, default=MemberRole.MEMBER)
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Join information
    joined_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    invited_by = Column(String, ForeignKey("users.id"))
    
    # Audit fields
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    organization = relationship("Organization", back_populates="memberships")
    user = relationship("User", foreign_keys=[user_id])
    inviter = relationship("User", foreign_keys=[invited_by])
    
    def __repr__(self):
        return f"<OrganizationMembership(org={self.organization_id}, user={self.user_id}, role={self.role})>"


class OrganizationInvitation(Base):
    """Invitations to join organizations"""
    __tablename__ = "organization_invitations"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Foreign keys
    organization_id = Column(String, ForeignKey("organizations.id"), nullable=False)
    invited_by = Column(String, ForeignKey("users.id"), nullable=False)
    
    # Invitation details
    email = Column(String(255), nullable=False, index=True)
    role = Column(SQLEnum(MemberRole), nullable=False, default=MemberRole.MEMBER)
    token = Column(String(255), unique=True, nullable=False, index=True)
    
    # Status and expiration
    is_accepted = Column(Boolean, default=False, nullable=False)
    is_expired = Column(Boolean, default=False, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    accepted_at = Column(DateTime)
    accepted_by = Column(String, ForeignKey("users.id"))
    
    # Audit fields
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    organization = relationship("Organization", back_populates="invitations")
    inviter = relationship("User", foreign_keys=[invited_by])
    accepter = relationship("User", foreign_keys=[accepted_by])
    
    def __repr__(self):
        return f"<OrganizationInvitation(org={self.organization_id}, email={self.email}, role={self.role})>"
    
    @property
    def is_valid(self) -> bool:
        """Check if invitation is still valid"""
        return not self.is_accepted and not self.is_expired and datetime.utcnow() < self.expires_at


class Project(Base):
    """Projects within organizations (example of tenant-scoped resource)"""
    __tablename__ = "projects"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Tenant isolation
    organization_id = Column(String, ForeignKey("organizations.id"), nullable=False, index=True)
    
    # Project details
    name = Column(String(255), nullable=False)
    description = Column(Text)
    status = Column(String(50), default="active")
    
    # Project settings
    settings = Column(JSON, default=dict)
    
    # Audit fields
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    created_by = Column(String, ForeignKey("users.id"))
    
    # Relationships
    organization = relationship("Organization", back_populates="projects")
    creator = relationship("User")
    
    def __repr__(self):
        return f"<Project(id={self.id}, name={self.name}, org={self.organization_id})>" 