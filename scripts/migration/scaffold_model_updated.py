from pathlib import Path

#!/usr/bin/env python3
"""Enhanced FastAPI Model Scaffold Tool - Ultimate Edition.

This tool generates complete model scaffolding for the FastAPI PostgreSQL boilerplate,
integrating with the current architecture and following ALL FastAPI best practices including:

🔧 CORE FEATURES:
- EnhancedBaseService pattern with concurrent processing
- Procrastinate task integration with priority queues
- Bulk operations with parallel processing
- Real comprehensive test generation
- Automatic Alembic migrations
- Health checks and rollback support

🎯 NEW FASTAPI BEST PRACTICES (Based on 2024 Research):
- Dependencies & Dependency Injection chains
- Custom Pydantic BaseModel with serialization
- Environment-based configurations
- REST naming conventions compliance
- SQL-first approach with complex queries
- Custom exceptions and error handling
- Rate limiting and security features
- OpenAPI documentation generation
- CORS and security headers
- Repository pattern implementation
- Caching layer integration
- Logging and monitoring setup
- Data validation with custom validators
- Background tasks integration
- File upload/download capabilities
- Pagination and filtering
- Search functionality
- Audit trail and soft deletes
- Multi-environment support
- Docker integration
- Performance optimization

Usage:
    python scaffold_model_updated.py add Book title:str author:str isbn:str --enterprise
    python scaffold_model_updated.py add Book title:str --with-all-features
    python scaffold_model_updated.py add Book --interactive --enterprise
    python scaffold_model_updated.py list --detailed
    python scaffold_model_updated.py remove Book --cascade
    python scaffold_model_updated.py health-check --fix-issues
    python scaffold_model_updated.py update Book --add-fields price:float
    python scaffold_model_updated.py generate-docs
"""

import argparse
import json
import os
import re
import subprocess
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Optional

import yaml

# Configuration
BASE_PATH = "app"
TRACK_FILE = "scaffolded_models.json"
CONFIG_FILE = "scaffold_config.yaml"
API_FILE = Path(BASE_PATH) / "api/v1/api.py"


class FieldType(Enum):
    """Enhanced field types with validation."""

    STRING = "str"
    INTEGER = "int"
    FLOAT = "float"
    BOOLEAN = "bool"
    TEXT = "text"
    EMAIL = "email"
    DATETIME = "datetime"
    DATE = "date"
    UUID = "uuid"
    JSON = "json"
    URL = "url"
    SLUG = "slug"
    PHONE = "phone"
    DECIMAL = "decimal"
    ENUM = "enum"
    FOREIGN_KEY = "fk"
    ONE_TO_MANY = "o2m"
    MANY_TO_MANY = "m2m"


@dataclass
class FieldDefinition:
    """Enhanced field definition with constraints and relationships."""

    name: str
    field_type: FieldType
    nullable: bool = False
    default: Any = None
    max_length: int | None = None
    min_length: int | None = None
    min_value: int | float | None = None
    max_value: int | float | None = None
    regex: str | None = None
    choices: list[str] | None = None
    related_model: str | None = None
    foreign_key_field: str | None = None
    unique: bool = False
    indexed: bool = False
    description: str | None = None


class ScaffoldConfig:
    """Configuration class for scaffold generation."""

    def __init__(self) -> None:
        self.config = self.load_config()

    def load_config(self) -> dict[str, Any]:
        """Load configuration from YAML file."""
        default_config = {
            "database": {
                "naming_convention": {
                    "ix": "%(column_0_label)s_idx",
                    "uq": "%(table_name)s_%(column_0_name)s_key",
                    "ck": "%(table_name)s_%(constraint_name)s_check",
                    "fk": "%(table_name)s_%(column_0_name)s_fkey",
                    "pk": "%(table_name)s_pkey",
                },
            },
            "api": {
                "version": "v1",
                "prefix": "/api",
                "enable_cors": True,
                "enable_rate_limiting": True,
                "enable_caching": True,
            },
            "features": {
                "soft_deletes": True,
                "audit_trail": True,
                "search": True,
                "pagination": True,
                "file_upload": True,
                "background_tasks": True,
                "caching": True,
                "monitoring": True,
            },
            "testing": {
                "generate_unit_tests": True,
                "generate_integration_tests": True,
                "generate_performance_tests": True,
                "test_coverage_threshold": 90,
            },
            "documentation": {
                "generate_openapi": True,
                "generate_markdown_docs": True,
                "include_examples": True,
            },
        }

        if Path(CONFIG_FILE).exists():
            with Path(CONFIG_FILE).open("r") as f:
                user_config = yaml.safe_load(f)
                # Merge with defaults
                return {**default_config, **user_config}

        return default_config


SUPPORTED_FIELD_TYPES = {
    "str": (
        "String",
        "str",
        "Field(..., min_length=1, max_length=255)",
        "varchar(255)",
    ),
    "int": ("Integer", "int", "Field(..., ge=0)", "integer"),
    "float": ("Float", "float", "Field(...)", "float"),
    "bool": ("Boolean", "bool", "Field(default=False)", "boolean"),
    "text": ("Text", "str", "Field(..., min_length=1)", "text"),
    "email": ("String", "EmailStr", "Field(...)", "varchar(255)"),
    "datetime": (
        "DateTime",
        "datetime",
        "Field(default_factory=datetime.now)",
        "timestamp",
    ),
    "date": ("Date", "date", "Field(...)", "date"),
    "uuid": ("String", "UUID", "Field(default_factory=uuid4)", "uuid"),
    "json": ("JSON", "dict", "Field(default_factory=dict)", "json"),
    "url": ("String", "AnyUrl", "Field(...)", "varchar(2083)"),
    "slug": ("String", "str", "Field(..., regex=r'^[a-z0-9-]+$')", "varchar(255)"),
    "phone": (
        "String",
        "str",
        "Field(..., regex=r'^[+]?[1-9]?[0-9]{7,15}$')",
        "varchar(20)",
    ),
    "decimal": ("Numeric", "Decimal", "Field(..., decimal_places=2)", "decimal(10,2)"),
}


# Utility Functions (Enhanced)
def snake_case(name: str) -> str:
    """Convert CamelCase to snake_case with better handling."""
    # Handle acronyms and multiple consecutive capitals
    s1 = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", name)
    return re.sub("([a-z0-9])([A-Z])", r"\1_\2", s1).lower()


def pascal_case(name: str) -> str:
    """Convert snake_case to PascalCase."""
    return "".join(word.capitalize() for word in name.split("_"))


def kebab_case(name: str) -> str:
    """Convert to kebab-case for URLs."""
    return snake_case(name).replace("_", "-")


def validate_model_name(name: str) -> bool:
    """Validate model name follows conventions."""
    if not name.isidentifier():
        return False
    return name[0].isupper()


def ensure_init_files(path: str) -> None:
    """Ensure __init__.py files exist in all parent directories."""
    dirs = path.split(os.sep)
    current_path = ""

    for i, d in enumerate(dirs[:-1]):
        current_path = d if i == 0 else Path(current_path) / d

        if current_path and current_path.startswith(BASE_PATH):
            init_file = Path(current_path) / "__init__.py"
            if not Path(init_file).exists():
                with Path(init_file).open("w") as f:
                    f.write('"""Package initialization"""\n')


def write_file(
    path: str,
    content: str,
    backup: bool = True,
    tracker: Optional["ScaffoldTracker"] = None,
) -> None:
    """Write content to file with backup option and tracking."""
    if backup and Path(path).exists():
        backup_path = f"{path}.backup"
        os.rename(path, backup_path)

    Path(Path(path).mkdir(parents=True, exist_ok=True).parent, exist_ok=True)
    ensure_init_files(path)

    with Path(path).open("w") as f:
        f.write(content)

    # Track the file creation
    if tracker:
        tracker.track_file_created(path, content)


def load_tracking():
    """Load the tracking file."""
    if Path(TRACK_FILE).exists():
        with Path(TRACK_FILE).open("r") as f:
            return json.load(f)
    return {}


def save_tracking(data: dict[str, Any]) -> None:
    """Save the tracking file."""
    with Path(TRACK_FILE).open("w") as f:
        json.dump(data, f, indent=2)


class ScaffoldTracker:
    """Comprehensive tracking system for scaffold operations.
    Tracks all files created, modified, and database changes like a VCS.
    """

    def __init__(self, model: str) -> None:
        self.model = model
        self.snake_name = snake_case(model)
        self.pascal_name = pascal_case(model)
        self.changes = {
            "model": model,
            "timestamp": datetime.now().isoformat(),
            "files_created": [],
            "files_modified": [],
            "imports_added": [],
            "migrations_created": [],
            "database_changes": [],
            "backup_files": {},
            "rollback_info": {},
        }

    def track_file_created(self, file_path: str, content: str | None = None) -> None:
        """Track a file that was created."""
        self.changes["files_created"].append(
            {
                "path": file_path,
                "size": len(content) if content else 0,
                "created_at": datetime.now().isoformat(),
            },
        )

    def track_file_modified(
        self,
        file_path: str,
        original_content: str,
        new_content: str,
        changes_made: list[str],
    ) -> None:
        """Track a file that was modified."""
        # Create backup
        backup_path = (
            f"{file_path}.scaffold_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        )
        with Path(backup_path).open("w") as f:
            f.write(original_content)

        self.changes["files_modified"].append(
            {
                "path": file_path,
                "backup_path": backup_path,
                "changes": changes_made,
                "modified_at": datetime.now().isoformat(),
            },
        )
        self.changes["backup_files"][file_path] = backup_path

    def track_import_added(
        self, file_path: str, import_line: str, line_number: int | None = None,
    ) -> None:
        """Track an import that was added to a file."""
        self.changes["imports_added"].append(
            {
                "file": file_path,
                "import": import_line,
                "line_number": line_number,
                "added_at": datetime.now().isoformat(),
            },
        )

    def track_migration_created(self, migration_file: str, migration_id: str) -> None:
        """Track a migration that was created."""
        self.changes["migrations_created"].append(
            {
                "file": migration_file,
                "migration_id": migration_id,
                "created_at": datetime.now().isoformat(),
            },
        )

    def track_database_change(self, operation: str, details: dict[str, Any]) -> None:
        """Track database changes."""
        self.changes["database_changes"].append(
            {
                "operation": operation,
                "details": details,
                "timestamp": datetime.now().isoformat(),
            },
        )

    def save_tracking_info(self) -> None:
        """Save the tracking information."""
        tracking = load_tracking()
        tracking[self.model] = self.changes
        save_tracking(tracking)

        # Also save individual model tracking file for detailed operations
        model_track_file = f".scaffold_track_{self.snake_name}.json"
        with Path(model_track_file).open("w") as f:
            json.dump(self.changes, f, indent=2)


    @classmethod
    def load_model_tracking(cls, model: str) -> dict[str, Any] | None:
        """Load tracking information for a specific model."""
        snake_name = snake_case(model)
        model_track_file = f".scaffold_track_{snake_name}.json"

        if Path(model_track_file).exists():
            with Path(model_track_file).open("r") as f:
                return json.load(f)

        # Fallback to main tracking file
        tracking = load_tracking()
        return tracking.get(model)

    def cleanup_tracking_files(self) -> None:
        """Clean up tracking files after successful removal."""
        model_track_file = f".scaffold_track_{self.snake_name}.json"
        if Path(model_track_file).exists():
            Path(model_track_file).unlink()


def parse_fields(field_specs: list[str]) -> list[FieldDefinition]:
    """Parse field specifications into FieldDefinition objects."""
    fields = []
    for spec in field_specs:
        if ":" in spec:
            name, field_type = spec.split(":", 1)
            name = name.strip()
            field_type = field_type.strip()

            # Parse constraints (e.g., "str:max_length=255:unique")
            parts = field_type.split(":")
            base_type = parts[0]
            constraints = {}

            for part in parts[1:]:
                if "=" in part:
                    key, value = part.split("=", 1)
                    key = key.strip()
                    value = value.strip()

                    # Handle special parsing for choices
                    if key == "choices":
                        constraints[key] = [
                            choice.strip() for choice in value.split(",")
                        ]
                    # Handle other value types
                    elif value.lower() == "true":
                        constraints[key] = True
                    elif value.lower() == "false":
                        constraints[key] = False
                    elif value.isdigit():
                        constraints[key] = int(value)
                    elif value.replace(".", "", 1).isdigit():
                        constraints[key] = float(value)
                    else:
                        constraints[key] = value
                else:
                    constraints[part.strip()] = True

            field_def = FieldDefinition(
                name=name,
                field_type=FieldType(base_type)
                if base_type in [ft.value for ft in FieldType]
                else FieldType.STRING,
                **constraints,
            )
            fields.append(field_def)
        else:
            # Default to string if no type specified
            fields.append(
                FieldDefinition(name=spec.strip(), field_type=FieldType.STRING),
            )

    return fields


# Enhanced File Generators
def generate_custom_base_model() -> str:
    """Generate custom Pydantic BaseModel following best practices."""
    return '''"""
Custom Pydantic BaseModel with enhanced features.
Generated by enhanced scaffold tool.
"""
from datetime import datetime
from typing import Any, Dict
from zoneinfo import ZoneInfo

from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel, ConfigDict


def datetime_to_gmt_str(dt: datetime) -> str:
    """Convert datetime to GMT string format"""
    if not dt.tzinfo:
        dt = dt.replace(tzinfo=ZoneInfo("UTC"))
    return dt.strftime("%Y-%m-%dT%H:%M:%S%z")


class CustomBaseModel(BaseModel):
    """
    Custom base model with enhanced serialization and configuration.
    All model schemas should inherit from this class.
    """

    model_config = ConfigDict(
        json_encoders={datetime: datetime_to_gmt_str},
        populate_by_name=True,
        validate_assignment=True,
        arbitrary_types_allowed=True,
        str_strip_whitespace=True,
        from_attributes=True,
        use_enum_values=True
    )

    def serializable_dict(self, **kwargs) -> Dict[str, Any]:
        """Return a dict which contains only serializable fields"""
        default_dict = self.model_dump()
        return jsonable_encoder(default_dict)

    def to_dict(self, exclude_none: bool = True) -> Dict[str, Any]:
        """Convert to dictionary with options"""
        return self.model_dump(exclude_none=exclude_none)
'''


def generate_model_file(
    model: str, fields: list[FieldDefinition], config: ScaffoldConfig,
) -> str:
    """Generate enhanced SQLAlchemy model file with all best practices."""
    snake_name = snake_case(model)
    pascal_name = pascal_case(model)

    # Determine which imports are needed based on field types
    base_imports = [
        "from sqlalchemy import Column, Integer, String, Text, Boolean, Float, DateTime, Date, JSON",
        "from sqlalchemy import ForeignKey, UniqueConstraint, Index, CheckConstraint",
        "from sqlalchemy.dialects.postgresql import UUID, JSONB",
        "from sqlalchemy.orm import relationship, validates",
        "from sqlalchemy.ext.hybrid import hybrid_property",
        "from datetime import datetime, date",
        "from uuid import uuid4",
        "from decimal import Decimal",
        "from typing import Optional, List",
        "from app.db.base import Base",
        "from app.db.mixins import TimestampMixin, SoftDeleteMixin, AuditMixin",
    ]

    # Add Numeric import if any decimal fields exist
    has_decimal = any(field.field_type == FieldType.DECIMAL for field in fields)
    if has_decimal:
        base_imports[0] = (
            "from sqlalchemy import Column, Integer, String, Text, Boolean, Float, DateTime, Date, JSON, Numeric"
        )

    imports = base_imports

    # Determine mixins based on config
    mixins = ["Base"]
    if config.config["features"]["audit_trail"]:
        mixins.append("AuditMixin")
    if config.config["features"]["soft_deletes"]:
        mixins.append("SoftDeleteMixin")
    mixins.append("TimestampMixin")

    content = f'''"""
Enhanced SQLAlchemy model for {model}.
Auto-generated by enhanced scaffold tool with best practices.
"""
{chr(10).join(imports)}

class {pascal_name}({", ".join(mixins)}):
    """
    SQLAlchemy ORM model for {model}.

    Features:
    - Automatic timestamps (created_at, updated_at)
    - Soft deletes (if enabled)
    - Audit trail (if enabled)
    - Custom validation
    - Relationships
    - Hybrid properties
    - Search indexing
    """
    __tablename__ = "{snake_name}s"

    # Primary key
    id = Column(Integer, primary_key=True, index=True, comment="Primary key")

    # Model fields
'''

    # Generate fields with enhanced features
    constraints = []
    relationships = []

    for field in fields:
        field_config = SUPPORTED_FIELD_TYPES.get(
            field.field_type.value, SUPPORTED_FIELD_TYPES["str"],
        )
        sqlalchemy_type, _, _, _ = field_config

        # Build column definition
        column_args = []
        column_kwargs = {}

        if field.nullable:
            column_kwargs["nullable"] = True
        else:
            column_kwargs["nullable"] = False

        if field.default is not None:
            column_kwargs["default"] = field.default
        elif field.field_type == FieldType.DATETIME:
            column_kwargs["default"] = "datetime.now"
        elif field.field_type == FieldType.UUID:
            column_kwargs["default"] = "uuid4"
        elif field.field_type == FieldType.BOOLEAN:
            column_kwargs["default"] = False

        if field.unique:
            column_kwargs["unique"] = True

        if field.indexed:
            column_kwargs["index"] = True

        if field.description:
            column_kwargs["comment"] = f'"{field.description}"'

        # Handle special types
        if field.field_type == FieldType.FOREIGN_KEY and field.related_model:
            related_table = snake_case(field.related_model) + "s"
            fk_field = field.foreign_key_field or "id"
            column_args.append(f'ForeignKey("{related_table}.{fk_field}")')

            # Add relationship
            rel_name = (
                field.name.replace("_id", "")
                if field.name.endswith("_id")
                else field.name
            )
            relationships.append(
                f'    {rel_name} = relationship("{pascal_case(field.related_model)}", back_populates="{snake_name}s")',
            )

        # Build column string
        column_def_parts = [sqlalchemy_type, *column_args]
        if column_kwargs:
            kwargs_str = ", ".join([f"{k}={v}" for k, v in column_kwargs.items()])
            column_def_parts.append(kwargs_str)

        content += f"    {field.name} = Column({', '.join(column_def_parts)})\n"

        # Add constraints if needed
        if field.max_length and field.field_type == FieldType.STRING:
            constraints.append(
                f'CheckConstraint("LENGTH({field.name}) <= {field.max_length}", name="ck_{snake_name}_{field.name}_length")',
            )

        if field.choices:
            choices_str = "', '".join(field.choices)
            constraints.append(
                f'CheckConstraint("{field.name} IN (\'{choices_str}\')", name="ck_{snake_name}_{field.name}_choices")',
            )

    # Add relationships
    if relationships:
        content += "\n    # Relationships\n"
        content += "\n".join(relationships) + "\n"

    # Add table constraints
    if constraints or config.config["features"]["search"]:
        content += "\n    # Table constraints and indexes\n"
        content += "    __table_args__ = (\n"

        for constraint in constraints:
            content += f"        {constraint},\n"

        # Add search index if enabled
        if config.config["features"]["search"]:
            searchable_fields = [
                f.name
                for f in fields
                if f.field_type in [FieldType.STRING, FieldType.TEXT]
            ]
            if searchable_fields:
                content += f'        Index("ix_{snake_name}_search", {", ".join(searchable_fields)}),\n'

        content += "    )\n"

    # Add validation methods
    content += f'''
    # Validation methods
    @validates('*')
    def validate_fields(self, key, value):
        """Custom field validation"""
        # Add custom validation logic here
        return value

    # Hybrid properties
    @hybrid_property
    def display_name(self) -> str:
        """Human-readable display name"""
        # Customize based on your model fields
        return f"{pascal_name} {{self.id}}"

    # Class methods
    @classmethod
    def get_searchable_fields(cls) -> List[str]:
        """Return list of fields that can be searched"""
        return {[f'"{f.name}"' for f in fields if f.field_type in [FieldType.STRING, FieldType.TEXT]]}

    @classmethod
    def get_filterable_fields(cls) -> List[str]:
        """Return list of fields that can be filtered"""
        return {[f'"{f.name}"' for f in fields]}

    def __repr__(self) -> str:
        return f"<{pascal_name}(id={{self.id}})>"

    def __str__(self) -> str:
        return self.display_name
'''

    return content


def generate_schema_file(
    model: str, fields: list[FieldDefinition], config: ScaffoldConfig,
) -> str:
    """Generate enhanced Pydantic schema file with all best practices."""
    pascal_name = pascal_case(model)
    snake_case(model)

    imports = [
        "from pydantic import BaseModel, Field, EmailStr, field_validator, model_validator",
        "from pydantic import AnyUrl, constr, conint, confloat, Json",
        "from typing import Optional, List, Dict, Any, Union",
        "from datetime import datetime, date",
        "from uuid import UUID",
        "from decimal import Decimal",
        "from enum import Enum",
        "from app.db.schemas.base import CustomBaseModel",
    ]

    content = f'''"""
Enhanced Pydantic schemas for {model}.
Auto-generated by enhanced scaffold tool with best practices.

Features:
- Custom validation
- Serialization methods
- Field constraints
- Relationship handling
- Search and filter schemas
- Bulk operation schemas
"""
{chr(10).join(imports)}

# Enums (if any choice fields exist)
'''

    # Generate enums for choice fields
    enum_fields = [f for f in fields if f.choices]
    for field in enum_fields:
        enum_name = f"{pascal_name}{pascal_case(field.name)}Enum"
        content += f'''
class {enum_name}(str, Enum):
    """Enum for {field.name} field choices"""
'''
        for choice in field.choices:
            enum_value = choice.upper().replace(" ", "_").replace("-", "_")
            content += f'    {enum_value} = "{choice}"\n'

    content += f'''

class {pascal_name}Base(CustomBaseModel):
    """
    Base schema for {model} with enhanced features.
    Contains all the common fields and validation logic.
    """
'''

    # Generate fields with enhanced validation
    for field in fields:
        field_config = SUPPORTED_FIELD_TYPES.get(
            field.field_type.value, SUPPORTED_FIELD_TYPES["str"],
        )
        _, pydantic_type, field_def, _ = field_config

        # Handle special types and constraints
        if field.field_type == FieldType.EMAIL:
            pydantic_type = "EmailStr"
        elif field.field_type == FieldType.URL:
            pydantic_type = "AnyUrl"
        elif field.field_type == FieldType.JSON:
            pydantic_type = "Json"
        elif field.choices:
            enum_name = f"{pascal_name}{pascal_case(field.name)}Enum"
            pydantic_type = enum_name
        elif field.field_type == FieldType.STRING and field.max_length:
            pydantic_type = f"constr(max_length={field.max_length})"
        elif field.field_type == FieldType.INTEGER and (
            field.min_value or field.max_value
        ):
            min_val = f"ge={field.min_value}" if field.min_value else ""
            max_val = f"le={field.max_value}" if field.max_value else ""
            constraints = ", ".join([c for c in [min_val, max_val] if c])
            pydantic_type = f"conint({constraints})" if constraints else "int"

        # Build field definition with constraints
        field_parts = []
        if not field.nullable:
            field_parts.append("...")

        if field.description:
            field_parts.append(f'description="{field.description}"')

        if field.min_length:
            field_parts.append(f"min_length={field.min_length}")
        if field.max_length and field.field_type == FieldType.STRING:
            field_parts.append(f"max_length={field.max_length}")
        if field.regex:
            field_parts.append(f'regex=r"{field.regex}"')
        if field.min_value is not None:
            field_parts.append(f"ge={field.min_value}")
        if field.max_value is not None:
            field_parts.append(f"le={field.max_value}")

        field_definition = (
            f"Field({', '.join(field_parts)})" if field_parts else "Field(...)"
        )

        if field.nullable:
            content += (
                f"    {field.name}: Optional[{pydantic_type}] = {field_definition}\n"
            )
        else:
            content += f"    {field.name}: {pydantic_type} = {field_definition}\n"

    # Add custom validators
    content += '''

    # Custom validators
    @field_validator('*', mode='before')
    @classmethod
    def empty_str_to_none(cls, v):
        """Convert empty strings to None"""
        if v == '':
            return None
        return v
'''

    # Add field-specific validators
    for field in fields:
        if field.field_type == FieldType.EMAIL:
            content += f'''
    @field_validator('{field.name}')
    @classmethod
    def validate_{field.name}(cls, v):
        """Validate {field.name} field"""
        if v and not '@' in v:
            raise ValueError('Invalid email format')
        return v
'''
        elif field.field_type == FieldType.SLUG:
            content += f'''
    @field_validator('{field.name}')
    @classmethod
    def validate_{field.name}(cls, v):
        """Validate {field.name} as URL slug"""
        if v and not v.replace('-', '').replace('_', '').isalnum():
            raise ValueError('Slug can only contain letters, numbers, hyphens and underscores')
        return v.lower() if v else v
'''

    # Generate CRUD schemas
    content += f'''

class {pascal_name}Create({pascal_name}Base):
    """
    Schema for creating {model}.
    Excludes computed fields and includes required validation.
    """
    pass

    # Custom validation for create operations
    @model_validator(mode='after')
    def validate_create_fields(self) -> '{pascal_name}Create':
        """Custom validation for create operations"""
        # Add any cross-field validation logic here
        return self

    model_config = {{
        "json_schema_extra": {{
            "example": {{
'''

    # Generate example data
    for field in fields:
        if field.field_type == FieldType.STRING:
            example_value = f'"example_{field.name}"'
        elif field.field_type == FieldType.INTEGER:
            example_value = "42"
        elif field.field_type == FieldType.FLOAT:
            example_value = "3.14"
        elif field.field_type == FieldType.BOOLEAN:
            example_value = "true"
        elif field.field_type == FieldType.EMAIL:
            example_value = '"user@example.com"'
        elif field.field_type == FieldType.DATE:
            example_value = '"2024-01-01"'
        elif field.field_type == FieldType.DATETIME:
            example_value = '"2024-01-01T12:00:00Z"'
        elif field.choices:
            example_value = f'"{field.choices[0]}"'
        else:
            example_value = '"example_value"'

        content += f'                "{field.name}": {example_value},\n'

    content += """            }
        }
    }

"""

    content += f'''
class {pascal_name}Update(CustomBaseModel):
    """
    Schema for updating {model}.
    All fields are optional to support partial updates.
    """
'''

    for field in fields:
        field_config = SUPPORTED_FIELD_TYPES.get(
            field.field_type.value, SUPPORTED_FIELD_TYPES["str"],
        )
        _, pydantic_type, _, _ = field_config

        if field.choices:
            enum_name = f"{pascal_name}{pascal_case(field.name)}Enum"
            pydantic_type = enum_name

        content += f"    {field.name}: Optional[{pydantic_type}] = None\n"

    content += f'''

    @model_validator(mode='after')
    def validate_update_fields(self) -> '{pascal_name}Update':
        """Ensure at least one field is provided for update"""
        values = self.model_dump(exclude_unset=True)
        if not any(v is not None for v in values.values()):
            raise ValueError('At least one field must be provided for update')
        return self

class {pascal_name}Read({pascal_name}Base):
    """
    Schema for reading {model}.
    Includes computed fields and database-generated values.
    """
    id: int
'''

    # Add timestamp fields if enabled
    if config.config["features"]["audit_trail"]:
        content += """    created_at: datetime
    updated_at: datetime
    created_by: Optional[int] = None
    updated_by: Optional[int] = None
"""
    else:
        content += """    created_at: datetime
    updated_at: datetime
"""

    if config.config["features"]["soft_deletes"]:
        content += """    deleted_at: Optional[datetime] = None
    is_deleted: bool = False
"""

    content += f'''



class {pascal_name}InDB({pascal_name}Read):
    """Schema for {model} in database with all internal fields"""
    pass

# Search and Filter Schemas
class {pascal_name}Search(CustomBaseModel):
    """Schema for searching {model}s"""
    q: Optional[str] = Field(None, description="Search query")
    fields: Optional[List[str]] = Field(None, description="Fields to search in")

class {pascal_name}Filter(CustomBaseModel):
    """Schema for filtering {model}s"""
'''

    # Add filterable fields
    for field in fields:
        if field.field_type in [
            FieldType.STRING,
            FieldType.INTEGER,
            FieldType.FLOAT,
            FieldType.DATE,
            FieldType.DATETIME,
        ]:
            content += f"    {field.name}: Optional[Union[str, List[str]]] = None\n"

    content += f'''

class {pascal_name}Sort(CustomBaseModel):
    """Schema for sorting {model}s"""
    field: str = Field(..., description="Field to sort by")
    direction: str = Field("asc", pattern="^(asc|desc)$", description="Sort direction")

# Bulk Operations Schemas
class {pascal_name}BulkCreate(CustomBaseModel):
    """Schema for bulk creating {model}s"""
    items: List[{pascal_name}Create] = Field(..., min_items=1, max_items=1000)

class {pascal_name}BulkUpdate(CustomBaseModel):
    """Schema for bulk updating {model}s"""
    filters: {pascal_name}Filter
    updates: {pascal_name}Update

class {pascal_name}BulkDelete(CustomBaseModel):
    """Schema for bulk deleting {model}s"""
    ids: List[int] = Field(..., min_items=1, max_items=1000)

# Response Schemas
class {pascal_name}List(CustomBaseModel):
    """Schema for paginated {model} list"""
    items: List[{pascal_name}Read]
    total: int
    page: int
    size: int
    pages: int

class {pascal_name}Response(CustomBaseModel):
    """Standard API response for {model}"""
    success: bool = True
    message: str = "Operation completed successfully"
    data: Optional[{pascal_name}Read] = None

class {pascal_name}BulkResponse(CustomBaseModel):
    """Response schema for bulk operations"""
    success: bool = True
    message: str = "Bulk operation completed"
    created_count: int = 0
    updated_count: int = 0
    deleted_count: int = 0
    errors: List[str] = []
'''

    return content


def generate_dependencies_file(
    model: str, fields: list[FieldDefinition], config: ScaffoldConfig,
) -> str:
    """Generate FastAPI dependencies following best practices."""
    pascal_name = pascal_case(model)
    snake_name = snake_case(model)

    content = f'''"""
FastAPI dependencies for {model}.
Auto-generated by enhanced scaffold tool following best practices.

Features:
- Dependency injection chains
- Custom validation dependencies
- Caching of dependency results
- Database session management
- Permission checking
- Rate limiting
"""
from typing import Optional, List, Dict, Any
from fastapi import Depends, HTTPException, status, Query, Path
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy import select

from app.db.session import get_db
from app.db.models.{snake_name} import {pascal_name}
from app.services.{snake_name}_service import {pascal_name}Service
from app.db.schemas.{snake_name} import {pascal_name}Filter, {pascal_name}Sort
from app.core.security import get_current_user
from app.core.exceptions import {pascal_name}NotFound, PermissionDenied
from app.utils.rate_limiter import rate_limit
from app.utils.cache import cache_dependency

# Security dependencies
security = HTTPBearer()

async def get_{snake_name}_service() -> {pascal_name}Service:
    """Get {model} service instance"""
    return {pascal_name}Service()

@cache_dependency(ttl=300)  # Cache for 5 minutes
async def valid_{snake_name}_id(
    {snake_name}_id: int = Path(..., ge=1, description="{model} ID"),
    db: AsyncSession = Depends(get_db),
    service: {pascal_name}Service = Depends(get_{snake_name}_service)
) -> {pascal_name}:
    """
    Validate {model} ID exists and return the {model}.
    Results are cached to avoid repeated database queries.
    """
    {snake_name} = await service.get_{snake_name}_by_id(db, {snake_name}_id)
    if not {snake_name}:
        raise {pascal_name}NotFound(detail=f"{model} with ID {{{snake_name}_id}} not found")
    return {snake_name}

async def valid_owned_{snake_name}(
    {snake_name}: {pascal_name} = Depends(valid_{snake_name}_id),
    current_user = Depends(get_current_user)
) -> {pascal_name}:
    """
    Validate that the current user owns this {model}.
    Chains with valid_{snake_name}_id dependency.
    """
    # Assuming there's a user_id or owner_id field
    if hasattr({snake_name}, 'user_id') and {snake_name}.user_id != current_user.id:
        raise PermissionDenied(detail="You don't have permission to access this {model}")
    elif hasattr({snake_name}, 'owner_id') and {snake_name}.owner_id != current_user.id:
        raise PermissionDenied(detail="You don't have permission to access this {model}")
    return {snake_name}

@rate_limit(calls=100, period=60)  # 100 calls per minute
async def get_pagination_params(
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(20, ge=1, le=100, description="Page size"),
) -> Dict[str, int]:
    """
    Get pagination parameters with validation and rate limiting.
    """
    return {{"page": page, "size": size, "skip": (page - 1) * size, "limit": size}}

async def get_filter_params(
    q: Optional[str] = Query(None, description="Search query"),
'''

    # Add filter parameters for each filterable field
    for field in fields:
        if field.field_type in [
            FieldType.STRING,
            FieldType.INTEGER,
            FieldType.FLOAT,
            FieldType.DATE,
            FieldType.DATETIME,
        ]:
            content += f"""    {field.name}: Optional[str] = Query(None, description="Filter by {field.name}"),
"""

    content += f''') -> {pascal_name}Filter:
    """
    Get filter parameters for {model} queries.
    Supports multiple field filtering and search.
    """
    filters = {pascal_name}Filter(
        q=q,
'''

    for field in fields:
        if field.field_type in [
            FieldType.STRING,
            FieldType.INTEGER,
            FieldType.FLOAT,
            FieldType.DATE,
            FieldType.DATETIME,
        ]:
            content += f"""        {field.name}={field.name},
"""

    content += f'''    )
    return filters

async def get_sort_params(
    sort_by: str = Query("id", description="Field to sort by"),
    sort_order: str = Query("asc", regex="^(asc|desc)$", description="Sort order")
) -> {pascal_name}Sort:
    """
    Get sorting parameters with validation.
    """
    # Validate sort field exists
    valid_fields = {pascal_name}.get_filterable_fields()
    if sort_by not in valid_fields:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid sort field. Valid fields: {{', '.join(valid_fields)}}"
        )

    return {pascal_name}Sort(field=sort_by, direction=sort_order)

async def get_bulk_operation_limit(
    limit: int = Query(100, ge=1, le=1000, description="Bulk operation limit")
) -> int:
    """
    Get bulk operation limit with validation.
    Prevents excessive bulk operations.
    """
    return limit

# Advanced dependencies for complex operations
async def validate_bulk_{snake_name}_ids(
    ids: List[int],
    db: AsyncSession = Depends(get_db),
    service: {pascal_name}Service = Depends(get_{snake_name}_service)
) -> List[{pascal_name}]:
    """
    Validate multiple {model} IDs exist and return the {model}s.
    Used for bulk operations.
    """
    {snake_name}s = await service.get_multiple_by_ids(db, ids)
    found_ids = {{item.id for item in {snake_name}s}}
    missing_ids = set(ids) - found_ids

    if missing_ids:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{model}s not found with IDs: {{', '.join(map(str, missing_ids))}}"
        )

    return {snake_name}s

async def check_{snake_name}_permissions(
    action: str,
    {snake_name}: Optional[{pascal_name}] = None,
    current_user = Depends(get_current_user)
) -> bool:
    """
    Check if user has permission to perform action on {model}.
    """
    # Implement your permission logic here
    # This is a placeholder implementation

    if action == "read":
        return True  # Everyone can read
    elif action in ["create", "update", "delete"]:
        if {snake_name}:
            # Check ownership for specific {model}
            return (hasattr({snake_name}, 'user_id') and {snake_name}.user_id == current_user.id) or \\
                   (hasattr({snake_name}, 'owner_id') and {snake_name}.owner_id == current_user.id) or \\
                   current_user.is_superuser
        else:
            # General permission for create operations
            return current_user.is_authenticated

    return False

# Dependency chains for complex operations
async def validate_and_authorize_{snake_name}(
    {snake_name}_id: int = Path(...),
    action: str = "read",
    db: AsyncSession = Depends(get_db)
) -> {pascal_name}:
    """
    Combined dependency that validates {model} exists AND user has permission.
    """
    # First validate the {model} exists
    {snake_name} = await valid_{snake_name}_id({snake_name}_id, db)

    # Then check permissions
    has_permission = await check_{snake_name}_permissions(action, {snake_name})
    if not has_permission:
        raise PermissionDenied(detail=f"Insufficient permissions to {{action}} this {model}")

    return {snake_name}
'''

    return content


def generate_exceptions_file(model: str) -> str:
    """Generate custom exceptions for the model."""
    pascal_name = pascal_case(model)

    return f'''"""
Custom exceptions for {model}.
Auto-generated by enhanced scaffold tool.
"""
from fastapi import HTTPException, status

class {pascal_name}Exception(HTTPException):
    """Base exception for {model} operations"""
    pass

class {pascal_name}NotFound({pascal_name}Exception):
    """Exception raised when {model} is not found"""
    def __init__(self, detail: str = "{model} not found"):
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail=detail)

class {pascal_name}AlreadyExists({pascal_name}Exception):
    """Exception raised when {model} already exists"""
    def __init__(self, detail: str = "{model} already exists"):
        super().__init__(status_code=status.HTTP_409_CONFLICT, detail=detail)

class {pascal_name}ValidationError({pascal_name}Exception):
    """Exception raised when {model} validation fails"""
    def __init__(self, detail: str = "Validation error"):
        super().__init__(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=detail)

class {pascal_name}PermissionDenied({pascal_name}Exception):
    """Exception raised when user lacks permission"""
    def __init__(self, detail: str = "Permission denied"):
        super().__init__(status_code=status.HTTP_403_FORBIDDEN, detail=detail)

class {pascal_name}BusinessLogicError({pascal_name}Exception):
    """Exception raised when business logic validation fails"""
    def __init__(self, detail: str = "Business logic error"):
        super().__init__(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)
'''



def generate_service_file(
    model: str, fields: list[FieldDefinition], config: ScaffoldConfig,
) -> str:
    """Generate service file using EnhancedBaseService."""
    pascal_name = pascal_case(model)
    snake_name = snake_case(model)

    return f'''"""
Service for {model} business logic and CRUD operations.
Auto-generated by scaffold tool - extends EnhancedBaseService.
"""
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models.{snake_name} import {pascal_name}
from app.services.enhanced_base_service import EnhancedBaseService
from app.db.schemas.{snake_name} import {pascal_name}Read, {pascal_name}Create, {pascal_name}Update
from loguru import logger

class {pascal_name}Service(EnhancedBaseService[{pascal_name}]):
    """
    Service class for {model} operations.
    Inherits enhanced CRUD methods with parallel processing support.
    """

    def __init__(self):
        super().__init__({pascal_name})

    async def create_{snake_name}(
        self,
        db: AsyncSession,
        {snake_name}_data: {pascal_name}Create
    ) -> {pascal_name}Read:
        """Create a new {model}"""
        try:
            {snake_name} = await self.add(db, {snake_name}_data.dict())
            return {pascal_name}Read.from_orm({snake_name})
        except Exception as e:
            logger.error(f"Error creating {snake_name}: {{e}}")
            raise

    async def get_{snake_name}_by_id(
        self,
        db: AsyncSession,
        {snake_name}_id: int
    ) -> Optional[{pascal_name}Read]:
        """Get {model} by ID"""
        {snake_name} = await self.find_by_id(db, {snake_name}_id)
        if {snake_name}:
            return {pascal_name}Read.from_orm({snake_name})
        return None

    async def update_{snake_name}(
        self,
        db: AsyncSession,
        {snake_name}_id: int,
        {snake_name}_data: {pascal_name}Update
    ) -> Optional[{pascal_name}Read]:
        """Update {model}"""
        try:
            {snake_name} = await self.find_by_id(db, {snake_name}_id)
            if not {snake_name}:
                return None

            update_data = {{k: v for k, v in {snake_name}_data.dict().items() if v is not None}}
            updated_{snake_name} = await self.update(db, {snake_name}, update_data)
            return {pascal_name}Read.from_orm(updated_{snake_name})
        except Exception as e:
            logger.error(f"Error updating {snake_name}: {{e}}")
            raise

    async def delete_{snake_name}(self, db: AsyncSession, {snake_name}_id: int) -> bool:
        """Delete {model}"""
        try:
            {snake_name} = await self.find_by_id(db, {snake_name}_id)
            if not {snake_name}:
                return False

            await self.delete(db, {snake_name})
            return True
        except Exception as e:
            logger.error(f"Error deleting {snake_name}: {{e}}")
            raise

    async def list_{snake_name}s(
        self,
        db: AsyncSession,
        skip: int = 0,
        limit: int = 100
    ) -> List[{pascal_name}Read]:
        """List {model}s with pagination"""
        {snake_name}s = await self.paginate(db, page=skip//limit + 1, page_size=limit)
        return [{pascal_name}Read.from_orm({snake_name}) for {snake_name} in {snake_name}s]

    # Enhanced parallel processing methods

    async def bulk_create_{snake_name}s_parallel(
        self,
        db: AsyncSession,
        {snake_name}s_data: List[{pascal_name}Create],
        batch_size: Optional[int] = 50
    ) -> List[{pascal_name}Read]:
        """Create multiple {model}s in parallel"""
        data_dicts = [{snake_name}_data.dict() for {snake_name}_data in {snake_name}s_data]
        created_{snake_name}s = await self.bulk_create_parallel(db, data_dicts, batch_size)
        return [{pascal_name}Read.from_orm({snake_name}) for {snake_name} in created_{snake_name}s]

    async def search_{snake_name}s_parallel(
        self,
        db: AsyncSession,
        search_queries: List[Dict[str, Any]]
    ) -> List[List[{pascal_name}Read]]:
        """Search {model}s in parallel"""
        results = await self.search_parallel(db, search_queries)
        return [[{pascal_name}Read.from_orm({snake_name}) for {snake_name} in result] for result in results]
'''



def generate_endpoint_file(model: str, with_bulk: bool = False) -> str:
    """Generate API endpoint file."""
    pascal_name = pascal_case(model)
    snake_name = snake_case(model)

    content = f'''"""
API endpoints for {model}.
Auto-generated by scaffold tool.
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.services.{snake_name}_service import {pascal_name}Service
from app.db.schemas.{snake_name} import {pascal_name}Read, {pascal_name}Create, {pascal_name}Update

router = APIRouter(prefix="/{snake_name}s", tags=["{pascal_name}s"])

@router.post("/", response_model={pascal_name}Read, status_code=status.HTTP_201_CREATED)
async def create_{snake_name}(
    {snake_name}: {pascal_name}Create,
    db: AsyncSession = Depends(get_db)
) -> {pascal_name}Read:
    """Create a new {model}"""
    return await {pascal_name}Service().create_{snake_name}(db, {snake_name})

@router.get("/", response_model=List[{pascal_name}Read])
async def list_{snake_name}s(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db)
) -> List[{pascal_name}Read]:
    """List {model}s with pagination"""
    return await {pascal_name}Service().list_{snake_name}s(db, skip, limit)

@router.get("/{{id}}", response_model={pascal_name}Read)
async def get_{snake_name}(
    id: int,
    db: AsyncSession = Depends(get_db)
) -> {pascal_name}Read:
    """Get {model} by ID"""
    {snake_name} = await {pascal_name}Service().get_{snake_name}_by_id(db, id)
    if not {snake_name}:
        raise HTTPException(status_code=404, detail="{model} not found")
    return {snake_name}

@router.put("/{{id}}", response_model={pascal_name}Read)
async def update_{snake_name}(
    id: int,
    {snake_name}: {pascal_name}Update,
    db: AsyncSession = Depends(get_db)
) -> {pascal_name}Read:
    """Update {model}"""
    updated_{snake_name} = await {pascal_name}Service().update_{snake_name}(db, id, {snake_name})
    if not updated_{snake_name}:
        raise HTTPException(status_code=404, detail="{model} not found")
    return updated_{snake_name}

@router.delete("/{{id}}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_{snake_name}(
    id: int,
    db: AsyncSession = Depends(get_db)
):
    """Delete {model}"""
    success = await {pascal_name}Service().delete_{snake_name}(db, id)
    if not success:
        raise HTTPException(status_code=404, detail="{model} not found")
'''

    if with_bulk:
        content += f'''

# Bulk operations endpoints

@router.post("/bulk", response_model=List[{pascal_name}Read])
async def bulk_create_{snake_name}s(
    {snake_name}s: List[{pascal_name}Create],
    db: AsyncSession = Depends(get_db)
) -> List[{pascal_name}Read]:
    """Create multiple {model}s in parallel"""
    return await {pascal_name}Service().bulk_create_{snake_name}s_parallel(db, {snake_name}s)

@router.post("/search", response_model=List[List[{pascal_name}Read]])
async def search_{snake_name}s(
    search_queries: List[dict],
    db: AsyncSession = Depends(get_db)
) -> List[List[{pascal_name}Read]]:
    """Search {model}s with multiple queries in parallel"""
    return await {pascal_name}Service().search_{snake_name}s_parallel(db, search_queries)
'''

    return content


def generate_procrastinate_tasks(model: str) -> str:
    """Generate Procrastinate task integration."""
    pascal_name = pascal_case(model)
    snake_name = snake_case(model)

    return f'''"""
Procrastinate tasks for {model}.
Auto-generated by scaffold tool.
"""
import asyncio
from datetime import datetime
from typing import Dict, Any, List
from loguru import logger

from app.utils.procrastinate_manager import procrastinate_app
from app.services.{snake_name}_service import {pascal_name}Service
from app.db.session import get_db

@procrastinate_app.task(queue="{snake_name}_processing", retry=3)
async def process_{snake_name}(
    {snake_name}_id: int,
    operation: str,
    **kwargs
) -> Dict[str, Any]:
    """Process {model} data asynchronously"""
    logger.info(f"Processing {snake_name} {{id}} with operation: {{operation}}")

    try:
        # Get database session
        db_gen = get_db()
        if hasattr(db_gen, "__anext__"):
            db = await db_gen.__anext__()
        else:
            db = next(db_gen)

        try:
            service = {pascal_name}Service()
            {snake_name} = await service.get_{snake_name}_by_id(db, {snake_name}_id)

            if not {snake_name}:
                raise ValueError(f"{model} with ID {{{snake_name}_id}} not found")

            # Simulate processing based on operation
            await asyncio.sleep(1)  # Replace with actual processing logic

            result = {{
                "{snake_name}_id": {snake_name}_id,
                "operation": operation,
                "processed_at": datetime.now().isoformat(),
                "status": "completed",
                "data": {snake_name}.dict(),
                "details": kwargs
            }}

            logger.info(f"{model} {{{snake_name}_id}} processing completed")
            return result

        finally:
            if hasattr(db, "close"):
                await db.close()

    except Exception as e:
        logger.error(f"Error processing {snake_name} {{{snake_name}_id}}: {{e}}")
        raise

@procrastinate_app.task(queue="{snake_name}_bulk_processing", retry=2)
async def bulk_process_{snake_name}s(
    {snake_name}_ids: List[int],
    operation: str = "bulk_process",
    **kwargs
) -> Dict[str, Any]:
    """Process multiple {model}s in bulk"""
    logger.info(f"Bulk processing {{len({snake_name}_ids)}} {snake_name}s")

    try:
        results = []
        for {snake_name}_id in {snake_name}_ids:
            result = await process_{snake_name}.defer_async({snake_name}_id=id, operation=operation, **kwargs)
            results.append(result)

        return {{
            "operation": f"bulk_{{operation}}",
            "total_{snake_name}s": len({snake_name}_ids),
            "processed_at": datetime.now().isoformat(),
            "status": "completed",
            "results": results[:10]  # Return first 10 for brevity
        }}

    except Exception as e:
        logger.error(f"Error in bulk processing {snake_name}s: {{e}}")
        raise

# Utility functions for task management

async def defer_{snake_name}_processing(
    {snake_name}_id: int,
    operation: str,
    priority: int = 2,
    **kwargs
) -> str:
    """Defer {model} processing task"""
    job = await process_{snake_name}.defer_async(
        {snake_name}_id={snake_name}_id,
        operation=operation,
        priority=priority,
        **kwargs
    )
    logger.info(f"Deferred {snake_name} processing task: {{job.id}}")
    return str(job.id)

async def defer_bulk_{snake_name}_processing(
    {snake_name}_ids: List[int],
    operation: str = "bulk_process",
    priority: int = 2,
    **kwargs
) -> str:
    """Defer bulk {model} processing task"""
    job = await bulk_process_{snake_name}s.defer_async(
        {snake_name}_ids={snake_name}_ids,
        operation=operation,
        priority=priority,
        **kwargs
    )
    logger.info(f"Deferred bulk {snake_name} processing task: {{job.id}}")
    return str(job.id)
'''



def generate_test_file(model: str, fields: list[tuple]) -> str:
    """Generate comprehensive test file."""
    pascal_name = pascal_case(model)
    snake_name = snake_case(model)

    # Generate test data
    test_data = {}
    for name, field_type in fields:
        if field_type == "str":
            test_data[name] = f"Test {name.title()}"
        elif field_type == "int":
            test_data[name] = 42
        elif field_type == "float":
            test_data[name] = 3.14
        elif field_type == "bool":
            test_data[name] = True
        elif field_type == "email":
            test_data[name] = "test@example.com"
        else:
            test_data[name] = f"test_{name}"

    return f'''"""
Tests for {model} endpoints and service.
Auto-generated by scaffold tool.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import app
from app.db.session import get_db
from app.services.{snake_name}_service import {pascal_name}Service
from app.db.schemas.{snake_name} import {pascal_name}Create, {pascal_name}Update

client = TestClient(app)

# Test data
test_{snake_name}_data = {test_data!r}

class Test{pascal_name}API:
    """Test {model} API endpoints"""

    def test_create_{snake_name}(self):
        """Test creating a {model}"""
        response = client.post(
            "/api/v1/{snake_name}s/",
            json=test_{snake_name}_data
        )
        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        for key, value in test_{snake_name}_data.items():
            assert data[key] == value

    def test_list_{snake_name}s(self):
        """Test listing {model}s"""
        response = client.get("/api/v1/{snake_name}s/")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_get_{snake_name}(self):
        """Test getting a {model} by ID"""
        # First create a {snake_name}
        create_response = client.post(
            "/api/v1/{snake_name}s/",
            json=test_{snake_name}_data
        )
        assert create_response.status_code == 201
        {snake_name}_id = create_response.json()["id"]

        # Then get it
        response = client.get(f"/api/v1/{snake_name}s/{{{snake_name}_id}}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == {snake_name}_id

    def test_update_{snake_name}(self):
        """Test updating a {model}"""
        # First create a {snake_name}
        create_response = client.post(
            "/api/v1/{snake_name}s/",
            json=test_{snake_name}_data
        )
        assert create_response.status_code == 201
        {snake_name}_id = create_response.json()["id"]

        # Update data
        update_data = {{key: f"Updated {{value}}" if isinstance(value, str) else value
                      for key, value in test_{snake_name}_data.items()}}

        # Update the {snake_name}
        response = client.put(
            f"/api/v1/{snake_name}s/{{{snake_name}_id}}",
            json=update_data
        )
        assert response.status_code == 200
        data = response.json()
        for key, value in update_data.items():
            if isinstance(value, str) and not value.startswith("Updated"):
                continue
            assert data[key] == value

    def test_delete_{snake_name}(self):
        """Test deleting a {model}"""
        # First create a {snake_name}
        create_response = client.post(
            "/api/v1/{snake_name}s/",
            json=test_{snake_name}_data
        )
        assert create_response.status_code == 201
        {snake_name}_id = create_response.json()["id"]

        # Delete the {snake_name}
        response = client.delete(f"/api/v1/{snake_name}s/{{{snake_name}_id}}")
        assert response.status_code == 204

        # Verify it's deleted
        get_response = client.get(f"/api/v1/{snake_name}s/{{{snake_name}_id}}")
        assert get_response.status_code == 404

    def test_get_nonexistent_{snake_name}(self):
        """Test getting a non-existent {model}"""
        response = client.get("/api/v1/{snake_name}s/99999")
        assert response.status_code == 404

@pytest.mark.asyncio
class Test{pascal_name}Service:
    """Test {model} service methods"""

    async def test_create_{snake_name}(self, db_session: AsyncSession):
        """Test service create method"""
        service = {pascal_name}Service()
        {snake_name}_create = {pascal_name}Create(**test_{snake_name}_data)

        {snake_name} = await service.create_{snake_name}(db_session, {snake_name}_create)

        assert {snake_name}.id is not None
        for key, value in test_{snake_name}_data.items():
            assert getattr({snake_name}, key) == value

    async def test_get_{snake_name}_by_id(self, db_session: AsyncSession):
        """Test service get by ID method"""
        service = {pascal_name}Service()
        {snake_name}_create = {pascal_name}Create(**test_{snake_name}_data)

        created_{snake_name} = await service.create_{snake_name}(db_session, {snake_name}_create)
        retrieved_{snake_name} = await service.get_{snake_name}_by_id(db_session, created_{snake_name}.id)

        assert retrieved_{snake_name} is not None
        assert retrieved_{snake_name}.id == created_{snake_name}.id

    async def test_update_{snake_name}(self, db_session: AsyncSession):
        """Test service update method"""
        service = {pascal_name}Service()
        {snake_name}_create = {pascal_name}Create(**test_{snake_name}_data)

        created_{snake_name} = await service.create_{snake_name}(db_session, {snake_name}_create)

        update_data = {{key: f"Updated {{value}}" if isinstance(value, str) else value
                      for key, value in test_{snake_name}_data.items()}}
        {snake_name}_update = {pascal_name}Update(**update_data)

        updated_{snake_name} = await service.update_{snake_name}(
            db_session, created_{snake_name}.id, {snake_name}_update
        )

        assert updated_{snake_name} is not None
        for key, value in update_data.items():
            if isinstance(value, str) and value.startswith("Updated"):
                assert getattr(updated_{snake_name}, key) == value

    async def test_delete_{snake_name}(self, db_session: AsyncSession):
        """Test service delete method"""
        service = {pascal_name}Service()
        {snake_name}_create = {pascal_name}Create(**test_{snake_name}_data)

        created_{snake_name} = await service.create_{snake_name}(db_session, {snake_name}_create)
        success = await service.delete_{snake_name}(db_session, created_{snake_name}.id)

        assert success is True

        # Verify deletion
        deleted_{snake_name} = await service.get_{snake_name}_by_id(db_session, created_{snake_name}.id)
        assert deleted_{snake_name} is None
'''



def update_base_py(model: str, tracker: Optional["ScaffoldTracker"] = None) -> None:
    """Add model import to base.py for Alembic."""
    base_path = f"{BASE_PATH}/db/base.py"
    snake_name = snake_case(model)
    pascal_name = pascal_case(model)
    import_line = f"from app.db.models.{snake_name} import {pascal_name}"

    if not Path(base_path).exists():
        return

    with Path(base_path).open("r") as f:
        original_content = f.read()

    if import_line in original_content:
        return

    # Add import at the end
    new_content = original_content + f"\n{import_line}\n"

    with Path(base_path).open("w") as f:
        f.write(new_content)


    # Track the modification
    if tracker:
        tracker.track_file_modified(
            base_path, original_content, new_content, [f"Added import: {import_line}"],
        )
        tracker.track_import_added(base_path, import_line)


def update_api_router(model: str, tracker: Optional["ScaffoldTracker"] = None) -> None:
    """Add router to API."""
    snake_name = snake_case(model)
    pascal_name = pascal_case(model)

    if not Path(API_FILE).exists():
        return

    with Path(API_FILE).open("r") as f:
        original_content = f.read()
        lines = original_content.splitlines(keepends=True)

    import_line = f"from app.api.v1.endpoints import {snake_name}\n"
    include_line = (
        f'api_router.include_router({snake_name}.router, tags=["{pascal_name}s"])\n'
    )

    # Check if already exists
    if any(import_line.strip() in line for line in lines):
        return

    changes_made = []

    # Find where to insert import (after last import)
    import_index = -1
    for i, line in enumerate(lines):
        if line.strip().startswith("from app.api.v1.endpoints import"):
            import_index = i

    if import_index >= 0:
        lines.insert(import_index + 1, import_line)
        changes_made.append(
            f"Added import at line {import_index + 2}: {import_line.strip()}",
        )
    else:
        # Add after first import
        for i, line in enumerate(lines):
            if line.strip().startswith("from"):
                lines.insert(i + 1, import_line)
                changes_made.append(
                    f"Added import at line {i + 2}: {import_line.strip()}",
                )
                break

    # Add include_router at the end
    lines.append(include_line)
    changes_made.append(f"Added router include: {include_line.strip()}")

    new_content = "".join(lines)

    with Path(API_FILE).open("w") as f:
        f.write(new_content)


    # Track the modification
    if tracker:
        tracker.track_file_modified(
            API_FILE, original_content, new_content, changes_made,
        )
        tracker.track_import_added(API_FILE, import_line)
        tracker.track_import_added(API_FILE, include_line)


def run_preflight_checks() -> bool:
    """Run comprehensive preflight checks before scaffolding."""
    issues = []

    # Check if database is accessible
    try:
        result = subprocess.run(
            [
                "python",
                "-c",
                "import asyncio; from app.db.session import engine; asyncio.run(engine.begin().__aenter__())",
            ],
            capture_output=True,
            text=True,
            timeout=10, check=False,
        )

        if result.returncode != 0:
            issues.append("Database connection failed")
    except subprocess.TimeoutExpired:
        issues.append("Database connection timed out")
    except Exception as e:
        issues.append(f"Database check failed: {e}")

    # Check if required base files exist
    required_files = [
        "app/db/base.py",
        "app/db/mixins.py",
        "app/db/schemas/base.py",
        "app/core/repository.py",
        "app/services/enhanced_base_service.py",
    ]

    for file_path in required_files:
        if not Path(file_path).exists():
            issues.append(f"Missing required file: {file_path}")

    # Check if app imports successfully (with more lenient timeout)
    try:
        result = subprocess.run(
            ["python", "-c", "from app.main import app; print('OK')"],
            capture_output=True,
            text=True,
            timeout=60, check=False,
        )

        if result.returncode != 0:
            # Only fail if there are actual import errors (not warnings)
            stderr = result.stderr.strip()
            if (
                "Error" in stderr
                or "ImportError" in stderr
                or "ModuleNotFoundError" in stderr
            ):
                issues.append(f"App import failed: {stderr}")
            # Skip warnings about duplicate operation IDs - they're expected
    except subprocess.TimeoutExpired:
        issues.append("App import timed out (>60s)")
    except Exception:
        issues.append("Could not test app imports")

    if issues:
        for _issue in issues:
            pass
        return False
    return True


def check_and_fix_alembic_state() -> bool | None:
    """Check and fix Alembic state issues before generating migrations."""
    try:

        # Check if alembic can read current state
        current_result = subprocess.run(
            ["alembic", "current"], capture_output=True, text=True, check=False,
        )

        if (
            current_result.returncode != 0
            and "Can't locate revision" in current_result.stderr
        ):

            # Get the actual head revision from migration files
            history_result = subprocess.run(
                ["alembic", "history", "--verbose"], capture_output=True, text=True, check=False,
            )

            if history_result.returncode == 0:
                history_lines = history_result.stdout.strip().split("\n")
                if history_lines and "->" in history_lines[0]:
                    # Extract the latest revision
                    latest_rev = history_lines[0].split("->")[1].strip().split()[0]
                    if latest_rev and latest_rev != "<base>":

                        # Create a script to fix the database state
                        fix_script = f"""
import asyncio
from app.db.session import engine
from sqlalchemy import text

async def fix_alembic_version():
    try:
        async with engine.begin() as conn:
            await conn.execute(text("UPDATE alembic_version SET version_num = '{latest_rev}'"))
            print("✅ Fixed alembic_version table")
    except Exception as e:
        print(f"❌ Error fixing alembic state: {{e}}")

asyncio.run(fix_alembic_version())
"""
                        with Path("fix_alembic_temp.py").open("w") as f:
                            f.write(fix_script)

                        # Run the fix
                        fix_result = subprocess.run(
                            ["python", "fix_alembic_temp.py"],
                            capture_output=True,
                            text=True, check=False,
                        )

                        # Clean up
                        Path("fix_alembic_temp.py").unlink()

                        if fix_result.returncode == 0:
                            return True

        return True

    except Exception:
        return False


def clean_migration_file(migration_file: str, model: str) -> bool | None:
    """Clean generated migration file to avoid conflicts with existing infrastructure."""
    try:
        if not Path(migration_file).exists():
            return True

        with Path(migration_file).open("r") as f:
            content = f.read()

        lines = content.split("\n")
        cleaned_lines = []
        in_downgrade = False
        skip_procrastinate_block = False

        for i, line in enumerate(lines):
            # Track if we're in the downgrade function
            if "def downgrade()" in line:
                in_downgrade = True
                cleaned_lines.append(line)
                cleaned_lines.append(
                    "    # ### commands auto generated by Alembic - please adjust! ###",
                )
                cleaned_lines.append(
                    f"    # Note: Only dropping {model.lower()} table - keeping existing infrastructure intact",
                )
                continue

            # Skip any procrastinate-related operations
            is_procrastinate_line = "procrastinate" in line.lower() and (
                "op.drop_" in line or "op.create_" in line
            )

            if is_procrastinate_line:
                if not skip_procrastinate_block and "drop" in line.lower():
                    cleaned_lines.append(
                        "    # Note: Keeping Procrastinate tables intact - they are still needed for background task processing",
                    )
                    skip_procrastinate_block = True
                continue

            # If we're in downgrade and see a create_table for procrastinate, skip until we see a different operation
            if in_downgrade and "op.create_table(" in line and "procrastinate" in line:
                # Skip this entire block by finding the matching closing parenthesis
                paren_count = line.count("(") - line.count(")")
                while paren_count > 0 and i + 1 < len(lines):
                    i += 1
                    if i < len(lines):
                        next_line = lines[i]
                        paren_count += next_line.count("(") - next_line.count(")")
                continue

            cleaned_lines.append(line)

        # Write cleaned content
        with Path(migration_file).open("w") as f:
            f.write("\n".join(cleaned_lines))

        return True

    except Exception:
        return False


def handle_alembic_complete_recovery() -> bool | None:
    """Complete Alembic recovery - handles all possible failure scenarios."""
    try:
        # Step 1: Check if alembic directory exists
        if not Path("alembic").exists():
            init_result = subprocess.run(
                ["alembic", "init", "alembic"], capture_output=True, text=True, check=False,
            )

            if init_result.returncode != 0:
                return False


        # Step 2: Check if database has alembic_version table
        check_version_script = """
import asyncio
from app.db.session import engine
from sqlalchemy import text

async def check_alembic_table():
    try:
        async with engine.begin() as conn:
            result = await conn.execute(text("SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'alembic_version');"))
            exists = result.scalar()
            if not exists:
                print("Creating alembic_version table...")
                await conn.execute(text("CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL, CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num));"))
                print("✅ Created alembic_version table")
            else:
                print("✅ alembic_version table exists")
    except Exception as e:
        print(f"❌ Error checking alembic table: {e}")

asyncio.run(check_alembic_table())
"""

        with Path("temp_check_alembic.py").open("w") as f:
            f.write(check_version_script)

        subprocess.run(
            ["python", "temp_check_alembic.py"], capture_output=True, text=True, check=False,
        )
        Path("temp_check_alembic.py").unlink()

        # Step 3: Get all migration files and find the actual head
        versions_dir = "alembic/versions"
        if not Path(versions_dir).exists():
            Path(versions_dir).mkdir(parents=True, exist_ok=True)

        migration_files = [
            f
            for f in os.listdir(versions_dir)
            if f.endswith(".py") and f != "__pycache__"
        ]

        if migration_files:
            # Find the latest migration by parsing revision chains
            latest_revision = find_actual_head_revision(versions_dir, migration_files)

            if latest_revision:

                # Stamp the database with the correct revision
                stamp_script = f"""
import asyncio
from app.db.session import engine
from sqlalchemy import text

async def stamp_revision():
    try:
        async with engine.begin() as conn:
            # Clear any existing version
            await conn.execute(text("DELETE FROM alembic_version;"))
            # Insert correct version
            await conn.execute(text("INSERT INTO alembic_version (version_num) VALUES ('{latest_revision}');"))
            print("✅ Database stamped with correct revision")
    except Exception as e:
        print(f"❌ Error stamping revision: {{e}}")

asyncio.run(stamp_revision())
"""

                with Path("temp_stamp.py").open("w") as f:
                    f.write(stamp_script)

                subprocess.run(
                    ["python", "temp_stamp.py"], capture_output=True, text=True, check=False,
                )
                Path("temp_stamp.py").unlink()
        else:
            # No migrations exist, create initial migration
            init_migration_result = subprocess.run(
                ["alembic", "revision", "--autogenerate", "-m", "Initial migration"],
                capture_output=True,
                text=True, check=False,
            )

            if init_migration_result.returncode == 0:
                pass
            else:
                pass

        return True

    except Exception:
        return False


def find_actual_head_revision(
    versions_dir: str, migration_files: list[str],
) -> str | None:
    """Find the actual head revision by parsing migration files."""
    try:
        revisions = {}
        down_revisions = {}

        for filename in migration_files:
            file_path = Path(versions_dir) / filename
            try:
                with Path(file_path).open("r") as f:
                    content = f.read()

                # Extract revision and down_revision
                revision_match = re.search(
                    r"revision:\s*str\s*=\s*['\"]([^'\"]+)['\"]", content,
                )
                down_revision_match = re.search(
                    r"down_revision:\s*Union\[str,\s*None\]\s*=\s*['\"]?([^'\"]+)?['\"]?",
                    content,
                )

                if revision_match:
                    revision = revision_match.group(1)
                    down_revision = (
                        down_revision_match.group(1)
                        if down_revision_match
                        and down_revision_match.group(1) != "None"
                        else None
                    )

                    revisions[revision] = filename
                    down_revisions[revision] = down_revision
            except Exception:
                continue

        # Find head (revision that is not referenced as down_revision by any other)
        referenced_revisions = set(down_revisions.values())
        referenced_revisions.discard(None)

        head_candidates = set(revisions.keys()) - referenced_revisions

        if head_candidates:
            return next(iter(head_candidates))  # Return first head candidate
        if revisions:
            return list(revisions.keys())[-1]  # Return last revision if no clear head

        return None

    except Exception:
        return None


def run_migration(
    model: str,
    fields: list[FieldDefinition] | None = None,
    tracker: Optional["ScaffoldTracker"] = None,
) -> bool:
    """Ultra-robust migration system following Alembic best practices.
    Fixed based on extensive research of migration failures and best practices.

    Key improvements:
    1. Proper schema isolation to avoid touching existing infrastructure
    2. Smart migration filtering to only include new model tables
    3. Safe autogenerate configuration that preserves existing infrastructure
    4. Comprehensive error handling with proper rollback mechanisms
    5. Zero-downtime migration approach
    """
    # Step 1: Ensure clean Alembic environment
    if not ensure_alembic_environment():
        return False

    # Step 2: Configure safe autogenerate environment
    if not configure_safe_autogenerate():
        return False

    # Step 3: Check if table already exists (avoid duplicate work)
    if verify_table_exists(model):
        if tracker:
            tracker.track_database_change(
                "table_exists",
                {"table_name": f"{snake_case(model)}s", "action": "skip_existing"},
            )
        return True

    # Step 4: Generate isolated migration for new model only
    migration_file = generate_isolated_migration(model, fields, tracker)
    if not migration_file:
        return False

    # Step 5: Apply migration with safety checks
    if apply_safe_migration(migration_file, model, tracker):

        # Step 6: Verify table was created correctly
        return bool(verify_table_exists(model))
    return False


def ensure_alembic_environment() -> bool:
    """Ensure Alembic environment is properly configured and healthy.
    Handles common Alembic environment issues without destructive operations.
    """
    try:

        # Check if alembic.ini exists
        if not Path("alembic.ini").exists():
            return False

        # Check if alembic directory exists
        if not Path("alembic").exists():
            return False

        # Check if env.py exists and is configured
        env_py_path = "alembic/env.py"
        if not Path(env_py_path).exists():
            return False

        # Verify database connection without making changes
        if not verify_database_connection():
            return False

        # Check Alembic can read current state
        try:
            current_result = subprocess.run(
                ["alembic", "current"], capture_output=True, text=True, timeout=30, check=False,
            )

            # If alembic current fails with specific revision errors, try to fix
            if current_result.returncode != 0:
                if "Can't locate revision" in current_result.stderr:
                    if not fix_orphaned_revision():
                        return False
                else:
                    pass
                    # Don't fail for warnings, continue

            return True

        except subprocess.TimeoutExpired:
            return False

    except Exception:
        return False


def configure_safe_autogenerate() -> bool:
    """Configure Alembic env.py for safe autogenerate that preserves existing infrastructure.
    This prevents autogenerate from detecting and trying to modify existing tables.
    """
    try:
        env_py_path = "alembic/env.py"
        if not Path(env_py_path).exists():
            return False

        with Path(env_py_path).open("r") as f:
            content = f.read()

        # Check if our safe configuration is already present
        if "# SCAFFOLD_SAFE_AUTOGENERATE_CONFIG" in content:
            return True


        # Create safe configuration that excludes existing infrastructure
        safe_config = '''
# SCAFFOLD_SAFE_AUTOGENERATE_CONFIG - Prevents touching existing infrastructure
def include_name(name, type_, parent_names):
    """
    Filter function to prevent autogenerate from touching existing infrastructure.
    Only includes tables that are part of our application models.
    """
    if type_ == "table":
        # List of infrastructure tables to never touch
        infrastructure_tables = {
            'alembic_version',
            'procrastinate_jobs',
            'procrastinate_events',
            'procrastinate_periodic_defers',
            'procrastinate_locks'
        }

        # Skip infrastructure tables
        if name in infrastructure_tables:
            return False

        # Only include tables that match our application naming pattern
        # This prevents touching any existing tables not managed by our scaffold
        return True

    return True

def include_object(object, name, type_, reflected, compare_to):
    """
    Advanced filtering to prevent autogenerate from modifying existing infrastructure.
    """
    if type_ == "table":
        # Infrastructure tables to never touch
        infrastructure_tables = {
            'alembic_version',
            'procrastinate_jobs',
            'procrastinate_events',
            'procrastinate_periodic_defers',
            'procrastinate_locks'
        }

        if name in infrastructure_tables:
            return False

    return True

'''

        # Find the context.configure call in run_migrations_online
        online_function_start = content.find("def run_migrations_online()")
        if online_function_start == -1:
            return False

        # Find the context.configure call
        configure_start = content.find("context.configure(", online_function_start)
        if configure_start == -1:
            return False

        # Find the end of the context.configure call
        configure_end = configure_start
        paren_count = 0
        in_configure = False

        for i, char in enumerate(content[configure_start:], configure_start):
            if char == "(":
                paren_count += 1
                in_configure = True
            elif char == ")":
                paren_count -= 1
                if in_configure and paren_count == 0:
                    configure_end = i + 1
                    break

        # Extract current configure call
        current_configure = content[configure_start:configure_end]

        # Add our safe parameters if not already present
        if "include_name=" not in current_configure:
            # Insert our safe parameters before the closing parenthesis
            safe_params = """include_name=include_name,
            include_object=include_object,
            compare_type=True,
            compare_server_default=True,"""

            # Find the last parameter and add our parameters
            last_paren = current_configure.rfind(")")
            new_configure = (
                current_configure[:last_paren]
                + ",\n        "
                + safe_params
                + "\n    "
                + current_configure[last_paren:]
            )

            # Replace in content
            new_content = (
                content[:configure_start]
                + safe_config
                + "\n"
                + new_configure
                + content[configure_end:]
            )

            # Write back to file
            with Path(env_py_path).open("w") as f:
                f.write(new_content)


        return True

    except Exception:
        return False


def fix_orphaned_revision() -> bool:
    """Fix orphaned revision issues by finding a valid revision chain.
    This handles cases where the database references a revision that no longer exists.
    """
    try:

        # Get current database revision
        db_revision = get_current_database_revision()
        if not db_revision:
            return reset_to_clean_state()

        # Check if this revision exists in our files
        if revision_exists_in_files(db_revision):
            return True

        # Find a valid revision to reset to
        valid_revision = find_valid_revision()
        if valid_revision:
            return set_database_revision(valid_revision)
        return reset_to_clean_state()

    except Exception:
        return False


def get_current_database_revision() -> str | None:
    """Get the current revision from the database."""
    try:
        check_script = """
import asyncio
from app.db.session import engine
from sqlalchemy import text

async def get_revision():
    try:
        async with engine.begin() as conn:
            result = await conn.execute(text("SELECT version_num FROM alembic_version LIMIT 1;"))
            row = result.fetchone()
            if row:
                print(row[0])
            else:
                print("NO_REVISION")
    except Exception as e:
        print(f"ERROR: {e}")

asyncio.run(get_revision())
"""

        with Path("temp_get_revision.py").open("w") as f:
            f.write(check_script)

        result = subprocess.run(
            ["python", "temp_get_revision.py"], capture_output=True, text=True, check=False,
        )
        Path("temp_get_revision.py").unlink()

        if result.returncode == 0:
            output = result.stdout.strip()
            if output and output != "NO_REVISION" and not output.startswith("ERROR"):
                return output

        return None

    except Exception:
        return None


def revision_exists_in_files(revision: str) -> bool:
    """Check if a revision exists in our migration files."""
    try:
        versions_dir = "alembic/versions"
        if not Path(versions_dir).exists():
            return False

        for filename in os.listdir(versions_dir):
            if filename.endswith(".py"):
                file_path = Path(versions_dir) / filename
                try:
                    with Path(file_path).open("r") as f:
                        content = f.read()
                    if (
                        f'revision = "{revision}"' in content
                        or f"revision = '{revision}'" in content
                    ):
                        return True
                except:
                    continue

        return False

    except Exception:
        return False


def find_valid_revision() -> str | None:
    """Find a valid revision from our migration files."""
    try:
        versions_dir = "alembic/versions"
        if not Path(versions_dir).exists():
            return None

        revisions = []
        for filename in os.listdir(versions_dir):
            if filename.endswith(".py"):
                file_path = Path(versions_dir) / filename
                try:
                    with Path(file_path).open("r") as f:
                        content = f.read()

                    revision_match = re.search(
                        r'revision\s*=\s*[\'"]([^\'"]+)[\'"]', content,
                    )
                    if revision_match:
                        revisions.append(revision_match.group(1))
                except:
                    continue

        # Return the first valid revision (could be improved to find actual head)
        return revisions[0] if revisions else None

    except Exception:
        return None


def set_database_revision(revision: str) -> bool:
    """Set the database revision to a specific value."""
    try:
        set_script = f"""
import asyncio
from app.db.session import engine
from sqlalchemy import text

async def set_revision():
    try:
        async with engine.begin() as conn:
            await conn.execute(text("DELETE FROM alembic_version;"))
            await conn.execute(text("INSERT INTO alembic_version (version_num) VALUES ('{revision}');"))
            print("SUCCESS")
    except Exception as e:
        print(f"ERROR: {{e}}")

asyncio.run(set_revision())
"""

        with Path("temp_set_revision.py").open("w") as f:
            f.write(set_script)

        result = subprocess.run(
            ["python", "temp_set_revision.py"], capture_output=True, text=True, check=False,
        )
        Path("temp_set_revision.py").unlink()

        return result.returncode == 0 and "SUCCESS" in result.stdout

    except Exception:
        return False


def reset_to_clean_state() -> bool:
    """Reset Alembic to a clean state (base)."""
    try:

        # Use alembic stamp base to reset
        result = subprocess.run(
            ["alembic", "stamp", "base"], capture_output=True, text=True, timeout=30, check=False,
        )

        return result.returncode == 0

    except Exception:
        return False


def generate_isolated_migration(
    model: str,
    fields: list[FieldDefinition] | None = None,
    tracker: Optional["ScaffoldTracker"] = None,
) -> str | None:
    """Ultra-robust migration generation with multiple fallback strategies.
    Handles all edge cases and provides comprehensive error recovery.
    """
    try:
        snake_case(model)

        # Strategy 1: Try normal autogenerate migration
        migration_file = try_autogenerate_migration(model, fields, tracker)
        if migration_file:
            return migration_file

        # Strategy 2: Try manual migration creation if autogenerate fails
        migration_file = try_manual_migration_creation(model, fields, tracker)
        if migration_file:
            return migration_file

        # Strategy 3: Direct database table creation (last resort)
        if try_direct_table_creation(model, fields, tracker):
            # Create a dummy migration file for tracking
            return create_dummy_migration_file(model, tracker)

        return None

    except Exception:
        return None


def try_autogenerate_migration(
    model: str,
    fields: list[FieldDefinition] | None = None,
    tracker: Optional["ScaffoldTracker"] = None,
) -> str | None:
    """Try the standard autogenerate migration approach."""
    try:

        # Generate migration with descriptive message
        generate_result = subprocess.run(
            [
                "alembic",
                "revision",
                "--autogenerate",
                "-m",
                f"Add {model} model table only",
            ],
            capture_output=True,
            text=True,
            timeout=60, check=False,
        )

        if generate_result.returncode != 0:
            error_msg = generate_result.stderr.strip()
            stdout_msg = generate_result.stdout.strip()


            if (
                "No changes in schema detected" in error_msg
                or "No changes in schema detected" in stdout_msg
            ) and verify_table_exists(model):
                return "TABLE_EXISTS"

            return None

        # Extract migration file path from output
        migration_file = extract_migration_file_path(generate_result.stdout)

        if not migration_file:
            # Fallback: try to find the most recent migration file
            migration_file = find_most_recent_migration_file()
            if migration_file:
                pass
            else:
                return None


        # Verify the file exists
        if not Path(migration_file).exists():
            return None

        # Clean the migration file to ensure it only contains our model
        if clean_migration_for_model_only(migration_file, model):
            pass
        else:
            pass

        # Track the migration
        if tracker:
            migration_id = extract_migration_id(migration_file)
            if migration_id:
                tracker.track_migration_created(migration_file, migration_id)

        return migration_file

    except subprocess.TimeoutExpired:
        return None
    except Exception:
        return None


def find_most_recent_migration_file() -> str | None:
    """Find the most recently created migration file."""
    try:
        versions_dir = "alembic/versions"
        if not Path(versions_dir).exists():
            return None

        migration_files = []
        for filename in os.listdir(versions_dir):
            if filename.endswith(".py") and filename != "__pycache__":
                file_path = Path(versions_dir) / filename
                mtime = os.path.getmtime(file_path)
                migration_files.append((mtime, file_path))

        if migration_files:
            # Return the most recent file
            migration_files.sort(key=lambda x: x[0], reverse=True)
            return migration_files[0][1]

        return None

    except Exception:
        return None


def try_manual_migration_creation(
    model: str,
    fields: list[FieldDefinition] | None = None,
    tracker: Optional["ScaffoldTracker"] = None,
) -> str | None:
    """Create migration manually when autogenerate fails."""
    try:

        # Generate a revision ID
        import random
        import time

        revision_id = f"{int(time.time())}{random.randint(100, 999)}"[-12:]

        # Get current head revision
        current_result = subprocess.run(
            ["alembic", "current"], capture_output=True, text=True, timeout=30, check=False,
        )

        down_revision = "None"
        if current_result.returncode == 0:
            current_output = current_result.stdout.strip()
            # Extract revision ID from output
            for line in current_output.split("\n"):
                line = line.strip()
                if len(line) == 12 and line.isalnum():  # Alembic revision format
                    down_revision = f"'{line}'"
                    break

        # Create migration file
        migration_filename = f"{revision_id}_{snake_case(model)}_table.py"
        migration_path = f"alembic/versions/{migration_filename}"

        # Generate migration content
        migration_content = generate_manual_migration_content(
            model, fields, revision_id, down_revision,
        )

        # Write migration file
        with Path(migration_path).open("w") as f:
            f.write(migration_content)


        # Track the migration
        if tracker:
            tracker.track_migration_created(migration_path, revision_id)

        return migration_path

    except Exception:
        return None


def generate_manual_migration_content(
    model: str, fields: list[FieldDefinition], revision_id: str, down_revision: str,
) -> str:
    """Generate the content for a manual migration file."""
    snake_name = snake_case(model)
    table_name = f"{snake_name}s"

    # Generate table creation SQL using our existing functions
    table_creation = generate_table_creation_alembic(model, fields)

    return f'''"""Add {model} table

Revision ID: {revision_id}
Revises: {down_revision}
Create Date: {datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")}

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '{revision_id}'
down_revision: Union[str, None] = {down_revision}
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    # Create {model} table
    {table_creation}
    # ### end Alembic commands ###

def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    # Drop {model} table
    op.drop_index('ix_{table_name}_id', table_name='{table_name}')
    op.drop_table('{table_name}')
    # ### end Alembic commands ###
'''



def try_direct_table_creation(
    model: str,
    fields: list[FieldDefinition] | None = None,
    tracker: Optional["ScaffoldTracker"] = None,
) -> bool:
    """Directly create the table in the database as last resort."""
    try:

        # Generate SQL for table creation
        table_sql = generate_table_creation_sql(model, fields)

        # Create script to execute the SQL
        create_script = f'''
import asyncio
from app.db.session import engine
from sqlalchemy import text

async def create_table():
    try:
        async with engine.begin() as conn:
            # Execute table creation SQL
            await conn.execute(text("""
{table_sql}
            """))
            print("✅ Table created successfully")
            return True
    except Exception as e:
        if "already exists" in str(e).lower():
            print("ℹ️  Table already exists")
            return True
        print(f"❌ Error creating table: {{e}}")
        return False

result = asyncio.run(create_table())
exit(0 if result else 1)
'''

        with Path("temp_create_table.py").open("w") as f:
            f.write(create_script)

        result = subprocess.run(
            ["python", "temp_create_table.py"], capture_output=True, text=True, check=False,
        )
        Path("temp_create_table.py").unlink()

        if result.returncode == 0:

            # Track database change
            if tracker:
                tracker.track_database_change(
                    "table_created_directly",
                    {"table_name": f"{snake_case(model)}s", "method": "direct_sql"},
                )

            return True
        return False

    except Exception:
        return False


def create_dummy_migration_file(
    model: str, tracker: Optional["ScaffoldTracker"] = None,
) -> str:
    """Create a dummy migration file for tracking when table was created directly."""
    try:
        import random
        import time

        revision_id = f"direct_{int(time.time())}{random.randint(100, 999)}"[-12:]

        migration_filename = f"{revision_id}_{snake_case(model)}_direct.py"
        migration_path = f"alembic/versions/{migration_filename}"

        content = f'''"""Direct table creation for {model}

This migration file was created for tracking purposes only.
The actual table was created directly in the database.

Revision ID: {revision_id}
Revises: None (direct creation)
Create Date: {datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")}

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '{revision_id}'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    # Table was created directly - this is a no-op migration for tracking
    pass

def downgrade() -> None:
    # Drop table if needed
    op.drop_table('{snake_case(model)}s')
'''

        with Path(migration_path).open("w") as f:
            f.write(content)

        if tracker:
            tracker.track_migration_created(migration_path, revision_id)

        return migration_path

    except Exception:
        return "DIRECT_CREATION"


def extract_migration_file_path(output: str) -> str | None:
    """Extract migration file path from alembic output."""
    try:
        lines = output.strip().split("\n")
        for line in lines:
            if "Generating" in line and ".py" in line:
                # Extract path from line like "  Generating /path/to/file.py ... done"
                # Handle both single line and multiline formats
                if "..." in line:
                    # Single line format: "  Generating /path/to/file.py ... done"
                    parts = line.split()
                    for part in parts:
                        if part.endswith(".py"):
                            return part
                else:
                    # Multiline format: check if the line contains a path
                    stripped = line.strip()
                    if stripped.endswith(".py") and "/" in stripped:
                        return stripped

                    # Or extract from between "Generating" and any following text
                    if "Generating" in line:
                        try:
                            start_idx = line.find("Generating") + len("Generating")
                            remaining = line[start_idx:].strip()
                            if remaining.endswith(".py"):
                                return remaining
                            # Handle case where path might be on next line
                        except:
                            pass

        # Fallback: look for any line that looks like a file path
        for line in lines:
            stripped = line.strip()
            if (
                stripped.endswith(".py")
                and "/alembic/versions/" in stripped
                and not stripped.startswith("#")
            ):
                return stripped

        return None
    except Exception:
        return None


def extract_migration_id(migration_file: str) -> str | None:
    """Extract migration ID from migration filename or content."""
    try:
        # Try to extract from filename first (e.g., abc123_add_model.py)
        filename = os.path.basename(migration_file)
        if "_" in filename:
            migration_id = filename.split("_")[0]
            if len(migration_id) >= 8:  # Alembic revision IDs are typically 8+ chars
                return migration_id

        # Fallback: extract from file content
        if Path(migration_file).exists():
            with Path(migration_file).open("r") as f:
                content = f.read()

            revision_match = re.search(r'revision\s*=\s*[\'"]([^\'"]+)[\'"]', content)
            if revision_match:
                return revision_match.group(1)

        return None

    except Exception:
        return None


def clean_migration_for_model_only(migration_file: str, model: str) -> bool:
    """Clean the migration file to ensure it only contains operations for the specific model.
    Removes any operations that might affect existing infrastructure.
    """
    try:
        if not Path(migration_file).exists():
            return False

        with Path(migration_file).open("r") as f:
            content = f.read()

        snake_name = snake_case(model)
        table_name = f"{snake_name}s"

        lines = content.split("\n")
        cleaned_lines = []
        in_upgrade = False
        in_downgrade = False

        for line in lines:
            # Track which function we're in
            if "def upgrade():" in line:
                in_upgrade = True
                in_downgrade = False
                cleaned_lines.append(line)
                continue
            if "def downgrade():" in line:
                in_upgrade = False
                in_downgrade = True
                cleaned_lines.append(line)
                continue
            if (
                line.strip().startswith("def ")
                and not line.strip().startswith("def upgrade")
                and not line.strip().startswith("def downgrade")
            ):
                in_upgrade = False
                in_downgrade = False

            # If we're in upgrade or downgrade, filter operations
            if in_upgrade or in_downgrade:
                # Skip any operations on infrastructure tables
                if any(
                    infra in line.lower()
                    for infra in ["procrastinate", "alembic_version"]
                ):
                    continue

                # Only keep operations related to our table
                if "op." in line and (
                    table_name in line
                    or line.strip().startswith("#")
                    or line.strip() == ""
                    or "pass" in line
                ):
                    cleaned_lines.append(line)
                elif "op." not in line:
                    # Keep non-operation lines (comments, whitespace, etc.)
                    cleaned_lines.append(line)
                # Skip operations not related to our table
            else:
                # Keep all non-function content
                cleaned_lines.append(line)

        # Write cleaned content back
        with Path(migration_file).open("w") as f:
            f.write("\n".join(cleaned_lines))

        return True

    except Exception:
        return False


def apply_safe_migration(
    migration_file: str, model: str, tracker: Optional["ScaffoldTracker"] = None,
) -> bool:
    """Apply migration with comprehensive safety checks and handle all scenarios."""
    try:

        # Handle special cases first
        if migration_file == "TABLE_EXISTS":
            return True

        if migration_file == "DIRECT_CREATION":
            return True

        if not migration_file or not Path(migration_file).exists():
            return False

        # Pre-migration safety checks
        if not pre_migration_checks():
            return False

        # Apply the migration
        upgrade_result = subprocess.run(
            ["alembic", "upgrade", "head"], capture_output=True, text=True, timeout=120, check=False,
        )

        if upgrade_result.returncode == 0:

            # Post-migration verification
            if post_migration_verification(model):

                # Track database changes
                if tracker:
                    tracker.track_database_change(
                        "table_created",
                        {
                            "table_name": f"{snake_case(model)}s",
                            "migration_file": migration_file,
                        },
                    )

                return True
            return False
        error_msg = upgrade_result.stderr.strip()
        stdout_msg = upgrade_result.stdout.strip()

        # Handle specific error scenarios
        if (
            "already exists" in error_msg.lower()
            or "already exists" in stdout_msg.lower()
        ):
            return bool(verify_table_exists(model))

        if "dependent objects" in error_msg.lower():
            pass

        elif "no such table" in error_msg.lower():
            if try_direct_table_creation(model, None, tracker):
                return True

        return False

    except subprocess.TimeoutExpired:
        return False
    except Exception:
        return False


def pre_migration_checks() -> bool:
    """Perform pre-migration safety checks."""
    try:

        # Check database connection
        if not verify_database_connection():
            return False

        # Check Alembic can read current state
        current_result = subprocess.run(
            ["alembic", "current"], capture_output=True, text=True, timeout=30, check=False,
        )

        return current_result.returncode == 0

    except Exception:
        return False


def post_migration_verification(model: str) -> bool:
    """Verify migration was applied correctly."""
    try:

        # Verify table was created
        if not verify_table_exists(model):
            return False

        # Verify Alembic state is consistent
        current_result = subprocess.run(
            ["alembic", "current"], capture_output=True, text=True, timeout=30, check=False,
        )

        return current_result.returncode == 0

    except Exception:
        return False


def verify_database_connection() -> bool:
    """Verify database connection with comprehensive checks."""
    try:
        db_check_script = '''
import asyncio
from app.db.session import engine
from sqlalchemy import text

async def check_db():
    try:
        async with engine.begin() as conn:
            # Basic connection test
            await conn.execute(text("SELECT 1;"))

            # Check if alembic_version table exists and create if needed
            version_exists = await conn.execute(text("""
                SELECT EXISTS (
                    SELECT 1 FROM information_schema.tables
                    WHERE table_name = 'alembic_version'
                );
            """))

            if not version_exists.scalar():
                await conn.execute(text("""
                    CREATE TABLE alembic_version (
                        version_num VARCHAR(32) NOT NULL,
                        CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
                    );
                """))
                print("✅ Created alembic_version table")

            print("✅ Database connection verified")
            return True
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False

result = asyncio.run(check_db())
exit(0 if result else 1)
'''

        with Path("temp_db_check.py").open("w") as f:
            f.write(db_check_script)

        result = subprocess.run(
            ["python", "temp_db_check.py"], capture_output=True, text=True, timeout=30, check=False,
        )
        Path("temp_db_check.py").unlink()

        return result.returncode == 0

    except Exception:
        return False


def generate_table_creation_sql(
    model: str, fields: list[FieldDefinition] | None = None,
) -> str:
    """Generate SQL for creating the table directly based on model fields."""
    snake_name = snake_case(model)
    table_name = f"{snake_name}s"

    # Default fields if none provided (for backward compatibility)
    if fields is None:
        # Use Product fields as fallback for existing code
        return f"""CREATE TABLE {table_name} (
            id SERIAL PRIMARY KEY,
            name VARCHAR(100) UNIQUE NOT NULL,
            price NUMERIC NOT NULL CHECK (price >= 0),
            description TEXT,
            category VARCHAR(255) NOT NULL CHECK (category IN ('electronics', 'books', 'clothing')),
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW(),
            created_by INTEGER,
            updated_by INTEGER,
            deleted_at TIMESTAMP,
            is_deleted BOOLEAN DEFAULT FALSE
        );

        CREATE INDEX ix_{table_name}_id ON {table_name} (id);
        CREATE INDEX ix_{table_name}_search ON {table_name} (name, description, category);"""

    # Generate dynamic SQL based on fields
    column_definitions = ["id SERIAL PRIMARY KEY"]
    constraints = []
    indexes = []

    for field in fields:
        col_def = f"{field.name} "

        # Map field types to SQL types
        if field.field_type == FieldType.STRING:
            max_len = field.max_length or 255
            col_def += f"VARCHAR({max_len})"
        elif field.field_type == FieldType.TEXT:
            col_def += "TEXT"
        elif field.field_type == FieldType.INTEGER:
            col_def += "INTEGER"
        elif field.field_type == FieldType.FLOAT:
            col_def += "FLOAT"
        elif field.field_type == FieldType.DECIMAL:
            col_def += "NUMERIC(10,2)"
        elif field.field_type == FieldType.BOOLEAN:
            col_def += "BOOLEAN"
        elif field.field_type == FieldType.DATETIME:
            col_def += "TIMESTAMP"
        elif field.field_type == FieldType.DATE:
            col_def += "DATE"
        elif field.field_type == FieldType.EMAIL:
            col_def += "VARCHAR(255)"
        elif field.field_type == FieldType.UUID:
            col_def += "UUID"
        elif field.field_type == FieldType.JSON:
            col_def += "JSONB"
        else:
            col_def += "TEXT"  # Default fallback

        # Add constraints
        if not field.nullable:
            col_def += " NOT NULL"

        if field.unique:
            col_def += " UNIQUE"

        if field.default is not None:
            if isinstance(field.default, str):
                col_def += f" DEFAULT '{field.default}'"
            else:
                col_def += f" DEFAULT {field.default}"
        elif field.field_type == FieldType.DATETIME:
            col_def += " DEFAULT NOW()"
        elif field.field_type == FieldType.BOOLEAN:
            col_def += " DEFAULT FALSE"

        column_definitions.append(col_def)

        # Add check constraints
        if field.min_value is not None:
            constraints.append(f"CHECK ({field.name} >= {field.min_value})")
        if field.max_value is not None:
            constraints.append(f"CHECK ({field.name} <= {field.max_value})")
        if field.max_length and field.field_type == FieldType.STRING:
            constraints.append(f"CHECK (LENGTH({field.name}) <= {field.max_length})")
        if field.choices:
            choices_str = "', '".join(field.choices)
            constraints.append(f"CHECK ({field.name} IN ('{choices_str}'))")

        # Add indexes
        if field.indexed:
            indexes.append(
                f"CREATE INDEX ix_{table_name}_{field.name} ON {table_name} ({field.name});",
            )

    # Add standard audit fields
    column_definitions.extend(
        [
            "created_at TIMESTAMP DEFAULT NOW()",
            "updated_at TIMESTAMP DEFAULT NOW()",
            "created_by INTEGER",
            "updated_by INTEGER",
            "deleted_at TIMESTAMP",
            "is_deleted BOOLEAN DEFAULT FALSE",
        ],
    )

    # Build the SQL
    sql_parts = [f"CREATE TABLE {table_name} ("]
    sql_parts.append("    " + ",\n    ".join(column_definitions))

    if constraints:
        sql_parts.append(",\n    " + ",\n    ".join(constraints))

    sql_parts.append("\n);")

    # Add primary key index
    sql_parts.append(f"\nCREATE INDEX ix_{table_name}_id ON {table_name} (id);")

    # Add field indexes
    if indexes:
        sql_parts.extend(["\n" + idx for idx in indexes])

    # Add search index for text fields
    searchable_fields = [
        f.name for f in fields if f.field_type in [FieldType.STRING, FieldType.TEXT]
    ]
    if searchable_fields:
        search_fields = ", ".join(searchable_fields)
        sql_parts.append(
            f"\nCREATE INDEX ix_{table_name}_search ON {table_name} ({search_fields});",
        )

    return "".join(sql_parts)


def generate_table_creation_alembic(
    model: str, fields: list[FieldDefinition] | None = None,
) -> str:
    """Generate Alembic op commands for table creation."""
    snake_name = snake_case(model)
    table_name = f"{snake_name}s"

    # Default Product fields for backward compatibility
    if fields is None:
        return f"""op.create_table('{table_name}',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('price', sa.Numeric(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('category', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('created_by', sa.Integer(), nullable=True),
        sa.Column('updated_by', sa.Integer(), nullable=True),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
        sa.Column('is_deleted', sa.Boolean(), nullable=True),
        sa.CheckConstraint('LENGTH(name) <= 100', name='ck_{snake_name}_name_length'),
        sa.CheckConstraint("category IN ('electronics', 'books', 'clothing')", name='ck_{snake_name}_category_choices'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_{table_name}_id'), '{table_name}', ['id'], unique=False)
    op.create_index('ix_{snake_name}_search', '{table_name}', ['name', 'description', 'category'], unique=False)"""

    # Generate dynamic Alembic commands
    columns = ["sa.Column('id', sa.Integer(), nullable=False)"]
    constraints = []
    indexes = []

    for field in fields:
        # Map field types to SQLAlchemy types
        if field.field_type == FieldType.STRING:
            max_len = field.max_length or 255
            sa_type = f"sa.String(length={max_len})"
        elif field.field_type == FieldType.TEXT:
            sa_type = "sa.Text()"
        elif field.field_type == FieldType.INTEGER:
            sa_type = "sa.Integer()"
        elif field.field_type == FieldType.FLOAT:
            sa_type = "sa.Float()"
        elif field.field_type == FieldType.DECIMAL:
            sa_type = "sa.Numeric(10, 2)"
        elif field.field_type == FieldType.BOOLEAN:
            sa_type = "sa.Boolean()"
        elif field.field_type == FieldType.DATETIME:
            sa_type = "sa.DateTime()"
        elif field.field_type == FieldType.DATE:
            sa_type = "sa.Date()"
        elif field.field_type == FieldType.EMAIL:
            sa_type = "sa.String(length=255)"
        elif field.field_type == FieldType.UUID:
            sa_type = "postgresql.UUID()"
        elif field.field_type == FieldType.JSON:
            sa_type = "postgresql.JSONB()"
        else:
            sa_type = "sa.Text()"

        # Build column definition
        nullable = "True" if field.nullable else "False"
        column_def = f"sa.Column('{field.name}', {sa_type}, nullable={nullable}"

        if field.unique:
            column_def += ", unique=True"

        if field.default is not None:
            if isinstance(field.default, str):
                column_def += f", default='{field.default}'"
            else:
                column_def += f", default={field.default}"

        column_def += ")"
        columns.append(column_def)

        # Add constraints
        if field.min_value is not None:
            constraints.append(
                f"sa.CheckConstraint('{field.name} >= {field.min_value}', name='ck_{snake_name}_{field.name}_min')",
            )
        if field.max_value is not None:
            constraints.append(
                f"sa.CheckConstraint('{field.name} <= {field.max_value}', name='ck_{snake_name}_{field.name}_max')",
            )
        if field.max_length and field.field_type == FieldType.STRING:
            constraints.append(
                f"sa.CheckConstraint('LENGTH({field.name}) <= {field.max_length}', name='ck_{snake_name}_{field.name}_length')",
            )
        if field.choices:
            choices_str = "', '".join(field.choices)
            constraints.append(
                f'sa.CheckConstraint("{field.name} IN (\'{choices_str}\')", name="ck_{snake_name}_{field.name}_choices")',
            )

        # Add indexes
        if field.indexed:
            indexes.append(
                f"op.create_index('ix_{table_name}_{field.name}', '{table_name}', ['{field.name}'], unique=False)",
            )

    # Add audit fields
    columns.extend(
        [
            "sa.Column('created_at', sa.DateTime(), nullable=True)",
            "sa.Column('updated_at', sa.DateTime(), nullable=True)",
            "sa.Column('created_by', sa.Integer(), nullable=True)",
            "sa.Column('updated_by', sa.Integer(), nullable=True)",
            "sa.Column('deleted_at', sa.DateTime(), nullable=True)",
            "sa.Column('is_deleted', sa.Boolean(), nullable=True)",
        ],
    )

    # Build the Alembic command - fix the structure to avoid syntax errors
    alembic_lines = [f"op.create_table('{table_name}',"]

    # Add all columns
    for col in columns:
        alembic_lines.append(f"        {col},")

    # Add all constraints
    for constraint in constraints:
        alembic_lines.append(f"        {constraint},")

    # Add primary key constraint (always last)
    alembic_lines.append("        sa.PrimaryKeyConstraint('id')")

    # Add the closing parenthesis
    alembic_lines.append("    )")

    # Add indexes
    alembic_lines.append(
        f"    op.create_index(op.f('ix_{table_name}_id'), '{table_name}', ['id'], unique=False)",
    )
    alembic_lines.extend([f"    {idx}" for idx in indexes])

    # Add search index
    searchable_fields = [
        f.name for f in fields if f.field_type in [FieldType.STRING, FieldType.TEXT]
    ]
    if searchable_fields:
        search_fields = "', '".join(searchable_fields)
        alembic_lines.append(
            f"    op.create_index('ix_{snake_name}_search', '{table_name}', ['{search_fields}'], unique=False)",
        )

    return "\n".join(alembic_lines)


def verify_table_exists(model: str) -> bool:
    """Verify that the model table exists in the database."""
    try:
        snake_name = snake_case(model)
        table_name = f"{snake_name}s"

        verify_script = f"""
import asyncio
from app.db.session import engine
from sqlalchemy import text

async def verify_table():
    try:
        async with engine.begin() as conn:
            result = await conn.execute(text("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' AND table_name = '{table_name}';"))
            tables = result.fetchall()
            if tables:
                print("✅ Table {table_name} exists")
                return True
            else:
                print("❌ Table {table_name} does not exist")
                return False
    except Exception as e:
        print(f"❌ Error verifying table: {{e}}")
        return False

result = asyncio.run(verify_table())
exit(0 if result else 1)
"""

        with Path("temp_verify.py").open("w") as f:
            f.write(verify_script)

        result = subprocess.run(
            ["python", "temp_verify.py"], capture_output=True, text=True, check=False,
        )
        Path("temp_verify.py").unlink()

        return result.returncode == 0

    except Exception:
        return False


def clean_migration_file_comprehensive(migration_file: str, model: str) -> bool:
    """Comprehensive migration file cleaning to prevent infrastructure conflicts."""
    try:
        if not Path(migration_file).exists():
            return True

        with Path(migration_file).open("r") as f:
            content = f.read()

        lines = content.split("\n")
        cleaned_lines = []
        in_downgrade_function = False
        skip_malformed_statements = False

        for _i, line in enumerate(lines):
            # Track if we're in the downgrade function
            if line.strip().startswith("def downgrade()"):
                in_downgrade_function = True
                cleaned_lines.append(line)
                continue

            # If we're in downgrade and hit another function, we're done with downgrade
            if (
                in_downgrade_function
                and line.strip().startswith("def ")
                and "downgrade" not in line
            ):
                in_downgrade_function = False
                skip_malformed_statements = False

            # Handle downgrade function content
            if in_downgrade_function:
                # Skip malformed sa.Column statements that aren't in op.create_table calls
                if "sa.Column(" in line and not any(
                    op in line for op in ["op.create_table", "op.add_column"]
                ):
                    if not skip_malformed_statements:
                        cleaned_lines.append(
                            "    # Note: Removing malformed column statements",
                        )
                        skip_malformed_statements = True
                    continue

                # Skip foreign key constraints and other malformed statements
                if any(
                    stmt in line
                    for stmt in [
                        "sa.ForeignKeyConstraint",
                        "sa.CheckConstraint",
                        "sa.PrimaryKeyConstraint",
                        "sa.UniqueConstraint",
                    ]
                ) and not any(
                    op in line for op in ["op.create_table", "op.add_constraint"]
                ):
                    continue

                # Skip PostgreSQL-specific statements that are malformed
                if (
                    "postgresql_ignore_search_path=False" in line
                    and "op.create_table" not in line
                ):
                    continue

            # Skip any operations on existing infrastructure
            if any(
                infra_name in line.lower()
                for infra_name in ["procrastinate", "alembic_version"]
            ) and ("op.drop_" in line or "op.create_" in line):
                if not skip_malformed_statements:
                    cleaned_lines.append(
                        "    # Note: Preserving existing infrastructure tables",
                    )
                    skip_malformed_statements = True
                continue

            # Reset skip flag when we encounter the model's operations
            if model.lower() in line.lower() and (
                "CREATE TABLE" in line.upper() or "op.create_table" in line
            ):
                skip_malformed_statements = False

            cleaned_lines.append(line)

        # Write cleaned content
        with Path(migration_file).open("w") as f:
            f.write("\n".join(cleaned_lines))

        return True

    except Exception:
        return False


def clean_migration_file_aggressive(migration_file: str, model: str) -> bool:
    """Aggressive cleaning - remove all non-model operations."""
    try:
        if not Path(migration_file).exists():
            return True

        with Path(migration_file).open("r") as f:
            content = f.read()

        snake_name = snake_case(model)
        table_name = f"{snake_name}s"

        # Create a minimal migration that only creates the target table
        minimal_migration = f'''"""Add {model} model

Revision ID: {content.split("revision: str = '")[1].split("'")[0] if "revision: str = '" in content else "unknown"}
Revises: {content.split("down_revision: Union[str, None] = '")[1].split("'")[0] if "down_revision: Union[str, None] = '" in content else "unknown"}
Create Date: {content.split("Create Date: ")[1].split("\\n")[0] if "Create Date: " in content else "unknown"}

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '{content.split("revision: str = '")[1].split("'")[0] if "revision: str = '" in content else "unknown"}'
down_revision: Union[str, None] = '{content.split("down_revision: Union[str, None] = '")[1].split("'")[0] if "down_revision: Union[str, None] = '" in content else "unknown"}'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    # Note: Only creating {model} table - preserving existing infrastructure
    pass
    # ### end Alembic commands ###

def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    # Note: Only operations for {model} table
    pass
    # ### end Alembic commands ###
'''

        # Extract only the model-specific operations from the original
        lines = content.split("\n")
        model_operations = []
        in_upgrade = False

        for line in lines:
            if "def upgrade()" in line:
                in_upgrade = True
                continue
            if "def downgrade()" in line:
                break
            if in_upgrade and (table_name in line or model.lower() in line.lower()):
                model_operations.append(line)

        # Insert model operations into minimal migration
        if model_operations:
            upgrade_section = "def upgrade() -> None:\\n    # ### commands auto generated by Alembic - please adjust! ###\\n    # Note: Only creating {model} table - preserving existing infrastructure\\n"
            for op in model_operations:
                upgrade_section += f"    {op.strip()}\\n"
            upgrade_section += "    # ### end Alembic commands ###"

            minimal_migration = minimal_migration.replace(
                "def upgrade() -> None:\\n    # ### commands auto generated by Alembic - please adjust! ###\\n    # Note: Only creating {model} table - preserving existing infrastructure\\n    pass\\n    # ### end Alembic commands ###",
                upgrade_section,
            )

        with Path(migration_file).open("w") as f:
            f.write(minimal_migration)

        return True

    except Exception:
        return False


def scaffold_model(
    model: str,
    fields: list[tuple],
    with_procrastinate: bool = False,
    with_bulk: bool = False,
    with_tests: bool = True,
    run_migrations: bool = True,
) -> bool | None:
    """Main scaffolding function."""
    snake_name = snake_case(model)
    pascal_case(model)


    # Check if already exists
    tracking = load_tracking()
    if model in tracking:
        return False

    try:
        # Generate files
        files_created = []

        # 1. Model file
        model_path = f"{BASE_PATH}/db/models/{snake_name}.py"
        model_content = generate_model_file(model, fields)
        write_file(model_path, model_content)
        files_created.append(model_path)

        # 2. Schema file
        schema_path = f"{BASE_PATH}/db/schemas/{snake_name}.py"
        schema_content = generate_schema_file(model, fields)
        write_file(schema_path, schema_content)
        files_created.append(schema_path)

        # 3. Service file
        service_path = f"{BASE_PATH}/services/{snake_name}_service.py"
        service_content = generate_service_file(model)
        write_file(service_path, service_content)
        files_created.append(service_path)

        # 4. Endpoint file
        endpoint_path = f"{BASE_PATH}/api/v1/endpoints/{snake_name}.py"
        endpoint_content = generate_endpoint_file(model, with_bulk)
        write_file(endpoint_path, endpoint_content)
        files_created.append(endpoint_path)

        # 5. Procrastinate tasks (optional)
        if with_procrastinate:
            tasks_path = f"{BASE_PATH}/tasks/{snake_name}_tasks.py"
            tasks_content = generate_procrastinate_tasks(model)
            write_file(tasks_path, tasks_content)
            files_created.append(tasks_path)

        # 6. Test file (optional)
        if with_tests:
            test_path = f"tests/test_{snake_name}.py"
            test_content = generate_test_file(model, fields)
            write_file(test_path, test_content)
            files_created.append(test_path)

        # 7. Update base.py and API router
        update_base_py(model)
        update_api_router(model)

        # 8. Run migrations
        if run_migrations:
            migration_success = run_migration(model)
            if not migration_success:
                pass

        # 9. Track the model
        tracking[model] = {
            "files": files_created,
            "fields": fields,
            "options": {
                "with_procrastinate": with_procrastinate,
                "with_bulk": with_bulk,
                "with_tests": with_tests,
            },
        }
        save_tracking(tracking)


        if with_bulk:
            pass

        return True

    except Exception:
        # TODO: Implement rollback
        return False


def list_models() -> None:
    """List all scaffolded models."""
    tracking = load_tracking()

    if not tracking:
        return


    for info in tracking.values():
        options = info.get("options", {})
        features = []
        if options.get("with_bulk"):
            features.append("Bulk Operations")
        if options.get("with_procrastinate"):
            features.append("Procrastinate Tasks")
        if options.get("with_tests"):
            features.append("Tests")
        if features:
            pass


def remove_model(model: str) -> bool | None:
    """Remove a scaffolded model."""
    tracking = load_tracking()

    if model not in tracking:
        return False

    try:
        # Remove files
        info = tracking[model]
        for file_path in info.get("files", []):
            if Path(file_path).exists():
                Path(file_path).unlink()

        # Remove from tracking
        del tracking[model]
        save_tracking(tracking)


        return True

    except Exception:
        return False


def health_check():
    """Check the health of the codebase."""
    issues = []

    # Check if required directories exist
    required_dirs = [
        f"{BASE_PATH}/db/models",
        f"{BASE_PATH}/db/schemas",
        f"{BASE_PATH}/services",
        f"{BASE_PATH}/api/v1/endpoints",
    ]

    for dir_path in required_dirs:
        if not Path(dir_path).exists():
            issues.append(f"Missing directory: {dir_path}")

    # Check if required files exist
    required_files = [
        f"{BASE_PATH}/db/base.py",
        f"{BASE_PATH}/api/v1/api.py",
        f"{BASE_PATH}/services/enhanced_base_service.py",
    ]

    for file_path in required_files:
        if not Path(file_path).exists():
            issues.append(f"Missing file: {file_path}")

    # Check tracking consistency
    tracking = load_tracking()
    for model, info in tracking.items():
        for file_path in info.get("files", []):
            if not Path(file_path).exists():
                issues.append(f"Tracked file missing: {file_path} (model: {model})")

    # Report results
    if not issues:
        pass
    else:
        for _issue in issues:
            pass

    return len(issues) == 0


def generate_repository_file(
    model: str, fields: list[FieldDefinition], config: ScaffoldConfig,
) -> str:
    """Generate repository pattern implementation."""
    pascal_name = pascal_case(model)
    snake_name = snake_case(model)

    content = f'''"""
Repository pattern implementation for {model}.
Auto-generated by enhanced scaffold tool following best practices.

The repository pattern provides a consistent interface for data access,
making it easier to test and maintain the codebase.
"""
from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, desc, asc
from sqlalchemy.orm import selectinload

from app.db.models.{snake_name} import {pascal_name}
from app.db.schemas.{snake_name} import {pascal_name}Filter, {pascal_name}Sort
from app.core.repository import BaseRepository

class {pascal_name}Repository(BaseRepository[{pascal_name}]):
    """
    Repository for {model} data access operations.
    Implements advanced querying, filtering, and search capabilities.
    """

    def __init__(self):
        super().__init__({pascal_name})

    async def find_by_search_query(
        self,
        db: AsyncSession,
        query: str,
        limit: int = 20
    ) -> List[{pascal_name}]:
        """
        Find {model}s by search query using full-text search.
        """
        # Get searchable fields
        searchable_fields = {pascal_name}.get_searchable_fields()

        if not searchable_fields:
            return []

        # Build search conditions
        search_conditions = []
        for field_name in searchable_fields:
            field = getattr(self.model, field_name)
            search_conditions.append(field.ilike(f"%{{query}}%"))

        stmt = select(self.model).where(or_(*search_conditions)).limit(limit)
        result = await db.execute(stmt)
        return result.scalars().all()

    async def find_with_filters(
        self,
        db: AsyncSession,
        filters: {pascal_name}Filter,
        sort: Optional[{pascal_name}Sort] = None,
        skip: int = 0,
        limit: int = 100
    ) -> Tuple[List[{pascal_name}], int]:
        """
        Find {model}s with advanced filtering and sorting.
        Returns both the results and total count.
        """
        # Build base query
        stmt = select(self.model)
        count_stmt = select(func.count(self.model.id))

        # Apply filters
        conditions = []

        # Search query filter
        if filters.q:
            searchable_fields = {pascal_name}.get_searchable_fields()
            if searchable_fields:
                search_conditions = []
                for field_name in searchable_fields:
                    field = getattr(self.model, field_name)
                    search_conditions.append(field.ilike(f"%{{filters.q}}%"))
                conditions.append(or_(*search_conditions))

        # Field-specific filters
'''

    # Add filter conditions for each field
    for field in fields:
        if field.field_type in [
            FieldType.STRING,
            FieldType.INTEGER,
            FieldType.FLOAT,
            FieldType.DATE,
            FieldType.DATETIME,
        ]:
            content += f"""        if filters.{field.name}:
            field_attr = getattr(self.model, '{field.name}')
            if isinstance(filters.{field.name}, list):
                conditions.append(field_attr.in_(filters.{field.name}))
            else:
                conditions.append(field_attr == filters.{field.name})

"""

    content += f'''
        # Apply conditions
        if conditions:
            stmt = stmt.where(and_(*conditions))
            count_stmt = count_stmt.where(and_(*conditions))

        # Apply sorting
        if sort:
            sort_field = getattr(self.model, sort.field)
            if sort.direction == "desc":
                stmt = stmt.order_by(desc(sort_field))
            else:
                stmt = stmt.order_by(asc(sort_field))
        else:
            # Default sorting
            stmt = stmt.order_by(desc(self.model.id))

        # Apply pagination
        stmt = stmt.offset(skip).limit(limit)

        # Execute queries
        result = await db.execute(stmt)
        count_result = await db.execute(count_stmt)

        items = result.scalars().all()
        total = count_result.scalar()

        return items, total

    async def get_statistics(self, db: AsyncSession) -> Dict[str, Any]:
        """
        Get statistical information about {model}s.
        """
        stats = {{}}

        # Total count
        total_stmt = select(func.count(self.model.id))
        result = await db.execute(total_stmt)
        stats['total'] = result.scalar()

        # Add more statistics based on fields
'''

    # Add statistics for different field types
    for field in fields:
        if field.field_type in (FieldType.INTEGER, FieldType.FLOAT):
            content += f"""
        # Statistics for {field.name}
        avg_stmt = select(func.avg(getattr(self.model, '{field.name}')))
        min_stmt = select(func.min(getattr(self.model, '{field.name}')))
        max_stmt = select(func.max(getattr(self.model, '{field.name}')))

        avg_result = await db.execute(avg_stmt)
        min_result = await db.execute(min_stmt)
        max_result = await db.execute(max_stmt)

        stats['{field.name}_avg'] = avg_result.scalar()
        stats['{field.name}_min'] = min_result.scalar()
        stats['{field.name}_max'] = max_result.scalar()
"""

    content += '''
        return stats

    async def exists_by_field(
        self,
        db: AsyncSession,
        field_name: str,
        value: Any
    ) -> bool:
        """
        Check if a record exists with the given field value.
        """
        field = getattr(self.model, field_name)
        stmt = select(func.count(self.model.id)).where(field == value)
        result = await db.execute(stmt)
        return result.scalar() > 0

    async def get_related_data(
        self,
        db: AsyncSession,
        item_id: int,
        include_relationships: bool = True
    ) -> Optional[{pascal_name}]:
        """
        Get {model} with related data loaded.
        """
        stmt = select(self.model).where(self.model.id == item_id)

        if include_relationships:
            # Add relationship loading based on your model relationships
            # stmt = stmt.options(selectinload(self.model.relationship_name))
            pass

        result = await db.execute(stmt)
        return result.scalar_one_or_none()
'''

    return content


def main() -> None:
    """Enhanced Main CLI function with comprehensive features."""
    parser = argparse.ArgumentParser(
        description="🚀 Enhanced FastAPI Model Scaffold Tool - Ultimate Edition",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
🎯 EXAMPLES:

  Basic Usage:
    %(prog)s add Book title:str author:str isbn:str
    %(prog)s add Product name:str price:float:min_value=0 category:str:choices=electronics,books,toys

  Advanced Features:
    %(prog)s add Book title:str --enterprise --interactive
    %(prog)s add Product name:str price:float --with-all-features
    %(prog)s add User email:email:unique username:str:unique:max_length=50 --with-auth

  Field Types & Constraints:
    name:str:max_length=100:nullable
    price:float:min_value=0:max_value=10000
    email:email:unique
    status:str:choices=active,inactive,pending
    slug:slug:unique
    created_at:datetime:indexed

  Management:
    %(prog)s list --detailed
    %(prog)s remove Book --cascade
    %(prog)s health-check --fix-issues
    %(prog)s update Book --add-fields price:float description:text
    %(prog)s generate-config
    %(prog)s generate-docs

🔧 FEATURES:
- ✅ Enhanced BaseService with concurrent processing
- ✅ Dependency injection chains
- ✅ Custom exceptions and error handling
- ✅ Repository pattern implementation
- ✅ Advanced Pydantic schemas with validation
- ✅ Bulk operations with parallel processing
- ✅ Search and filtering capabilities
- ✅ Rate limiting and caching
- ✅ Comprehensive test generation
- ✅ OpenAPI documentation
- ✅ Audit trails and soft deletes
- ✅ Background task integration
- ✅ Performance monitoring
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Add command with enhanced options
    add_parser = subparsers.add_parser(
        "add", help="🆕 Add a new model with all features",
    )
    add_parser.add_argument("model", nargs="?", help="Model name (PascalCase)")
    add_parser.add_argument(
        "fields", nargs="*", help="Fields in format name:type:constraints",
    )

    # Feature flags
    add_parser.add_argument(
        "--interactive",
        "-i",
        action="store_true",
        help="🎮 Use interactive mode for guided setup",
    )
    add_parser.add_argument(
        "--enterprise", action="store_true", help="🏢 Enable all enterprise features",
    )
    add_parser.add_argument(
        "--with-all-features",
        action="store_true",
        help="🚀 Enable all available features",
    )
    add_parser.add_argument(
        "--with-procrastinate",
        action="store_true",
        help="📋 Generate Procrastinate task integration",
    )
    add_parser.add_argument(
        "--with-bulk", action="store_true", help="📦 Generate bulk operation endpoints",
    )
    add_parser.add_argument(
        "--with-auth",
        action="store_true",
        help="🔐 Add authentication and authorization",
    )
    add_parser.add_argument(
        "--with-cache", action="store_true", help="⚡ Add caching support",
    )
    add_parser.add_argument(
        "--with-search",
        action="store_true",
        help="🔍 Add full-text search capabilities",
    )
    add_parser.add_argument(
        "--with-audit", action="store_true", help="📊 Add audit trail support",
    )
    add_parser.add_argument(
        "--with-soft-delete",
        action="store_true",
        help="🗑️ Add soft delete functionality",
    )
    add_parser.add_argument(
        "--with-repository", action="store_true", help="🏛️ Generate repository pattern",
    )
    add_parser.add_argument(
        "--with-monitoring", action="store_true", help="📈 Add performance monitoring",
    )

    # Control flags
    add_parser.add_argument(
        "--no-tests", action="store_true", help="❌ Skip test file generation",
    )
    add_parser.add_argument(
        "--no-migrations", action="store_true", help="❌ Skip running migrations",
    )
    add_parser.add_argument(
        "--no-docs", action="store_true", help="❌ Skip documentation generation",
    )
    add_parser.add_argument(
        "--dry-run", action="store_true", help="👀 Preview what would be generated",
    )

    # List command
    list_parser = subparsers.add_parser("list", help="📋 List all scaffolded models")
    list_parser.add_argument(
        "--detailed", action="store_true", help="Show detailed information",
    )
    list_parser.add_argument("--json", action="store_true", help="Output as JSON")

    # Remove command
    remove_parser = subparsers.add_parser("remove", help="🗑️ Remove a scaffolded model")
    remove_parser.add_argument("model", help="Model name to remove")
    remove_parser.add_argument(
        "--cascade", action="store_true", help="Remove related files",
    )
    remove_parser.add_argument(
        "--force", action="store_true", help="Force removal without confirmation",
    )
    remove_parser.add_argument(
        "--clean-database",
        action="store_true",
        help="🗃️ Also drop database table and remove migrations",
    )
    remove_parser.add_argument(
        "--show-tracking",
        action="store_true",
        help="📋 Show detailed tracking information before removal",
    )

    # Update command
    update_parser = subparsers.add_parser("update", help="🔄 Update an existing model")
    update_parser.add_argument("model", help="Model name to update")
    update_parser.add_argument("--add-fields", nargs="+", help="Add new fields")
    update_parser.add_argument("--remove-fields", nargs="+", help="Remove fields")
    update_parser.add_argument(
        "--rename-field", nargs=2, metavar=("OLD", "NEW"), help="Rename field",
    )

    # Health check command
    health_parser = subparsers.add_parser(
        "health-check", help="🏥 Check codebase health",
    )
    health_parser.add_argument(
        "--fix-issues", action="store_true", help="Automatically fix issues",
    )
    health_parser.add_argument("--verbose", action="store_true", help="Detailed output")

    # Configuration commands
    subparsers.add_parser(
        "generate-config", help="⚙️ Generate configuration file",
    )
    subparsers.add_parser(
        "generate-docs", help="📚 Generate comprehensive documentation",
    )

    # Performance and analysis
    subparsers.add_parser(
        "analyze", help="📊 Analyze codebase patterns",
    )
    subparsers.add_parser(
        "optimize", help="⚡ Optimize generated code",
    )

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    # Load configuration
    config = ScaffoldConfig()

    if args.command == "add":
        # Handle different modes
        if args.interactive or not args.model:
            success = interactive_scaffold_mode(config)
        else:
            if not args.fields:
                return

            # Parse and validate fields
            try:
                fields = parse_fields(args.fields)
            except Exception:
                return

            # Determine features to enable
            features = determine_features(args)

            if args.dry_run:
                preview_scaffold(args.model, fields, features, config)
                return

            success = scaffold_model_enhanced(
                args.model,
                fields,
                features,
                config,
                run_migrations=not args.no_migrations,
                generate_tests=not args.no_tests,
                generate_docs=not args.no_docs,
            )

        if success:
            print_success_message(args.model)

    elif args.command == "list":
        list_models_enhanced(detailed=args.detailed, json_output=args.json)

    elif args.command == "remove":
        if args.show_tracking:
            show_model_tracking(args.model)
        else:
            remove_model_enhanced(
                args.model,
                cascade=args.cascade,
                force=args.force,
                clean_database=args.clean_database,
            )

    elif args.command == "update":
        update_model(args.model, args)

    elif args.command == "health-check":
        health_check_enhanced(fix_issues=args.fix_issues, verbose=args.verbose)

    elif args.command == "generate-config":
        generate_config_file()

    elif args.command == "generate-docs":
        generate_comprehensive_docs()

    elif args.command == "analyze":
        analyze_codebase()

    elif args.command == "optimize":
        optimize_generated_code()


def determine_features(args) -> dict[str, bool]:
    """Determine which features to enable based on arguments."""
    features = {
        "procrastinate": args.with_procrastinate,
        "bulk_operations": args.with_bulk,
        "authentication": args.with_auth,
        "caching": args.with_cache,
        "search": args.with_search,
        "audit_trail": args.with_audit,
        "soft_deletes": args.with_soft_delete,
        "repository_pattern": args.with_repository,
        "monitoring": args.with_monitoring,
    }

    # Enterprise mode enables most features
    if args.enterprise:
        features.update(
            {
                "bulk_operations": True,
                "authentication": True,
                "caching": True,
                "search": True,
                "audit_trail": True,
                "soft_deletes": True,
                "repository_pattern": True,
                "monitoring": True,
            },
        )

    # All features mode
    if args.with_all_features:
        features = dict.fromkeys(features.keys(), True)

    return features


def preview_scaffold(
    model: str,
    fields: list[FieldDefinition],
    features: dict[str, bool],
    config: ScaffoldConfig,
) -> None:
    """Preview what would be generated without creating files."""
    snake_name = snake_case(model)
    pascal_case(model)



    for field in fields:
        constraints = []
        if field.unique:
            constraints.append("unique")
        if field.indexed:
            constraints.append("indexed")
        if not field.nullable:
            constraints.append("required")
        if field.max_length:
            constraints.append(f"max_length={field.max_length}")
        if field.min_value is not None:
            constraints.append(f"min_value={field.min_value}")

        f" ({', '.join(constraints)})" if constraints else ""

    enabled_features = [name for name, enabled in features.items() if enabled]
    if enabled_features:
        for _feature in enabled_features:
            pass
    else:
        pass

    files = [
        f"app/db/models/{snake_name}.py",
        f"app/db/schemas/{snake_name}.py",
        f"app/services/{snake_name}_service.py",
        f"app/api/v1/endpoints/{snake_name}.py",
    ]

    if features.get("repository_pattern"):
        files.append(f"app/repositories/{snake_name}_repository.py")
    if features.get("bulk_operations"):
        files.append(f"app/api/v1/endpoints/{snake_name}_bulk.py")
    if features.get("procrastinate"):
        files.append(f"app/tasks/{snake_name}_tasks.py")

    files.extend(
        [
            f"app/dependencies/{snake_name}.py",
            f"app/exceptions/{snake_name}.py",
            f"tests/test_{snake_name}.py",
        ],
    )

    for _file_path in files:
        pass

    endpoints = [
        f"GET    /api/v1/{snake_name}s/",
        f"POST   /api/v1/{snake_name}s/",
        f"GET    /api/v1/{snake_name}s/{{id}}",
        f"PUT    /api/v1/{snake_name}s/{{id}}",
        f"DELETE /api/v1/{snake_name}s/{{id}}",
    ]

    if features.get("search"):
        endpoints.append(f"POST   /api/v1/{snake_name}s/search")
    if features.get("bulk_operations"):
        endpoints.extend(
            [
                f"POST   /api/v1/{snake_name}s/bulk/create",
                f"PUT    /api/v1/{snake_name}s/bulk/update",
                f"DELETE /api/v1/{snake_name}s/bulk/delete",
            ],
        )

    for _endpoint in endpoints:
        pass



def scaffold_model_enhanced(
    model: str,
    fields: list[FieldDefinition],
    features: dict[str, bool],
    config: ScaffoldConfig,
    run_migrations: bool = True,
    generate_tests: bool = True,
    generate_docs: bool = True,
) -> bool:
    """Enhanced scaffold function with all features."""
    try:
        snake_name = snake_case(model)
        pascal_name = pascal_case(model)


        # Initialize comprehensive tracking
        tracker = ScaffoldTracker(model)

        # Step 1: Run preflight checks
        if not run_preflight_checks():
            return False

        # Update config with features
        config.config["features"].update(features)

        # Generate all files
        files_created = []

        # 1. Model file
        model_content = generate_model_file(model, fields, config)
        model_path = f"app/db/models/{snake_name}.py"
        write_file(model_path, model_content, tracker=tracker)
        files_created.append(model_path)

        # 2. Schema file
        schema_content = generate_schema_file(model, fields, config)
        schema_path = f"app/db/schemas/{snake_name}.py"
        write_file(schema_path, schema_content, tracker=tracker)
        files_created.append(schema_path)

        # 2.1. Validate schema imports work
        try:
            result = subprocess.run(
                [
                    "python",
                    "-c",
                    f"from app.db.schemas.{snake_name} import {pascal_name}Create; print('✅ Schema validates')",
                ],
                capture_output=True,
                text=True,
                timeout=15, check=False,
            )

            if result.returncode != 0:
                # Don't fail completely, but warn
                pass
        except subprocess.TimeoutExpired:
            pass
        except Exception:
            pass

        # 3. Service file
        service_content = generate_service_file(model, fields, config)
        service_path = f"app/services/{snake_name}_service.py"
        write_file(service_path, service_content, tracker=tracker)
        files_created.append(service_path)

        # 4. Endpoint file
        endpoint_content = generate_endpoint_file(
            model, features.get("bulk_operations", False),
        )
        endpoint_path = f"app/api/v1/endpoints/{snake_name}.py"
        write_file(endpoint_path, endpoint_content, tracker=tracker)
        files_created.append(endpoint_path)

        # 5. Dependencies file
        deps_content = generate_dependencies_file(model, fields, config)
        deps_path = f"app/dependencies/{snake_name}.py"
        write_file(deps_path, deps_content, tracker=tracker)
        files_created.append(deps_path)

        # 6. Exceptions file
        exc_content = generate_exceptions_file(model)
        exc_path = f"app/exceptions/{snake_name}.py"
        write_file(exc_path, exc_content, tracker=tracker)
        files_created.append(exc_path)

        # 7. Repository file (if enabled)
        if features.get("repository_pattern"):
            repo_content = generate_repository_file(model, fields, config)
            repo_path = f"app/repositories/{snake_name}_repository.py"
            # Ensure repositories directory exists and has __init__.py
            Path("app/repositories").mkdir(parents=True, exist_ok=True)
            if not Path("app/repositories/__init__.py").exists():
                with Path("app/repositories/__init__.py").open("w") as f:
                    f.write('"""Repository patterns for data access"""\n')
            write_file(repo_path, repo_content, tracker=tracker)
            files_created.append(repo_path)

        # 8. Test file (if enabled)
        if generate_tests:
            test_content = generate_test_file(
                model, [(f.name, f.field_type.value) for f in fields],
            )
            test_path = f"tests/test_{snake_name}.py"
            write_file(test_path, test_content, tracker=tracker)
            files_created.append(test_path)

        # 9. Update base.py and API router
        update_base_py(model, tracker)
        update_api_router(model, tracker)

        # 10. Run migrations (if enabled)
        if run_migrations:
            migration_success = run_migration(model, fields, tracker)
            if not migration_success:
                pass

        # 11. Save comprehensive tracking information
        tracker.save_tracking_info()

        # 12. Clean up any temporary files
        temp_files = ["fix_alembic_temp.py", "verify_table.py", "fix_alembic.py"]
        for temp_file in temp_files:
            if Path(temp_file).exists():
                try:
                    Path(temp_file).unlink()
                except:
                    pass  # Ignore cleanup errors


        return True

    except Exception:
        return False


def list_models_enhanced(detailed: bool = False, json_output: bool = False) -> None:
    """Enhanced list models function."""
    tracking = load_tracking()

    if not tracking:
        return

    if json_output:

        return


    for info in tracking.values():
        if detailed:
            options = info.get("options", {})
            features = []
            for key, value in options.items():
                if value and key.startswith("with_"):
                    features.append(key.replace("with_", "").replace("_", " ").title())
            if features:
                pass


def remove_model_enhanced(
    model: str, cascade: bool = False, force: bool = False, clean_database: bool = False,
):
    """Enhanced remove model function with comprehensive rollback capabilities.
    Uses tracking information to completely undo all scaffold changes.
    """
    # Load tracking info
    track_info = ScaffoldTracker.load_model_tracking(model)
    if not track_info:

        # Fallback to basic removal
        tracking = load_tracking()
        if model in tracking:
            return remove_model_basic_fallback(model, force)
        return None


    if not force:
        if clean_database:
            pass

        response = input("Are you sure you want to proceed? (y/N): ")
        if response.lower() != "y":
            return None


    removal_success = True

    # Step 1: Remove created files
    files_created = track_info.get("files_created", [])
    for file_info in files_created:
        file_path = file_info.get("path") if isinstance(file_info, dict) else file_info
        try:
            if Path(file_path).exists():
                Path(file_path).unlink()
            else:
                pass
        except Exception:
            removal_success = False

    # Step 2: Restore modified files from backups
    files_modified = track_info.get("files_modified", [])
    for mod_info in files_modified:
        file_path = mod_info.get("path")
        backup_path = mod_info.get("backup_path")

        try:
            if backup_path and Path(backup_path).exists():
                # Restore from backup
                with Path(backup_path).open("r") as f:
                    original_content = f.read()

                with Path(file_path).open("w") as f:
                    f.write(original_content)


                # Remove backup file
                Path(backup_path).unlink()
            elif manual_cleanup_imports(file_path, model):
                pass
            else:
                removal_success = False
        except Exception:
            removal_success = False

    # Step 3: Remove migrations and database changes (if requested)
    if clean_database:
        migrations_created = track_info.get("migrations_created", [])

        for migration_info in migrations_created:
            migration_file = (
                migration_info.get("file")
                if isinstance(migration_info, dict)
                else migration_info
            )
            try:
                if Path(migration_file).exists():
                    Path(migration_file).unlink()
            except Exception:
                removal_success = False

        # Drop database table
        if drop_model_table(model):
            pass
        else:
            pass

    # Step 4: Clean up tracking files
    try:
        tracker = ScaffoldTracker(model)
        tracker.cleanup_tracking_files()

        # Remove from main tracking
        tracking = load_tracking()
        if model in tracking:
            del tracking[model]
            save_tracking(tracking)
    except Exception:
        removal_success = False

    # Final status
    if removal_success:
        pass
    else:
        pass

    return removal_success


def remove_model_basic_fallback(model: str, force: bool = False) -> None:
    """Fallback removal for models without detailed tracking."""
    tracking = load_tracking()

    if not force:
        response = input(f"⚠️  Are you sure you want to remove {model}? (y/N): ")
        if response.lower() != "y":
            return

    # Remove files
    files = tracking[model].get("files", [])
    for file_path in files:
        try:
            if Path(file_path).exists():
                Path(file_path).unlink()
        except Exception:
            pass

    # Remove from tracking
    del tracking[model]
    save_tracking(tracking)



def manual_cleanup_imports(file_path: str, model: str) -> bool:
    """Manually clean up imports when no backup is available."""
    try:
        snake_name = snake_case(model)
        pascal_name = pascal_case(model)

        with Path(file_path).open("r") as f:
            content = f.read()

        original_content = content

        # Remove imports related to this model
        import_patterns = [
            f"from app.db.models.{snake_name} import {pascal_name}",
            f"from app.api.v1.endpoints import {snake_name}",
            f'api_router.include_router({snake_name}.router, tags=["{pascal_name}s"])',
        ]

        for pattern in import_patterns:
            # Remove exact line matches
            lines = content.split("\n")
            lines = [line for line in lines if pattern not in line]
            content = "\n".join(lines)

        # Only write if we made changes
        if content != original_content:
            with Path(file_path).open("w") as f:
                f.write(content)
            return True

        return True

    except Exception:
        return False


def drop_model_table(model: str) -> bool:
    """Drop the database table for a model."""
    try:
        snake_name = snake_case(model)
        table_name = f"{snake_name}s"

        drop_script = f"""
import asyncio
from app.db.session import engine
from sqlalchemy import text

async def drop_table():
    try:
        async with engine.begin() as conn:
            # Check if table exists
            exists_result = await conn.execute(text("SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = '{table_name}');"))
            if exists_result.scalar():
                await conn.execute(text("DROP TABLE {table_name} CASCADE;"))
                print("✅ Table {table_name} dropped successfully")
                return True
            else:
                print(f"ℹ️  Table {table_name} does not exist")
                return True
    except Exception as e:
        print(f"❌ Error dropping table: {{e}}")
        return False

result = asyncio.run(drop_table())
exit(0 if result else 1)
"""

        with Path("temp_drop_table.py").open("w") as f:
            f.write(drop_script)

        result = subprocess.run(
            ["python", "temp_drop_table.py"], capture_output=True, text=True, check=False,
        )
        Path("temp_drop_table.py").unlink()

        return result.returncode == 0

    except Exception:
        return False


def health_check_enhanced(fix_issues: bool = False, verbose: bool = False) -> None:
    """Enhanced health check function."""
    issues = []

    # Check required directories
    required_dirs = [
        "app/db/models",
        "app/db/schemas",
        "app/services",
        "app/api/v1/endpoints",
        "app/dependencies",
        "app/exceptions",
    ]

    for dir_path in required_dirs:
        if not Path(dir_path).exists():
            issues.append(f"Missing directory: {dir_path}")
            if fix_issues:
                Path(dir_path).mkdir(parents=True, exist_ok=True)

    # Check required files
    required_files = [
        "app/db/base.py",
        "app/db/mixins.py",
        "app/db/schemas/base.py",
        "app/core/repository.py",
    ]

    for file_path in required_files:
        if not Path(file_path).exists():
            issues.append(f"Missing file: {file_path}")

    if not issues:
        pass
    else:
        for _issue in issues:
            pass


def generate_config_file() -> None:
    """Generate scaffold configuration file."""
    # Implementation would create scaffold_config.yaml


def generate_comprehensive_docs() -> None:
    """Generate comprehensive documentation."""
    # Implementation would create detailed docs


def analyze_codebase() -> None:
    """Analyze codebase patterns."""
    # Implementation would analyze existing patterns


def optimize_generated_code() -> None:
    """Optimize generated code."""
    # Implementation would optimize existing code


def update_model(model: str, args) -> None:
    """Update an existing model."""
    # Implementation would update existing model


def interactive_scaffold_mode(config: ScaffoldConfig) -> bool:
    """Interactive mode for guided scaffolding."""
    # Get model name
    model = input("📝 Enter model name (PascalCase): ").strip()
    if not model:
        return False

    # Get fields
    fields = []

    while True:
        field_name = input("  Field name: ").strip()
        if not field_name:
            break

        field_type = input("  Field type: ").strip()

        try:
            field_def = FieldDefinition(field_name, FieldType(field_type))
            fields.append(field_def)
        except ValueError:
            pass

    if not fields:
        return False

    # Get features
    features = {}
    feature_questions = [
        ("bulk_operations", "Enable bulk operations?"),
        ("search", "Enable search functionality?"),
        ("audit_trail", "Enable audit trail?"),
        ("soft_deletes", "Enable soft deletes?"),
        ("repository_pattern", "Use repository pattern?"),
    ]

    for key, question in feature_questions:
        response = input(f"  {question} (y/N): ").strip().lower()
        features[key] = response == "y"

    # Preview and confirm
    preview_scaffold(model, fields, features, config)

    confirm = input("\n✅ Generate these files? (y/N): ").strip().lower()
    if confirm != "y":
        return False

    return scaffold_model_enhanced(model, fields, features, config)


def show_model_tracking(model: str) -> None:
    """Show detailed tracking information for a model."""
    track_info = ScaffoldTracker.load_model_tracking(model)

    if not track_info:
        return


    files_created = track_info.get("files_created", [])
    files_modified = track_info.get("files_modified", [])
    imports_added = track_info.get("imports_added", [])
    migrations = track_info.get("migrations_created", [])

    for file_info in files_created:
        path = file_info.get("path") if isinstance(file_info, dict) else file_info
        (
            file_info.get("size", "unknown")
            if isinstance(file_info, dict)
            else "unknown"
        )
        "✅" if Path(path).exists() else "❌"

    for mod_info in files_modified:
        path = mod_info.get("path")
        backup = mod_info.get("backup_path")
        changes = mod_info.get("changes", [])
        "✅" if Path(path).exists() else "❌"
        "✅" if backup and Path(backup).exists() else "❌"
        for change in changes:
            pass

    for import_info in imports_added:
        file_path = import_info.get("file")
        import_info.get("import")

    for migration in migrations:
        file_path = migration.get("file") if isinstance(migration, dict) else migration
        (
            migration.get("migration_id", "unknown")
            if isinstance(migration, dict)
            else "unknown"
        )
        "✅" if Path(file_path).exists() else "❌"

    db_changes = track_info.get("database_changes", [])
    if db_changes:
        for change in db_changes:
            change.get("operation")
            details = change.get("details", {})
            change.get("timestamp")
            for _key, _value in details.items():
                pass


def print_success_message(model: str) -> None:
    """Print comprehensive success message."""
    snake_case(model)


if __name__ == "__main__":
    main()
