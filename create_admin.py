#!/usr/bin/env python3
"""Simple script to create the first admin user."""

import asyncio

from loguru import logger

from app.db.schemas.user import UserCreate
from app.db.session import AsyncSessionLocal
from app.services.user_service import enhanced_user_service


async def create_admin():
    """Create the first admin user."""
    async with AsyncSessionLocal() as db:
        try:
            # Check if admin already exists
            existing = await enhanced_user_service.get_by_username_or_email(
                db, "admin", "admin@yourapp.com",
            )

            if existing:
                logger.info("Admin user already exists")
                return existing

            # Create admin user
            user_create = UserCreate(
                username="admin",
                email="admin@yourapp.com",
                first_name="System",
                last_name="Administrator",
                password="Zx9#mK8$pL2@vN5!",
            )

            user = await enhanced_user_service.create_user(db, user_create)
            logger.info(f"Created admin user: {user.username}")

            # Assign super_admin role
            await enhanced_user_service.assign_role(db, user.id, "super_admin")
            logger.info("Assigned super_admin role")

            # Verify user immediately
            user.is_verified = True
            user.email_verified_at = user.created_at
            await db.commit()

            logger.info("✅ Admin user created successfully!")
            return user

        except Exception as e:
            logger.error(f"Error creating admin user: {e}")
            await db.rollback()
            raise


if __name__ == "__main__":
    asyncio.run(create_admin())
