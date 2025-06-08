"""ProductTest service layer - Business logic."""

from typing import Any

from sqlalchemy import or_

from app.services.enhanced_base_service import EnhancedBaseService

from .models import ProductTest
from .schemas import ProductTestCreate, ProductTestUpdate


class ProductTestService(EnhancedBaseService[ProductTest]):
    """Business logic service for ProductTest."""

    def __init__(self) -> None:
        super().__init__(ProductTest)

    async def create(self, **kwargs) -> ProductTest:
        """Create a new product_test with business validation."""
        # Add any business logic validation here
        return await super().create(**kwargs)

    async def get_by_name(self, name: str) -> ProductTest | None:
        """Get product_test by name if name field exists."""
        if hasattr(ProductTest, "name"):
            return await self.get_by_field("name", name)
        return None

    async def search(
        self, query: str, limit: int = 10, skip: int = 0,
    ) -> list[ProductTest]:
        """Search product_tests by text fields."""
        async with self.get_db() as db:
            # Build search conditions for text fields
            search_conditions = []

            search_conditions = [
                self.model.name.ilike(f"%{query}%"),
                self.model.category.ilike(f"%{query}%"),
            ]

            if search_conditions:
                db_query = (
                    db.query(self.model)
                    .filter(or_(*search_conditions))
                    .offset(skip)
                    .limit(limit)
                )
                return await db_query.all()

            # Fallback to get_all if no searchable fields
            return await self.get_all(skip=skip, limit=limit)

    async def get_statistics(self) -> dict[str, Any]:
        """Get product_test statistics."""
        async with self.get_db():
            total = await self.count()

            # Add more statistics as needed
            return {"total_product_tests": total, "model_name": "ProductTest"}


    async def bulk_create(self, items: list[ProductTestCreate]) -> list[ProductTest]:
        """Create multiple product_tests."""
        results = []
        for item in items:
            result = await self.create(**item.dict())
            results.append(result)
        return results

    async def bulk_update(self, updates: list[ProductTestUpdate]) -> list[ProductTest]:
        """Update multiple product_tests."""
        results = []
        for update in updates:
            if update.id:
                result = await self.update(
                    update.id, **update.dict(exclude={"id"}, exclude_unset=True),
                )
                if result:
                    results.append(result)
        return results

    async def cleanup_old_records(self, older_than_days: int = 30) -> int:
        """Cleanup old product_test records (for background tasks)."""
        # Implement cleanup logic based on created_at
        # This is a placeholder - customize based on your needs
        return 0

    async def validate_business_rules(self, data: dict[str, Any]) -> dict[str, Any]:
        """Validate business rules for ProductTest."""
        errors = []

        # Add custom business validation here
        # Example:
        # if 'email' in data and not self._is_valid_email(data['email']):
        #     errors.append("Invalid email format")

        return {"valid": len(errors) == 0, "errors": errors}

    def _is_searchable_field(self, field_name: str) -> bool:
        """Check if field is searchable (text fields)."""
        field = getattr(ProductTest, field_name, None)
        if field is None:
            return False

        # Check if it's a string-like field
        searchable_types = ["String", "Text"]
        return any(field_type in str(field.type) for field_type in searchable_types)
