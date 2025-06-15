"""
Product background tasks
"""
import asyncio
from typing import Dict, Any, List

from .services import ProductService

# Procrastinate integration with error handling
try:
    from app.utils.procrastinate_manager import get_procrastinate_app
    # Get the procrastinate app instance
    procrastinate_app = get_procrastinate_app()
    PROCRASTINATE_AVAILABLE = True
except ImportError:
    print(f"⚠️ Procrastinate not available for Product plugin - background tasks disabled")
    procrastinate_app = None
    PROCRASTINATE_AVAILABLE = False


# Task functions for Product
if PROCRASTINATE_AVAILABLE and procrastinate_app:
    @procrastinate_app.task(name="product_cleanup")
    async def cleanup_product_records(older_than_days: int = 30):
        """Background task to cleanup old product records"""
        service = ProductService()
        try:
            count = await service.cleanup_old_records(older_than_days)
            print(f"Cleaned up {count} old product records")
            return {"status": "success", "cleaned_count": count}
        except Exception as e:
            print(f"Error cleaning up product records: {e}")
            return {"status": "error", "message": str(e)}
else:
    # Fallback function when Procrastinate is not available
    async def cleanup_product_records(older_than_days: int = 30):
        """Cleanup old product records (fallback without background processing)"""
        print("⚠️ Background task processing not available - executing synchronously")
        service = ProductService()
        try:
            count = await service.cleanup_old_records(older_than_days)
            print(f"Cleaned up {count} old product records")
            return {"status": "success", "cleaned_count": count}
        except Exception as e:
            print(f"Error cleaning up product records: {e}")
            return {"status": "error", "message": str(e)}


async def process_product_batch(batch_data: List[Dict[str, Any]]):
    """Process a batch of product data"""
    service = ProductService()
    try:
        results = []
        for item_data in batch_data:
            # Add your batch processing logic here
            result = await service.create(**item_data)
            results.append(result.id)
        
        print(f"Processed batch of {len(results)} product items")
        return {"status": "success", "processed_ids": results}
    except Exception as e:
        print(f"Error processing product batch: {e}")
        return {"status": "error", "message": str(e)}


async def generate_product_statistics():
    """Generate statistics for products"""
    service = ProductService()
    try:
        stats = await service.get_statistics()
        print(f"Generated product statistics: {stats}")
        return {"status": "success", "statistics": stats}
    except Exception as e:
        print(f"Error generating product statistics: {e}")
        return {"status": "error", "message": str(e)}


# Export tasks for registration
TASKS = {
    "cleanup_product_records": cleanup_product_records,
    "process_product_batch": process_product_batch,
    "generate_product_statistics": generate_product_statistics
}
