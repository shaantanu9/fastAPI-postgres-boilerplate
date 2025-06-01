"""
Enhanced Base Service with Concurrent Processing Capabilities.

This service extends the original BaseService with parallel processing features
using concurrent.futures for improved performance with large datasets.
"""

from typing import Type, TypeVar, Generic, Optional, List, Any, Dict, Callable, Union
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import func, delete as sqlalchemy_delete, update as sqlalchemy_update
import asyncio
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
from loguru import logger
import time

from app.services.base_service import BaseService
from app.utils.concurrent_utils import (
    execute_parallel, TaskType, parallel_io, parallel_cpu, 
    concurrent_manager, ConcurrentConfig
)

ModelType = TypeVar("ModelType")


class EnhancedBaseService(BaseService[ModelType]):
    """
    Enhanced Base Service with concurrent processing capabilities.
    
    Extends BaseService with parallel processing methods for:
    - Bulk operations with parallel database access
    - Parallel data validation and transformation
    - Concurrent external API calls
    - Parallel file processing
    
    Example:
        class UserService(EnhancedBaseService[User]):
            def __init__(self):
                super().__init__(User)
    """
    
    def __init__(self, model: Type[ModelType]):
        super().__init__(model)
        self.batch_size = ConcurrentConfig.DEFAULT_BATCH_SIZE
    
    # Parallel Database Operations
    
    async def bulk_create_parallel(
        self, 
        db: AsyncSession, 
        items: List[Dict[str, Any]], 
        batch_size: Optional[int] = None,
        validate_func: Optional[Callable] = None
    ) -> List[ModelType]:
        """
        Create multiple records in parallel batches with optional validation.
        
        Args:
            db: Database session
            items: List of dictionaries to create
            batch_size: Size of each batch for processing
            validate_func: Optional validation function to run in parallel
        
        Returns:
            List of created model instances
        """
        if not items:
            return []
        
        start_time = time.time()
        logger.info(f"Starting bulk parallel create for {self.model.__name__}: {len(items)} items")
        
        # Validate items in parallel if validation function provided
        if validate_func:
            validated_items = await execute_parallel(
                validate_func, items, TaskType.CPU_BOUND, batch_size=batch_size
            )
            # Filter out validation errors
            items = [item for item in validated_items if not isinstance(item, Exception)]
        
        # Process in batches to avoid overwhelming the database
        batch_size = batch_size or self.batch_size
        batches = [items[i:i + batch_size] for i in range(0, len(items), batch_size)]
        
        async def create_batch(batch: List[Dict[str, Any]]) -> List[ModelType]:
            """Create a single batch of items"""
            try:
                return await self.bulk_add(db, batch)
            except Exception as e:
                logger.error(f"Error creating batch: {e}")
                return []
        
        # Execute batches in parallel using I/O executor
        batch_results = await execute_parallel(
            create_batch, batches, TaskType.IO_BOUND, max_workers=5
        )
        
        # Flatten results
        results = []
        for batch_result in batch_results:
            if isinstance(batch_result, list):
                results.extend(batch_result)
        
        duration = time.time() - start_time
        logger.info(f"Completed bulk parallel create: {len(results)} items in {duration:.2f}s")
        
        return results
    
    async def bulk_update_parallel(
        self, 
        db: AsyncSession, 
        updates: List[Dict[str, Any]], 
        id_field: str = "id",
        processor_func: Optional[Callable] = None
    ) -> List[ModelType]:
        """
        Update multiple records in parallel.
        
        Args:
            db: Database session
            updates: List of update dictionaries with id_field
            id_field: Field name for identifying records to update
            processor_func: Optional processing function for update data
        
        Returns:
            List of updated model instances
        """
        if not updates:
            return []
        
        start_time = time.time()
        logger.info(f"Starting bulk parallel update for {self.model.__name__}: {len(updates)} items")
        
        # Process update data in parallel if processor provided
        if processor_func:
            processed_updates = await execute_parallel(
                processor_func, updates, TaskType.CPU_BOUND
            )
            updates = [item for item in processed_updates if not isinstance(item, Exception)]
        
        async def update_single(update_data: Dict[str, Any]) -> Optional[ModelType]:
            """Update a single record"""
            try:
                record_id = update_data.pop(id_field)
                return await self.update_one(db, {id_field: record_id}, update_data)
            except Exception as e:
                logger.error(f"Error updating record: {e}")
                return None
        
        # Execute updates in parallel
        results = await execute_parallel(
            update_single, updates, TaskType.IO_BOUND, max_workers=10
        )
        
        # Filter out None results
        successful_updates = [r for r in results if r is not None and not isinstance(r, Exception)]
        
        duration = time.time() - start_time
        logger.info(f"Completed bulk parallel update: {len(successful_updates)} items in {duration:.2f}s")
        
        return successful_updates
    
    async def bulk_delete_parallel(
        self, 
        db: AsyncSession, 
        identifiers: List[Any], 
        id_field: str = "id"
    ) -> int:
        """
        Delete multiple records in parallel.
        
        Args:
            db: Database session
            identifiers: List of identifiers to delete
            id_field: Field name for identification
        
        Returns:
            Number of records deleted
        """
        if not identifiers:
            return 0
        
        start_time = time.time()
        logger.info(f"Starting bulk parallel delete for {self.model.__name__}: {len(identifiers)} items")
        
        async def delete_single(identifier: Any) -> bool:
            """Delete a single record"""
            try:
                return await self.delete_one(db, {id_field: identifier})
            except Exception as e:
                logger.error(f"Error deleting record {identifier}: {e}")
                return False
        
        # Execute deletions in parallel
        results = await execute_parallel(
            delete_single, identifiers, TaskType.IO_BOUND, max_workers=10
        )
        
        # Count successful deletions
        deleted_count = sum(1 for r in results if r is True)
        
        duration = time.time() - start_time
        logger.info(f"Completed bulk parallel delete: {deleted_count} items in {duration:.2f}s")
        
        return deleted_count
    
    # Parallel Data Processing
    
    async def process_data_parallel(
        self, 
        data: List[Any], 
        processor_func: Callable,
        task_type: TaskType = TaskType.CPU_BOUND,
        max_workers: Optional[int] = None,
        batch_size: Optional[int] = None
    ) -> List[Any]:
        """
        Process data in parallel using the specified processor function.
        
        Args:
            data: List of data items to process
            processor_func: Function to process each item
            task_type: Type of task (CPU_BOUND or IO_BOUND)
            max_workers: Maximum number of workers
            batch_size: Batch size for large datasets
        
        Returns:
            List of processed results
        """
        return await execute_parallel(
            processor_func, data, task_type, max_workers, batch_size
        )
    
    async def validate_data_parallel(
        self, 
        data: List[Dict[str, Any]], 
        validation_func: Callable,
        max_workers: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Validate data in parallel using CPU-bound processing.
        
        Args:
            data: List of data dictionaries to validate
            validation_func: Validation function
            max_workers: Maximum number of processes
        
        Returns:
            List of validated data (errors filtered out)
        """
        results = await execute_parallel(
            validation_func, data, TaskType.CPU_BOUND, max_workers
        )
        
        # Filter out validation errors and return only valid data
        return [item for item in results if not isinstance(item, Exception)]
    
    # Parallel External Operations
    
    async def fetch_external_data_parallel(
        self, 
        urls_or_params: List[Any], 
        fetch_func: Callable,
        max_workers: Optional[int] = None
    ) -> List[Any]:
        """
        Fetch data from external sources in parallel.
        
        Args:
            urls_or_params: List of URLs or parameters for fetching
            fetch_func: Function to fetch data
            max_workers: Maximum number of threads
        
        Returns:
            List of fetched results
        """
        return await execute_parallel(
            fetch_func, urls_or_params, TaskType.IO_BOUND, max_workers
        )
    
    async def send_notifications_parallel(
        self, 
        notifications: List[Dict[str, Any]], 
        send_func: Callable,
        max_workers: Optional[int] = None
    ) -> List[Any]:
        """
        Send notifications (email, SMS, etc.) in parallel.
        
        Args:
            notifications: List of notification data
            send_func: Function to send single notification
            max_workers: Maximum number of threads
        
        Returns:
            List of sending results
        """
        return await execute_parallel(
            send_func, notifications, TaskType.IO_BOUND, max_workers
        )
    
    # Parallel File Operations
    
    async def process_files_parallel(
        self, 
        file_paths: List[str], 
        process_func: Callable,
        task_type: TaskType = TaskType.CPU_BOUND,
        max_workers: Optional[int] = None
    ) -> List[Any]:
        """
        Process files in parallel (reading, transformation, etc.).
        
        Args:
            file_paths: List of file paths to process
            process_func: Function to process single file
            task_type: CPU_BOUND for processing, IO_BOUND for reading/writing
            max_workers: Maximum number of workers
        
        Returns:
            List of processing results
        """
        return await execute_parallel(
            process_func, file_paths, task_type, max_workers
        )
    
    # Advanced Query Operations
    
    async def find_parallel_with_conditions(
        self, 
        db: AsyncSession, 
        condition_sets: List[Dict[str, Any]],
        max_workers: Optional[int] = None
    ) -> List[List[ModelType]]:
        """
        Execute multiple find operations with different conditions in parallel.
        
        Args:
            db: Database session
            condition_sets: List of condition dictionaries
            max_workers: Maximum number of threads
        
        Returns:
            List of query results for each condition set
        """
        async def find_with_condition(conditions: Dict[str, Any]) -> List[ModelType]:
            return await self.find(db, conditions)
        
        return await execute_parallel(
            find_with_condition, condition_sets, TaskType.IO_BOUND, max_workers
        )
    
    async def aggregate_parallel(
        self, 
        db: AsyncSession, 
        aggregation_configs: List[Dict[str, Any]],
        max_workers: Optional[int] = None
    ) -> List[Any]:
        """
        Execute multiple aggregation queries in parallel.
        
        Args:
            db: Database session
            aggregation_configs: List of aggregation configurations
            max_workers: Maximum number of threads
        
        Returns:
            List of aggregation results
        """
        async def execute_aggregation(config: Dict[str, Any]) -> Any:
            return await self.aggregate(
                db, 
                config.get('aggregates', {}), 
                config.get('filters')
            )
        
        return await execute_parallel(
            execute_aggregation, aggregation_configs, TaskType.IO_BOUND, max_workers
        )
    
    # Statistics and Analytics
    
    async def generate_statistics_parallel(
        self, 
        db: AsyncSession, 
        stat_configs: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Generate multiple statistics in parallel.
        
        Args:
            db: Database session
            stat_configs: List of statistic configurations
        
        Returns:
            Dictionary of statistics results
        """
        async def calculate_stat(config: Dict[str, Any]) -> tuple:
            stat_name = config['name']
            if config['type'] == 'count':
                result = await self.count(db, config.get('filters'))
            elif config['type'] == 'aggregation':
                result = await self.aggregate(db, config['aggregates'], config.get('filters'))
            else:
                result = None
            
            return stat_name, result
        
        results = await execute_parallel(
            calculate_stat, stat_configs, TaskType.IO_BOUND
        )
        
        # Convert to dictionary
        return {name: result for name, result in results if not isinstance((name, result), Exception)}
    
    # Utility Methods
    
    def set_batch_size(self, batch_size: int):
        """Set the default batch size for operations"""
        self.batch_size = batch_size
    
    async def health_check_parallel(self, db: AsyncSession) -> Dict[str, Any]:
        """
        Perform parallel health checks on the service.
        """
        async def check_db_connection():
            try:
                await db.execute(select(1))
                return True
            except Exception:
                return False
        
        async def check_table_exists():
            try:
                await db.execute(select(func.count()).select_from(self.model))
                return True
            except Exception:
                return False
        
        checks = [check_db_connection(), check_table_exists()]
        results = await asyncio.gather(*checks, return_exceptions=True)
        
        return {
            "service": self.model.__name__,
            "database_connection": results[0] if not isinstance(results[0], Exception) else False,
            "table_exists": results[1] if not isinstance(results[1], Exception) else False,
            "status": "healthy" if all(results) else "unhealthy"
        }

    # Bridge methods for scaffold-generated plugins compatibility
    # These methods provide expected signatures that match scaffold-generated code
    # They use a dependency injection pattern to get database sessions
    
    async def _get_db_session(self):
        """Get database session using AsyncSessionLocal directly"""
        from app.db.session import AsyncSessionLocal
        return AsyncSessionLocal()
    
    async def get_all(self, skip: int = 0, limit: int = 100, filters: Optional[Dict[str, Any]] = None) -> List[ModelType]:
        """
        Get all records with pagination - bridges to BaseService.paginate() or all()
        Compatible with scaffold-generated plugins expecting get_all(skip, limit)
        """
        db = await self._get_db_session()
        try:
            if skip == 0 and limit == 100:
                # Use the all() method for default parameters
                return await self.all(db, filters)
            else:
                # Use pagination for custom skip/limit
                page = (skip // limit) + 1
                return await self.paginate(db, page=page, page_size=limit, filters=filters)
        except Exception as e:
            logger.error(f"Error in get_all: {e}")
            raise
        finally:
            await db.close()
    
    async def get(self, id: int) -> Optional[ModelType]:
        """
        Get a single record by ID - bridges to BaseService.find_by_id()
        Compatible with scaffold-generated plugins expecting get(id)
        """
        db = await self._get_db_session()
        try:
            return await self.find_by_id(db, id)
        except Exception as e:
            logger.error(f"Error in get: {e}")
            raise
        finally:
            await db.close()
    
    async def create(self, **kwargs) -> ModelType:
        """
        Create a new record - bridges to BaseService.add()
        Compatible with scaffold-generated plugins expecting create(**kwargs)
        """
        db = await self._get_db_session()
        try:
            result = await self.add(db, kwargs)
            await db.commit()  # Explicitly commit the transaction
            await db.refresh(result)  # Refresh to get updated data
            return result
        except Exception as e:
            await db.rollback()  # Rollback on error
            logger.error(f"Error in create: {e}")
            raise
        finally:
            await db.close()
    
    async def update_by_id(self, id: int, **kwargs) -> Optional[ModelType]:
        """
        Update a record by ID - bridges to BaseService.update_one()
        Compatible with scaffold-generated plugins expecting update(id, **kwargs)
        """
        db = await self._get_db_session()
        try:
            result = await self.update_one(db, {"id": id}, kwargs)
            if result:
                await db.commit()  # Explicitly commit the transaction
                await db.refresh(result)  # Refresh to get updated data
            return result
        except Exception as e:
            await db.rollback()  # Rollback on error
            logger.error(f"Error in update_by_id: {e}")
            raise
        finally:
            await db.close()
    
    # Alias for backward compatibility - use different name to avoid conflict
    async def update_record(self, id: int, **kwargs) -> Optional[ModelType]:
        """Update a record by ID - alias for update_by_id"""
        return await self.update_by_id(id, **kwargs)
    
    # Override the update method to handle both signatures
    async def update(self, *args, **kwargs):
        """
        Smart update method that handles both base service and bridge signatures
        - If called with (db, db_obj, obj_in) -> calls parent update
        - If called with (id, **kwargs) -> calls update_by_id
        """
        if len(args) == 3 and not kwargs:
            # Base service signature: update(db, db_obj, obj_in)
            return await super().update(*args)
        elif len(args) == 1 and kwargs:
            # Bridge signature: update(id, **kwargs)
            return await self.update_by_id(args[0], **kwargs)
        else:
            raise ValueError(f"Invalid update signature: args={args}, kwargs={kwargs}")
    
    async def delete_by_id(self, id: int) -> bool:
        """
        Delete a record by ID - bridges to BaseService.delete_one()
        Compatible with scaffold-generated plugins expecting delete(id)
        """
        db = await self._get_db_session()
        try:
            result = await self.delete_one(db, {"id": id})
            if result:
                await db.commit()  # Explicitly commit the transaction
            return result
        except Exception as e:
            await db.rollback()  # Rollback on error
            logger.error(f"Error in delete_by_id: {e}")
            raise
        finally:
            await db.close()
    
    # Override the delete method to handle both signatures
    async def delete(self, *args, **kwargs):
        """
        Smart delete method that handles both base service and bridge signatures
        - If called with (db, db_obj) -> calls parent delete
        - If called with (id) -> calls delete_by_id
        """
        if len(args) == 2 and not kwargs:
            # Base service signature: delete(db, db_obj)
            return await super().delete(*args)
        elif len(args) == 1 and not kwargs:
            # Bridge signature: delete(id)
            return await self.delete_by_id(args[0])
        else:
            raise ValueError(f"Invalid delete signature: args={args}, kwargs={kwargs}")
    
    async def get_by_field(self, field_name: str, value: Any) -> Optional[ModelType]:
        """
        Get a record by a specific field value
        Compatible with scaffold-generated plugins expecting get_by_field(field, value)
        """
        db = await self._get_db_session()
        try:
            return await self.find_one(db, {field_name: value})
        except Exception as e:
            logger.error(f"Error in get_by_field: {e}")
            raise
        finally:
            await db.close()
    
    async def search_by_text(self, query: str, fields: List[str], limit: int = 10) -> List[ModelType]:
        """
        Search records by text in specified fields
        Compatible with scaffold-generated plugins expecting text search
        """
        db = await self._get_db_session()
        try:
            from sqlalchemy import or_
            stmt = select(self.model)
            # Create LIKE conditions for each field
            conditions = []
            for field in fields:
                if hasattr(self.model, field):
                    field_attr = getattr(self.model, field)
                    conditions.append(field_attr.like(f"%{query}%"))
            
            if conditions:
                stmt = stmt.where(or_(*conditions))
            
            stmt = stmt.limit(limit)
            result = await db.execute(stmt)
            return result.scalars().all()
        except Exception as e:
            logger.error(f"Search error: {e}")
            return []
        finally:
            await db.close()
    
    async def bulk_create(self, items: List[Dict[str, Any]]) -> List[ModelType]:
        """
        Bulk create records - bridges to BaseService.bulk_add()
        Compatible with scaffold-generated plugins expecting bulk_create(items)
        """
        db = await self._get_db_session()
        try:
            results = await self.bulk_add(db, items)
            await db.commit()  # Explicitly commit the transaction
            # Refresh all created items
            for result in results:
                await db.refresh(result)
            return results
        except Exception as e:
            await db.rollback()  # Rollback on error
            logger.error(f"Error in bulk_create: {e}")
            raise
        finally:
            await db.close()
    
    async def bulk_update_by_ids(self, updates: List[Dict[str, Any]]) -> List[ModelType]:
        """
        Bulk update records by their IDs
        Compatible with scaffold-generated plugins expecting bulk updates
        """
        db = await self._get_db_session()
        try:
            results = []
            for update_data in updates:
                if 'id' in update_data:
                    item_id = update_data.pop('id')
                    result = await self.update_one(db, {"id": item_id}, update_data)
                    if result:
                        results.append(result)
            
            if results:
                await db.commit()  # Explicitly commit the transaction
                # Refresh all updated items
                for result in results:
                    await db.refresh(result)
            return results
        except Exception as e:
            await db.rollback()  # Rollback on error
            logger.error(f"Error in bulk_update_by_ids: {e}")
            raise
        finally:
            await db.close()
    
    async def bulk_delete_by_ids(self, ids: List[int]) -> int:
        """
        Bulk delete records by their IDs
        Compatible with scaffold-generated plugins expecting bulk deletes
        """
        db = await self._get_db_session()
        try:
            count = 0
            for item_id in ids:
                if await self.delete_one(db, {"id": item_id}):
                    count += 1
            
            if count > 0:
                await db.commit()  # Explicitly commit the transaction
            return count
        except Exception as e:
            await db.rollback()  # Rollback on error
            logger.error(f"Error in bulk_delete_by_ids: {e}")
            raise
        finally:
            await db.close() 