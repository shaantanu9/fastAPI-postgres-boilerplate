"""
Order service layer - Business logic
"""
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_

from app.services.enhanced_base_service import EnhancedBaseService
from .models import Order
from .schemas import OrderCreate, OrderUpdate, OrderResponse


class OrderService(EnhancedBaseService[Order]):
    """Business logic service for Order"""
    
    def __init__(self):
        super().__init__(Order)
    
    async def create(self, **kwargs) -> Order:
        """Create a new order with business validation"""
        # Add any business logic validation here
        return await super().create(**kwargs)
    
    async def get_by_name(self, name: str) -> Optional[Order]:
        """Get order by name if name field exists"""
        if hasattr(Order, 'name'):
            return await self.get_by_field("name", name)
        return None
    
    async def search(self, query: str, limit: int = 10, skip: int = 0) -> List[Order]:
        """Search orders by text fields"""
        async with self.get_db() as db:
            # Build search conditions for text fields
            search_conditions = []
            
            search_conditions = [
                self.model.customer_name.ilike(f'%{query}%'),
                self.model.customer_email.ilike(f'%{query}%'),
                self.model.status.ilike(f'%{query}%'),
                self.model.shipping_address.ilike(f'%{query}%'),
                self.model.notes.ilike(f'%{query}%')
            ]
            
            if search_conditions:
                db_query = db.query(self.model).filter(
                    or_(*search_conditions)
                ).offset(skip).limit(limit)
                result = await db_query.all()
                return result
            
            # Fallback to get_all if no searchable fields
            return await self.get_all(skip=skip, limit=limit)
    
    async def get_statistics(self) -> Dict[str, Any]:
        """Get order statistics"""
        async with self.get_db() as db:
            total = await self.count()
            
            # Add more statistics as needed
            stats = {
                'total_orders': total,
                'model_name': 'Order'
            }
            
            return stats
    
    async def bulk_create(self, items: List[OrderCreate]) -> List[Order]:
        """Create multiple orders"""
        results = []
        for item in items:
            result = await self.create(**item.dict())
            results.append(result)
        return results
    
    async def bulk_update(self, updates: List[OrderUpdate]) -> List[Order]:
        """Update multiple orders"""
        results = []
        for update in updates:
            if update.id:
                result = await self.update(update.id, **update.dict(exclude={'id'}, exclude_unset=True))
                if result:
                    results.append(result)
        return results
    
    async def cleanup_old_records(self, older_than_days: int = 30) -> int:
        """Cleanup old order records (for background tasks)"""
        # Implement cleanup logic based on created_at
        # This is a placeholder - customize based on your needs
        return 0
    
    async def validate_business_rules(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate business rules for Order"""
        errors = []
        
        # Add custom business validation here
        # Example:
        # if 'email' in data and not self._is_valid_email(data['email']):
        #     errors.append("Invalid email format")
        
        return {
            'valid': len(errors) == 0,
            'errors': errors
        }
    
    def _is_searchable_field(self, field_name: str) -> bool:
        """Check if field is searchable (text fields)"""
        field = getattr(Order, field_name, None)
        if field is None:
            return False
        
        # Check if it's a string-like field
        searchable_types = ['String', 'Text']
        return any(field_type in str(field.type) for field_type in searchable_types)
