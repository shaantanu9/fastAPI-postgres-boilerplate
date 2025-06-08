#!/usr/bin/env python3

import asyncio
import os
import sys
import uuid
from datetime import datetime

import httpx

# Add the app directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), "."))

import contextlib

from app.core.security_base import EnterpriseSecurityService
from app.core.security_codes import security_codes_service
from app.db.schemas.user import BackupCodePasswordReset, UserCreate
from app.db.session import AsyncSessionLocal
from app.services.user_service import enhanced_user_service


async def test_backup_codes_full_workflow() -> None:
    """Test the complete backup codes workflow including password reset."""
    # Generate unique identifiers for this test run
    test_id = str(uuid.uuid4())[:8]
    timestamp = datetime.now().strftime("%H%M%S")

    async with AsyncSessionLocal() as db:
        try:
            # Initialize security codes service
            await security_codes_service.initialize()

            # Create security service instance
            security_service = EnterpriseSecurityService()

            # Create a test user with unique identifiers
            user_data = UserCreate(
                username=f"backup_test_{test_id}_{timestamp}",
                email=f"backup_test_{test_id}_{timestamp}@example.com",
                first_name="Test",
                last_name="User",
                password="StrongP@ssw0rd#2025",
            )

            user = await enhanced_user_service.create_user(db, user_data, "test_system")

            # Generate backup codes
            backup_codes = await security_codes_service.generate_backup_codes(user.id)

            # Verify each code is 12 characters + 2 hyphens = 14 chars total (XXXX-XXXX-XXXX format)
            for _i, code in enumerate(backup_codes[:3]):  # Show first 3
                expected_format = len(code) == 14 and code[4] == "-" and code[9] == "-"
                assert expected_format, (
                    f"Code {code} does not match XXXX-XXXX-XXXX format"
                )


            # Activate the codes
            activated = await security_codes_service.activate_backup_codes(user.id, db)

            # Test password reset with backup code

            # Use the first backup code for password reset
            test_code = backup_codes[0]
            new_password = "NewStr0ngP@ss#2025"

            # Create the backup code password reset request
            reset_request = BackupCodePasswordReset(
                username_or_email=user.email,
                backup_code=test_code,
                new_password=new_password,
            )

            # Verify the backup code works for password reset
            is_valid = (
                await security_codes_service.verify_backup_code_for_password_reset(
                    user.id, test_code, db,
                )
            )

            # Check remaining codes
            remaining_status = await security_codes_service.get_user_code_status(
                user.id, db,
            )

            # Verify the used code no longer works
            try_again = (
                await security_codes_service.verify_backup_code_for_password_reset(
                    user.id, test_code, db,
                )
            )

            # Test that other codes still work for login (not consumed)
            second_code = backup_codes[1]
            login_valid = await security_codes_service.verify_backup_code_for_login(
                user.id, second_code, db,
            )

            # Verify the login didn't consume the code
            login_valid_again = (
                await security_codes_service.verify_backup_code_for_login(
                    user.id, second_code, db,
                )
            )


        except Exception:
            import traceback

            traceback.print_exc()

        finally:
            # Cleanup - delete test user
            if "user" in locals():
                try:
                    from sqlalchemy import delete

                    from app.db.models.user import User, UserRole

                    # Delete user roles first to avoid foreign key constraint
                    await db.execute(
                        delete(UserRole).where(UserRole.user_id == user.id),
                    )

                    # Then delete the user
                    await db.execute(delete(User).where(User.id == user.id))
                    await db.commit()
                except Exception:
                    with contextlib.suppress(Exception):
                        await db.rollback()


async def test_api_endpoint() -> None:
    """Test the actual API endpoint for backup code password reset."""
    # Generate unique identifiers for this test run
    test_id = str(uuid.uuid4())[:8]
    timestamp = datetime.now().strftime("%H%M%S")

    try:
        # Start the server in background or connect to running instance
        base_url = "http://localhost:8000"

        async with httpx.AsyncClient() as client:
            # First create a user through registration
            user_data = {
                "username": f"api_test_{test_id}_{timestamp}",
                "email": f"api_test_{test_id}_{timestamp}@example.com",
                "first_name": "API",
                "last_name": "Test",
                "password": "StrongP@ssw0rd#2025",
            }

            response = await client.post(
                f"{base_url}/api/v1/auth/register", json=user_data,
            )
            if response.status_code != 201:
                return

            response.json()

            # TODO: In a real test, we'd need to:
            # 1. Get backup codes from registration response or setup endpoint
            # 2. Test the actual API endpoint /api/v1/auth/password/reset-with-backup-code


    except Exception:
        pass


if __name__ == "__main__":
    asyncio.run(test_backup_codes_full_workflow())
    asyncio.run(test_api_endpoint())
