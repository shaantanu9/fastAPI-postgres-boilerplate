"""
Customer SQLAlchemy model
"""
from sqlalchemy import Column, Integer, String, Boolean, Float, Text, DateTime, Date, JSON
from datetime import datetime

# Base import - this will be configured based on the project structure
try:
    from app.db.base import Base
except ImportError:
    # Fallback for standalone testing
    from sqlalchemy.ext.declarative import declarative_base
    Base = declarative_base()


class Customer(Base):
    """SQLAlchemy model for Customer"""
    __tablename__ = "customers"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False)
    phone = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    def __repr__(self):
        return f"<Customer(id={self.id})>"
    
    def to_dict(self):
        """Convert model to dictionary"""
        return {
            'id': self.id,
            'name': self.name,
            'email': self.email,
            'phone': self.phone,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }
