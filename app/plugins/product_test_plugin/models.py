"""ProductTest SQLAlchemy model."""

from datetime import datetime

from sqlalchemy import Column, DateTime, Index, Integer, Numeric, String

from app.db.base import Base


class ProductTest(Base):
    """SQLAlchemy model for ProductTest."""

    __tablename__ = "product_tests"

    __table_args__ = (Index("idx_name", "name", unique=True),)

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    category = Column(String(255), default="general", nullable=False)
    product_rating = Column(Numeric(5, 2), nullable=True, default=4.50)
    price = Column(Numeric(8, 4), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False,
    )

    def __repr__(self) -> str:
        return f"<ProductTest(id={self.id})>"

    def to_dict(self):
        """Convert model to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "category": self.category,
            "created_at": self.created_at,
            "product_rating": self.product_rating,
            "price": self.price,
            "updated_at": self.updated_at,
        }
