import json
import os
from datetime import datetime
from typing import Any

BASE_PATH = "app"
SCAFFOLD_CONFIG_FILE = "scaffold_config.json"


def snake_case(name):
    return "".join(["_" + c.lower() if c.isupper() else c for c in name]).lstrip("_")


def pascal_case(name):
    return "".join(word.capitalize() for word in name.split("_"))


def ensure_init(path) -> None:
    """Ensure __init__.py exists in each parent directory."""
    dirs = path.split(os.sep)
    for i in range(1, len(dirs)):
        d = os.sep.join(dirs[:i])
        if d and not os.path.exists(os.path.join(d, "__init__.py")):
            with open(os.path.join(d, "__init__.py"), "a"):
                pass


def prompt_enterprise_config():
    """Prompt for enterprise configuration options."""
    # Authentication configuration
    requires_auth = input("Require authentication? (y/n) [y]: ").strip().lower()
    requires_auth = requires_auth != "n"

    # Organization/Multi-tenancy
    is_tenant_scoped = (
        input("Enable multi-tenancy/organization scoping? (y/n) [n]: ").strip().lower()
    )
    is_tenant_scoped = is_tenant_scoped == "y"

    # Role-based access control
    role_based = input("Enable role-based access control? (y/n) [n]: ").strip().lower()
    role_based = role_based == "y"

    allowed_roles = []
    if role_based:
        roles_input = input(
            "Enter allowed roles (comma-separated) [ADMIN,MANAGER]: ",
        ).strip()
        if roles_input:
            allowed_roles = [r.strip().upper() for r in roles_input.split(",")]
        else:
            allowed_roles = ["ADMIN", "MANAGER"]

    # Rate limiting
    rate_limiting = input("Enable rate limiting? (y/n) [n]: ").strip().lower()
    rate_limiting = rate_limiting == "y"

    rate_limit_config = {}
    if rate_limiting:
        calls = input("Rate limit calls per minute [100]: ").strip()
        rate_limit_config = {"calls_per_minute": int(calls) if calls else 100}

    # Caching
    enable_caching = input("Enable response caching? (y/n) [n]: ").strip().lower()
    enable_caching = enable_caching == "y"

    cache_config = {}
    if enable_caching:
        ttl = input("Cache TTL in seconds [300]: ").strip()
        cache_config = {"ttl_seconds": int(ttl) if ttl else 300}

    # Bulk operations
    enable_bulk = input("Enable bulk operations? (y/n) [y]: ").strip().lower()
    enable_bulk = enable_bulk != "n"

    # Export functionality
    enable_export = input("Enable data export (CSV/JSON)? (y/n) [y]: ").strip().lower()
    enable_export = enable_export != "n"

    # Audit logging
    enable_audit = input("Enable audit logging? (y/n) [n]: ").strip().lower()
    enable_audit = enable_audit == "y"

    return {
        "requires_auth": requires_auth,
        "is_tenant_scoped": is_tenant_scoped,
        "role_based": role_based,
        "allowed_roles": allowed_roles,
        "rate_limiting": rate_limiting,
        "rate_limit_config": rate_limit_config,
        "enable_caching": enable_caching,
        "cache_config": cache_config,
        "enable_bulk": enable_bulk,
        "enable_export": enable_export,
        "enable_audit": enable_audit,
    }


def prompt_fields():
    fields = []
    while True:
        field = input("Field: ")
        if field.lower() == "done":
            break
        if ":" in field:
            parts = field.split(":")
            name = parts[0].strip()
            typ = parts[1].strip() if len(parts) > 1 else "str"
            nullable = parts[2].strip().lower() == "true" if len(parts) > 2 else False
            fields.append((name, typ, nullable))
    return fields


def save_scaffold_config(model_name: str, config: dict[str, Any]) -> None:
    """Save scaffold configuration for future reference."""
    if os.path.exists(SCAFFOLD_CONFIG_FILE):
        with open(SCAFFOLD_CONFIG_FILE) as f:
            all_configs = json.load(f)
    else:
        all_configs = {}

    all_configs[model_name] = {
        **config,
        "created_at": datetime.now().isoformat(),
        "scaffold_version": "v4_enterprise",
    }

    with open(SCAFFOLD_CONFIG_FILE, "w") as f:
        json.dump(all_configs, f, indent=2)



def get_sqlalchemy_type(typ: str) -> str:
    """Convert field type to SQLAlchemy type."""
    type_mapping = {
        "str": "String(255)",
        "int": "Integer",
        "float": "Float",
        "bool": "Boolean",
        "datetime": "DateTime",
        "text": "Text",
        "json": "JSON",
    }
    return type_mapping.get(typ, "String(255)")


def get_python_type(typ: str) -> str:
    """Convert field type to Python type hint."""
    type_mapping = {
        "str": "str",
        "int": "int",
        "float": "float",
        "bool": "bool",
        "datetime": "datetime",
        "text": "str",
        "json": "Dict[str, Any]",
    }
    return type_mapping.get(typ, "str")


def make_model(model_name, fields, config) -> None:
    fname = f"{BASE_PATH}/db/models/{snake_case(model_name)}.py"
    ensure_init(os.path.dirname(fname))
    if os.path.exists(fname):
        return

    # Determine imports based on field types and config
    imports = [
        "from app.db.base import Base",
        "from sqlalchemy import Column, String, Integer, Boolean, Float, Text, DateTime, JSON, ForeignKey",
    ]

    if config.get("is_tenant_scoped"):
        imports.append("from sqlalchemy.orm import relationship")

    if any(typ == "datetime" for _, typ, _ in fields) or config.get("enable_audit"):
        imports.append("from datetime import datetime")

    if config.get("enable_audit"):
        imports.append("import uuid")

    with open(fname, "w") as f:
        f.write(f'''"""
Enterprise SQLAlchemy model for {model_name} with multi-tenancy and audit support.
Generated by Scaffold v4 Enterprise Edition.
"""
{chr(10).join(imports)}

class {model_name}(Base):
    \"\"\"
    Enterprise SQLAlchemy ORM model for {model_name}.

    Features:
    - {"Multi-tenant organization scoping" if config.get("is_tenant_scoped") else "No tenant scoping"}
    - {"Role-based access control" if config.get("role_based") else "No role restrictions"}
    - {"Audit logging enabled" if config.get("enable_audit") else "No audit logging"}
    \"\"\"
    __tablename__ = "{snake_case(model_name)}s"

    # Primary key
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
''')

        # Add tenant scoping if enabled
        if config.get("is_tenant_scoped"):
            f.write("""
    # Multi-tenancy support
    organization_id = Column(String, ForeignKey("organizations.id"), nullable=False, index=True)
""")

        # Add user-defined fields
        for name, typ, nullable in fields:
            sqlatype = get_sqlalchemy_type(typ)
            f.write(f"    {name} = Column({sqlatype}, nullable={nullable})\n")

        # Add audit fields if enabled
        if config.get("enable_audit"):
            f.write("""
    # Audit fields
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    created_by = Column(String, ForeignKey("users.id"))
    updated_by = Column(String, ForeignKey("users.id"))
""")

        # Add relationships if tenant scoped
        if config.get("is_tenant_scoped"):
            f.write(f"""
    # Relationships
    organization = relationship("Organization", back_populates="{snake_case(model_name)}s")
""")
            if config.get("enable_audit"):
                f.write("""    creator = relationship("User", foreign_keys=[created_by])
    updater = relationship("User", foreign_keys=[updated_by])
""")

        # Add utility methods
        f.write(f"""
    def __repr__(self):
        return f"<{model_name}(id={{self.id}}, {"organization_id={self.organization_id}, " if config.get("is_tenant_scoped") else ""}...)>"

    @property
    def dict(self):
        \"\"\"Convert model to dictionary for JSON serialization.\"\"\"
        return {{
            'id': self.id,
""")

        for name, typ, _ in fields:
            f.write(f"            '{name}': self.{name},\n")

        if config.get("is_tenant_scoped"):
            f.write("            'organization_id': self.organization_id,\n")

        if config.get("enable_audit"):
            f.write("""            'is_active': self.is_active,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'created_by': self.created_by,
            'updated_by': self.updated_by,
""")

        f.write(f"""        }}

    def can_access(self, user_id: str, organization_id: str = None) -> bool:
        \"\"\"Check if user can access this {snake_case(model_name)}.\"\"\"
        if not self.is_active:
            return False

        {"if organization_id and self.organization_id != organization_id:" if config.get("is_tenant_scoped") else "# No tenant scoping"}
        {"    return False" if config.get("is_tenant_scoped") else ""}

        return True
""")

    # Add to __init__.py for Alembic
    init_file = f"{BASE_PATH}/db/models/__init__.py"
    ensure_init(os.path.dirname(init_file))
    with open(init_file, "a") as f:
        f.write(f"from .{snake_case(model_name)} import {model_name}\n")

    if config.get("is_tenant_scoped"):
        pass
    if config.get("enable_audit"):
        pass


def make_schema(model_name, fields, config) -> None:
    fname = f"{BASE_PATH}/db/schemas/{snake_case(model_name)}.py"
    ensure_init(os.path.dirname(fname))
    if os.path.exists(fname):
        return

    # Determine imports based on field types
    imports = [
        "from pydantic import BaseModel, Field",
        "from typing import Optional, Dict, Any",
    ]

    if any(typ == "datetime" for _, typ, _ in fields) or config.get("enable_audit"):
        imports.append("from datetime import datetime")

    with open(fname, "w") as f:
        f.write(f'''"""
Enterprise Pydantic schemas for {model_name} with validation and multi-tenancy support.
Generated by Scaffold v4 Enterprise Edition.
"""
{chr(10).join(imports)}

class {model_name}Base(BaseModel):
    """Base schema for {model_name} with common fields."""
''')

        # Add user-defined fields
        for name, typ, nullable in fields:
            pytyp = get_python_type(typ)
            if nullable:
                f.write(f"    {name}: Optional[{pytyp}] = None\n")
            else:
                f.write(f"    {name}: {pytyp}\n")

        f.write(f'''
class {model_name}Create({model_name}Base):
    """Schema for creating a {model_name}."""
    pass

class {model_name}Update(BaseModel):
    """Schema for updating a {model_name}."""
''')

        # Add optional update fields
        for name, typ, _ in fields:
            pytyp = get_python_type(typ)
            f.write(f"    {name}: Optional[{pytyp}] = None\n")

        f.write(f'''
class {model_name}Read({model_name}Base):
    """Schema for reading a {model_name}."""
    id: str
''')

        # Add tenant scoping if enabled
        if config.get("is_tenant_scoped"):
            f.write("    organization_id: str\n")

        # Add audit fields if enabled
        if config.get("enable_audit"):
            f.write("""    is_active: bool
    created_at: datetime
    updated_at: datetime
    created_by: Optional[str] = None
    updated_by: Optional[str] = None
""")

        f.write("""
    class Config:
        from_attributes = True
""")

        # Add bulk operations schemas if enabled
        if config.get("enable_bulk"):
            f.write(f'''

class {model_name}BulkCreate(BaseModel):
    """Schema for bulk creating {snake_case(model_name)}s."""
    items: list[{model_name}Create]

class {model_name}BulkUpdate(BaseModel):
    """Schema for bulk updating {snake_case(model_name)}s."""
    updates: list[Dict[str, Any]]  # [{"id": "...", "field": "value"}]

class {model_name}BulkResponse(BaseModel):
    """Schema for bulk operation responses."""
    successful: list[{model_name}Read]
    failed: list[Dict[str, str]]  # [{"id": "...", "error": "reason"}]
    summary: Dict[str, int]  # {"total": 10, "successful": 8, "failed": 2}
''')

        # Add list response schema
        f.write(f'''

class {model_name}ListResponse(BaseModel):
    """Schema for paginated {snake_case(model_name)} list."""
    items: list[{model_name}Read]
    total: int
    page: int
    size: int
    has_next: bool
    has_prev: bool
''')

        # Add export schemas if enabled
        if config.get("enable_export"):
            f.write(f'''

class {model_name}ExportRequest(BaseModel):
    """Schema for {snake_case(model_name)} export request."""
    format: str = Field(..., regex="^(csv|json|xlsx)$")
    filters: Optional[Dict[str, Any]] = None
    fields: Optional[list[str]] = None  # Specific fields to export

class {model_name}ExportResponse(BaseModel):
    """Schema for {snake_case(model_name)} export response."""
    download_url: str
    expires_at: datetime
    format: str
    total_records: int
''')

    # Add to __init__.py for import convenience
    init_file = f"{BASE_PATH}/db/schemas/__init__.py"
    ensure_init(os.path.dirname(init_file))
    with open(init_file, "a") as f:
        schemas_to_import = [
            f"{model_name}Create",
            f"{model_name}Read",
            f"{model_name}Update",
            f"{model_name}ListResponse",
        ]
        if config.get("enable_bulk"):
            schemas_to_import.extend(
                [
                    f"{model_name}BulkCreate",
                    f"{model_name}BulkUpdate",
                    f"{model_name}BulkResponse",
                ],
            )
        if config.get("enable_export"):
            schemas_to_import.extend(
                [f"{model_name}ExportRequest", f"{model_name}ExportResponse"],
            )

        f.write(
            f"from .{snake_case(model_name)} import {', '.join(schemas_to_import)}\n",
        )

    if config.get("enable_bulk"):
        pass
    if config.get("enable_export"):
        pass


def make_service(model_name, config) -> None:
    fname = f"{BASE_PATH}/services/{snake_case(model_name)}_service.py"
    ensure_init(os.path.dirname(fname))
    if os.path.exists(fname):
        return

    # Determine imports based on config
    imports = [
        "from typing import List, Dict, Any, Optional, Tuple",
        "from sqlalchemy.ext.asyncio import AsyncSession",
        "from sqlalchemy import select, and_, func, desc",
        "from fastapi import HTTPException, status",
        "from loguru import logger",
        "from app.services.base_service import BaseService",
        f"from app.db.models.{snake_case(model_name)} import {model_name}",
    ]

    if config.get("is_tenant_scoped"):
        imports.append(
            "from app.services.organization_service import organization_service",
        )
        imports.append("from app.db.models.organization import MemberRole")

    if config.get("enable_export"):
        imports.append("import csv")
        imports.append("import json")
        imports.append("from datetime import datetime, timedelta")
        imports.append("from io import StringIO")

    with open(fname, "w") as f:
        f.write(f'''"""
Enterprise Service for {model_name} with multi-tenancy, role-based access, and enhanced features.
Generated by Scaffold v4 Enterprise Edition.
"""
{chr(10).join(imports)}

class {model_name}Service(BaseService[{model_name}]):
    \"\"\"
    Enhanced service class for {model_name} with parallel processing capabilities.
    Provides concurrent operations for bulk processing and improved performance.
    \"\"\"

    def __init__(self):
        super().__init__({model_name})

    # Add custom parallel processing methods here

    async def bulk_process_{snake_case(model_name)}s(
        self,
        db: AsyncSession,
        items: List[Dict[str, Any]],
        processor_func: callable = None
    ) -> List[{model_name}]:
        \"\"\"
        Process multiple {snake_case(model_name)}s in parallel.

        Args:
            db: Database session
            items: List of {snake_case(model_name)} data to process
            processor_func: Optional custom processing function

        Returns:
            List of processed {model_name} instances
        \"\"\"
        if processor_func:
            # Use custom processor function
            processed_items = await self.process_data_parallel(
                items, processor_func, TaskType.CPU_BOUND
            )
            return await self.bulk_create_parallel(db, processed_items)
        else:
            # Default processing - direct bulk create
            return await self.bulk_create_parallel(db, items)

    async def validate_{snake_case(model_name)}s_parallel(
        self,
        data: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        \"\"\"
        Validate multiple {snake_case(model_name)}s in parallel.

        Args:
            data: List of {snake_case(model_name)} data to validate

        Returns:
            List of validated data
        \"\"\"
        def validate_{snake_case(model_name)}_data(item_data: Dict[str, Any]) -> Dict[str, Any]:
            # Add your validation logic here
            # Example: Check required fields
            required_fields = ['name']  # Customize based on your model
            for field in required_fields:
                if not item_data.get(field):
                    raise ValueError(f"Missing required field: {{field}}")
            return item_data

        return await self.validate_data_parallel(data, validate_{snake_case(model_name)}_data)

    async def export_{snake_case(model_name)}s_parallel(
        self,
        db: AsyncSession,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        \"\"\"
        Export {snake_case(model_name)}s data in parallel with processing.

        Args:
            db: Database session
            filters: Optional filters for selection

        Returns:
            List of exported {snake_case(model_name)} data
        \"\"\"
        # Get items based on filters
        items = await self.find(db, filters)

        def process_{snake_case(model_name)}_export(item: {model_name}) -> Dict[str, Any]:
            \"\"\"Process {snake_case(model_name)} data for export\"\"\"
            return {{
                'id': item.id,
                # Add other fields as needed
                # 'name': item.name,
                # 'created_at': getattr(item, 'created_at', None),
            }}

        return await self.process_data_parallel(
            items, process_{snake_case(model_name)}_export, TaskType.CPU_BOUND
        )

    async def generate_{snake_case(model_name)}_statistics_parallel(
        self,
        db: AsyncSession
    ) -> Dict[str, Any]:
        \"\"\"
        Generate comprehensive {snake_case(model_name)} statistics in parallel.

        Args:
            db: Database session

        Returns:
            Dictionary of statistics
        \"\"\"
        stat_configs = [
            {{'name': 'total_{snake_case(model_name)}s', 'type': 'count', 'filters': None}},
            # Add more statistics as needed
            # {{'name': 'active_{snake_case(model_name)}s', 'type': 'count', 'filters': {{'is_active': True}}}},
        ]

        return await self.generate_statistics_parallel(db, stat_configs)
''')
    # Add to __init__.py for import convenience
    init_file = f"{BASE_PATH}/services/__init__.py"
    ensure_init(os.path.dirname(init_file))
    with open(init_file, "a") as f:
        f.write(f"from .{snake_case(model_name)}_service import {model_name}Service\n")


def make_endpoint(model_name) -> None:
    fname = f"{BASE_PATH}/api/v1/endpoints/{snake_case(model_name)}.py"
    ensure_init(os.path.dirname(fname))
    if os.path.exists(fname):
        return
    with open(fname, "w") as f:
        f.write(f'''"""
Auto-generated CRUD endpoints for {model_name}.
"""
from app.api.v1.endpoints.base import get_crud_router
from app.services.{snake_case(model_name)}_service import {model_name}Service
from app.db.schemas.{snake_case(model_name)} import {model_name}Read, {model_name}Create
from app.db.session import get_db

router = get_crud_router(
    service={model_name}Service(),
    schema_read={model_name}Read,
    schema_create={model_name}Create,
    prefix="/{snake_case(model_name)}s",
    get_db=get_db,
    tags=["{model_name}s"]
)

# Example custom endpoint (extend as needed)
# from fastapi import Depends, HTTPException
# @router.get("/{snake_case(model_name)}s/by_field/{{value}}", tags=["{model_name}s"], description="Get a {model_name} by field value.")
# async def get_by_field(value: str, db=Depends(get_db)):
#     ...
''')
    # Add to __init__.py for import convenience
    init_file = f"{BASE_PATH}/api/v1/endpoints/__init__.py"
    ensure_init(os.path.dirname(init_file))
    with open(init_file, "a") as f:
        f.write(
            f"from .{snake_case(model_name)} import router as {snake_case(model_name)}_router\n",
        )


def main() -> None:
    model_name = input("Enter model name (CamelCase, e.g., Book): ").strip()
    fields = prompt_fields()
    make_model(model_name, fields)
    make_schema(model_name, fields)
    make_service(model_name)
    make_endpoint(model_name)


if __name__ == "__main__":
    main()
