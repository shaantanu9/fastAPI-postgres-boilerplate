"""Cache Plugin.

This plugin provides advanced caching capabilities:
- Redis integration
- In-memory caching
- Cache invalidation strategies
- Performance metrics
- Cache warming
"""

import asyncio
import contextlib
import json
from datetime import datetime, timedelta
from typing import Any

import redis
from fastapi import APIRouter, HTTPException

from app.core.plugin_system import PluginBase, PluginMetadata


class CacheManager:
    """Manages different cache backends."""

    def __init__(self) -> None:
        self.redis_client: redis.Redis | None = None
        self.memory_cache: dict[str, dict] = {}
        self.cache_stats = {"hits": 0, "misses": 0, "sets": 0, "deletes": 0}

    async def connect_redis(self, redis_url: str = "redis://localhost:6379") -> bool | None:
        """Connect to Redis."""
        try:
            self.redis_client = redis.from_url(redis_url, decode_responses=True)
            # Test connection
            self.redis_client.ping()
            return True
        except Exception:
            return False

    async def get(self, key: str, use_redis: bool = True) -> Any | None:
        """Get value from cache."""
        cache_key = self._generate_key(key)

        # Try Redis first if available
        if use_redis and self.redis_client:
            try:
                value = self.redis_client.get(cache_key)
                if value:
                    self.cache_stats["hits"] += 1
                    return json.loads(value)
            except Exception:
                pass

        # Fallback to memory cache
        if cache_key in self.memory_cache:
            entry = self.memory_cache[cache_key]
            if entry["expires_at"] > datetime.utcnow():
                self.cache_stats["hits"] += 1
                return entry["value"]
            # Expired, remove it
            del self.memory_cache[cache_key]

        self.cache_stats["misses"] += 1
        return None

    async def set(
        self, key: str, value: Any, ttl: int = 3600, use_redis: bool = True,
    ) -> bool:
        """Set value in cache."""
        cache_key = self._generate_key(key)
        serialized_value = json.dumps(value, default=str)

        # Set in Redis if available
        if use_redis and self.redis_client:
            with contextlib.suppress(Exception):
                self.redis_client.setex(cache_key, ttl, serialized_value)

        # Set in memory cache as backup
        self.memory_cache[cache_key] = {
            "value": value,
            "expires_at": datetime.utcnow() + timedelta(seconds=ttl),
            "created_at": datetime.utcnow(),
        }

        self.cache_stats["sets"] += 1
        return True

    async def delete(self, key: str, use_redis: bool = True) -> bool:
        """Delete value from cache."""
        cache_key = self._generate_key(key)

        # Delete from Redis
        if use_redis and self.redis_client:
            with contextlib.suppress(Exception):
                self.redis_client.delete(cache_key)

        # Delete from memory cache
        if cache_key in self.memory_cache:
            del self.memory_cache[cache_key]

        self.cache_stats["deletes"] += 1
        return True

    async def clear_all(self, pattern: str = "*") -> int:
        """Clear cache entries matching pattern."""
        count = 0

        # Clear Redis
        if self.redis_client:
            try:
                keys = self.redis_client.keys(f"cache:{pattern}")
                if keys:
                    count += self.redis_client.delete(*keys)
            except Exception:
                pass

        # Clear memory cache
        keys_to_delete = [
            k for k in self.memory_cache if pattern == "*" or pattern in k
        ]
        for key in keys_to_delete:
            del self.memory_cache[key]
            count += 1

        return count

    def get_stats(self) -> dict:
        """Get cache statistics."""
        total_requests = self.cache_stats["hits"] + self.cache_stats["misses"]
        hit_rate = (
            (self.cache_stats["hits"] / total_requests * 100)
            if total_requests > 0
            else 0
        )

        redis_info = {}
        if self.redis_client:
            try:
                redis_info = self.redis_client.info()
            except:
                redis_info = {"error": "Unable to get Redis info"}

        return {
            "cache_stats": self.cache_stats,
            "hit_rate_percent": round(hit_rate, 2),
            "memory_cache_size": len(self.memory_cache),
            "redis_connected": self.redis_client is not None,
            "redis_info": redis_info,
        }

    def _generate_key(self, key: str) -> str:
        """Generate cache key with prefix."""
        return f"cache:{key}"

    async def cleanup_expired(self):
        """Clean up expired entries from memory cache."""
        now = datetime.utcnow()
        expired_keys = [
            key
            for key, entry in self.memory_cache.items()
            if entry["expires_at"] <= now
        ]

        for key in expired_keys:
            del self.memory_cache[key]

        return len(expired_keys)


class CachePlugin(PluginBase):
    """Advanced caching plugin with Redis and in-memory support."""

    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="cache",
            version="1.1.0",
            description="Advanced caching with Redis and in-memory backends",
            author="Your Team",
            min_app_version="1.0.0",
            dependencies=["monitoring"],  # Depends on monitoring plugin
            tags=["cache", "redis", "performance", "storage"],
            priority=15,  # Lower priority - load after dependencies
        )

    def __init__(self) -> None:
        super().__init__()
        self.router = APIRouter()
        self.cache_manager = CacheManager()
        self.monitoring_service = None
        self.setup_routes()

    def setup_routes(self) -> None:
        """Setup cache management routes."""

        @self.router.get("/cache/stats", tags=["Cache"])
        async def get_cache_stats():
            """Get cache statistics and performance metrics."""
            stats = self.cache_manager.get_stats()

            # Emit cache stats event for monitoring
            self.emit_event("cache_stats_requested", stats=stats)

            return stats

        @self.router.post("/cache/set", tags=["Cache"])
        async def set_cache_value(key: str, value: dict, ttl: int = 3600):
            """Set a value in cache."""
            try:
                success = await self.cache_manager.set(key, value, ttl)

                # Emit cache set event
                self.emit_event("cache_set", key=key, ttl=ttl, success=success)

                return {
                    "success": success,
                    "key": key,
                    "ttl": ttl,
                    "message": "Value cached successfully",
                }
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Cache set failed: {e!s}")

        @self.router.get("/cache/get/{key}", tags=["Cache"])
        async def get_cache_value(key: str):
            """Get a value from cache."""
            try:
                value = await self.cache_manager.get(key)

                # Emit cache get event
                self.emit_event("cache_get", key=key, hit=value is not None)

                if value is not None:
                    return {
                        "success": True,
                        "key": key,
                        "value": value,
                        "cache_hit": True,
                    }
                return {
                    "success": False,
                    "key": key,
                    "value": None,
                    "cache_hit": False,
                    "message": "Key not found in cache",
                }
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Cache get failed: {e!s}")

        @self.router.delete("/cache/delete/{key}", tags=["Cache"])
        async def delete_cache_value(key: str):
            """Delete a value from cache."""
            try:
                success = await self.cache_manager.delete(key)

                # Emit cache delete event
                self.emit_event("cache_delete", key=key, success=success)

                return {
                    "success": success,
                    "key": key,
                    "message": "Key deleted from cache",
                }
            except Exception as e:
                raise HTTPException(
                    status_code=500, detail=f"Cache delete failed: {e!s}",
                )

        @self.router.post("/cache/clear", tags=["Cache"])
        async def clear_cache(pattern: str = "*"):
            """Clear cache entries matching pattern."""
            try:
                count = await self.cache_manager.clear_all(pattern)

                # Emit cache clear event
                self.emit_event("cache_clear", pattern=pattern, count=count)

                return {
                    "success": True,
                    "pattern": pattern,
                    "cleared_count": count,
                    "message": f"Cleared {count} cache entries",
                }
            except Exception as e:
                raise HTTPException(
                    status_code=500, detail=f"Cache clear failed: {e!s}",
                )

        @self.router.post("/cache/warm", tags=["Cache"])
        async def warm_cache():
            """Warm up cache with frequently accessed data."""
            try:
                # Example cache warming - customize for your application
                warming_data = [
                    {
                        "key": "app_config",
                        "value": {
                            "version": "1.0.0",
                            "features": ["cache", "monitoring"],
                        },
                        "ttl": 7200,
                    },
                    {
                        "key": "user_settings_default",
                        "value": {"theme": "light", "notifications": True},
                        "ttl": 3600,
                    },
                    {
                        "key": "system_status",
                        "value": {
                            "status": "healthy",
                            "timestamp": datetime.utcnow().isoformat(),
                        },
                        "ttl": 300,
                    },
                ]

                count = 0
                for item in warming_data:
                    await self.cache_manager.set(
                        item["key"], item["value"], item["ttl"],
                    )
                    count += 1

                # Emit cache warm event
                self.emit_event("cache_warmed", count=count)

                return {
                    "success": True,
                    "warmed_count": count,
                    "message": f"Cache warmed with {count} entries",
                }
            except Exception as e:
                raise HTTPException(
                    status_code=500, detail=f"Cache warming failed: {e!s}",
                )

    async def initialize(self, app, context) -> None:
        """Initialize the cache plugin."""
        await super().initialize(app, context)

        # Get monitoring service (dependency)
        self.monitoring_service = context.get_service("monitoring")
        if not self.monitoring_service:
            pass

        # Register cache service
        context.register_service("cache", self.cache_manager)

        # Subscribe to events
        self.subscribe_event("application_startup", self.on_startup)
        self.subscribe_event("monitoring_ready", self.on_monitoring_ready)

        # Try to connect to Redis
        await self.cache_manager.connect_redis()

        # Start cleanup task
        asyncio.create_task(self._periodic_cleanup())

        # Status will be set by plugin manager - don't override here

    async def startup(self) -> None:
        """Plugin startup tasks."""
        await super().startup()

        # Warm up cache
        await self._warm_essential_cache()

        # Emit cache ready event
        self.emit_event(
            "cache_ready", features=["redis", "memory", "warming", "cleanup"],
        )

    async def shutdown(self) -> None:
        """Plugin shutdown tasks."""
        await super().shutdown()

        # Close Redis connection
        if self.cache_manager.redis_client:
            self.cache_manager.redis_client.close()

        # Emit cache shutdown event
        self.emit_event("cache_shutdown")

    def get_routes(self) -> list[Any]:
        """Return cache management routes."""
        return [self.router]

    def get_middleware(self) -> list[Any]:
        """Return cache middleware."""
        # Could add cache middleware here for automatic request caching
        return []

    async def _periodic_cleanup(self) -> None:
        """Periodically clean up expired cache entries."""
        while True:
            try:
                await asyncio.sleep(300)  # Clean up every 5 minutes

                expired_count = await self.cache_manager.cleanup_expired()
                if expired_count > 0:

                    # Emit cleanup event
                    self.emit_event("cache_cleanup", expired_count=expired_count)

            except Exception:
                pass

    async def _warm_essential_cache(self) -> None:
        """Warm up cache with essential data."""
        try:
            # Warm up with system information
            await self.cache_manager.set(
                "system_info",
                {
                    "cache_plugin_version": self.metadata.version,
                    "features": ["redis", "memory", "stats", "warming"],
                    "startup_time": datetime.utcnow().isoformat(),
                },
                ttl=3600,
            )


        except Exception:
            pass

    async def on_startup(self, **kwargs) -> None:
        """Handle application startup event."""
        # Report cache status to monitoring if available
        if self.monitoring_service:
            self.cache_manager.get_stats()

    async def on_monitoring_ready(self, **kwargs) -> None:
        """Handle monitoring ready event."""
        # Could register custom metrics with monitoring system
        features = kwargs.get("features", [])
        if "metrics" in features:

            # Start reporting cache metrics to monitoring
            asyncio.create_task(self._report_metrics_to_monitoring())

    async def _report_metrics_to_monitoring(self) -> None:
        """Periodically report cache metrics to monitoring system."""
        while True:
            try:
                await asyncio.sleep(60)  # Report every minute

                stats = self.cache_manager.get_stats()

                # Emit detailed cache metrics for monitoring
                self.emit_event(
                    "cache_metrics_report",
                    hit_rate=stats["hit_rate_percent"],
                    total_hits=stats["cache_stats"]["hits"],
                    total_misses=stats["cache_stats"]["misses"],
                    memory_cache_size=stats["memory_cache_size"],
                    redis_connected=stats["redis_connected"],
                )

            except Exception:
                pass
