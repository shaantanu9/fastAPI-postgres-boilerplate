"""Database mixins for common model functionality.
Auto-generated to support enhanced scaffold tool.
"""

from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Integer
from sqlalchemy.sql import func


class TimestampMixin:
    """Mixin for automatic timestamp tracking.
    Adds created_at and updated_at fields to models.
    """

    created_at = Column(
        DateTime,
        default=func.now(),
        nullable=False,
        comment="Record creation timestamp",
    )
    updated_at = Column(
        DateTime,
        default=func.now(),
        onupdate=func.now(),
        nullable=False,
        comment="Record last update timestamp",
    )


class SoftDeleteMixin:
    """Mixin for soft delete functionality.
    Adds deleted_at and is_deleted fields to models.
    """

    deleted_at = Column(DateTime, nullable=True, comment="Soft delete timestamp")
    is_deleted = Column(
        Boolean, default=False, nullable=False, comment="Soft delete flag",
    )

    def soft_delete(self) -> None:
        """Mark the record as deleted."""
        self.is_deleted = True
        self.deleted_at = datetime.now()

    def restore(self) -> None:
        """Restore a soft deleted record."""
        self.is_deleted = False
        self.deleted_at = None


class AuditMixin:
    """Mixin for audit trail functionality.
    Tracks who created and last modified records.
    """

    created_by = Column(
        Integer, nullable=True, comment="User ID who created this record",
    )
    updated_by = Column(
        Integer, nullable=True, comment="User ID who last updated this record",
    )
