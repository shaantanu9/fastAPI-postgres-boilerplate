"""
ShoppingCart SQLAlchemy model with enterprise authentication
"""
from sqlalchemy import Column, Integer, String, Boolean, Float, Text, DateTime, Date, JSON, Numeric, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime

from app.db.base import Base


class ShoppingCart(Base):
    """SQLAlchemy model for ShoppingCart with authentication features"""
    __tablename__ = "shopping_carts"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False)
    session_id = Column(String(255), nullable=False)
    status = Column(String(255), nullable=False)
    total_items = Column(Integer, default=0, nullable=False)
    total_price = Column(Float, default=0.0, nullable=False)
    currency = Column(String(255), default="USD", nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    coupon_code = Column(String(255), nullable=False)
    notes = Column(Text, nullable=False)
    is_guest = Column(Boolean, default=False, nullable=False)
    metadata = Column(JSON, nullable=False)
    # Audit fields
    created_ip = Column(String(45), nullable=True)  # IPv6 support
    updated_ip = Column(String(45), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    
    def __repr__(self):
        return f"<ShoppingCart(id={self.id})>"
    
    def to_dict(self):
        """Convert model to dictionary"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'session_id': self.session_id,
            'status': self.status,
            'total_items': self.total_items,
            'total_price': self.total_price,
            'currency': self.currency,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'expires_at': self.expires_at,
            'coupon_code': self.coupon_code,
            'notes': self.notes,
            'is_guest': self.is_guest,
            'metadata': self.metadata,
            'created_ip': self.created_ip,
            'updated_ip': self.updated_ip,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }

    
    def to_dict_secure(self, user_id: str = None, is_admin: bool = False) -> dict:
        """Convert to dictionary with security filtering"""
        data = self.to_dict()
        
        # Remove sensitive fields for non-owners/non-admins
        if not is_admin and hasattr(self, 'created_by_id') and self.created_by_id != user_id:
            # Remove audit fields for non-owners
            data.pop('created_ip', None)
            data.pop('updated_ip', None)
            
        return data
    
    def get_audit_trail(self) -> dict:
        """Get audit trail information"""
        trail = {
            'id': self.id,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }
        
        if hasattr(self, 'created_by_id'):
            trail.update({
                'created_by_id': self.created_by_id,
                'updated_by_id': self.updated_by_id,
                'created_ip': self.created_ip,
                'updated_ip': self.updated_ip
            })
            
        if hasattr(self, 'version'):
            trail.update({
                'version': self.version,
                'revision_notes': self.revision_notes
            })
            
        return trail
    
    @classmethod
    def get_resource_name(cls) -> str:
        """Get resource name for permission checks"""
        return "shoppingcart"
