# app/services/organization_service.py

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func, desc
from sqlalchemy.orm import selectinload, joinedload
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timedelta
import secrets
import uuid

from app.db.models.organization import (
    Organization, OrganizationMembership, OrganizationInvitation, Project,
    OrganizationPlan, OrganizationStatus, MemberRole
)
from app.db.models.user import User
from app.db.schemas.organization import (
    OrganizationCreate, OrganizationUpdate, OrganizationMemberRead,
    OrganizationInvitationCreate, ProjectCreate, ProjectUpdate,
    OrganizationUsage
)
from app.services.base_service import BaseService
from app.core.email import email_service
from fastapi import HTTPException, status
from loguru import logger


class OrganizationService(BaseService):
    """Service for managing organizations and multi-tenancy"""
    
    def __init__(self):
        super().__init__(Organization)
    
    async def create_organization(
        self, 
        db: AsyncSession, 
        org_data: OrganizationCreate, 
        owner_user_id: str
    ) -> Organization:
        """Create a new organization with the user as owner"""
        
        # Check if slug is unique
        existing = await db.execute(
            select(Organization).where(Organization.slug == org_data.slug)
        )
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Organization slug already exists"
            )
        
        # Create organization
        org_dict = org_data.dict()
        org_dict['created_by'] = owner_user_id
        org_dict['trial_ends_at'] = datetime.utcnow() + timedelta(days=14)  # 14-day trial
        
        # Set default features based on plan
        org_dict['features'] = self._get_default_features(OrganizationPlan.FREE)
        
        organization = Organization(**org_dict)
        db.add(organization)
        await db.flush()  # Get the ID
        
        # Create owner membership
        membership = OrganizationMembership(
            organization_id=organization.id,
            user_id=owner_user_id,
            role=MemberRole.OWNER,
            invited_by=owner_user_id
        )
        db.add(membership)
        
        # Update usage count
        organization.current_users = 1
        
        await db.commit()
        await db.refresh(organization)
        
        logger.info(f"Created organization: {organization.name} ({organization.id})")
        return organization
    
    async def get_user_organizations(
        self, 
        db: AsyncSession, 
        user_id: str,
        skip: int = 0,
        limit: int = 100
    ) -> Tuple[List[Organization], int]:
        """Get all organizations for a user"""
        
        # Query with membership join
        query = (
            select(Organization)
            .join(OrganizationMembership)
            .where(
                and_(
                    OrganizationMembership.user_id == user_id,
                    OrganizationMembership.is_active == True,
                    Organization.is_active == True
                )
            )
            .options(selectinload(Organization.memberships))
            .order_by(desc(Organization.created_at))
            .offset(skip)
            .limit(limit)
        )
        
        result = await db.execute(query)
        organizations = result.scalars().all()
        
        # Get total count
        count_query = (
            select(func.count(Organization.id))
            .join(OrganizationMembership)
            .where(
                and_(
                    OrganizationMembership.user_id == user_id,
                    OrganizationMembership.is_active == True,
                    Organization.is_active == True
                )
            )
        )
        total_result = await db.execute(count_query)
        total = total_result.scalar()
        
        return list(organizations), total
    
    async def get_organization_by_slug(
        self, 
        db: AsyncSession, 
        slug: str,
        user_id: Optional[str] = None
    ) -> Optional[Organization]:
        """Get organization by slug, optionally checking user membership"""
        
        query = select(Organization).where(
            and_(
                Organization.slug == slug,
                Organization.is_active == True
            )
        ).options(
            selectinload(Organization.memberships),
            selectinload(Organization.projects)
        )
        
        result = await db.execute(query)
        organization = result.scalar_one_or_none()
        
        if not organization:
            return None
        
        # Check if user is a member (if user_id provided)
        if user_id:
            is_member = await self.is_user_member(db, organization.id, user_id)
            if not is_member:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You are not a member of this organization"
                )
        
        return organization
    
    async def update_organization(
        self,
        db: AsyncSession,
        organization_id: str,
        org_data: OrganizationUpdate,
        user_id: str
    ) -> Organization:
        """Update organization (requires admin role)"""
        
        # Check permissions
        await self._check_organization_permission(db, organization_id, user_id, [MemberRole.OWNER, MemberRole.ADMIN])
        
        organization = await self.get_by_id(db, organization_id)
        if not organization:
            raise HTTPException(status_code=404, detail="Organization not found")
        
        # Update fields
        update_data = org_data.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(organization, field, value)
        
        organization.updated_at = datetime.utcnow()
        await db.commit()
        await db.refresh(organization)
        
        return organization
    
    async def delete_organization(
        self,
        db: AsyncSession,
        organization_id: str,
        user_id: str
    ) -> bool:
        """Soft delete organization (owner only)"""
        
        # Check permissions (only owner can delete)
        await self._check_organization_permission(db, organization_id, user_id, [MemberRole.OWNER])
        
        organization = await self.get_by_id(db, organization_id)
        if not organization:
            raise HTTPException(status_code=404, detail="Organization not found")
        
        # Soft delete
        organization.is_active = False
        organization.updated_at = datetime.utcnow()
        await db.commit()
        
        logger.info(f"Deleted organization: {organization.name} ({organization.id})")
        return True
    
    # Member Management
    async def get_organization_members(
        self,
        db: AsyncSession,
        organization_id: str,
        user_id: str,
        skip: int = 0,
        limit: int = 100
    ) -> Tuple[List[OrganizationMemberRead], int]:
        """Get organization members with user details"""
        
        # Check if user is member
        await self._check_organization_membership(db, organization_id, user_id)
        
        # Query members with user details
        query = (
            select(OrganizationMembership, User)
            .join(User)
            .where(
                and_(
                    OrganizationMembership.organization_id == organization_id,
                    OrganizationMembership.is_active == True
                )
            )
            .order_by(
                OrganizationMembership.role.asc(),
                OrganizationMembership.joined_at.desc()
            )
            .offset(skip)
            .limit(limit)
        )
        
        result = await db.execute(query)
        membership_user_pairs = result.all()
        
        # Transform to response format
        members = []
        for membership, user in membership_user_pairs:
            member = OrganizationMemberRead(
                id=membership.id,
                user_id=membership.user_id,
                role=membership.role,
                is_active=membership.is_active,
                joined_at=membership.joined_at,
                user_email=user.email,
                user_name=user.username,
                user_first_name=user.first_name,
                user_last_name=user.last_name,
                user_is_verified=user.is_verified,
                user_last_login=user.last_login
            )
            members.append(member)
        
        # Get total count
        count_query = (
            select(func.count(OrganizationMembership.id))
            .where(
                and_(
                    OrganizationMembership.organization_id == organization_id,
                    OrganizationMembership.is_active == True
                )
            )
        )
        total_result = await db.execute(count_query)
        total = total_result.scalar()
        
        return members, total
    
    async def invite_user_to_organization(
        self,
        db: AsyncSession,
        organization_id: str,
        invitation_data: OrganizationInvitationCreate,
        inviter_user_id: str
    ) -> OrganizationInvitation:
        """Invite user to organization"""
        
        # Check permissions (admin or above)
        await self._check_organization_permission(
            db, organization_id, inviter_user_id, 
            [MemberRole.OWNER, MemberRole.ADMIN, MemberRole.MANAGER]
        )
        
        # Check if organization can add more users
        organization = await self.get_by_id(db, organization_id)
        if not organization.can_add_user():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Organization has reached maximum user limit"
            )
        
        # Check if user is already a member
        existing_member = await db.execute(
            select(OrganizationMembership).where(
                and_(
                    OrganizationMembership.organization_id == organization_id,
                    OrganizationMembership.user_id.in_(
                        select(User.id).where(User.email == invitation_data.email)
                    )
                )
            )
        )
        if existing_member.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User is already a member of this organization"
            )
        
        # Check for existing pending invitation
        existing_invitation = await db.execute(
            select(OrganizationInvitation).where(
                and_(
                    OrganizationInvitation.organization_id == organization_id,
                    OrganizationInvitation.email == invitation_data.email,
                    OrganizationInvitation.is_accepted == False,
                    OrganizationInvitation.is_expired == False,
                    OrganizationInvitation.expires_at > datetime.utcnow()
                )
            )
        )
        if existing_invitation.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Pending invitation already exists for this email"
            )
        
        # Create invitation
        invitation = OrganizationInvitation(
            organization_id=organization_id,
            email=invitation_data.email,
            role=invitation_data.role,
            token=secrets.token_urlsafe(32),
            invited_by=inviter_user_id,
            expires_at=datetime.utcnow() + timedelta(days=7)  # 7-day expiration
        )
        
        db.add(invitation)
        await db.commit()
        await db.refresh(invitation)
        
        # Send invitation email
        try:
            await email_service.send_invitation_email(
                invitation.email,
                f"Team at {organization.name}",
                organization.name,
                invitation.token
            )
        except Exception as e:
            logger.error(f"Failed to send invitation email: {e}")
        
        logger.info(f"Invited {invitation.email} to organization {organization_id}")
        return invitation
    
    async def accept_organization_invitation(
        self,
        db: AsyncSession,
        token: str,
        user_id: str
    ) -> OrganizationMembership:
        """Accept organization invitation"""
        
        # Find and validate invitation
        invitation = await db.execute(
            select(OrganizationInvitation)
            .where(OrganizationInvitation.token == token)
            .options(selectinload(OrganizationInvitation.organization))
        )
        invitation = invitation.scalar_one_or_none()
        
        if not invitation or not invitation.is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired invitation"
            )
        
        # Get user and verify email matches
        user = await db.execute(select(User).where(User.id == user_id))
        user = user.scalar_one_or_none()
        
        if not user or user.email != invitation.email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invitation email does not match user email"
            )
        
        # Check if organization can add more users
        if not invitation.organization.can_add_user():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Organization has reached maximum user limit"
            )
        
        # Create membership
        membership = OrganizationMembership(
            organization_id=invitation.organization_id,
            user_id=user_id,
            role=invitation.role,
            invited_by=invitation.invited_by
        )
        
        db.add(membership)
        
        # Mark invitation as accepted
        invitation.is_accepted = True
        invitation.accepted_at = datetime.utcnow()
        invitation.accepted_by = user_id
        
        # Update organization user count
        invitation.organization.current_users += 1
        
        await db.commit()
        await db.refresh(membership)
        
        logger.info(f"User {user_id} accepted invitation to organization {invitation.organization_id}")
        return membership
    
    async def update_member_role(
        self,
        db: AsyncSession,
        organization_id: str,
        member_user_id: str,
        new_role: MemberRole,
        updater_user_id: str
    ) -> OrganizationMembership:
        """Update member role"""
        
        # Check permissions
        await self._check_organization_permission(
            db, organization_id, updater_user_id, 
            [MemberRole.OWNER, MemberRole.ADMIN]
        )
        
        # Get membership
        membership = await db.execute(
            select(OrganizationMembership).where(
                and_(
                    OrganizationMembership.organization_id == organization_id,
                    OrganizationMembership.user_id == member_user_id,
                    OrganizationMembership.is_active == True
                )
            )
        )
        membership = membership.scalar_one_or_none()
        
        if not membership:
            raise HTTPException(status_code=404, detail="Member not found")
        
        # Prevent changing owner role (unless you're the owner)
        if membership.role == MemberRole.OWNER:
            await self._check_organization_permission(
                db, organization_id, updater_user_id, [MemberRole.OWNER]
            )
        
        # Update role
        membership.role = new_role
        membership.updated_at = datetime.utcnow()
        
        await db.commit()
        await db.refresh(membership)
        
        return membership
    
    async def remove_member(
        self,
        db: AsyncSession,
        organization_id: str,
        member_user_id: str,
        remover_user_id: str
    ) -> bool:
        """Remove member from organization"""
        
        # Check permissions
        await self._check_organization_permission(
            db, organization_id, remover_user_id, 
            [MemberRole.OWNER, MemberRole.ADMIN]
        )
        
        # Get membership
        membership = await db.execute(
            select(OrganizationMembership).where(
                and_(
                    OrganizationMembership.organization_id == organization_id,
                    OrganizationMembership.user_id == member_user_id,
                    OrganizationMembership.is_active == True
                )
            )
        )
        membership = membership.scalar_one_or_none()
        
        if not membership:
            raise HTTPException(status_code=404, detail="Member not found")
        
        # Cannot remove owner
        if membership.role == MemberRole.OWNER:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot remove organization owner"
            )
        
        # Deactivate membership
        membership.is_active = False
        membership.updated_at = datetime.utcnow()
        
        # Update organization user count
        organization = await self.get_by_id(db, organization_id)
        organization.current_users = max(0, organization.current_users - 1)
        
        await db.commit()
        
        logger.info(f"Removed user {member_user_id} from organization {organization_id}")
        return True
    
    # Usage and Analytics
    async def get_organization_usage(
        self,
        db: AsyncSession,
        organization_id: str,
        user_id: str
    ) -> OrganizationUsage:
        """Get organization usage statistics"""
        
        await self._check_organization_membership(db, organization_id, user_id)
        
        organization = await self.get_by_id(db, organization_id)
        
        return OrganizationUsage(
            users_percentage=organization.get_usage_percentage('users'),
            projects_percentage=organization.get_usage_percentage('projects'),
            storage_percentage=organization.get_usage_percentage('storage'),
            api_calls_percentage=organization.get_usage_percentage('api_calls'),
            
            users_count=f"{organization.current_users} / {organization.max_users}",
            projects_count=f"{organization.current_projects} / {organization.max_projects}",
            storage_count=f"{organization.current_storage_gb} / {organization.max_storage_gb} GB",
            api_calls_count=f"{organization.current_api_calls_this_month:,} / {organization.max_api_calls_per_month:,}"
        )
    
    # Helper Methods
    async def is_user_member(
        self,
        db: AsyncSession,
        organization_id: str,
        user_id: str
    ) -> bool:
        """Check if user is a member of organization"""
        
        result = await db.execute(
            select(OrganizationMembership).where(
                and_(
                    OrganizationMembership.organization_id == organization_id,
                    OrganizationMembership.user_id == user_id,
                    OrganizationMembership.is_active == True
                )
            )
        )
        return result.scalar_one_or_none() is not None
    
    async def get_user_role_in_organization(
        self,
        db: AsyncSession,
        organization_id: str,
        user_id: str
    ) -> Optional[MemberRole]:
        """Get user's role in organization"""
        
        result = await db.execute(
            select(OrganizationMembership.role).where(
                and_(
                    OrganizationMembership.organization_id == organization_id,
                    OrganizationMembership.user_id == user_id,
                    OrganizationMembership.is_active == True
                )
            )
        )
        role = result.scalar_one_or_none()
        return role
    
    async def _check_organization_membership(
        self,
        db: AsyncSession,
        organization_id: str,
        user_id: str
    ):
        """Check if user is a member, raise exception if not"""
        
        if not await self.is_user_member(db, organization_id, user_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not a member of this organization"
            )
    
    async def _check_organization_permission(
        self,
        db: AsyncSession,
        organization_id: str,
        user_id: str,
        required_roles: List[MemberRole]
    ):
        """Check if user has required role in organization"""
        
        user_role = await self.get_user_role_in_organization(db, organization_id, user_id)
        
        if not user_role or user_role not in required_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions for this operation"
            )
    
    def _get_default_features(self, plan: OrganizationPlan) -> Dict[str, Any]:
        """Get default features for organization plan"""
        
        features_by_plan = {
            OrganizationPlan.FREE: {
                "api_access": True,
                "custom_branding": False,
                "advanced_analytics": False,
                "priority_support": False,
                "sso": False,
                "audit_logs": False
            },
            OrganizationPlan.STARTER: {
                "api_access": True,
                "custom_branding": True,
                "advanced_analytics": False,
                "priority_support": False,
                "sso": False,
                "audit_logs": True
            },
            OrganizationPlan.PROFESSIONAL: {
                "api_access": True,
                "custom_branding": True,
                "advanced_analytics": True,
                "priority_support": True,
                "sso": False,
                "audit_logs": True
            },
            OrganizationPlan.ENTERPRISE: {
                "api_access": True,
                "custom_branding": True,
                "advanced_analytics": True,
                "priority_support": True,
                "sso": True,
                "audit_logs": True
            }
        }
        
        return features_by_plan.get(plan, features_by_plan[OrganizationPlan.FREE])


# Global service instance
organization_service = OrganizationService() 