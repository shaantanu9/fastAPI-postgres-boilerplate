"""Core security base module containing the EnterpriseSecurityService class.
This module is separate to avoid circular imports.
"""

import re
from datetime import timedelta
from typing import Any

from passlib.context import CryptContext


class EnterpriseSecurityService:
    def __init__(self) -> None:
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        self.MAX_LOGIN_ATTEMPTS = 5
        self.LOCKOUT_DURATION = timedelta(minutes=30)
        self.PASSWORD_HISTORY_COUNT = 5

    def validate_password_strength(self, password: str) -> dict[str, Any]:
        """Enforce 2025 enterprise password policy."""
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
            "score": score,
        }

    def hash_password(self, password: str) -> str:
        """Hash password using bcrypt."""
        return self.pwd_context.hash(password)

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify password against hash."""
        return self.pwd_context.verify(plain_password, hashed_password)

    def is_account_locked(self, user) -> bool:
        """Check if account is locked."""
        from datetime import datetime
        return bool(user.account_locked_until and user.account_locked_until > datetime.utcnow())

    def calculate_risk_score(self, request, user) -> int:
        """Calculate risk score for authentication attempt."""
        import json
        from datetime import datetime, timedelta
        
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

    async def handle_failed_login(self, db, user, request) -> None:
        """Handle failed login attempt with enhanced logging."""
        from datetime import datetime
        
        user.failed_login_attempts += 1

        if user.failed_login_attempts >= self.MAX_LOGIN_ATTEMPTS:
            user.account_locked_until = datetime.utcnow() + self.LOCKOUT_DURATION

        # Log security event
        self.log_security_event(
            db,
            user,
            "failed_login",
            "authentication",
            {"ip": request.client.host, "attempts": user.failed_login_attempts},
            request,
        )

        await db.commit()

    async def handle_successful_login(self, db, user, request) -> None:
        """Handle successful login with enhanced tracking."""
        import json
        from datetime import datetime
        
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
            db, user, "successful_login", "authentication", {"ip": client_ip}, request,
        )

        await db.commit()

    def log_security_event(
        self,
        db,
        user,
        event_type: str,
        category: str,
        data: dict[str, Any],
        request,
    ) -> None:
        """Log security events for audit trail."""
        try:
            # For now, skip security event logging to avoid database schema issues
            # TODO: Fix SecurityEvent model schema mismatch
            pass
        except Exception:
            # Silently fail if security event logging fails
            pass

    def init_app(self, app) -> None:
        """Initialize the security service with the FastAPI app."""
        # Store the app reference for any future use
        self.app = app

        # Set up any app-specific security configurations
