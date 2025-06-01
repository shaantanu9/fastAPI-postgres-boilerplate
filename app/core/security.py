from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
import jwt
from jwt import PyJWTError
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel
from app.db.schemas.user import UserRead

from app.db.models.user import User
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session
from app.db.session import get_db
import os
import re
import secrets
import hashlib
import json
import pyotp
import qrcode
import base64
from io import BytesIO

# Settings
# Secret key and algorithm for JWT
from app.core.config import get_settings
SECRET_KEY = get_settings().jwt_secret_token  # Loaded from .env via Settings
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

# OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token")

# Pydantic models for token and user output
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None
    roles: Optional[list] = []

# JWT utils

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Generate a JWT access token using pyjwt.
    """
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    # pyjwt returns a string in v2+, bytes in v1. Ensure string output
    if isinstance(encoded_jwt, bytes):
        encoded_jwt = encoded_jwt.decode('utf-8')
    return encoded_jwt

async def get_current_user(token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)) -> User:
    # Import inside function to avoid circular import
    from app.services.user_service import UserService
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username, roles=payload.get("roles", []))
    except PyJWTError:
        raise credentials_exception
    user = await UserService.get_by_username_or_email(db, token_data.username)
    if not user:
        raise credentials_exception
    return UserRead.from_orm(user)

async def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

# Role/permission helpers

def has_role(user: User, role: str) -> bool:
    return role in getattr(user, "roles", [])

def require_role(role: str):
    def role_checker(user: User = Depends(get_current_active_user)):
        if not has_role(user, role):
            raise HTTPException(status_code=403, detail=f"User lacks required role: {role}")
        return user
    return role_checker

class EnterpriseSecurityService:
    def __init__(self):
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        self.MAX_LOGIN_ATTEMPTS = 5
        self.LOCKOUT_DURATION = timedelta(minutes=30)
        self.PASSWORD_HISTORY_COUNT = 5

    def validate_password_strength(self, password: str) -> Dict[str, Any]:
        """Enforce 2025 enterprise password policy"""
        errors = []
        score = 0

        # Length check (minimum 12 chars)
        if len(password) < 12:
            errors.append("Password must be at least 12 characters long")
        else:
            score += 1

        # Character variety checks
        if not re.search(r"[A-Z]", password):
            errors.append("Password must contain at least one uppercase letter")
        else:
            score += 1

        if not re.search(r"[a-z]", password):
            errors.append("Password must contain at least one lowercase letter")
        else:
            score += 1

        if not re.search(r"\d", password):
            errors.append("Password must contain at least one digit")
        else:
            score += 1

        if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
            errors.append("Password must contain at least one special character")
        else:
            score += 1

        # Advanced checks
        if len(set(password)) < len(password) * 0.6:
            errors.append("Password has too many repeated characters")
        else:
            score += 1

        # Common patterns
        common_patterns = [
            r"(\w)\1{2,}",  # Three or more repeated characters
            r"(012|123|234|345|456|567|678|789|890)",  # Sequential numbers
            r"(abc|bcd|cde|def|efg|fgh|ghi|hij|ijk|jkl|klm|lmn|mno|nop|opq|pqr|qrs|rst|stu|tuv|uvw|vwx|wxy|xyz)",  # Sequential letters
        ]

        for pattern in common_patterns:
            if re.search(pattern, password.lower()):
                errors.append("Password contains common patterns")
                break
        else:
            score += 1

        # Calculate strength
        if score >= 6:
            strength = "Strong"
        elif score >= 4:
            strength = "Medium"
        else:
            strength = "Weak"

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "strength": strength,
            "score": score
        }

    def hash_password(self, password: str) -> str:
        """Hash password using bcrypt"""
        return self.pwd_context.hash(password)

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify password against hash"""
        return self.pwd_context.verify(plain_password, hashed_password)

    def is_account_locked(self, user) -> bool:
        """Check if account is locked"""
        if user.account_locked_until and user.account_locked_until > datetime.utcnow():
            return True
        return False

    def calculate_risk_score(self, request: Request, user) -> int:
        """Calculate risk score for authentication attempt"""
        score = 0

        # IP-based risk
        client_ip = request.client.host
        ip_history = json.loads(user.login_ip_history or "[]")

        if client_ip not in ip_history:
            score += 30  # New IP

        # Time-based risk
        if user.last_login:
            time_since_last = datetime.utcnow() - user.last_login
            if time_since_last > timedelta(days=30):
                score += 20  # Long time since last login

        # Failed attempts
        score += user.failed_login_attempts * 10

        return min(score, 100)

    async def handle_failed_login(self, db: Session, user, request: Request):
        """Handle failed login attempt with enhanced logging"""
        user.failed_login_attempts += 1

        if user.failed_login_attempts >= self.MAX_LOGIN_ATTEMPTS:
            user.account_locked_until = datetime.utcnow() + self.LOCKOUT_DURATION

        # Log security event
        self.log_security_event(
            db, user, "failed_login", "authentication",
            {"ip": request.client.host, "attempts": user.failed_login_attempts},
            request
        )

        await db.commit()

    async def handle_successful_login(self, db: Session, user, request: Request):
        """Handle successful login with enhanced tracking"""
        # Reset failed attempts
        user.failed_login_attempts = 0
        user.account_locked_until = None
        user.last_login = datetime.utcnow()

        # Update IP history
        client_ip = request.client.host
        ip_history = json.loads(user.login_ip_history or "[]")

        if client_ip not in ip_history:
            ip_history.append(client_ip)
            # Keep only last 10 IPs
            if len(ip_history) > 10:
                ip_history = ip_history[-10:]
            user.login_ip_history = json.dumps(ip_history)

        # Log security event
        self.log_security_event(
            db, user, "successful_login", "authentication",
            {"ip": client_ip}, request
        )

        await db.commit()

    def log_security_event(self, db: Session, user, event_type: str,
                          category: str, data: Dict[str, Any], request: Request):
        """Log security events for audit trail"""
        from app.db.models.user import SecurityEvent

        event = SecurityEvent(
            user_id=user.id if user else None,
            event_type=event_type,
            event_category=category,
            event_data=json.dumps(data),
            ip_address=request.client.host,
            user_agent=request.headers.get("user-agent"),
            risk_score=self.calculate_risk_score(request, user) if user else 0
        )

        db.add(event)

    # MFA Methods (2025 Feature)
    def generate_mfa_secret(self) -> str:
        """Generate TOTP secret for MFA"""
        return pyotp.random_base32()

    def generate_mfa_qr_code(self, user_email: str, secret: str,
                            app_name: str = "FastAPI App") -> str:
        """Generate QR code for MFA setup"""
        totp_uri = pyotp.totp.TOTP(secret).provisioning_uri(
            name=user_email,
            issuer_name=app_name
        )

        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(totp_uri)
        qr.make(fit=True)

        img = qr.make_image(fill_color="black", back_color="white")
        buf = BytesIO()
        img.save(buf, format='PNG')
        buf.seek(0)

        return base64.b64encode(buf.getvalue()).decode()

    def verify_mfa_token(self, secret: str, token: str) -> bool:
        """Verify TOTP token"""
        totp = pyotp.TOTP(secret)
        return totp.verify(token, valid_window=1)

    def generate_backup_codes(self, count: int = 10) -> List[str]:
        """Generate backup codes for MFA"""
        return [secrets.token_hex(4).upper() for _ in range(count)]

# Initialize service
security_service = EnterpriseSecurityService()

