# app/db/schemas/organization.py

from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class OrganizationPlan(str, Enum):
    FREE = "free"
    STARTER = "starter"
    PROFESSIONAL = "professional"
    ENTERPRISE = "enterprise"


class OrganizationStatus(str, Enum):
    ACTIVE = "active"
    SUSPENDED = "suspended"
    TRIAL = "trial"
    EXPIRED = "expired"


class MemberRole(str, Enum):
    OWNER = "owner"
    ADMIN = "admin"
    MANAGER = "manager"
    MEMBER = "member"
    VIEWER = "viewer"


# Organization Schemas
class OrganizationBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    slug: str = Field(..., min_length=3, max_length=100, pattern=r'^[a-z0-9-]+$')
    description: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    website: Optional[str] = None
    
    # Address
    address_line1: Optional[str] = None
    address_line2: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    postal_code: Optional[str] = None
    country: Optional[str] = None
    
    # Business info
    tax_id: Optional[str] = None
    industry: Optional[str] = None
    company_size: Optional[str] = None
    
    # Branding
    logo_url: Optional[str] = None
    primary_color: Optional[str] = Field(None, pattern=r'^#[0-9A-Fa-f]{6}$')
    
    @validator('slug')
    def validate_slug(cls, v):
        if not v.replace('-', '').replace('_', '').isalnum():
            raise ValueError('Slug must contain only letters, numbers, hyphens, and underscores')
        return v.lower()


class OrganizationCreate(OrganizationBase):
    pass


class OrganizationUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    website: Optional[str] = None
    
    # Address
    address_line1: Optional[str] = None
    address_line2: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    postal_code: Optional[str] = None
    country: Optional[str] = None
    
    # Business info
    tax_id: Optional[str] = None
    industry: Optional[str] = None
    company_size: Optional[str] = None
    
    # Branding
    logo_url: Optional[str] = None
    primary_color: Optional[str] = Field(None, pattern=r'^#[0-9A-Fa-f]{6}$')


class OrganizationRead(OrganizationBase):
    id: str
    status: OrganizationStatus
    plan: OrganizationPlan
    
    # Usage and limits
    max_users: int
    max_projects: int
    max_storage_gb: int
    max_api_calls_per_month: int
    
    current_users: int
    current_projects: int
    current_storage_gb: int
    current_api_calls_this_month: int
    
    # Subscription info
    trial_ends_at: Optional[datetime] = None
    subscription_starts_at: Optional[datetime] = None
    subscription_ends_at: Optional[datetime] = None
    
    # Settings
    settings: Dict[str, Any] = {}
    features: Dict[str, Any] = {}
    
    # Audit
    is_active: bool
    created_at: datetime
    updated_at: datetime
    created_by: Optional[str] = None
    
    class Config:
        from_attributes = True


class OrganizationUsage(BaseModel):
    """Organization usage statistics"""
    users_percentage: float
    projects_percentage: float
    storage_percentage: float
    api_calls_percentage: float
    
    users_count: str  # "3 / 5"
    projects_count: str  # "2 / 3"
    storage_count: str  # "0.5 / 1 GB"
    api_calls_count: str  # "1,234 / 10,000"


# Membership Schemas
class OrganizationMembershipBase(BaseModel):
    role: MemberRole = MemberRole.MEMBER


class OrganizationMembershipCreate(OrganizationMembershipBase):
    user_id: str


class OrganizationMembershipUpdate(BaseModel):
    role: Optional[MemberRole] = None
    is_active: Optional[bool] = None


class OrganizationMembershipRead(OrganizationMembershipBase):
    id: str
    organization_id: str
    user_id: str
    is_active: bool
    joined_at: datetime
    invited_by: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class OrganizationMemberRead(BaseModel):
    """Member with user details"""
    id: str
    user_id: str
    role: MemberRole
    is_active: bool
    joined_at: datetime
    
    # User details
    user_email: str
    user_name: str
    user_first_name: str
    user_last_name: str
    user_is_verified: bool
    user_last_login: Optional[datetime] = None


# Invitation Schemas
class OrganizationInvitationBase(BaseModel):
    email: EmailStr
    role: MemberRole = MemberRole.MEMBER


class OrganizationInvitationCreate(OrganizationInvitationBase):
    pass


class OrganizationInvitationRead(OrganizationInvitationBase):
    id: str
    organization_id: str
    token: str
    is_accepted: bool
    is_expired: bool
    expires_at: datetime
    accepted_at: Optional[datetime] = None
    accepted_by: Optional[str] = None
    invited_by: str
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class OrganizationInvitationAccept(BaseModel):
    token: str


# Project Schemas
class ProjectBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    status: str = "active"
    settings: Dict[str, Any] = {}


class ProjectCreate(ProjectBase):
    pass


class ProjectUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    status: Optional[str] = None
    settings: Optional[Dict[str, Any]] = None


class ProjectRead(ProjectBase):
    id: str
    organization_id: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
    created_by: Optional[str] = None
    
    class Config:
        from_attributes = True


# Request/Response Models
class OrganizationListResponse(BaseModel):
    organizations: List[OrganizationRead]
    total: int
    page: int
    size: int


class OrganizationMembersResponse(BaseModel):
    members: List[OrganizationMemberRead]
    total: int


class OrganizationInvitationsResponse(BaseModel):
    invitations: List[OrganizationInvitationRead]
    total: int


class OrganizationProjectsResponse(BaseModel):
    projects: List[ProjectRead]
    total: int


class OrganizationSettings(BaseModel):
    """Organization settings update"""
    settings: Dict[str, Any]


class OrganizationFeatures(BaseModel):
    """Organization features update"""
    features: Dict[str, Any]


class BulkMemberUpdate(BaseModel):
    """Bulk update member roles"""
    member_updates: List[Dict[str, Any]]  # [{"user_id": "...", "role": "..."}]


class OrganizationInviteBulk(BaseModel):
    """Bulk invitation"""
    invitations: List[OrganizationInvitationCreate] 