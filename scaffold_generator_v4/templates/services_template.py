"""
Services template generator for business logic
"""
from typing import List, Dict, Any
import re


class ServicesTemplate:
    """Generates service layer templates"""
    
    def generate(self, model_name: str, fields: List[Dict[str, Any]]) -> str:
        """Generate service layer file content"""
        snake_name = re.sub(r'(?<!^)(?=[A-Z])', '_', model_name).lower()
        pascal_name = model_name
        
        template = f'''"""
{pascal_name} service layer - Business logic
"""
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_

# Enhanced base service import - configurable based on project structure
try:
    from app.services.enhanced_base_service import EnhancedBaseService
except ImportError:
    # Fallback for standalone testing
    class EnhancedBaseService:
        def __init__(self, model):
            self.model = model
        
        async def create(self, **kwargs):
            # Placeholder implementation
            pass
        
        async def get_by_field(self, field, value):
            # Placeholder implementation
            pass
        
        async def get_all(self, skip=0, limit=10):
            # Placeholder implementation
            pass
        
        async def count(self):
            # Placeholder implementation
            return 0
        
        async def update(self, id, **kwargs):
            # Placeholder implementation
            pass
        
        def get_db(self):
            # Placeholder implementation
            pass

from .models import {pascal_name}
from .schemas import {pascal_name}Create, {pascal_name}Update, {pascal_name}Response


class {pascal_name}Service(EnhancedBaseService[{pascal_name}]):
    """Business logic service for {pascal_name}"""
    
    def __init__(self):
        super().__init__({pascal_name})
    
    async def create(self, **kwargs) -> {pascal_name}:
        """Create a new {snake_name} with business validation"""
        # Add any business logic validation here
        return await super().create(**kwargs)
    
    async def get_by_name(self, name: str) -> Optional[{pascal_name}]:
        """Get {snake_name} by name if name field exists"""
        if hasattr({pascal_name}, 'name'):
            return await self.get_by_field("name", name)
        return None
    
    async def search(self, query: str, limit: int = 10, skip: int = 0) -> List[{pascal_name}]:
        """Search {snake_name}s by text fields"""
        async with self.get_db() as db:
            # Build search conditions for text fields
            search_conditions = []
            
            {self._generate_search_conditions(fields)}
            
            if search_conditions:
                db_query = db.query(self.model).filter(
                    or_(*search_conditions)
                ).offset(skip).limit(limit)
                result = await db_query.all()
                return result
            
            # Fallback to get_all if no searchable fields
            return await self.get_all(skip=skip, limit=limit)
    
    async def get_statistics(self) -> Dict[str, Any]:
        """Get {snake_name} statistics"""
        async with self.get_db() as db:
            total = await self.count()
            
            # Add more statistics as needed
            stats = {{
                'total_{snake_name}s': total,
                'model_name': '{pascal_name}'
            }}
            
            return stats
    
    async def bulk_create(self, items: List[{pascal_name}Create]) -> List[{pascal_name}]:
        """Create multiple {snake_name}s"""
        results = []
        for item in items:
            result = await self.create(**item.dict())
            results.append(result)
        return results
    
    async def bulk_update(self, updates: List[{pascal_name}Update]) -> List[{pascal_name}]:
        """Update multiple {snake_name}s"""
        results = []
        for update in updates:
            if update.id:
                result = await self.update(update.id, **update.dict(exclude={{'id'}}, exclude_unset=True))
                if result:
                    results.append(result)
        return results
    
    async def cleanup_old_records(self, older_than_days: int = 30) -> int:
        """Cleanup old {snake_name} records (for background tasks)"""
        # Implement cleanup logic based on created_at
        # This is a placeholder - customize based on your needs
        return 0
    
    async def validate_business_rules(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate business rules for {pascal_name}"""
        errors = []
        
        # Add custom business validation here
        # Example:
        # if 'email' in data and not self._is_valid_email(data['email']):
        #     errors.append("Invalid email format")
        
        return {{
            'valid': len(errors) == 0,
            'errors': errors
        }}
    
    def _is_searchable_field(self, field_name: str) -> bool:
        """Check if field is searchable (text fields)"""
        field = getattr({pascal_name}, field_name, None)
        if field is None:
            return False
        
        # Check if it's a string-like field
        searchable_types = ['String', 'Text']
        return any(field_type in str(field.type) for field_type in searchable_types)
'''
        
        return template
    
    def _generate_search_conditions(self, fields: List[Dict[str, Any]]) -> str:
        """Generate search conditions for text fields"""
        text_fields = [field for field in fields if field['type'] in ['str', 'text', 'email', 'url']]
        
        if not text_fields:
            return "# No searchable text fields available"
        
        conditions = []
        for field in text_fields:
            field_name = field['name']
            conditions.append(f"                self.model.{field_name}.ilike(f'%{{query}}%')")
        
        if conditions:
            conditions_str = ',\n'.join(conditions)
            return f"search_conditions = [\n{conditions_str}\n            ]"
        else:
            return "# No searchable fields found" 