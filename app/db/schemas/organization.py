# app/db/schemas/organization.py

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, EmailStr, Field, field_validator


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
    slug: str = Field(..., min_length=3, max_length=100, pattern=r"^[a-z0-9-]+$")
    description: str | None = None
    email: EmailStr | None = None
    phone: str | None = None
    website: str | None = None

    # Address
    address_line1: str | None = None
    address_line2: str | None = None
    city: str | None = None
    state: str | None = None
    postal_code: str | None = None
    country: str | None = None

    # Business info
    tax_id: str | None = None
    industry: str | None = None
    company_size: str | None = None

    # Branding
    logo_url: str | None = None
    primary_color: str | None = Field(None, pattern=r"^#[0-9A-Fa-f]{6}$")

    @field_validator("slug")
    @classmethod
    def validate_slug(cls, v):
        if not v.replace("-", "").replace("_", "").isalnum():
            msg = "Slug must contain only letters, numbers, hyphens, and underscores"
            raise ValueError(
                msg,
            )
        return v.lower()


class OrganizationCreate(OrganizationBase):
    pass


class OrganizationUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None
    email: EmailStr | None = None
    phone: str | None = None
    website: str | None = None

    # Address
    address_line1: str | None = None
    address_line2: str | None = None
    city: str | None = None
    state: str | None = None
    postal_code: str | None = None
    country: str | None = None

    # Business info
    tax_id: str | None = None
    industry: str | None = None
    company_size: str | None = None

    # Branding
    logo_url: str | None = None
    primary_color: str | None = Field(None, pattern=r"^#[0-9A-Fa-f]{6}$")


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
    trial_ends_at: datetime | None = None
    subscription_starts_at: datetime | None = None
    subscription_ends_at: datetime | None = None

    # Settings
    settings: dict[str, Any] = {}
    features: dict[str, Any] = {}

    # Audit
    is_active: bool
    created_at: datetime
    updated_at: datetime
    created_by: str | None = None

    class Config:
        from_attributes = True


class OrganizationUsage(BaseModel):
    """Organization usage statistics."""

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
    role: MemberRole | None = None
    is_active: bool | None = None


class OrganizationMembershipRead(OrganizationMembershipBase):
    id: str
    organization_id: str
    user_id: str
    is_active: bool
    joined_at: datetime
    invited_by: str | None = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class OrganizationMemberRead(BaseModel):
    """Member with user details."""

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
    user_last_login: datetime | None = None


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
    accepted_at: datetime | None = None
    accepted_by: str | None = None
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
    description: str | None = None
    status: str = "active"
    settings: dict[str, Any] = {}


class ProjectCreate(ProjectBase):
    pass


class ProjectUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None
    status: str | None = None
    settings: dict[str, Any] | None = None


class ProjectRead(ProjectBase):
    id: str
    organization_id: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
    created_by: str | None = None

    class Config:
        from_attributes = True


# Request/Response Models
class OrganizationListResponse(BaseModel):
    organizations: list[OrganizationRead]
    total: int
    page: int
    size: int


class OrganizationMembersResponse(BaseModel):
    members: list[OrganizationMemberRead]
    total: int


class OrganizationInvitationsResponse(BaseModel):
    invitations: list[OrganizationInvitationRead]
    total: int


class OrganizationProjectsResponse(BaseModel):
    projects: list[ProjectRead]
    total: int


class OrganizationSettings(BaseModel):
    """Organization settings update."""

    settings: dict[str, Any]


class OrganizationFeatures(BaseModel):
    """Organization features update."""

    features: dict[str, Any]


class BulkMemberUpdate(BaseModel):
    """Bulk update member roles."""

    member_updates: list[dict[str, Any]]  # [{"user_id": "...", "role": "..."}]


class OrganizationInviteBulk(BaseModel):
    """Bulk invitation."""

    invitations: list[OrganizationInvitationCreate]
