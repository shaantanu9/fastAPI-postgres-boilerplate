"""
Script to seed default roles and permissions for SaaS application.
Run this after database initialization to set up the basic RBAC structure.
"""

import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import AsyncSessionLocal
from app.db.models.user import Role, Permission, RolePermission
from sqlalchemy import select
from loguru import logger

async def create_default_permissions(db: AsyncSession):
    """Create default permissions"""
    
    default_permissions = [
        # User management permissions
        {"name": "users.create", "resource": "users", "action": "create", "description": "Create new users"},
        {"name": "users.read", "resource": "users", "action": "read", "description": "View user information"},
        {"name": "users.update", "resource": "users", "action": "update", "description": "Update user information"},
        {"name": "users.delete", "resource": "users", "action": "delete", "description": "Delete users"},
        {"name": "users.invite", "resource": "users", "action": "invite", "description": "Invite new users"},
        
        # Profile management
        {"name": "profile.read", "resource": "profile", "action": "read", "description": "View own profile"},
        {"name": "profile.update", "resource": "profile", "action": "update", "description": "Update own profile"},
        
        # Organization management
        {"name": "organization.read", "resource": "organization", "action": "read", "description": "View organization info"},
        {"name": "organization.update", "resource": "organization", "action": "update", "description": "Update organization settings"},
        {"name": "organization.manage", "resource": "organization", "action": "manage", "description": "Full organization management"},
        
        # File management
        {"name": "files.upload", "resource": "files", "action": "upload", "description": "Upload files"},
        {"name": "files.download", "resource": "files", "action": "download", "description": "Download files"},
        {"name": "files.delete", "resource": "files", "action": "delete", "description": "Delete files"},
        {"name": "files.manage", "resource": "files", "action": "manage", "description": "Manage all files"},
        
        # API access
        {"name": "api.read", "resource": "api", "action": "read", "description": "Read API access"},
        {"name": "api.write", "resource": "api", "action": "write", "description": "Write API access"},
        {"name": "api.admin", "resource": "api", "action": "admin", "description": "Admin API access"},
        
        # Billing & subscriptions (SaaS specific)
        {"name": "billing.read", "resource": "billing", "action": "read", "description": "View billing information"},
        {"name": "billing.manage", "resource": "billing", "action": "manage", "description": "Manage billing and subscriptions"},
        
        # Analytics and reporting
        {"name": "analytics.read", "resource": "analytics", "action": "read", "description": "View analytics"},
        {"name": "reports.generate", "resource": "reports", "action": "generate", "description": "Generate reports"},
        
        # System administration
        {"name": "system.admin", "resource": "system", "action": "admin", "description": "System administration"},
        {"name": "system.monitoring", "resource": "system", "action": "monitoring", "description": "System monitoring"},
        
        # Role and permission management
        {"name": "roles.read", "resource": "roles", "action": "read", "description": "View roles"},
        {"name": "roles.manage", "resource": "roles", "action": "manage", "description": "Manage roles and permissions"},
    ]
    
    created_permissions = []
    
    for perm_data in default_permissions:
        # Check if permission already exists
        existing = await db.execute(
            select(Permission).where(Permission.name == perm_data["name"])
        )
        if existing.scalar_one_or_none():
            logger.info(f"Permission {perm_data['name']} already exists, skipping")
            continue
        
        permission = Permission(**perm_data)
        db.add(permission)
        created_permissions.append(permission)
        logger.info(f"Created permission: {perm_data['name']}")
    
    await db.commit()
    return created_permissions


async def create_default_roles(db: AsyncSession):
    """Create default roles"""
    
    default_roles = [
        {
            "name": "super_admin",
            "description": "Super administrator with full system access",
            "is_system_role": True,
            "permissions": [
                "users.create", "users.read", "users.update", "users.delete", "users.invite",
                "organization.read", "organization.update", "organization.manage",
                "files.upload", "files.download", "files.delete", "files.manage",
                "api.read", "api.write", "api.admin",
                "billing.read", "billing.manage",
                "analytics.read", "reports.generate",
                "system.admin", "system.monitoring",
                "roles.read", "roles.manage",
                "profile.read", "profile.update"
            ]
        },
        {
            "name": "admin",
            "description": "Organization administrator",
            "is_system_role": True,
            "permissions": [
                "users.create", "users.read", "users.update", "users.invite",
                "organization.read", "organization.update",
                "files.upload", "files.download", "files.delete", "files.manage",
                "api.read", "api.write",
                "billing.read", "billing.manage",
                "analytics.read", "reports.generate",
                "roles.read",
                "profile.read", "profile.update"
            ]
        },
        {
            "name": "manager",
            "description": "Team manager with limited administrative access",
            "is_system_role": True,
            "permissions": [
                "users.read", "users.invite",
                "organization.read",
                "files.upload", "files.download", "files.delete",
                "api.read", "api.write",
                "analytics.read", "reports.generate",
                "profile.read", "profile.update"
            ]
        },
        {
            "name": "user",
            "description": "Standard user with basic access",
            "is_system_role": True,
            "permissions": [
                "organization.read",
                "files.upload", "files.download",
                "api.read",
                "profile.read", "profile.update"
            ]
        },
        {
            "name": "viewer",
            "description": "Read-only access user",
            "is_system_role": True,
            "permissions": [
                "organization.read",
                "files.download",
                "api.read",
                "profile.read"
            ]
        }
    ]
    
    created_roles = []
    
    for role_data in default_roles:
        # Check if role already exists
        existing = await db.execute(
            select(Role).where(Role.name == role_data["name"])
        )
        if existing.scalar_one_or_none():
            logger.info(f"Role {role_data['name']} already exists, skipping")
            continue
        
        # Create role
        role = Role(
            name=role_data["name"],
            description=role_data["description"],
            is_system_role=role_data["is_system_role"]
        )
        db.add(role)
        await db.flush()  # Get the role ID
        
        # Assign permissions to role
        for permission_name in role_data["permissions"]:
            permission = await db.execute(
                select(Permission).where(Permission.name == permission_name)
            )
            permission = permission.scalar_one_or_none()
            
            if permission:
                role_permission = RolePermission(
                    role_id=role.id,
                    permission_id=permission.id
                )
                db.add(role_permission)
        
        created_roles.append(role)
        logger.info(f"Created role: {role_data['name']} with {len(role_data['permissions'])} permissions")
    
    await db.commit()
    return created_roles


async def seed_rbac():
    """Main function to seed RBAC data"""
    logger.info("Starting RBAC seeding process...")
    
    async with AsyncSessionLocal() as db:
        try:
            # Create permissions first
            logger.info("Creating default permissions...")
            permissions = await create_default_permissions(db)
            logger.info(f"Created {len(permissions)} permissions")
            
            # Create roles with permission assignments
            logger.info("Creating default roles...")
            roles = await create_default_roles(db)
            logger.info(f"Created {len(roles)} roles")
            
            logger.info("RBAC seeding completed successfully!")
            
        except Exception as e:
            logger.error(f"Error during RBAC seeding: {str(e)}")
            await db.rollback()
            raise


async def create_first_admin_user(
    username: str,
    email: str,
    password: str,
    first_name: str,
    last_name: str
):
    """Create the first admin user"""
    from app.services.user_service import enhanced_user_service
    from app.db.schemas.user import UserCreate
    
    logger.info(f"Creating first admin user: {username}")
    
    async with AsyncSessionLocal() as db:
        try:
            # Check if user already exists
            existing = await enhanced_user_service.get_by_username_or_email(db, username, email)
            if existing:
                logger.info("Admin user already exists, skipping creation")
                return existing
            
            # Create user
            user_create = UserCreate(
                username=username,
                email=email,
                first_name=first_name,
                last_name=last_name,
                password=password
            )
            
            user = await enhanced_user_service.create_user(db, user_create)
            
            # Assign super_admin role
            await enhanced_user_service.assign_role(db, user.id, "super_admin")
            
            # Verify user immediately for admin
            user.is_verified = True
            user.email_verified_at = user.created_at
            await db.commit()
            
            logger.info(f"First admin user created successfully: {username}")
            return user
            
        except Exception as e:
            logger.error(f"Error creating admin user: {str(e)}")
            await db.rollback()
            raise


if __name__ == "__main__":
    # Run seeding
    asyncio.run(seed_rbac())
    
    # Create first admin user (uncomment and modify as needed)
    asyncio.run(create_first_admin_user(
        username="admin",
        email="admin@yourapp.com",
        password="AdminPassword123!",
        first_name="System",
        last_name="Administrator"
    )) 