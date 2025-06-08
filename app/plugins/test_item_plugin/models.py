"""TestItem SQLAlchemy model."""

from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String, Text

from app.db.base import Base


class TestItem(Base):
    """SQLAlchemy model for TestItem."""

    __tablename__ = "test_items"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    priority = Column(Integer, nullable=True, default=1)
    item_status = Column(String(255), nullable=True, default="active")
    rating = Column(Integer, nullable=True, default=0)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False,
    )

    # TODO: Create index on item_status, priority (UNIQUE)
    def __repr__(self) -> str:
        return f"<TestItem(id={self.id})>"

    def to_dict(self):
        """Convert model to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "created_at": self.created_at,
            "priority": self.priority,
            "item_status": self.item_status,
            "rating": self.rating,
            "updated_at": self.updated_at,
        }
