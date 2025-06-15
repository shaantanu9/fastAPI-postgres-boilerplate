"""
Order background tasks
"""
import asyncio
from typing import Dict, Any, List

from .services import OrderService

# Procrastinate integration with error handling
try:
    from app.utils.procrastinate_manager import get_procrastinate_app
    # Get the procrastinate app instance
    procrastinate_app = get_procrastinate_app()
    PROCRASTINATE_AVAILABLE = True
except ImportError:
    print(f"⚠️ Procrastinate not available for Order plugin - background tasks disabled")
    procrastinate_app = None
    PROCRASTINATE_AVAILABLE = False


# Task functions for Order
if PROCRASTINATE_AVAILABLE and procrastinate_app:
    @procrastinate_app.task(name="order_cleanup")
    async def cleanup_order_records(older_than_days: int = 30):
        """Background task to cleanup old order records"""
        service = OrderService()
        try:
            count = await service.cleanup_old_records(older_than_days)
            print(f"Cleaned up {count} old order records")
            return {"status": "success", "cleaned_count": count}
        except Exception as e:
            print(f"Error cleaning up order records: {e}")
            return {"status": "error", "message": str(e)}
else:
    # Fallback function when Procrastinate is not available
    async def cleanup_order_records(older_than_days: int = 30):
        """Cleanup old order records (fallback without background processing)"""
        print("⚠️ Background task processing not available - executing synchronously")
        service = OrderService()
        try:
            count = await service.cleanup_old_records(older_than_days)
            print(f"Cleaned up {count} old order records")
            return {"status": "success", "cleaned_count": count}
        except Exception as e:
            print(f"Error cleaning up order records: {e}")
            return {"status": "error", "message": str(e)}


async def process_order_batch(batch_data: List[Dict[str, Any]]):
    """Process a batch of order data"""
    service = OrderService()
    try:
        results = []
        for item_data in batch_data:
            # Add your batch processing logic here
            result = await service.create(**item_data)
            results.append(result.id)
        
        print(f"Processed batch of {len(results)} order items")
        return {"status": "success", "processed_ids": results}
    except Exception as e:
        print(f"Error processing order batch: {e}")
        return {"status": "error", "message": str(e)}


async def generate_order_statistics():
    """Generate statistics for orders"""
    service = OrderService()
    try:
        stats = await service.get_statistics()
        print(f"Generated order statistics: {stats}")
        return {"status": "success", "statistics": stats}
    except Exception as e:
        print(f"Error generating order statistics: {e}")
        return {"status": "error", "message": str(e)}


# Export tasks for registration
TASKS = {
    "cleanup_order_records": cleanup_order_records,
    "process_order_batch": process_order_batch,
    "generate_order_statistics": generate_order_statistics
}
