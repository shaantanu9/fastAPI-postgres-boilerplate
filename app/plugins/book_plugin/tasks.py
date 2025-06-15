"""
Book background tasks
"""
import asyncio
from typing import Dict, Any, List

from .services import BookService

# Procrastinate integration with error handling
try:
    from app.utils.procrastinate_manager import get_procrastinate_app
    # Get the procrastinate app instance
    procrastinate_app = get_procrastinate_app()
    PROCRASTINATE_AVAILABLE = True
except ImportError:
    print(f"⚠️ Procrastinate not available for Book plugin - background tasks disabled")
    procrastinate_app = None
    PROCRASTINATE_AVAILABLE = False


# Task functions for Book
if PROCRASTINATE_AVAILABLE and procrastinate_app:
    @procrastinate_app.task(name="book_cleanup")
    async def cleanup_book_records(older_than_days: int = 30):
        """Background task to cleanup old book records"""
        service = BookService()
        try:
            count = await service.cleanup_old_records(older_than_days)
            print(f"Cleaned up {count} old book records")
            return {"status": "success", "cleaned_count": count}
        except Exception as e:
            print(f"Error cleaning up book records: {e}")
            return {"status": "error", "message": str(e)}
else:
    # Fallback function when Procrastinate is not available
    async def cleanup_book_records(older_than_days: int = 30):
        """Cleanup old book records (fallback without background processing)"""
        print("⚠️ Background task processing not available - executing synchronously")
        service = BookService()
        try:
            count = await service.cleanup_old_records(older_than_days)
            print(f"Cleaned up {count} old book records")
            return {"status": "success", "cleaned_count": count}
        except Exception as e:
            print(f"Error cleaning up book records: {e}")
            return {"status": "error", "message": str(e)}


async def process_book_batch(batch_data: List[Dict[str, Any]]):
    """Process a batch of book data"""
    service = BookService()
    try:
        results = []
        for item_data in batch_data:
            # Add your batch processing logic here
            result = await service.create(**item_data)
            results.append(result.id)
        
        print(f"Processed batch of {len(results)} book items")
        return {"status": "success", "processed_ids": results}
    except Exception as e:
        print(f"Error processing book batch: {e}")
        return {"status": "error", "message": str(e)}


async def generate_book_statistics():
    """Generate statistics for books"""
    service = BookService()
    try:
        stats = await service.get_statistics()
        print(f"Generated book statistics: {stats}")
        return {"status": "success", "statistics": stats}
    except Exception as e:
        print(f"Error generating book statistics: {e}")
        return {"status": "error", "message": str(e)}


# Export tasks for registration
TASKS = {
    "cleanup_book_records": cleanup_book_records,
    "process_book_batch": process_book_batch,
    "generate_book_statistics": generate_book_statistics
}
