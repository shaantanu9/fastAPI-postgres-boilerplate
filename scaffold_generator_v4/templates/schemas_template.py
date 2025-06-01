"""
Pydantic schemas template generator
"""
from typing import List, Dict, Any
import re


class SchemasTemplate:
    """Generates Pydantic schema templates"""
    
    def generate(self, model_name: str, fields: List[Dict[str, Any]], field_validator) -> str:
        """Generate Pydantic schemas file content"""
        pascal_name = model_name
        
        # Generate field definitions
        pydantic_fields = []
        pydantic_update_fields = []
        
        for field in fields:
            pydantic_fields.append(field_validator.get_pydantic_field(field))
            pydantic_update_fields.append(field_validator.get_pydantic_field(field, for_update=True))
        
        pydantic_fields_str = '\n'.join(pydantic_fields)
        pydantic_update_fields_str = '\n'.join(pydantic_update_fields)
        
        # Get required imports
        imports = field_validator.get_required_imports(fields)
        pydantic_import_str = self._generate_import_statements(imports)
        
        template = f'''"""
{pascal_name} Pydantic schemas
"""
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
{pydantic_import_str}from datetime import datetime


class {pascal_name}Base(BaseModel):
    """Base schema for {pascal_name}"""
{pydantic_fields_str}


class {pascal_name}Create({pascal_name}Base):
    """Schema for creating {pascal_name}"""
    pass


class {pascal_name}Update(BaseModel):
    """Schema for updating {pascal_name}"""
    id: Optional[int] = None
{pydantic_update_fields_str}


class {pascal_name}Response({pascal_name}Base):
    """Schema for {pascal_name} response"""
    id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class {pascal_name}List(BaseModel):
    """Schema for {pascal_name} list response"""
    items: List[{pascal_name}Response]
    total: int
    page: int
    size: int
    pages: int


class {pascal_name}Search(BaseModel):
    """Schema for {pascal_name} search parameters"""
    query: Optional[str] = None
    page: int = 1
    size: int = 10
    sort_by: Optional[str] = None
    sort_order: Optional[str] = "asc"
'''
        
        return template
    
    def _generate_import_statements(self, imports: Dict[str, List[str]]) -> str:
        """Generate import statements based on field types"""
        import_lines = []
        
        pydantic_imports = imports.get('pydantic', [])
        if pydantic_imports:
            if 'EmailStr' in pydantic_imports or 'HttpUrl' in pydantic_imports:
                email_url_imports = [imp for imp in pydantic_imports if imp in ['EmailStr', 'HttpUrl']]
                import_lines.append(f"from pydantic import {', '.join(email_url_imports)}")
            
            if 'UUID' in pydantic_imports:
                import_lines.append("from uuid import UUID")
            
            if 'datetime' in pydantic_imports or 'date' in pydantic_imports:
                datetime_imports = [imp for imp in pydantic_imports if imp in ['datetime', 'date']]
                import_lines.append(f"from datetime import {', '.join(datetime_imports)}")
            
            if 'Dict' in pydantic_imports or 'Any' in pydantic_imports:
                typing_imports = [imp for imp in pydantic_imports if imp in ['Dict', 'Any']]
                # These are already imported in the main typing import
        
        if import_lines:
            return '\n'.join(import_lines) + '\n'
        return '' 