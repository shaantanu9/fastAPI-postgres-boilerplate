import secrets
from datetime import datetime, timedelta
from typing import Any

import jwt
import redis
from fastapi import HTTPException, status

from app.core.config import get_settings


class EnhancedJWTService:
    def __init__(self) -> None:
        settings = get_settings()
        self.SECRET_KEY = settings.jwt_secret_token  # Use environment variable
        self.ALGORITHM = "HS256"
        self.ACCESS_TOKEN_EXPIRE_MINUTES = 15  # Short-lived tokens
        self.REFRESH_TOKEN_EXPIRE_DAYS = 30

        # Redis for token blacklisting (optional, fallback without Redis)
        try:
            self.redis_client = redis.Redis(
                host="localhost", port=6379, db=0, decode_responses=True,
            )
            # Test connection
            self.redis_client.ping()
            self.redis_available = True
        except Exception:
            # Redis not available, tokens won't be blacklisted
            self.redis_client = None
            self.redis_available = False

    def create_access_token(
        self, data: dict[str, Any], expires_delta: timedelta | None = None,
    ) -> str:
        """Create enhanced JWT access token with 2025 standards."""
        to_encode = data.copy()

        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(
                minutes=self.ACCESS_TOKEN_EXPIRE_MINUTES,
            )

        # Enhanced claims (2025 standards)
        jti = secrets.token_urlsafe(32)  # JWT ID for blacklisting
        to_encode.update(
            {
                "exp": expire,
                "iat": datetime.utcnow(),
                "nbf": datetime.utcnow(),  # Not before
                "type": "access",
                "jti": jti,  # JWT ID for revocation
                "aud": "api",  # Audience
                "iss": "fastapi-app",  # Issuer
                "scope": data.get("scopes", []),  # OAuth2 scopes
            },
        )

        return jwt.encode(to_encode, self.SECRET_KEY, algorithm=self.ALGORITHM)

    def create_refresh_token(self, user_id: str, session_id: str) -> str:
        """Create refresh token."""
        to_encode = {
            "sub": user_id,
            "session_id": session_id,
            "exp": datetime.utcnow() + timedelta(days=self.REFRESH_TOKEN_EXPIRE_DAYS),
            "iat": datetime.utcnow(),
            "type": "refresh",
            "jti": secrets.token_urlsafe(32),
        }

        return jwt.encode(to_encode, self.SECRET_KEY, algorithm=self.ALGORITHM)

    def verify_token(self, token: str, token_type: str = "access") -> dict[str, Any]:
        """Verify JWT token with blacklist check."""
        try:
            # Decode with audience verification if it's an access token
            if token_type == "access":
                payload = jwt.decode(
                    token,
                    self.SECRET_KEY,
                    algorithms=[self.ALGORITHM],
                    audience="api",  # Verify the audience claim
                    issuer="fastapi-app",  # Verify the issuer claim
                )
            else:
                # For refresh tokens, don't require audience/issuer
                payload = jwt.decode(
                    token, self.SECRET_KEY, algorithms=[self.ALGORITHM],
                )

            # Check token type
            if payload.get("type") != token_type:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token type",
                )

            # Check if token is blacklisted
            jti = payload.get("jti")
            if jti and self.is_token_blacklisted(jti):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token has been revoked",
                )

            return payload

        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired",
            )
        except jwt.InvalidAudienceError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token audience",
            )
        except jwt.InvalidIssuerError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token issuer",
            )
        except jwt.InvalidTokenError:  # Fixed: was jwt.JWTError
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token",
            )
        except Exception as e:
            # Catch any other JWT-related errors
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Token validation failed: {e!s}",
            )

    def blacklist_token(self, jti: str, expires_at: datetime) -> None:
        """Add token to blacklist."""
        if not self.redis_available:
            # If Redis is not available, we can't blacklist tokens
            # In production, consider using database fallback
            return

        try:
            # Calculate TTL for Redis
            ttl = int((expires_at - datetime.utcnow()).total_seconds())
            if ttl > 0:
                self.redis_client.setex(f"blacklist:{jti}", ttl, "1")
        except Exception:
            # If Redis operation fails, log the error
            # In production, you might want to use a database fallback
            pass

    def is_token_blacklisted(self, jti: str) -> bool:
        """Check if token is blacklisted."""
        if not self.redis_available:
            # If Redis is not available, assume token is not blacklisted
            # In production, you might want to use a database fallback
            return False

        try:
            return bool(self.redis_client.exists(f"blacklist:{jti}"))
        except Exception:
            # If Redis is not available, assume token is not blacklisted
            # In production, you might want to use a database fallback
            return False


jwt_service = EnhancedJWTService()
