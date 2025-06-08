"""SQLAlchemy models template generator."""

import re
from typing import Any


class ModelsTemplate:
    """Generates SQLAlchemy model templates."""

    def generate(
        self, model_name: str, fields: list[dict[str, Any]], field_validator,
    ) -> str:
        """Generate SQLAlchemy model file content."""
        snake_name = re.sub(r"(?<!^)(?=[A-Z])", "_", model_name).lower()
        pascal_name = model_name

        # Generate field definitions
        sqlalchemy_fields = []
        for field in fields:
            field_def = field_validator.get_sqlalchemy_column(field)
            sqlalchemy_fields.append(field_def)

        sqlalchemy_fields_str = "\n".join(sqlalchemy_fields)

        return f'''"""
{pascal_name} SQLAlchemy model
"""
from sqlalchemy import Column, Integer, String, Boolean, Float, Text, DateTime, Date, JSON
from datetime import datetime
from app.db.base import Base


class {pascal_name}(Base):
    """SQLAlchemy model for {pascal_name}"""
    __tablename__ = "{snake_name}s"

    id = Column(Integer, primary_key=True, index=True)
{sqlalchemy_fields_str}
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<{pascal_name}(id={{self.id}})>"

    def to_dict(self):
        """Convert model to dictionary"""
        return {{
            'id': self.id,
            {self._generate_dict_fields(fields)},
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }}
'''


    def _generate_dict_fields(self, fields: list[dict[str, Any]]) -> str:
        """Generate dictionary fields for to_dict method."""
        dict_fields = []
        for field in fields:
            field_name = field["name"]
            dict_fields.append(f"'{field_name}': self.{field_name}")

        return ",\n            ".join(dict_fields)
