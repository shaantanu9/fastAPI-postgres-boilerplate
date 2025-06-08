"""
API Key SQLAlchemy model for database representation.
"""

import uuid
from datetime import datetime
from typing import Optional, List
from sqlalchemy import Column, String, DateTime, Boolean, ForeignKey, JSON, Text
from sqlalchemy.dialects.postgresql import UUID

from app.db.base import Base


class APIKey(Base):
    """
    API Key model for authentication and authorization.
    
    Stores hashed API keys (never raw keys) for secure machine-to-machine authentication.
    """
    __tablename__ = "api_keys"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False, index=True)
    key_hash = Column(String, nullable=False, unique=True, index=True)
    
    # Ownership and access control
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=True)
    
    # Key status
    is_active = Column(Boolean, default=True, nullable=False)
    is_revoked = Column(Boolean, default=False, nullable=False)
    
    # Access control
    scopes = Column(JSON, nullable=False, default=list)  # List of permission scopes
    
    # Metadata
    last_used_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)
    
    # Optional additional metadata
    meta_data = Column(JSON, nullable=True)
    description = Column(Text, nullable=True)
    
    def __repr__(self) -> str:
        return f"<APIKey id={self.id} name={self.name} user_id={self.user_id}>"
    
    @property
    def is_expired(self) -> bool:
        """Check if the API key is expired."""
        if self.expires_at is None:
            return False
        return datetime.utcnow() > self.expires_at
    
    @property
    def is_valid(self) -> bool:
        """Check if the API key is valid for use."""
        return self.is_active and not self.is_revoked and not self.is_expired
