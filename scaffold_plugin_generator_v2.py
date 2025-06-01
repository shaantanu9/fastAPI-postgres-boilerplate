#!/usr/bin/env python3
"""
Enterprise Plugin-Based Model Scaffold Generator v2.0

This tool generates complete model plugins for the FastAPI Enterprise Plugin Architecture.
Improvements in v2.0:
- Fixed Procrastinate task imports
- Better error handling and validation
- Improved plugin structure with proper separation of concerns
- Enhanced middleware and service integration
- Better status tracking and initialization

Usage:
    python scaffold_plugin_generator_v2.py add User name:str email:email age:int --with-tasks --with-bulk
    python scaffold_plugin_generator_v2.py list
    python scaffold_plugin_generator_v2.py remove User
    python scaffold_plugin_generator_v2.py health-check
    python scaffold_plugin_generator_v2.py fix-plugins  # New: Fix existing plugin issues

Features:
- ✅ Complete plugin generation in single file
- ✅ SQLAlchemy model with proper table configuration
- ✅ Pydantic schemas with validation
- ✅ Enhanced service with repository pattern
- ✅ FastAPI endpoints with full CRUD + bulk operations
- ✅ Procrastinate tasks (optional) with proper imports
- ✅ Event emission and monitoring integration
- ✅ Automatic plugin registration and discovery
- ✅ Proper middleware integration
- ✅ Database migration generation
- ✅ Error handling and validation
- ✅ Plugin status tracking fixes
"""

import argparse
import os
import sys
import subprocess
import re
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional
import json

def validate_field_definition(field_def: str) -> Dict[str, Any]:
    """
    Validate and parse field definition.
    Format: name:type[:constraint1:constraint2]
    
    Examples:
    - name:str
    - email:email:max_length=100
    - age:int:ge=0:le=120
    - price:float:gt=0
    - description:text
    - is_active:bool:default=True
    """
    parts = field_def.split(':')
    if len(parts) < 2:
        raise ValueError(f"Invalid field definition: {field_def}. Expected format: name:type[:constraints]")
    
    field_name = parts[0].strip()
    field_type = parts[1].strip()
    constraints = parts[2:] if len(parts) > 2 else []
    
    # Validate field name
    if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', field_name):
        raise ValueError(f"Invalid field name: {field_name}. Must be a valid Python identifier.")
    
    # Map field types
    type_mapping = {
        'str': 'str',
        'string': 'str', 
        'text': 'str',
        'int': 'int',
        'integer': 'int',
        'float': 'float',
        'decimal': 'float',
        'bool': 'bool',
        'boolean': 'bool',
        'date': 'date',
        'datetime': 'datetime',
        'email': 'EmailStr',
        'url': 'HttpUrl',
        'uuid': 'UUID',
        'json': 'Dict[str, Any]'
    }
    
    if field_type not in type_mapping:
        raise ValueError(f"Unsupported field type: {field_type}. Supported types: {list(type_mapping.keys())}")
    
    return {
        'name': field_name,
        'type': field_type,
        'python_type': type_mapping[field_type],
        'constraints': constraints
    }

def generate_sqlalchemy_field(field: Dict[str, Any]) -> str:
    """Generate SQLAlchemy column definition"""
    field_name = field['name']
    field_type = field['type']
    constraints = field['constraints']
    
    # Map to SQLAlchemy types
    sqlalchemy_mapping = {
        'str': 'String(255)',
        'text': 'Text',
        'int': 'Integer',
        'float': 'Float',
        'bool': 'Boolean',
        'date': 'Date',
        'datetime': 'DateTime',
        'email': 'String(255)',
        'url': 'String(500)',
        'uuid': 'String(36)',
        'json': 'JSON'
    }
    
    column_type = sqlalchemy_mapping.get(field_type, 'String(255)')
    
    # Handle constraints
    column_args = []
    for constraint in constraints:
        if constraint.startswith('max_length='):
            length = constraint.split('=')[1]
            if field_type in ['str', 'email', 'url']:
                column_type = f'String({length})'
        elif constraint == 'unique':
            column_args.append('unique=True')
        elif constraint == 'indexed':
            column_args.append('index=True')
        elif constraint.startswith('default='):
            default_val = constraint.split('=')[1]
            if field_type == 'bool':
                column_args.append(f'default={default_val}')
            elif field_type in ['str', 'email', 'url', 'text']:
                column_args.append(f'default="{default_val}"')
            else:
                column_args.append(f'default={default_val}')
    
    # Add nullable=False by default
    column_args.append('nullable=False')
    
    args_str = ', '.join(column_args)
    if args_str:
        return f"    {field_name} = Column({column_type}, {args_str})"
    else:
        return f"    {field_name} = Column({column_type})"

def generate_pydantic_field(field: Dict[str, Any]) -> str:
    """Generate Pydantic field definition"""
    field_name = field['name']
    python_type = field['python_type']
    constraints = field['constraints']
    
    # Handle constraints for Pydantic Field
    field_constraints = []
    for constraint in constraints:
        if constraint.startswith('max_length='):
            length = constraint.split('=')[1]
            field_constraints.append(f'max_length={length}')
        elif constraint.startswith('min_length='):
            length = constraint.split('=')[1]
            field_constraints.append(f'min_length={length}')
        elif constraint.startswith('ge='):
            val = constraint.split('=')[1]
            field_constraints.append(f'ge={val}')
        elif constraint.startswith('le='):
            val = constraint.split('=')[1]
            field_constraints.append(f'le={val}')
        elif constraint.startswith('gt='):
            val = constraint.split('=')[1]
            field_constraints.append(f'gt={val}')
        elif constraint.startswith('lt='):
            val = constraint.split('=')[1]
            field_constraints.append(f'lt={val}')
    
    if field_constraints:
        constraints_str = ', '.join(field_constraints)
        return f"    {field_name}: {python_type} = Field(..., {constraints_str})"
    else:
        return f"    {field_name}: {python_type}"

def generate_plugin_template(model_name: str, fields: List[Dict[str, Any]], with_tasks: bool = False, with_bulk: bool = False) -> str:
    """Generate the complete plugin template"""
    
    snake_name = re.sub(r'(?<!^)(?=[A-Z])', '_', model_name).lower()
    pascal_name = model_name
    
    # Generate field definitions
    sqlalchemy_fields = []
    pydantic_fields = []
    
    for field in fields:
        sqlalchemy_fields.append(generate_sqlalchemy_field(field))
        pydantic_fields.append(generate_pydantic_field(field))
    
    sqlalchemy_fields_str = '\n'.join(sqlalchemy_fields)
    pydantic_fields_str = '\n'.join(pydantic_fields)
    
    # Generate imports based on field types
    imports = set(['str', 'int', 'float', 'bool'])
    for field in fields:
        if field['python_type'] in ['EmailStr', 'HttpUrl', 'UUID', 'Dict']:
            imports.add(field['python_type'])
        if field['type'] in ['date', 'datetime']:
            imports.add(field['type'])
    
    pydantic_imports = []
    if 'EmailStr' in imports:
        pydantic_imports.append('EmailStr')
    if 'HttpUrl' in imports:
        pydantic_imports.append('HttpUrl')
    if 'UUID' in imports:
        pydantic_imports.append('UUID')
    if 'Dict' in imports:
        pydantic_imports.append('Dict')
    
    pydantic_import_str = ', '.join(pydantic_imports) if pydantic_imports else ''
    if pydantic_import_str:
        pydantic_import_str = f', {pydantic_import_str}'
    
    datetime_imports = []
    if 'date' in imports:
        datetime_imports.append('date')
    if 'datetime' in imports:
        datetime_imports.append('datetime')
    
    datetime_import_str = ', '.join(datetime_imports) if datetime_imports else ''
    if datetime_import_str:
        datetime_import_str = f'from datetime import {datetime_import_str}\n'
    else:
        datetime_import_str = 'from datetime import datetime\n'
    
    # Generate the plugin template
    template = f'''"""
{pascal_name} Plugin

This plugin provides complete CRUD operations for {pascal_name} entities with:
- SQLAlchemy model with optimized fields
- Pydantic schemas with validation
- Enhanced service with repository pattern
- FastAPI endpoints with full CRUD operations
- Event emission for monitoring
- Service registry integration
{"- Procrastinate task integration" if with_tasks else ""}
{"- Bulk operations support" if with_bulk else ""}

Auto-generated by Enterprise Plugin Scaffold Generator v2.0
Generated at: {datetime.now().isoformat()}
"""

from typing import List, Any, Dict, Optional, Union
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import JSONResponse
from sqlalchemy import Column, Integer, String, Text, Float, Boolean, DateTime, Date, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field{pydantic_import_str}
{datetime_import_str}import asyncio

from app.core.plugin_system import PluginBase, PluginMetadata, PluginStatus
from app.db.base import Base
from app.db.session import get_db
from app.services.enhanced_base_service import EnhancedBaseService


# SQLAlchemy Model
class {pascal_name}(Base):
    """
    {pascal_name} SQLAlchemy model with enterprise-grade features.
    """
    __tablename__ = "{snake_name}s"
    __table_args__ = {{'extend_existing': True}}
    
    id = Column(Integer, primary_key=True, index=True)
{sqlalchemy_fields_str}
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


# Pydantic Schemas
class {pascal_name}Base(BaseModel):
    """Base {pascal_name} schema for shared fields"""
{pydantic_fields_str}


class {pascal_name}Create({pascal_name}Base):
    """Schema for creating {pascal_name}"""
    pass


class {pascal_name}Update(BaseModel):
    """Schema for updating {pascal_name} (all fields optional)"""
{chr(10).join([f"    {field['name']}: Optional[{field['python_type']}] = None" for field in fields])}


class {pascal_name}InDB({pascal_name}Base):
    """Schema for {pascal_name} from database"""
    id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class {pascal_name}Response({pascal_name}InDB):
    """Schema for {pascal_name} API responses"""
    pass


# Enhanced Service
class {pascal_name}Service(EnhancedBaseService):
    """
    Enhanced {pascal_name} service with repository pattern and event emission.
    """
    
    def __init__(self, db: Session, plugin_context=None):
        super().__init__(db, {pascal_name})
        self.plugin_context = plugin_context
    
    async def create_{snake_name}(self, {snake_name}_data: {pascal_name}Create) -> {pascal_name}:
        """Create a new {snake_name} with event emission"""
        # Validate data
        validated_data = {snake_name}_data.model_dump()
        
        # Create entity
        {snake_name} = await self.create(validated_data)
        
        # Emit creation event
        if self.plugin_context:
            self.plugin_context.event_bus.emit(
                "{snake_name}_created",
                {snake_name}_id={snake_name}.id,
                data=validated_data,
                plugin="{snake_name}_plugin"
            )
        
        return {snake_name}
    
    async def get_{snake_name}_by_id(self, {snake_name}_id: int) -> Optional[{pascal_name}]:
        """Get {snake_name} by ID with event emission"""
        {snake_name} = await self.get_by_id({snake_name}_id)
        
        if {snake_name} and self.plugin_context:
            self.plugin_context.event_bus.emit(
                "{snake_name}_accessed",
                {snake_name}_id={snake_name}_id,
                plugin="{snake_name}_plugin"
            )
        
        return {snake_name}
    
    async def update_{snake_name}(self, {snake_name}_id: int, {snake_name}_data: {pascal_name}Update) -> Optional[{pascal_name}]:
        """Update {snake_name} with event emission"""
        # Get existing entity
        existing_{snake_name} = await self.get_by_id({snake_name}_id)
        if not existing_{snake_name}:
            return None
        
        # Update with only provided fields
        update_data = {{k: v for k, v in {snake_name}_data.model_dump().items() if v is not None}}
        
        if not update_data:
            return existing_{snake_name}
        
        updated_{snake_name} = await self.update({snake_name}_id, update_data)
        
        # Emit update event
        if self.plugin_context:
            self.plugin_context.event_bus.emit(
                "{snake_name}_updated",
                {snake_name}_id={snake_name}_id,
                changes=update_data,
                plugin="{snake_name}_plugin"
            )
        
        return updated_{snake_name}
    
    async def delete_{snake_name}(self, {snake_name}_id: int) -> bool:
        """Delete {snake_name} with event emission"""
        success = await self.delete({snake_name}_id)
        
        if success and self.plugin_context:
            self.plugin_context.event_bus.emit(
                "{snake_name}_deleted",
                {snake_name}_id={snake_name}_id,
                plugin="{snake_name}_plugin"
            )
        
        return success
    
    async def list_{snake_name}s(self, skip: int = 0, limit: int = 100, **filters) -> List[{pascal_name}]:
        """List {snake_name}s with filtering"""
        return await self.get_multi(skip=skip, limit=limit, **filters)
    
    async def get_{snake_name}_count(self, **filters) -> int:
        """Get total count of {snake_name}s"""
        return await self.count(**filters)

{"" if not with_bulk else f'''
    async def bulk_create_{snake_name}s(self, {snake_name}_list: List[{pascal_name}Create]) -> List[{pascal_name}]:
        """Bulk create {snake_name}s"""
        {snake_name}s = await self.bulk_create([item.model_dump() for item in {snake_name}_list])
        
        # Emit bulk creation event
        if self.plugin_context:
            self.plugin_context.event_bus.emit(
                "{snake_name}s_bulk_created",
                count=len({snake_name}s),
                plugin="{snake_name}_plugin"
            )
        
        return {snake_name}s
    
    async def bulk_update_{snake_name}s(self, updates: List[Dict[str, Any]]) -> List[{pascal_name}]:
        """Bulk update {snake_name}s"""
        {snake_name}s = await self.bulk_update(updates)
        
        # Emit bulk update event
        if self.plugin_context:
            self.plugin_context.event_bus.emit(
                "{snake_name}s_bulk_updated",
                count=len({snake_name}s),
                plugin="{snake_name}_plugin"
            )
        
        return {snake_name}s
'''}

{"" if not with_tasks else f'''
# Procrastinate Tasks
from app.utils.procrastinate_manager import procrastinate_app

@procrastinate_app.task(queue="{snake_name}_queue")
async def process_{snake_name}_task({snake_name}_id: int, operation: str, **kwargs):
    """
    Process background task for {snake_name}.
    
    Args:
        {snake_name}_id: ID of the {snake_name} to process
        operation: Type of operation (e.g., 'send_notification', 'generate_report')
        **kwargs: Additional task parameters
    """
    from app.db.session import get_async_session
    
    async with get_async_session() as db:
        service = {pascal_name}Service(db)
        {snake_name} = await service.get_{snake_name}_by_id({snake_name}_id)
        
        if not {snake_name}:
            raise ValueError(f"{pascal_name} with ID {{{snake_name}_id}} not found")
        
        if operation == "send_notification":
            # Implement notification logic
            print(f"Sending notification for {pascal_name} {{{snake_name}_id}}")
        elif operation == "generate_report":
            # Implement report generation logic
            print(f"Generating report for {pascal_name} {{{snake_name}_id}}")
        else:
            print(f"Unknown operation: {{operation}} for {pascal_name} {{{snake_name}_id}}")


@procrastinate_app.task(queue="{snake_name}_queue")
async def cleanup_{snake_name}_data(older_than_days: int = 30):
    """
    Cleanup old {snake_name} data.
    
    Args:
        older_than_days: Delete records older than this many days
    """
    from app.db.session import get_async_session
    from datetime import datetime, timedelta
    
    cutoff_date = datetime.utcnow() - timedelta(days=older_than_days)
    
    async with get_async_session() as db:
        # Implement cleanup logic
        print(f"Cleaning up {pascal_name} records older than {{cutoff_date}}")
'''}


# Plugin Class
class {pascal_name}Plugin(PluginBase):
    """
    Enterprise {pascal_name} plugin with complete CRUD operations.
    """
    
    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="{snake_name}_plugin",
            version="1.0.0",
            description="Complete {pascal_name} management with CRUD operations, validation, and monitoring",
            author="Enterprise Plugin Generator v2.0",
            min_app_version="1.0.0",
            dependencies=["monitoring"],  # Depend on monitoring for metrics
            tags=["{snake_name}", "model", "crud", "enterprise"] + 
                 (["tasks"] if with_tasks else []) + 
                 (["bulk"] if with_bulk else []),
            priority=20  # Lower priority - load after core plugins
        )
    
    def __init__(self):
        super().__init__()
        self.router = APIRouter()
        self.setup_routes()
    
    def setup_routes(self):
        """Setup {pascal_name} CRUD routes"""
        
        @self.router.post("/{snake_name}s/", response_model={pascal_name}Response, tags=["{pascal_name}"])
        async def create_{snake_name}({snake_name}_data: {pascal_name}Create, db: Session = Depends(get_db)):
            """Create a new {snake_name}"""
            service = {pascal_name}Service(db, self._context)
            try:
                {snake_name} = await service.create_{snake_name}({snake_name}_data)
                return {pascal_name}Response.model_validate({snake_name})
            except Exception as e:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
        
        @self.router.get("/{snake_name}s/", response_model=List[{pascal_name}Response], tags=["{pascal_name}"])
        async def list_{snake_name}s(
            skip: int = Query(0, ge=0),
            limit: int = Query(100, ge=1, le=1000),
            db: Session = Depends(get_db)
        ):
            """List {snake_name}s with pagination"""
            service = {pascal_name}Service(db, self._context)
            {snake_name}s = await service.list_{snake_name}s(skip=skip, limit=limit)
            return [{pascal_name}Response.model_validate({snake_name}) for {snake_name} in {snake_name}s]
        
        @self.router.get("/{snake_name}s/{{item_id}}", response_model={pascal_name}Response, tags=["{pascal_name}"])
        async def get_{snake_name}(item_id: int, db: Session = Depends(get_db)):
            """Get {snake_name} by ID"""
            service = {pascal_name}Service(db, self._context)
            {snake_name} = await service.get_{snake_name}_by_id(item_id)
            if not {snake_name}:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="{pascal_name} not found")
            return {pascal_name}Response.model_validate({snake_name})
        
        @self.router.put("/{snake_name}s/{{item_id}}", response_model={pascal_name}Response, tags=["{pascal_name}"])
        async def update_{snake_name}(item_id: int, {snake_name}_data: {pascal_name}Update, db: Session = Depends(get_db)):
            """Update {snake_name}"""
            service = {pascal_name}Service(db, self._context)
            {snake_name} = await service.update_{snake_name}(item_id, {snake_name}_data)
            if not {snake_name}:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="{pascal_name} not found")
            return {pascal_name}Response.model_validate({snake_name})
        
        @self.router.delete("/{snake_name}s/{{item_id}}", tags=["{pascal_name}"])
        async def delete_{snake_name}(item_id: int, db: Session = Depends(get_db)):
            """Delete {snake_name}"""
            service = {pascal_name}Service(db, self._context)
            success = await service.delete_{snake_name}(item_id)
            if not success:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="{pascal_name} not found")
            return {{"message": "{pascal_name} deleted successfully"}}
        
        @self.router.get("/{snake_name}s/count/", tags=["{pascal_name}"])
        async def get_{snake_name}_count(db: Session = Depends(get_db)):
            """Get total count of {snake_name}s"""
            service = {pascal_name}Service(db, self._context)
            count = await service.get_{snake_name}_count()
            return {{"count": count}}

{"" if not with_bulk else f'''        
        @self.router.post("/{snake_name}s/bulk/", response_model=List[{pascal_name}Response], tags=["{pascal_name}"])
        async def bulk_create_{snake_name}s({snake_name}_list: List[{pascal_name}Create], db: Session = Depends(get_db)):
            """Bulk create {snake_name}s"""
            service = {pascal_name}Service(db, self._context)
            {snake_name}s = await service.bulk_create_{snake_name}s({snake_name}_list)
            return [{pascal_name}Response.model_validate({snake_name}) for {snake_name} in {snake_name}s]
        
        @self.router.put("/{snake_name}s/bulk/", response_model=List[{pascal_name}Response], tags=["{pascal_name}"])
        async def bulk_update_{snake_name}s(updates: List[Dict[str, Any]], db: Session = Depends(get_db)):
            """Bulk update {snake_name}s"""
            service = {pascal_name}Service(db, self._context)
            {snake_name}s = await service.bulk_update_{snake_name}s(updates)
            return [{pascal_name}Response.model_validate({snake_name}) for {snake_name} in {snake_name}s]
'''}

{"" if not with_tasks else f'''        
        @self.router.post("/{snake_name}s/{{item_id}}/tasks/{{operation}}", tags=["{pascal_name}"])
        async def trigger_{snake_name}_task(item_id: int, operation: str, db: Session = Depends(get_db)):
            """Trigger background task for {snake_name}"""
            # Verify {snake_name} exists
            service = {pascal_name}Service(db, self._context)
            {snake_name} = await service.get_{snake_name}_by_id(item_id)
            if not {snake_name}:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="{pascal_name} not found")
            
            # Queue the task
            task = await process_{snake_name}_task.defer_async({snake_name}_id=item_id, operation=operation)
            return {{"message": f"Task {{operation}} queued for {pascal_name} {{item_id}}", "task_id": str(task.id)}}
'''}    
    async def initialize(self, app, context):
        """Initialize the {snake_name} plugin"""
        await super().initialize(app, context)
        
        # Register {snake_name} service
        context.register_service("{snake_name}_service", {pascal_name}Service)
        
        # Subscribe to application events
        self.subscribe_event("application_startup", self.on_startup)
        self.subscribe_event("monitoring_ready", self.on_monitoring_ready)
        
        self.metadata.status = PluginStatus.INITIALIZED
    
    async def startup(self):
        """Plugin startup tasks"""
        await super().startup()
        
        # Emit plugin ready event
        self.emit_event("{snake_name}_plugin_ready", 
                       features=["crud", "validation", "events"] + 
                               (["tasks"] if with_tasks else []) + 
                               (["bulk"] if with_bulk else []))
    
    async def shutdown(self):
        """Plugin shutdown tasks"""
        await super().shutdown()
        
        # Emit plugin shutdown event
        self.emit_event("{snake_name}_plugin_shutdown")
    
    def get_routes(self) -> List[Any]:
        """Return {snake_name} routes"""
        return [self.router]
    
    def get_middleware(self) -> List[Any]:
        """Return {snake_name} middleware"""
        return []  # No custom middleware for this plugin
    
    async def on_startup(self, **kwargs):
        """Handle application startup event"""
        print(f"{pascal_name} plugin: Application started, {snake_name} management ready")
    
    async def on_monitoring_ready(self, **kwargs):
        """Handle monitoring ready event"""
        print(f"{pascal_name} plugin: Monitoring system ready, integrating {snake_name} metrics")
        
        # Could register custom metrics with monitoring system
        features = kwargs.get("features", [])
        if "metrics" in features:
            print(f"{pascal_name} plugin: Monitoring supports metrics collection")
'''
    
    return template

def create_plugin_file(model_name: str, fields: List[Dict[str, Any]], with_tasks: bool = False, with_bulk: bool = False) -> str:
    """Create the plugin file"""
    snake_name = re.sub(r'(?<!^)(?=[A-Z])', '_', model_name).lower()
    
    # Ensure plugins directory exists
    plugins_dir = Path("app/plugins")
    plugins_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate plugin content
    plugin_content = generate_plugin_template(model_name, fields, with_tasks, with_bulk)
    
    # Write plugin file
    plugin_file = plugins_dir / f"{snake_name}_plugin.py"
    with open(plugin_file, 'w') as f:
        f.write(plugin_content)
    
    return str(plugin_file)

def generate_migration(model_name: str) -> bool:
    """Generate Alembic migration for the model"""
    try:
        snake_name = re.sub(r'(?<!^)(?=[A-Z])', '_', model_name).lower()
        
        # Generate migration
        result = subprocess.run([
            "alembic", "revision", "--autogenerate", 
            "-m", f"Add {model_name} model"
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"✅ Migration generated successfully for {model_name}")
            
            # Apply migration
            apply_result = subprocess.run([
                "alembic", "upgrade", "head"
            ], capture_output=True, text=True)
            
            if apply_result.returncode == 0:
                print(f"✅ Migration applied successfully for {model_name}")
                return True
            else:
                print(f"❌ Failed to apply migration: {apply_result.stderr}")
                return False
        else:
            print(f"❌ Failed to generate migration: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ Migration error: {e}")
        return False

def list_plugins() -> None:
    """List all generated plugins"""
    plugins_dir = Path("app/plugins")
    if not plugins_dir.exists():
        print("❌ No plugins directory found")
        return
    
    plugin_files = list(plugins_dir.glob("*_plugin.py"))
    if not plugin_files:
        print("📭 No plugins found")
        return
    
    print("🔌 Generated Plugins:")
    print("=" * 50)
    
    for plugin_file in plugin_files:
        plugin_name = plugin_file.stem.replace('_plugin', '')
        model_name = ''.join(word.capitalize() for word in plugin_name.split('_'))
        
        # Try to read plugin metadata
        try:
            with open(plugin_file, 'r') as f:
                content = f.read()
                
            # Extract features
            features = []
            if 'with_tasks' in content or 'procrastinate_app.task' in content:
                features.append('Tasks')
            if 'bulk_create' in content:
                features.append('Bulk Operations')
            if 'monitoring' in content:
                features.append('Monitoring')
            
            features_str = ', '.join(features) if features else 'Basic CRUD'
            
            print(f"  📋 {model_name}")
            print(f"     File: {plugin_file}")
            print(f"     Features: {features_str}")
            print()
            
        except Exception as e:
            print(f"  ❌ {plugin_file}: Error reading file - {e}")

def remove_plugin(model_name: str) -> bool:
    """Remove a plugin and its migration"""
    snake_name = re.sub(r'(?<!^)(?=[A-Z])', '_', model_name).lower()
    
    # Remove plugin file
    plugin_file = Path(f"app/plugins/{snake_name}_plugin.py")
    if plugin_file.exists():
        plugin_file.unlink()
        print(f"✅ Removed plugin file: {plugin_file}")
    else:
        print(f"❌ Plugin file not found: {plugin_file}")
        return False
    
    # Note: We don't automatically remove migrations as they might affect database state
    print(f"⚠️  Note: Database migration not removed. Please handle manually if needed.")
    
    return True

def health_check() -> None:
    """Perform health check on the plugin system"""
    print("🏥 Plugin System Health Check")
    print("=" * 40)
    
    # Check if required directories exist
    required_dirs = [
        "app/plugins",
        "app/core",
        "app/db",
        "app/services"
    ]
    
    for dir_path in required_dirs:
        if Path(dir_path).exists():
            print(f"✅ {dir_path} - OK")
        else:
            print(f"❌ {dir_path} - Missing")
    
    # Check if required files exist
    required_files = [
        "app/core/plugin_system.py",
        "app/db/base.py",
        "app/services/enhanced_base_service.py",
        "app/utils/procrastinate_manager.py"
    ]
    
    for file_path in required_files:
        if Path(file_path).exists():
            print(f"✅ {file_path} - OK")
        else:
            print(f"❌ {file_path} - Missing")
    
    # Check plugin files
    plugins_dir = Path("app/plugins")
    if plugins_dir.exists():
        plugin_files = list(plugins_dir.glob("*_plugin.py"))
        print(f"📊 Found {len(plugin_files)} plugin files")
        
        for plugin_file in plugin_files:
            try:
                # Try to compile the plugin
                with open(plugin_file, 'r') as f:
                    content = f.read()
                compile(content, str(plugin_file), 'exec')
                print(f"✅ {plugin_file.name} - Syntax OK")
            except SyntaxError as e:
                print(f"❌ {plugin_file.name} - Syntax Error: {e}")
            except Exception as e:
                print(f"⚠️  {plugin_file.name} - Warning: {e}")
    
    print("\n🎯 System Status: Ready for plugin generation")

def fix_plugins() -> None:
    """Fix common issues in existing plugins"""
    print("🔧 Fixing Plugin Issues")
    print("=" * 30)
    
    plugins_dir = Path("app/plugins")
    if not plugins_dir.exists():
        print("❌ No plugins directory found")
        return
    
    plugin_files = list(plugins_dir.glob("*_plugin.py"))
    if not plugin_files:
        print("📭 No plugins found")
        return
    
    for plugin_file in plugin_files:
        print(f"🔍 Checking {plugin_file.name}...")
        
        try:
            with open(plugin_file, 'r') as f:
                content = f.read()
            
            original_content = content
            fixed = False
            
            # Fix 1: Procrastinate import
            if 'import procrastinate' in content and 'from app.utils.procrastinate_manager import procrastinate_app' not in content:
                content = content.replace(
                    'import procrastinate',
                    'from app.utils.procrastinate_manager import procrastinate_app'
                )
                content = content.replace(
                    '@procrastinate.task(',
                    '@procrastinate_app.task('
                )
                fixed = True
                print(f"  ✅ Fixed Procrastinate imports")
            
            # Fix 2: Table extend_existing
            if '__table_args__' not in content and '__tablename__' in content:
                content = content.replace(
                    '__tablename__ = ',
                    '__tablename__ = '
                ).replace(
                    '__tablename__ = "',
                    '__tablename__ = "\n    __table_args__ = {\'extend_existing\': True}\n    '
                )
                fixed = True
                print(f"  ✅ Added extend_existing table args")
            
            # Fix 3: Middleware import
            if 'from fastapi.middleware.base import BaseHTTPMiddleware' in content:
                content = content.replace(
                    'from fastapi.middleware.base import BaseHTTPMiddleware',
                    'from starlette.middleware.base import BaseHTTPMiddleware'
                )
                fixed = True
                print(f"  ✅ Fixed middleware import")
            
            if fixed:
                with open(plugin_file, 'w') as f:
                    f.write(content)
                print(f"  💾 Saved fixes to {plugin_file.name}")
            else:
                print(f"  ✅ No fixes needed")
                
        except Exception as e:
            print(f"  ❌ Error fixing {plugin_file.name}: {e}")

def main():
    parser = argparse.ArgumentParser(
        description="Enterprise Plugin-Based Model Scaffold Generator v2.0",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scaffold_plugin_generator_v2.py add User name:str email:email age:int
  python scaffold_plugin_generator_v2.py add Product title:str:max_length=200 price:float:gt=0 --with-tasks --with-bulk
  python scaffold_plugin_generator_v2.py list
  python scaffold_plugin_generator_v2.py remove User
  python scaffold_plugin_generator_v2.py health-check
  python scaffold_plugin_generator_v2.py fix-plugins

Field Types:
  str, text, int, float, bool, date, datetime, email, url, uuid, json

Field Constraints:
  max_length=N, min_length=N, ge=N, le=N, gt=N, lt=N, unique, indexed, default=VALUE
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Add command
    add_parser = subparsers.add_parser('add', help='Generate a new model plugin')
    add_parser.add_argument('model', help='Model name (PascalCase)')
    add_parser.add_argument('fields', nargs='+', help='Field definitions (name:type[:constraints])')
    add_parser.add_argument('--with-tasks', action='store_true', help='Include Procrastinate tasks')
    add_parser.add_argument('--with-bulk', action='store_true', help='Include bulk operations')
    add_parser.add_argument('--no-migration', action='store_true', help='Skip database migration')
    
    # List command
    list_parser = subparsers.add_parser('list', help='List all generated plugins')
    
    # Remove command
    remove_parser = subparsers.add_parser('remove', help='Remove a plugin')
    remove_parser.add_argument('model', help='Model name to remove')
    
    # Health check command
    health_parser = subparsers.add_parser('health-check', help='Check plugin system health')
    
    # Fix plugins command
    fix_parser = subparsers.add_parser('fix-plugins', help='Fix common issues in existing plugins')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    try:
        if args.command == 'add':
            # Validate model name
            if not re.match(r'^[A-Z][a-zA-Z0-9]*$', args.model):
                print("❌ Model name must be PascalCase (e.g., User, ProductCategory)")
                return
            
            # Parse and validate fields
            fields = []
            for field_def in args.fields:
                try:
                    field = validate_field_definition(field_def)
                    fields.append(field)
                except ValueError as e:
                    print(f"❌ {e}")
                    return
            
            print(f"🚀 Generating {args.model} plugin...")
            print(f"📋 Fields: {[f'{f['name']}:{f['type']}' for f in fields]}")
            print(f"{'🔄 With Procrastinate tasks' if args.with_tasks else ''}")
            print(f"{'📦 With bulk operations' if args.with_bulk else ''}")
            print()
            
            # Create plugin
            plugin_file = create_plugin_file(args.model, fields, args.with_tasks, args.with_bulk)
            print(f"✅ Plugin created: {plugin_file}")
            
            # Generate migration
            if not args.no_migration:
                print("🔄 Generating database migration...")
                if generate_migration(args.model):
                    print("✅ Database migration completed")
                else:
                    print("⚠️  Plugin created but migration failed")
            
            print(f"\n🎉 {args.model} plugin generated successfully!")
            print(f"📁 Location: {plugin_file}")
            print(f"🔗 Endpoints will be available at: /{re.sub(r'(?<!^)(?=[A-Z])', '_', args.model).lower()}s/")
            
        elif args.command == 'list':
            list_plugins()
            
        elif args.command == 'remove':
            if remove_plugin(args.model):
                print(f"✅ {args.model} plugin removed successfully")
            else:
                print(f"❌ Failed to remove {args.model} plugin")
                
        elif args.command == 'health-check':
            health_check()
            
        elif args.command == 'fix-plugins':
            fix_plugins()
            
    except KeyboardInterrupt:
        print("\n⚠️  Operation cancelled by user")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 