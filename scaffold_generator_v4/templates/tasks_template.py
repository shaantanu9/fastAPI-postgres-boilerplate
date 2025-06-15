"""
Background tasks template generator
"""
from typing import List, Dict, Any
import re


class TasksTemplate:
    """Generates background tasks templates"""
    
    def generate(self, model_name: str) -> str:
        """Generate background tasks file content"""
        snake_name = re.sub(r'(?<!^)(?=[A-Z])', '_', model_name).lower()
        pascal_name = model_name
        
        template = f'''"""
{pascal_name} background tasks
"""
import asyncio
from typing import Dict, Any, List

from .services import {pascal_name}Service

# Procrastinate integration with error handling
try:
    from app.utils.procrastinate_manager import get_procrastinate_app
    # Get the procrastinate app instance
    procrastinate_app = get_procrastinate_app()
    PROCRASTINATE_AVAILABLE = True
except ImportError:
    print(f"⚠️ Procrastinate not available for {pascal_name} plugin - background tasks disabled")
    procrastinate_app = None
    PROCRASTINATE_AVAILABLE = False


# Task functions for {pascal_name}
if PROCRASTINATE_AVAILABLE and procrastinate_app:
    @procrastinate_app.task(name="{snake_name}_cleanup")
    async def cleanup_{snake_name}_records(older_than_days: int = 30):
        """Background task to cleanup old {snake_name} records"""
        service = {pascal_name}Service()
        try:
            count = await service.cleanup_old_records(older_than_days)
            print(f"Cleaned up {{count}} old {snake_name} records")
            return {{"status": "success", "cleaned_count": count}}
        except Exception as e:
            print(f"Error cleaning up {snake_name} records: {{e}}")
            return {{"status": "error", "message": str(e)}}
else:
    # Fallback function when Procrastinate is not available
    async def cleanup_{snake_name}_records(older_than_days: int = 30):
        """Cleanup old {snake_name} records (fallback without background processing)"""
        print("⚠️ Background task processing not available - executing synchronously")
        service = {pascal_name}Service()
        try:
            count = await service.cleanup_old_records(older_than_days)
            print(f"Cleaned up {{count}} old {snake_name} records")
            return {{"status": "success", "cleaned_count": count}}
        except Exception as e:
            print(f"Error cleaning up {snake_name} records: {{e}}")
            return {{"status": "error", "message": str(e)}}


async def process_{snake_name}_batch(batch_data: List[Dict[str, Any]]):
    """Process a batch of {snake_name} data"""
    service = {pascal_name}Service()
    try:
        results = []
        for item_data in batch_data:
            # Add your batch processing logic here
            result = await service.create(**item_data)
            results.append(result.id)
        
        print(f"Processed batch of {{len(results)}} {snake_name} items")
        return {{"status": "success", "processed_ids": results}}
    except Exception as e:
        print(f"Error processing {snake_name} batch: {{e}}")
        return {{"status": "error", "message": str(e)}}


async def generate_{snake_name}_statistics():
    """Generate statistics for {snake_name}s"""
    service = {pascal_name}Service()
    try:
        stats = await service.get_statistics()
        print(f"Generated {snake_name} statistics: {{stats}}")
        return {{"status": "success", "statistics": stats}}
    except Exception as e:
        print(f"Error generating {snake_name} statistics: {{e}}")
        return {{"status": "error", "message": str(e)}}


# Export tasks for registration
TASKS = {{
    "cleanup_{snake_name}_records": cleanup_{snake_name}_records,
    "process_{snake_name}_batch": process_{snake_name}_batch,
    "generate_{snake_name}_statistics": generate_{snake_name}_statistics
}}
'''
        
        return template 