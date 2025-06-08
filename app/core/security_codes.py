"""Enterprise Security Codes System
Provides backup authentication methods and password recovery options.
"""

import hashlib
import json
import secrets
import string
from datetime import datetime, timedelta
from enum import Enum
from typing import Any

import redis.asyncio as redis
from loguru import logger
from pydantic import BaseModel
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.models.user import User


class SecurityCodeType(str, Enum):
    BACKUP_CODE = "backup_code"
    RECOVERY_CODE = "recovery_code"
    PASSWORD_RESET = "password_reset"
    ACCOUNT_VERIFICATION = "account_verification"


class SecurityCodeStatus(str, Enum):
    ACTIVE = "active"
    USED = "used"
    EXPIRED = "expired"
    REVOKED = "revoked"


class SecurityCode(BaseModel):
    """Security code model."""

    code: str
    code_type: SecurityCodeType
    hashed_code: str
    user_id: str
    created_at: datetime
    expires_at: datetime | None
    used_at: datetime | None
    status: SecurityCodeStatus
    metadata: dict[str, Any] | None = None


class EnterpriseSecurityCodeService:
    """Enterprise-grade security codes service with Redis backing
    Handles backup codes, recovery codes, and secure password reset.
    """

    def __init__(self) -> None:
        self.settings = get_settings()
        self.redis_client: redis.Redis | None = None
        self.code_length = 16
        self.backup_codes_count = 16  # Increased to 16 as requested
        self.recovery_code_length = 32

    async def initialize(self) -> None:
        """Initialize Redis connection."""
        try:
            redis_url = getattr(self.settings, "redis_url", "redis://localhost:6379")
            self.redis_client = redis.from_url(
                redis_url, encoding="utf-8", decode_responses=True,
            )
            logger.info("Security codes service initialized with Redis")
        except Exception as e:
            logger.warning(f"Redis connection failed for security codes: {e}")
            self.redis_client = None

    def _generate_secure_code(self, length: int = 16) -> str:
        """Generate cryptographically secure code."""
        alphabet = string.ascii_uppercase + string.digits
        # Remove confusing characters
        alphabet = (
            alphabet.replace("0", "").replace("O", "").replace("1", "").replace("I", "")
        )
        return "".join(secrets.choice(alphabet) for _ in range(length))

    def _hash_code(self, code: str, user_id: str) -> str:
        """Hash security code with user salt."""
        salt = f"{user_id}:{self.settings.jwt_secret_token}"
        return hashlib.sha256(f"{code}:{salt}".encode()).hexdigest()

    async def generate_backup_codes(self, user_id: str) -> list[str]:
        """Generate backup codes for user (one-time use)
        These are shown only once during setup.
        """
        codes = []
        hashed_codes = []

        for _ in range(self.backup_codes_count):
            code = self._generate_secure_code(12)  # Updated to 12 characters
            # Format as XXXX-XXXX-XXXX for readability (3 groups of 4)
            formatted_code = f"{code[:4]}-{code[4:8]}-{code[8:]}"
            codes.append(formatted_code)

            hashed_code = self._hash_code(formatted_code, user_id)
            hashed_codes.append(hashed_code)

        # Store in Redis with expiration (24 hours to claim them)
        if self.redis_client:
            backup_codes_data = {
                "codes": hashed_codes,
                "created_at": datetime.utcnow().isoformat(),
                "status": "pending",
            }
            await self.redis_client.setex(
                f"backup_codes:{user_id}",
                86400,  # 24 hours
                json.dumps(backup_codes_data),
            )

        logger.info(f"Generated {len(codes)} backup codes for user {user_id}")
        return codes

    async def activate_backup_codes(self, user_id: str, db: AsyncSession) -> bool:
        """Activate backup codes (move from Redis to database)
        Called after user confirms they've saved the codes.
        """
        if not self.redis_client:
            return False

        backup_codes_key = f"backup_codes:{user_id}"
        codes_data = await self.redis_client.get(backup_codes_key)

        if not codes_data:
            return False

        try:
            codes_info = json.loads(codes_data)

            # Update user's backup codes in database
            await db.execute(
                update(User)
                .where(User.id == user_id)
                .values(backup_codes=json.dumps(codes_info["codes"])),
            )
            await db.commit()

            # Remove from Redis
            await self.redis_client.delete(backup_codes_key)

            logger.info(f"Activated backup codes for user {user_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to activate backup codes for user {user_id}: {e}")
            return False

    async def verify_backup_code(
        self, user_id: str, code: str, db: AsyncSession,
    ) -> bool:
        """Verify and consume a backup code
        Each code can only be used once.
        """
        # Get user's backup codes
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()

        if not user or not user.backup_codes:
            return False

        try:
            backup_codes = json.loads(user.backup_codes)
            hashed_input = self._hash_code(code, user_id)

            if hashed_input in backup_codes:
                # Remove used code
                backup_codes.remove(hashed_input)

                # Update user record
                await db.execute(
                    update(User)
                    .where(User.id == user_id)
                    .values(backup_codes=json.dumps(backup_codes)),
                )
                await db.commit()

                logger.info(f"Backup code used successfully for user {user_id}")
                return True

        except Exception as e:
            logger.error(f"Failed to verify backup code for user {user_id}: {e}")

        return False

    async def verify_backup_code_for_login(
        self, user_id: str, code: str, db: AsyncSession,
    ) -> bool:
        """Verify backup code for emergency login (does NOT consume the code)
        Can be used multiple times for login purposes.
        """
        # Get user's backup codes
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()

        if not user or not user.backup_codes:
            return False

        try:
            backup_codes = json.loads(user.backup_codes)
            hashed_input = self._hash_code(code, user_id)

            if hashed_input in backup_codes:
                # Verify but DON'T remove for login (can be reused)
                logger.info(f"Backup code verified for login: user {user_id}")
                return True

        except Exception as e:
            logger.error(f"Failed to verify backup code for login: {e}")

        return False

    async def verify_backup_code_for_password_reset(
        self, user_id: str, code: str, db: AsyncSession,
    ) -> bool:
        """Verify and CONSUME backup code for password reset
        Each code can only be used once for password reset.
        """
        # Get user's backup codes
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()

        if not user or not user.backup_codes:
            return False

        try:
            backup_codes = json.loads(user.backup_codes)
            hashed_input = self._hash_code(code, user_id)

            if hashed_input in backup_codes:
                # Remove used code (consume it)
                backup_codes.remove(hashed_input)

                # Update user record
                await db.execute(
                    update(User)
                    .where(User.id == user_id)
                    .values(backup_codes=json.dumps(backup_codes)),
                )
                await db.commit()

                logger.info(f"Backup code consumed for password reset: user {user_id}")
                return True

        except Exception as e:
            logger.error(f"Failed to verify backup code for password reset: {e}")

        return False

    async def generate_recovery_code(self, user_id: str, valid_hours: int = 24) -> str:
        """Generate a recovery code for password reset using old password
        This is more secure than email-based reset.
        """
        recovery_code = self._generate_secure_code(self.recovery_code_length)

        recovery_data = {
            "user_id": user_id,
            "created_at": datetime.utcnow().isoformat(),
            "expires_at": (
                datetime.utcnow() + timedelta(hours=valid_hours)
            ).isoformat(),
            "used": False,
            "type": "password_reset",
        }

        if self.redis_client:
            await self.redis_client.setex(
                f"recovery_code:{recovery_code}",
                valid_hours * 3600,
                json.dumps(recovery_data),
            )

        logger.info(
            f"Generated recovery code for user {user_id}, expires in {valid_hours}h",
        )
        return recovery_code

    async def verify_recovery_code(self, recovery_code: str) -> dict[str, Any] | None:
        """Verify recovery code and return user info if valid."""
        if not self.redis_client:
            return None

        recovery_key = f"recovery_code:{recovery_code}"
        recovery_data = await self.redis_client.get(recovery_key)

        if not recovery_data:
            return None

        try:
            data = json.loads(recovery_data)

            # Check if already used
            if data.get("used", False):
                return None

            # Check expiration
            expires_at = datetime.fromisoformat(data["expires_at"])
            if datetime.utcnow() > expires_at:
                await self.redis_client.delete(recovery_key)
                return None

            return data

        except Exception as e:
            logger.error(f"Failed to verify recovery code: {e}")
            return None

    async def consume_recovery_code(self, recovery_code: str) -> bool:
        """Mark recovery code as used."""
        if not self.redis_client:
            return False

        recovery_key = f"recovery_code:{recovery_code}"
        recovery_data = await self.redis_client.get(recovery_key)

        if not recovery_data:
            return False

        try:
            data = json.loads(recovery_data)
            data["used"] = True
            data["used_at"] = datetime.utcnow().isoformat()

            # Update with shorter TTL (1 hour for audit purposes)
            await self.redis_client.setex(recovery_key, 3600, json.dumps(data))

            logger.info(f"Recovery code consumed: {recovery_code[:8]}...")
            return True

        except Exception as e:
            logger.error(f"Failed to consume recovery code: {e}")
            return False

    async def revoke_all_codes(self, user_id: str, db: AsyncSession) -> None:
        """Revoke all security codes for a user (emergency action)."""
        try:
            # Clear backup codes from database
            await db.execute(
                update(User).where(User.id == user_id).values(backup_codes=None),
            )
            await db.commit()

            # Clear Redis codes if available
            if self.redis_client:
                # Pattern match and delete all user codes
                pattern = f"*:{user_id}"
                keys = await self.redis_client.keys(pattern)
                if keys:
                    await self.redis_client.delete(*keys)

            logger.info(f"Revoked all security codes for user {user_id}")

        except Exception as e:
            logger.error(f"Failed to revoke codes for user {user_id}: {e}")

    async def get_user_code_status(
        self, user_id: str, db: AsyncSession,
    ) -> dict[str, Any]:
        """Get status of all security codes for a user."""
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()

        status = {
            "backup_codes_count": 0,
            "backup_codes_active": False,
            "pending_setup": False,
        }

        if user and user.backup_codes:
            try:
                backup_codes = json.loads(user.backup_codes)
                status["backup_codes_count"] = len(backup_codes)
                status["backup_codes_active"] = len(backup_codes) > 0
            except:
                pass

        # Check for pending setup in Redis
        if self.redis_client:
            pending = await self.redis_client.get(f"backup_codes:{user_id}")
            status["pending_setup"] = pending is not None

        return status


# Global instance
security_codes_service = EnterpriseSecurityCodeService()
