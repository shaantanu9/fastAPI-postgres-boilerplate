"""
Book SQLAlchemy model
"""
from sqlalchemy import Column, Integer, String, Boolean, Float, Text, DateTime, Date, JSON
from datetime import datetime
from app.db.base import Base


class Book(Base):
    """SQLAlchemy model for Book"""
    __tablename__ = "books"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    author = Column(String(255), nullable=False)
    isbn = Column(String(255), nullable=False)
    pages = Column(Integer, nullable=False)
    published_date = Column(Date, nullable=False)
    price = Column(Float, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    def __repr__(self):
        return f"<Book(id={self.id})>"
    
    def to_dict(self):
        """Convert model to dictionary"""
        return {
            'id': self.id,
            'title': self.title,
            'author': self.author,
            'isbn': self.isbn,
            'pages': self.pages,
            'published_date': self.published_date,
            'price': self.price,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }
