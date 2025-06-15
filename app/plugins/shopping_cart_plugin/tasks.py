"""
ShoppingCart background tasks
"""
import asyncio
from typing import Dict, Any, List

from .services import ShoppingCartService

# Procrastinate integration with error handling
try:
    from app.utils.procrastinate_manager import get_procrastinate_app
    # Get the procrastinate app instance
    procrastinate_app = get_procrastinate_app()
    PROCRASTINATE_AVAILABLE = True
except ImportError:
    print(f"⚠️ Procrastinate not available for ShoppingCart plugin - background tasks disabled")
    procrastinate_app = None
    PROCRASTINATE_AVAILABLE = False


# Task functions for ShoppingCart
if PROCRASTINATE_AVAILABLE and procrastinate_app:
    @procrastinate_app.task(name="shopping_cart_cleanup")
    async def cleanup_shopping_cart_records(older_than_days: int = 30):
        """Background task to cleanup old shopping_cart records"""
        service = ShoppingCartService()
        try:
            count = await service.cleanup_old_records(older_than_days)
            print(f"Cleaned up {count} old shopping_cart records")
            return {"status": "success", "cleaned_count": count}
        except Exception as e:
            print(f"Error cleaning up shopping_cart records: {e}")
            return {"status": "error", "message": str(e)}
else:
    # Fallback function when Procrastinate is not available
    async def cleanup_shopping_cart_records(older_than_days: int = 30):
        """Cleanup old shopping_cart records (fallback without background processing)"""
        print("⚠️ Background task processing not available - executing synchronously")
        service = ShoppingCartService()
        try:
            count = await service.cleanup_old_records(older_than_days)
            print(f"Cleaned up {count} old shopping_cart records")
            return {"status": "success", "cleaned_count": count}
        except Exception as e:
            print(f"Error cleaning up shopping_cart records: {e}")
            return {"status": "error", "message": str(e)}


async def process_shopping_cart_batch(batch_data: List[Dict[str, Any]]):
    """Process a batch of shopping_cart data"""
    service = ShoppingCartService()
    try:
        results = []
        for item_data in batch_data:
            # Add your batch processing logic here
            result = await service.create(**item_data)
            results.append(result.id)
        
        print(f"Processed batch of {len(results)} shopping_cart items")
        return {"status": "success", "processed_ids": results}
    except Exception as e:
        print(f"Error processing shopping_cart batch: {e}")
        return {"status": "error", "message": str(e)}


async def generate_shopping_cart_statistics():
    """Generate statistics for shopping_carts"""
    service = ShoppingCartService()
    try:
        stats = await service.get_statistics()
        print(f"Generated shopping_cart statistics: {stats}")
        return {"status": "success", "statistics": stats}
    except Exception as e:
        print(f"Error generating shopping_cart statistics: {e}")
        return {"status": "error", "message": str(e)}


# Export tasks for registration
TASKS = {
    "cleanup_shopping_cart_records": cleanup_shopping_cart_records,
    "process_shopping_cart_batch": process_shopping_cart_batch,
    "generate_shopping_cart_statistics": generate_shopping_cart_statistics
}
