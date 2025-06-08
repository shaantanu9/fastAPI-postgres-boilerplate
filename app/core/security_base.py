"""
Core security base module containing the EnterpriseSecurityService class.
This module is separate to avoid circular imports.
"""

from datetime import datetime, timedelta
from typing import Dict, Any
from passlib.context import CryptContext
import re

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
    
    def init_app(self, app):
        """Initialize the security service with the FastAPI app"""
        # Store the app reference for any future use
        self.app = app
        
        # Set up any app-specific security configurations
        print("🔒 Enterprise Security Service initialized with app")
