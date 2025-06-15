"""
Product SQLAlchemy model
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


class Product(Base):
    """SQLAlchemy model for Product"""
    __tablename__ = "products"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    price = Column(Float, nullable=False)
    category = Column(String(255), nullable=False)
    description = Column(String(255), nullable=True)
    stock = Column(Integer, nullable=False)
    is_active = Column(Boolean, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    def __repr__(self):
        return f"<Product(id={self.id})>"
    
    def to_dict(self):
        """Convert model to dictionary"""
        return {
            'id': self.id,
            'name': self.name,
            'price': self.price,
            'category': self.category,
            'description': self.description,
            'stock': self.stock,
            'is_active': self.is_active,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }
