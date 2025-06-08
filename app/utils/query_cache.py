"""Query Result Cache System.

A sophisticated caching system for SQLAlchemy query results with:
- Automatic TTL management based on query complexity
- Smart cache invalidation strategies
- Redis-based distributed caching
- Fallback to local memory cache
- Performance metrics and monitoring
"""

import hashlib
import inspect
import json
import time
from collections.abc import Callable
from datetime import datetime
from functools import wraps

import redis.asyncio as redis
from loguru import logger
from sqlalchemy import Select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import DeclarativeMeta

# Import the existing cache manager
from app.plugins.cache_plugin import CacheManager


class QueryComplexity:
    """Calculates query complexity for dynamic TTL assignment."""

    @staticmethod
    def calculate_complexity(query: Select | str) -> int:
        """Calculate query complexity score to determine appropriate TTL
        - Higher complexity = longer TTL (less frequent updates)
        - Lower complexity = shorter TTL (more frequent updates).
        """
        complexity = 10  # Base complexity

        if isinstance(query, str):
            # Parse the SQL string for complexity factors
            query_lower = query.lower()

            # Check for joins
            join_count = query_lower.count("join")
            complexity += join_count * 5

            # Check for where clauses
            where_count = query_lower.count("where")
            complexity += where_count * 2

            # Check for group by
            if "group by" in query_lower:
                complexity += 5

            # Check for order by
            if "order by" in query_lower:
                complexity += 3

            # Check for aggregation functions
            agg_funcs = ["count(", "sum(", "avg(", "min(", "max("]
            for func in agg_funcs:
                if func in query_lower:
                    complexity += 4

            # Check for subqueries
            subquery_count = query_lower.count(
                "select", 1,
            )  # Start at index 1 to skip the first SELECT
            complexity += subquery_count * 8

        elif hasattr(query, "whereclause") and query.whereclause:
            # SQLAlchemy Select object - count joins and conditions
            complexity += 10  # Assume moderate complexity for SQLAlchemy objects

            # Add more specific SQLAlchemy complexity analysis as needed
            if hasattr(query, "froms") and query.froms:
                complexity += len(query.froms) * 4

        return complexity


class QueryCacheManager:
    """Manages caching of SQLAlchemy query results."""

    def __init__(self, redis_url: str | None = None) -> None:
        self.redis_url = redis_url or "redis://localhost:6379/0"
        self.redis_client = None
        self.cache_manager = CacheManager()
        self.metrics = {
            "hits": 0,
            "misses": 0,
            "errors": 0,
            "invalidations": 0,
        }
        self.models_last_updated = {}  # Track model last update time

    async def initialize(self) -> bool | None:
        """Initialize cache connections."""
        try:
            self.redis_client = redis.from_url(self.redis_url, decode_responses=True)
            await self.redis_client.ping()
            logger.info(f"QueryCache connected to Redis at {self.redis_url}")
            await self.cache_manager.connect_redis(self.redis_url)
            return True
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            return False

    def _generate_cache_key(self, query: Select | str, params: dict | None = None) -> str:
        """Generate a unique cache key for a query."""
        if isinstance(query, Select):
            # Convert SQLAlchemy query object to string
            compiled = query.compile(compile_kwargs={"literal_binds": True})
            query_str = str(compiled)
        else:
            query_str = str(query)

        # Include parameters in the key
        key_parts = [query_str]
        if params:
            # Sort params to ensure consistent key generation
            sorted_params = sorted((str(k), str(v)) for k, v in params.items())
            key_parts.extend(f"{k}={v}" for k, v in sorted_params)

        # Create a hash for the key
        key = hashlib.md5("|".join(key_parts).encode()).hexdigest()
        return f"query_cache:{key}"

    async def get(self, key: str) -> dict | None:
        """Get cached query result."""
        try:
            if self.redis_client:
                data = await self.redis_client.get(key)
                if data:
                    self.metrics["hits"] += 1
                    return json.loads(data)

            # Fallback to existing cache manager
            result = await self.cache_manager.get(key, use_redis=True)
            if result:
                self.metrics["hits"] += 1
                return result

            self.metrics["misses"] += 1
            return None
        except Exception as e:
            logger.error(f"Error retrieving from cache: {e}")
            self.metrics["errors"] += 1
            return None

    async def set(
        self,
        key: str,
        data: dict,
        ttl: int = 300,
        model_dependencies: list[type[DeclarativeMeta]] | None = None,
    ) -> bool:
        """Set cached query result with TTL
        - model_dependencies: track models this query depends on for invalidation.
        """
        try:
            serialized = json.dumps(data, default=str)

            # Store in Redis
            if self.redis_client:
                await self.redis_client.setex(key, ttl, serialized)

                # Store model dependencies for invalidation
                if model_dependencies:
                    for model in model_dependencies:
                        model_name = model.__name__
                        dep_key = f"model_deps:{model_name}"
                        # Add this key to the model's dependency set
                        await self.redis_client.sadd(dep_key, key)

            # Also store in memory cache as backup
            await self.cache_manager.set(key, data, ttl=ttl, use_redis=True)
            return True

        except Exception as e:
            logger.error(f"Error setting cache: {e}")
            self.metrics["errors"] += 1
            return False

    async def invalidate(self, models: list[type[DeclarativeMeta]]) -> int:
        """Invalidate cache entries for specific models
        Returns number of invalidated keys.
        """
        invalidated = 0

        try:
            if self.redis_client:
                for model in models:
                    model_name = model.__name__
                    dep_key = f"model_deps:{model_name}"

                    # Get all keys that depend on this model
                    dependent_keys = await self.redis_client.smembers(dep_key)

                    if dependent_keys:
                        # Delete all dependent keys
                        await self.redis_client.delete(*dependent_keys)
                        invalidated += len(dependent_keys)

                        # Clear the dependency tracking set
                        await self.redis_client.delete(dep_key)

                    # Update last updated timestamp
                    self.models_last_updated[model_name] = datetime.now()

            self.metrics["invalidations"] += invalidated
            return invalidated

        except Exception as e:
            logger.error(f"Error invalidating cache: {e}")
            self.metrics["errors"] += 1
            return 0

    def get_dynamic_ttl(self, query: Select | str, base_ttl: int = 300) -> int:
        """Calculate dynamic TTL based on query complexity
        - More complex queries get longer TTL (less frequent changes)
        - Simpler queries get shorter TTL (more frequent updates).
        """
        complexity = QueryComplexity.calculate_complexity(query)

        if complexity <= 10:  # Simple queries
            return base_ttl
        if complexity <= 20:  # Moderate queries
            return base_ttl * 2
        if complexity <= 30:  # Complex queries
            return base_ttl * 3
        # Very complex queries
        return base_ttl * 5

    def get_metrics(self) -> dict:
        """Get cache performance metrics."""
        total_requests = self.metrics["hits"] + self.metrics["misses"]
        hit_rate = (
            (self.metrics["hits"] / total_requests * 100) if total_requests > 0 else 0
        )

        return {
            **self.metrics,
            "hit_rate_percent": round(hit_rate, 2),
            "total_requests": total_requests,
            "models_last_updated": {
                k: v.isoformat() for k, v in self.models_last_updated.items()
            },
        }


# Singleton instance
query_cache_manager = QueryCacheManager()


async def init_query_cache(redis_url: str | None = None):
    """Initialize the query cache manager."""
    return await query_cache_manager.initialize()


class cached_query:
    """Decorator for caching SQLAlchemy query results.

    Usage:

    @cached_query(ttl=300, models=[User, Order])
    async def get_user_orders(db: AsyncSession, user_id: int) -> List[Dict]:
        query = select(Order).where(Order.user_id == user_id)
        result = await db.execute(query)
        return [row._asdict() for row in result]
    """

    def __init__(
        self,
        ttl: int = 300,
        models: list[type[DeclarativeMeta]] | None = None,
        dynamic_ttl: bool = True,
        condition: Callable | None = None,
    ) -> None:
        self.ttl = ttl
        self.models = models or []
        self.dynamic_ttl = dynamic_ttl
        self.condition = (
            condition  # Optional function that returns True if result should be cached
        )

    def __call__(self, func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract query parameters from function arguments
            params = {}
            sig = inspect.signature(func)
            bound_args = sig.bind(*args, **kwargs)

            # Skip caching if first argument is not AsyncSession (not a query function)
            if not args or not isinstance(args[0], AsyncSession):
                return await func(*args, **kwargs)

            # Add named parameters to cache key
            for param_name, param_value in bound_args.arguments.items():
                if param_name not in {"db", "self"}:  # Skip db session
                    params[param_name] = param_value

            # Generate a unique key based on function name and parameters
            func_name = f"{func.__module__}.{func.__qualname__}"
            key = f"{func_name}:{hashlib.md5(json.dumps(params, default=str).encode()).hexdigest()}"

            # Get cached result
            cached_result = await query_cache_manager.get(key)

            if cached_result is not None:
                logger.debug(f"Cache hit for {func_name}")
                return cached_result

            # Execute the function
            start_time = time.time()
            result = await func(*args, **kwargs)
            execution_time = time.time() - start_time

            # Only cache if the condition is met (if provided)
            if self.condition is not None and not self.condition(result):
                return result

            # Use dynamic TTL if enabled
            ttl = self.ttl
            if self.dynamic_ttl:
                # Try to get the query from the function
                query = None
                frame = inspect.currentframe()
                try:
                    # Look for SQLAlchemy select statement in function locals
                    if frame is not None:
                        frame_locals = frame.f_back.f_locals
                        for var_value in frame_locals.values():
                            if isinstance(var_value, Select):
                                query = var_value
                                break

                    if query:
                        ttl = query_cache_manager.get_dynamic_ttl(query, self.ttl)
                finally:
                    del frame  # Avoid reference cycles

            # Cache the result
            await query_cache_manager.set(
                key, result, ttl=ttl, model_dependencies=self.models,
            )
            logger.debug(
                f"Cached {func_name} (took {execution_time:.4f}s), TTL: {ttl}s",
            )

            return result

        return wrapper


async def clear_model_cache(models: list[type[DeclarativeMeta]]) -> int:
    """Clear cache for specific models - useful after updates."""
    return await query_cache_manager.invalidate(models)
