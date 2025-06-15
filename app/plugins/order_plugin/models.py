"""
Order SQLAlchemy model
"""
from sqlalchemy import Column, Integer, String, Boolean, Float, Text, DateTime, Date, JSON
from datetime import datetime
from app.db.base import Base


class Order(Base):
    """SQLAlchemy model for Order"""
    __tablename__ = "orders"
    
    id = Column(Integer, primary_key=True, index=True)
    customer_name = Column(String(255), nullable=False)
    customer_email = Column(String(255), nullable=False)
    total_amount = Column(Float, nullable=False)
    status = Column(String(255), nullable=False)
    order_date = Column(DateTime, nullable=False)
    shipping_address = Column(String(255), nullable=False)
    notes = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    def __repr__(self):
        return f"<Order(id={self.id})>"
    
    def to_dict(self):
        """Convert model to dictionary"""
        return {
            'id': self.id,
            'customer_name': self.customer_name,
            'customer_email': self.customer_email,
            'total_amount': self.total_amount,
            'status': self.status,
            'order_date': self.order_date,
            'shipping_address': self.shipping_address,
            'notes': self.notes,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }
