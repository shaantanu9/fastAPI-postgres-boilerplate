#!/usr/bin/env python3
"""
Enhanced Registration System with Backup Codes
Provides backup codes during registration that can be used for login and password reset.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from pydantic import BaseModel
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

class RegistrationWithBackupCodes(BaseModel):
    """Registration response with backup codes"""
    user_id: str
    username: str
    email: str
    backup_codes: List[str]
    backup_codes_count: int
    message: str

class BackupCodeLoginRequest(BaseModel):
    """Login request using backup code"""
    username_or_email: str
    backup_code: str

class BackupCodePasswordReset(BaseModel):
    """Password reset using backup code"""
    username_or_email: str
    backup_code: str
    new_password: str

class EnhancedSecurityCodesService:
    """Enhanced security codes service with registration integration"""
    
    def __init__(self):
        from app.core.config import get_settings
        self.settings = get_settings()
        self.redis_client = None
        
        # Enhanced configuration
        self.backup_codes_count = 16  # Increased from 10 to 16
        self.code_length = 8  # XXXX-XXXX format
        self.recovery_code_length = 32
        
    async def initialize(self):
        """Initialize Redis connection"""
        try:
            import redis.asyncio as redis
            redis_url = getattr(self.settings, 'redis_url', 'redis://localhost:6379')
            self.redis_client = redis.from_url(
                redis_url,
                encoding="utf-8",
                decode_responses=True
            )
        except Exception as e:
            print(f"Redis connection failed: {e}")
            self.redis_client = None

    def _generate_secure_code(self, length: int = 8) -> str:
        """Generate cryptographically secure code"""
        import secrets
        import string
        alphabet = string.ascii_uppercase + string.digits
        # Remove confusing characters
        alphabet = alphabet.replace('0', '').replace('O', '').replace('1', '').replace('I', '')
        return ''.join(secrets.choice(alphabet) for _ in range(length))

    def _hash_code(self, code: str, user_id: str) -> str:
        """Hash security code with user salt"""
        import hashlib
        salt = f"{user_id}:{self.settings.jwt_secret_token}"
        return hashlib.sha256(f"{code}:{salt}".encode()).hexdigest()

    async def generate_registration_backup_codes(self, user_id: str) -> List[str]:
        """
        Generate 16 backup codes during user registration
        These codes can be used for:
        1. Emergency login (bypassing password)
        2. Password reset (without email)
        3. Account recovery
        """
        codes = []
        hashed_codes = []
        
        for _ in range(self.backup_codes_count):
            code = self._generate_secure_code(self.code_length)
            # Format as XXXX-XXXX for readability
            formatted_code = f"{code[:4]}-{code[4:]}"
            codes.append(formatted_code)
            
            hashed_code = self._hash_code(formatted_code, user_id)
            hashed_codes.append(hashed_code)

        # Store immediately in Redis (ready for use)
        if self.redis_client:
            import json
            backup_codes_data = {
                "codes": hashed_codes,
                "created_at": datetime.utcnow().isoformat(),
                "status": "active",  # Active immediately
                "usage_count": 0,
                "last_used": None
            }
            # Store for 365 days (1 year)
            await self.redis_client.setex(
                f"backup_codes:{user_id}",
                365 * 24 * 3600,  # 1 year
                json.dumps(backup_codes_data)
            )

        print(f"Generated {len(codes)} backup codes for user {user_id}")
        return codes

    async def store_backup_codes_in_database(self, user_id: str, db: AsyncSession) -> bool:
        """Store backup codes in database for persistence"""
        if not self.redis_client:
            return False

        try:
            import json
            from sqlalchemy import update
            from app.db.models.user import User
            
            backup_codes_key = f"backup_codes:{user_id}"
            codes_data = await self.redis_client.get(backup_codes_key)
            
            if codes_data:
                codes_info = json.loads(codes_data)
                
                # Update user's backup codes in database
                await db.execute(
                    update(User)
                    .where(User.id == user_id)
                    .values(backup_codes=json.dumps(codes_info))
                )
                await db.commit()
                return True
                
        except Exception as e:
            print(f"Failed to store backup codes in database: {e}")
            
        return False

    async def verify_backup_code_for_login(self, user_id: str, code: str) -> bool:
        """
        Verify backup code for emergency login
        Does NOT consume the code (can be reused)
        """
        if not self.redis_client:
            return False

        try:
            import json
            backup_codes_key = f"backup_codes:{user_id}"
            codes_data = await self.redis_client.get(backup_codes_key)
            
            if not codes_data:
                return False

            codes_info = json.loads(codes_data)
            hashed_input = self._hash_code(code, user_id)
            
            if hashed_input in codes_info["codes"]:
                # Update usage statistics but don't consume
                codes_info["usage_count"] += 1
                codes_info["last_used"] = datetime.utcnow().isoformat()
                
                await self.redis_client.setex(
                    backup_codes_key,
                    365 * 24 * 3600,  # Reset TTL
                    json.dumps(codes_info)
                )
                
                print(f"Backup code verified for login: user {user_id}")
                return True
                
        except Exception as e:
            print(f"Failed to verify backup code for login: {e}")
            
        return False

    async def verify_backup_code_for_password_reset(self, user_id: str, code: str) -> bool:
        """
        Verify and CONSUME backup code for password reset
        This is a one-time use for security
        """
        if not self.redis_client:
            return False

        try:
            import json
            backup_codes_key = f"backup_codes:{user_id}"
            codes_data = await self.redis_client.get(backup_codes_key)
            
            if not codes_data:
                return False

            codes_info = json.loads(codes_data)
            hashed_input = self._hash_code(code, user_id)
            
            if hashed_input in codes_info["codes"]:
                # CONSUME the code for password reset
                codes_info["codes"].remove(hashed_input)
                codes_info["usage_count"] += 1
                codes_info["last_used"] = datetime.utcnow().isoformat()
                
                await self.redis_client.setex(
                    backup_codes_key,
                    365 * 24 * 3600,  # Reset TTL
                    json.dumps(codes_info)
                )
                
                print(f"Backup code consumed for password reset: user {user_id}")
                return True
                
        except Exception as e:
            print(f"Failed to verify backup code for password reset: {e}")
            
        return False

    async def get_remaining_backup_codes_count(self, user_id: str) -> int:
        """Get count of remaining backup codes"""
        if not self.redis_client:
            return 0

        try:
            import json
            backup_codes_key = f"backup_codes:{user_id}"
            codes_data = await self.redis_client.get(backup_codes_key)
            
            if codes_data:
                codes_info = json.loads(codes_data)
                return len(codes_info["codes"])
                
        except Exception as e:
            print(f"Failed to get backup codes count: {e}")
            
        return 0

    async def regenerate_backup_codes(self, user_id: str, db: AsyncSession) -> List[str]:
        """
        Regenerate backup codes (emergency action)
        Use when user runs out of codes or suspects compromise
        """
        try:
            # Generate new codes
            new_codes = await self.generate_registration_backup_codes(user_id)
            
            # Store in database
            await self.store_backup_codes_in_database(user_id, db)
            
            print(f"Regenerated backup codes for user {user_id}")
            return new_codes
            
        except Exception as e:
            print(f"Failed to regenerate backup codes: {e}")
            return []


# Enhanced Registration Endpoint
async def enhanced_registration_endpoint(
    username: str,
    email: str,
    password: str,
    db: AsyncSession
) -> RegistrationWithBackupCodes:
    """
    Enhanced registration that includes backup code generation
    """
    
    # 1. Create user account (existing registration logic)
    from app.services.user_service import UserService
    from app.core.security import get_password_hash
    
    # Check if user exists
    existing_user = await UserService.get_by_username_or_email(db, username)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username or email already registered"
        )
    
    # Create user
    user_data = {
        "username": username,
        "email": email,
        "hashed_password": get_password_hash(password),
        "is_active": True,
        "is_verified": False
    }
    
    user = await UserService.create(db, user_data)
    
    # 2. Generate backup codes
    security_service = EnhancedSecurityCodesService()
    await security_service.initialize()
    
    backup_codes = await security_service.generate_registration_backup_codes(user.id)
    await security_service.store_backup_codes_in_database(user.id, db)
    
    # 3. Return registration response with backup codes
    return RegistrationWithBackupCodes(
        user_id=user.id,
        username=user.username,
        email=user.email,
        backup_codes=backup_codes,
        backup_codes_count=len(backup_codes),
        message=f"Registration successful! Save these {len(backup_codes)} backup codes safely. You can use them for emergency login or password reset."
    )


# Backup Code Login
async def backup_code_login(
    request: BackupCodeLoginRequest,
    db: AsyncSession
) -> Dict[str, Any]:
    """
    Login using backup code instead of password
    """
    from app.services.user_service import UserService
    from app.core.security import create_access_token
    
    # Find user
    user = await UserService.get_by_username_or_email(db, request.username_or_email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )
    
    # Verify backup code
    security_service = EnhancedSecurityCodesService()
    await security_service.initialize()
    
    is_valid = await security_service.verify_backup_code_for_login(user.id, request.backup_code)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid backup code"
        )
    
    # Generate access token
    access_token = create_access_token(data={"sub": user.username})
    
    remaining_codes = await security_service.get_remaining_backup_codes_count(user.id)
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user_id": user.id,
        "username": user.username,
        "remaining_backup_codes": remaining_codes,
        "message": "Login successful using backup code"
    }


# Backup Code Password Reset
async def backup_code_password_reset(
    request: BackupCodePasswordReset,
    db: AsyncSession
) -> Dict[str, Any]:
    """
    Reset password using backup code
    """
    from app.services.user_service import UserService
    from app.core.security import get_password_hash
    from sqlalchemy import update
    from app.db.models.user import User
    
    # Find user
    user = await UserService.get_by_username_or_email(db, request.username_or_email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Verify and consume backup code
    security_service = EnhancedSecurityCodesService()
    await security_service.initialize()
    
    is_valid = await security_service.verify_backup_code_for_password_reset(user.id, request.backup_code)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid backup code"
        )
    
    # Update password
    new_password_hash = get_password_hash(request.new_password)
    await db.execute(
        update(User)
        .where(User.id == user.id)
        .values(
            hashed_password=new_password_hash,
            password_changed_at=datetime.utcnow()
        )
    )
    await db.commit()
    
    remaining_codes = await security_service.get_remaining_backup_codes_count(user.id)
    
    return {
        "message": "Password reset successful using backup code",
        "user_id": user.id,
        "remaining_backup_codes": remaining_codes,
        "warning": "Backup code has been consumed. Consider regenerating codes if running low."
    }


# Test the enhanced system
async def test_enhanced_backup_codes():
    """Test the enhanced backup codes system"""
    print("🔄 Testing Enhanced Backup Codes System...")
    
    try:
        security_service = EnhancedSecurityCodesService()
        await security_service.initialize()
        
        user_id = "test_enhanced_user"
        
        # Test code generation
        codes = await security_service.generate_registration_backup_codes(user_id)
        print(f"  ✅ Generated {len(codes)} backup codes")
        print(f"  📝 Sample codes: {codes[:3]}")
        
        # Test login verification
        test_code = codes[0]
        login_valid = await security_service.verify_backup_code_for_login(user_id, test_code)
        print(f"  ✅ Login verification: {login_valid}")
        
        # Test password reset verification
        reset_code = codes[1]
        reset_valid = await security_service.verify_backup_code_for_password_reset(user_id, reset_code)
        print(f"  ✅ Password reset verification: {reset_valid}")
        
        # Check remaining codes
        remaining = await security_service.get_remaining_backup_codes_count(user_id)
        print(f"  ✅ Remaining codes after password reset: {remaining}")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Enhanced backup codes test failed: {e}")
        return False


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_enhanced_backup_codes()) 