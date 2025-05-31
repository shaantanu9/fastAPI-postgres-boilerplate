import os

BASE_PATH = "app"

def snake_case(name):
    return ''.join(['_' + c.lower() if c.isupper() else c for c in name]).lstrip('_')

def pascal_case(name):
    return ''.join(word.capitalize() for word in name.split('_'))

def ensure_init(path):
    """Ensure __init__.py exists in each parent directory."""
    dirs = path.split(os.sep)
    for i in range(1, len(dirs)):
        d = os.sep.join(dirs[:i])
        if d and not os.path.exists(os.path.join(d, "__init__.py")):
            with open(os.path.join(d, "__init__.py"), "a") as f:
                pass

def prompt_fields():
    fields = []
    print("Enter fields for your model (format: name:type), e.g., title:str. Type 'done' when finished.")
    while True:
        field = input("Field: ")
        if field.lower() == "done":
            break
        if ':' in field:
            name, typ = field.split(':', 1)
            fields.append((name.strip(), typ.strip()))
    return fields

def make_model(model_name, fields):
    fname = f"{BASE_PATH}/db/models/{snake_case(model_name)}.py"
    ensure_init(os.path.dirname(fname))
    if os.path.exists(fname):
        print(f"File {fname} already exists! Skipping.")
        return
    with open(fname, "w") as f:
        f.write(f'''"""
SQLAlchemy model for {model_name}.
"""
from app.db.base import Base
from sqlalchemy import Column, Integer, String

class {model_name}(Base):
    \"\"\"SQLAlchemy ORM model for {model_name}.\"\"\"
    __tablename__ = "{snake_case(model_name)}s"
    id = Column(Integer, primary_key=True, index=True)
''')
        for name, typ in fields:
            sqlatype = "String" if typ == "str" else "Integer" if typ == "int" else "String"
            f.write(f"    {name} = Column({sqlatype}, nullable=False)\n")
    # Add to __init__.py for Alembic
    init_file = f"{BASE_PATH}/db/models/__init__.py"
    ensure_init(os.path.dirname(init_file))
    with open(init_file, "a") as f:
        f.write(f"from .{snake_case(model_name)} import {model_name}\n")
    print(f"Created model: {fname}")

def make_schema(model_name, fields):
    fname = f"{BASE_PATH}/db/schemas/{snake_case(model_name)}.py"
    ensure_init(os.path.dirname(fname))
    if os.path.exists(fname):
        print(f"File {fname} already exists! Skipping.")
        return
    with open(fname, "w") as f:
        f.write(f'''"""
Pydantic schemas for {model_name}.
"""
from pydantic import BaseModel

class {model_name}Create(BaseModel):
    """Schema for creating a {model_name}."""
''')
        for name, typ in fields:
            pytyp = "str" if typ == "str" else "int" if typ == "int" else "str"
            f.write(f"    {name}: {pytyp}\n")
        f.write(f"""\n
class {model_name}Read({model_name}Create):
    \"\"\"Schema for reading a {model_name}.\"\"\"
    id: int

    class Config:
        orm_mode = True
""")
    # Add to __init__.py for import convenience
    init_file = f"{BASE_PATH}/db/schemas/__init__.py"
    ensure_init(os.path.dirname(init_file))
    with open(init_file, "a") as f:
        f.write(f"from .{snake_case(model_name)} import {model_name}Create, {model_name}Read\n")
    print(f"Created schemas: {fname}")

def make_service(model_name):
    fname = f"{BASE_PATH}/services/{snake_case(model_name)}_service.py"
    ensure_init(os.path.dirname(fname))
    if os.path.exists(fname):
        print(f"File {fname} already exists! Skipping.")
        return
    with open(fname, "w") as f:
        f.write(f'''"""
Enhanced Service for {model_name} with concurrent processing capabilities.
"""
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.services.enhanced_base_service import EnhancedBaseService
from app.db.models.{snake_case(model_name)} import {model_name}
from app.utils.concurrent_utils import TaskType, execute_parallel

class {model_name}Service(EnhancedBaseService[{model_name}]):
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
    print(f"Created service: {fname}")

def make_endpoint(model_name):
    fname = f"{BASE_PATH}/api/v1/endpoints/{snake_case(model_name)}.py"
    ensure_init(os.path.dirname(fname))
    if os.path.exists(fname):
        print(f"File {fname} already exists! Skipping.")
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
        f.write(f"from .{snake_case(model_name)} import router as {snake_case(model_name)}_router\n")
    print(f"Created endpoint: {fname}")

def main():
    model_name = input("Enter model name (CamelCase, e.g., Book): ").strip()
    fields = prompt_fields()
    make_model(model_name, fields)
    make_schema(model_name, fields)
    make_service(model_name)
    make_endpoint(model_name)
    print("\nNext steps:")
    print(f"- Register the new router in app/api/v1/api.py (if not already auto-imported):")
    print(f"    from app.api.v1.endpoints import {snake_case(model_name)}_router")
    print(f"    api_router.include_router({snake_case(model_name)}_router)")
    print("- Run Alembic migration:")
    print("    alembic revision --autogenerate -m \"Add new model\"")
    print("    alembic upgrade head")
    print("- Add tests in app/tests/ as needed.")

if __name__ == '__main__':
    main()