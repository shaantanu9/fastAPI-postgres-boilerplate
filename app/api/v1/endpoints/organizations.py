# app/api/v1/endpoints/organizations.py

from fastapi import APIRouter, Depends, HTTPException, status, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from app.db.session import get_db
from app.db.schemas.organization import (
    OrganizationCreate, OrganizationUpdate, OrganizationRead,
    OrganizationListResponse, OrganizationMembersResponse,
    OrganizationInvitationCreate, OrganizationInvitationRead,
    OrganizationInvitationAccept, OrganizationUsage,
    OrganizationMembershipUpdate, MemberRole, ProjectCreate,
    ProjectUpdate, ProjectRead, OrganizationSettings,
    OrganizationFeatures, BulkMemberUpdate, OrganizationInviteBulk
)
from app.db.schemas.user import UserRead
from app.services.organization_service import organization_service
from app.api.v1.endpoints.auth import get_current_user
from loguru import logger

router = APIRouter()

# ===== ORGANIZATION CRUD =====

@router.post("/", response_model=OrganizationRead, status_code=status.HTTP_201_CREATED)
async def create_organization(
    org_data: OrganizationCreate,
    current_user: UserRead = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new organization (user becomes owner)"""
    
    try:
        organization = await organization_service.create_organization(
            db, org_data, current_user.id
        )
        return OrganizationRead.from_orm(organization)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create organization: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create organization"
        )


@router.get("/", response_model=OrganizationListResponse)
async def list_user_organizations(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    current_user: UserRead = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get all organizations for current user"""
    
    try:
        organizations, total = await organization_service.get_user_organizations(
            db, current_user.id, skip, limit
        )
        
        return OrganizationListResponse(
            organizations=[OrganizationRead.from_orm(org) for org in organizations],
            total=total,
            page=skip // limit + 1,
            size=limit
        )
    except Exception as e:
        logger.error(f"Failed to list organizations: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve organizations"
        )


@router.get("/{organization_slug}", response_model=OrganizationRead)
async def get_organization(
    organization_slug: str,
    current_user: UserRead = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get organization by slug"""
    
    try:
        organization = await organization_service.get_organization_by_slug(
            db, organization_slug, current_user.id
        )
        
        if not organization:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Organization not found"
            )
        
        return OrganizationRead.from_orm(organization)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get organization: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve organization"
        )


@router.put("/{organization_id}", response_model=OrganizationRead)
async def update_organization(
    organization_id: str,
    org_data: OrganizationUpdate,
    current_user: UserRead = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update organization (requires admin role)"""
    
    try:
        organization = await organization_service.update_organization(
            db, organization_id, org_data, current_user.id
        )
        return OrganizationRead.from_orm(organization)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update organization: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update organization"
        )


@router.delete("/{organization_id}")
async def delete_organization(
    organization_id: str,
    current_user: UserRead = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete organization (owner only)"""
    
    try:
        await organization_service.delete_organization(
            db, organization_id, current_user.id
        )
        return {"message": "Organization deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete organization: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete organization"
        )


# ===== MEMBER MANAGEMENT =====

@router.get("/{organization_id}/members", response_model=OrganizationMembersResponse)
async def get_organization_members(
    organization_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    current_user: UserRead = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get organization members"""
    
    try:
        members, total = await organization_service.get_organization_members(
            db, organization_id, current_user.id, skip, limit
        )
        
        return OrganizationMembersResponse(
            members=members,
            total=total
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get organization members: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve organization members"
        )


@router.post("/{organization_id}/invitations", response_model=OrganizationInvitationRead)
async def invite_user_to_organization(
    organization_id: str,
    invitation_data: OrganizationInvitationCreate,
    background_tasks: BackgroundTasks,
    current_user: UserRead = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Invite user to organization"""
    
    try:
        invitation = await organization_service.invite_user_to_organization(
            db, organization_id, invitation_data, current_user.id
        )
        return OrganizationInvitationRead.from_orm(invitation)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to invite user: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send invitation"
        )


@router.post("/{organization_id}/invitations/bulk")
async def bulk_invite_users(
    organization_id: str,
    bulk_invitation: OrganizationInviteBulk,
    background_tasks: BackgroundTasks,
    current_user: UserRead = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Bulk invite users to organization"""
    
    try:
        invitations = []
        failed_invitations = []
        
        for invitation_data in bulk_invitation.invitations:
            try:
                invitation = await organization_service.invite_user_to_organization(
                    db, organization_id, invitation_data, current_user.id
                )
                invitations.append(OrganizationInvitationRead.from_orm(invitation))
            except HTTPException as e:
                failed_invitations.append({
                    "email": invitation_data.email,
                    "error": str(e.detail)
                })
            except Exception as e:
                failed_invitations.append({
                    "email": invitation_data.email,
                    "error": "Failed to send invitation"
                })
        
        return {
            "successful_invitations": invitations,
            "failed_invitations": failed_invitations,
            "summary": {
                "total": len(bulk_invitation.invitations),
                "successful": len(invitations),
                "failed": len(failed_invitations)
            }
        }
    except Exception as e:
        logger.error(f"Failed to process bulk invitations: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process bulk invitations"
        )


@router.post("/invitations/accept")
async def accept_organization_invitation(
    invitation_accept: OrganizationInvitationAccept,
    current_user: UserRead = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Accept organization invitation"""
    
    try:
        membership = await organization_service.accept_organization_invitation(
            db, invitation_accept.token, current_user.id
        )
        return {"message": "Invitation accepted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to accept invitation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to accept invitation"
        )


@router.put("/{organization_id}/members/{member_user_id}/role")
async def update_member_role(
    organization_id: str,
    member_user_id: str,
    role_update: OrganizationMembershipUpdate,
    current_user: UserRead = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update member role"""
    
    try:
        if role_update.role is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Role is required"
            )
        
        membership = await organization_service.update_member_role(
            db, organization_id, member_user_id, role_update.role, current_user.id
        )
        return {"message": "Member role updated successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update member role: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update member role"
        )


@router.put("/{organization_id}/members/bulk")
async def bulk_update_member_roles(
    organization_id: str,
    bulk_update: BulkMemberUpdate,
    current_user: UserRead = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Bulk update member roles"""
    
    try:
        successful_updates = []
        failed_updates = []
        
        for update_data in bulk_update.member_updates:
            try:
                user_id = update_data["user_id"]
                role = MemberRole(update_data["role"])
                
                await organization_service.update_member_role(
                    db, organization_id, user_id, role, current_user.id
                )
                successful_updates.append({"user_id": user_id, "role": role})
            except Exception as e:
                failed_updates.append({
                    "user_id": update_data.get("user_id", "unknown"),
                    "error": str(e)
                })
        
        return {
            "successful_updates": successful_updates,
            "failed_updates": failed_updates,
            "summary": {
                "total": len(bulk_update.member_updates),
                "successful": len(successful_updates),
                "failed": len(failed_updates)
            }
        }
    except Exception as e:
        logger.error(f"Failed to process bulk member updates: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process bulk updates"
        )


@router.delete("/{organization_id}/members/{member_user_id}")
async def remove_member_from_organization(
    organization_id: str,
    member_user_id: str,
    current_user: UserRead = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Remove member from organization"""
    
    try:
        await organization_service.remove_member(
            db, organization_id, member_user_id, current_user.id
        )
        return {"message": "Member removed successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to remove member: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to remove member"
        )


# ===== ORGANIZATION USAGE & ANALYTICS =====

@router.get("/{organization_id}/usage", response_model=OrganizationUsage)
async def get_organization_usage(
    organization_id: str,
    current_user: UserRead = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get organization usage statistics"""
    
    try:
        usage = await organization_service.get_organization_usage(
            db, organization_id, current_user.id
        )
        return usage
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get organization usage: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve usage statistics"
        )


# ===== ORGANIZATION SETTINGS =====

@router.put("/{organization_id}/settings")
async def update_organization_settings(
    organization_id: str,
    settings_update: OrganizationSettings,
    current_user: UserRead = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update organization settings"""
    
    try:
        # Check permissions
        await organization_service._check_organization_permission(
            db, organization_id, current_user.id, [MemberRole.OWNER, MemberRole.ADMIN]
        )
        
        organization = await organization_service.get_by_id(db, organization_id)
        if not organization:
            raise HTTPException(status_code=404, detail="Organization not found")
        
        # Update settings
        organization.settings.update(settings_update.settings)
        await db.commit()
        
        return {"message": "Settings updated successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update organization settings: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update settings"
        )


@router.put("/{organization_id}/features")
async def update_organization_features(
    organization_id: str,
    features_update: OrganizationFeatures,
    current_user: UserRead = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update organization features (owner only)"""
    
    try:
        # Check permissions (owner only for feature updates)
        await organization_service._check_organization_permission(
            db, organization_id, current_user.id, [MemberRole.OWNER]
        )
        
        organization = await organization_service.get_by_id(db, organization_id)
        if not organization:
            raise HTTPException(status_code=404, detail="Organization not found")
        
        # Update features
        organization.features.update(features_update.features)
        await db.commit()
        
        return {"message": "Features updated successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update organization features: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update features"
        )


# ===== PROJECTS (Example of tenant-scoped resources) =====

@router.get("/{organization_id}/projects")
async def get_organization_projects(
    organization_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    current_user: UserRead = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get organization projects"""
    
    try:
        # Check membership
        await organization_service._check_organization_membership(
            db, organization_id, current_user.id
        )
        
        from sqlalchemy import select, func
        from app.db.models.organization import Project
        
        # Get projects
        query = (
            select(Project)
            .where(Project.organization_id == organization_id)
            .where(Project.is_active == True)
            .offset(skip)
            .limit(limit)
        )
        
        result = await db.execute(query)
        projects = result.scalars().all()
        
        # Get total count
        count_query = (
            select(func.count(Project.id))
            .where(Project.organization_id == organization_id)
            .where(Project.is_active == True)
        )
        total_result = await db.execute(count_query)
        total = total_result.scalar()
        
        return {
            "projects": [ProjectRead.from_orm(project) for project in projects],
            "total": total,
            "page": skip // limit + 1,
            "size": limit
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get organization projects: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve projects"
        )


@router.post("/{organization_id}/projects", response_model=ProjectRead)
async def create_organization_project(
    organization_id: str,
    project_data: ProjectCreate,
    current_user: UserRead = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new project in organization"""
    
    try:
        # Check membership and project creation limit
        await organization_service._check_organization_membership(
            db, organization_id, current_user.id
        )
        
        organization = await organization_service.get_by_id(db, organization_id)
        if not organization.can_create_project():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Organization has reached maximum project limit"
            )
        
        from app.db.models.organization import Project
        
        # Create project
        project_dict = project_data.dict()
        project_dict['organization_id'] = organization_id
        project_dict['created_by'] = current_user.id
        
        project = Project(**project_dict)
        db.add(project)
        
        # Update organization project count
        organization.current_projects += 1
        
        await db.commit()
        await db.refresh(project)
        
        return ProjectRead.from_orm(project)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create project: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create project"
        )


# ===== UTILITY ENDPOINTS =====

@router.get("/{organization_id}/check-membership")
async def check_organization_membership(
    organization_id: str,
    current_user: UserRead = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Check if current user is a member of organization"""
    
    try:
        is_member = await organization_service.is_user_member(
            db, organization_id, current_user.id
        )
        
        role = None
        if is_member:
            role = await organization_service.get_user_role_in_organization(
                db, organization_id, current_user.id
            )
        
        return {
            "is_member": is_member,
            "role": role,
            "organization_id": organization_id
        }
    except Exception as e:
        logger.error(f"Failed to check membership: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to check membership"
        ) 