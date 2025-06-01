"""
Field validation and processing for scaffold generator
"""
import re
from typing import Dict, Any, List


class FieldValidator:
    """Handles validation and processing of field definitions"""
    
    def __init__(self):
        self.type_mapping = {
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
        
        self.sqlalchemy_mapping = {
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
    
    def validate_field_definition(self, field_def: str) -> Dict[str, Any]:
        """
        Validate and parse field definition.
        Format: name:type[:constraint1:constraint2]
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
        
        if field_type not in self.type_mapping:
            raise ValueError(f"Unsupported field type: {field_type}. Supported types: {list(self.type_mapping.keys())}")
        
        return {
            'name': field_name,
            'type': field_type,
            'python_type': self.type_mapping[field_type],
            'constraints': constraints
        }
    
    def validate_fields_batch(self, field_definitions: List[str]) -> List[Dict[str, Any]]:
        """Validate multiple field definitions"""
        validated_fields = []
        for field_def in field_definitions:
            validated_field = self.validate_field_definition(field_def)
            validated_fields.append(validated_field)
        return validated_fields
    
    def get_sqlalchemy_column(self, field: Dict[str, Any]) -> str:
        """Generate SQLAlchemy column definition"""
        field_name = field['name']
        field_type = field['type']
        constraints = field['constraints']
        
        column_type = self.sqlalchemy_mapping.get(field_type, 'String(255)')
        
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
    
    def get_pydantic_field(self, field: Dict[str, Any], for_update: bool = False) -> str:
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
        
        if for_update:
            # For update schemas, make fields optional
            if field_constraints:
                constraints_str = ', '.join(field_constraints)
                return f"    {field_name}: Optional[{python_type}] = Field(None, {constraints_str})"
            else:
                return f"    {field_name}: Optional[{python_type}] = None"
        else:
            # For create schemas, keep fields required
            if field_constraints:
                constraints_str = ', '.join(field_constraints)
                return f"    {field_name}: {python_type} = Field(..., {constraints_str})"
            else:
                return f"    {field_name}: {python_type}"
    
    def get_required_imports(self, fields: List[Dict[str, Any]]) -> Dict[str, List[str]]:
        """Get required imports based on field types"""
        pydantic_imports = set()
        
        for field in fields:
            if field['python_type'] == 'EmailStr':
                pydantic_imports.add('EmailStr')
            elif field['python_type'] == 'HttpUrl':
                pydantic_imports.add('HttpUrl')
            elif field['python_type'] == 'UUID':
                pydantic_imports.add('UUID')
            elif field['python_type'] == 'datetime':
                pydantic_imports.add('datetime')
            elif field['python_type'] == 'date':
                pydantic_imports.add('date')
            elif field['python_type'] == 'Dict[str, Any]':
                pydantic_imports.add('Dict')
                pydantic_imports.add('Any')
        
        return {
            'pydantic': list(pydantic_imports)
        } 