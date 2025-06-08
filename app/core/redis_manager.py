"""
Enterprise Redis Manager
Centralized Redis management for caching, rate limiting, sessions, and real-time features.
"""

import asyncio
import json
import pickle
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union, Callable
from enum import Enum
import redis.asyncio as redis
from redis.asyncio import Redis
from loguru import logger
from app.core.config import get_settings


class RedisNamespace(str, Enum):
    """Redis key namespaces for organization"""
    CACHE = "cache"
    RATE_LIMIT = "rate_limit"
    SESSION = "session"
    SECURITY = "security"
    WEBSOCKET = "websocket"
    TASK_QUEUE = "task_queue"
    FEATURE_FLAGS = "feature_flags"
    MONITORING = "monitoring"


class CacheStrategy(str, Enum):
    """Cache invalidation strategies"""
    TTL = "ttl"                    # Time-based expiration
    LRU = "lru"                    # Least Recently Used
    WRITE_THROUGH = "write_through" # Write to cache and DB simultaneously
    WRITE_BEHIND = "write_behind"   # Write to cache first, DB later
    READ_THROUGH = "read_through"   # Read from cache, fetch from DB if miss


class EnterpriseRedisManager:
    """
    Enterprise Redis manager with connection pooling, failover, and monitoring
    """
    
    def __init__(self):
        self.settings = get_settings()
        self.redis_client: Optional[Redis] = None
        self.redis_cluster: Optional[Redis] = None
        self.connection_pool = None
        self._health_check_interval = 30
        self._is_healthy = False
        self._fallback_cache = {}  # In-memory fallback
        
    async def initialize(self) -> bool:
        """Initialize Redis connection with retry logic"""
        max_retries = 3
        retry_delay = 2
        
        for attempt in range(max_retries):
            try:
                # Primary Redis connection
                redis_url = getattr(self.settings, 'redis_url', 'redis://localhost:6379/0')
                
                self.redis_client = redis.from_url(
                    redis_url,
                    encoding="utf-8",
                    decode_responses=False,  # Handle binary data
                    max_connections=20,
                    retry_on_timeout=True,
                    socket_keepalive=True,
                    socket_keepalive_options={},
                    health_check_interval=30
                )
                
                # Test connection
                await self.redis_client.ping()
                self._is_healthy = True
                
                logger.info(f"Redis connected successfully: {redis_url}")
                
                # Start health monitoring
                asyncio.create_task(self._health_monitor())
                
                return True
                
            except Exception as e:
                logger.error(f"Redis connection attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay * (attempt + 1))
                    
        logger.warning("Redis connection failed, falling back to in-memory cache")
        return False

    async def _health_monitor(self):
        """Background health monitoring"""
        while True:
            try:
                await asyncio.sleep(self._health_check_interval)
                if self.redis_client:
                    await self.redis_client.ping()
                    self._is_healthy = True
            except Exception as e:
                logger.error(f"Redis health check failed: {e}")
                self._is_healthy = False

    def _get_key(self, namespace: RedisNamespace, key: str) -> str:
        """Generate namespaced Redis key"""
        app_name = getattr(self.settings, 'app_name', 'fastapi_app')
        return f"{app_name}:{namespace.value}:{key}"

    async def _fallback_get(self, key: str) -> Any:
        """Fallback to in-memory cache"""
        return self._fallback_cache.get(key)

    async def _fallback_set(self, key: str, value: Any, ttl: int = 3600):
        """Fallback to in-memory cache with TTL simulation"""
        self._fallback_cache[key] = {
            'value': value,
            'expires_at': datetime.utcnow() + timedelta(seconds=ttl)
        }

    # ====================
    # CACHING OPERATIONS
    # ====================

    async def cache_get(self, key: str, namespace: RedisNamespace = RedisNamespace.CACHE) -> Any:
        """Get cached value with automatic deserialization"""
        redis_key = self._get_key(namespace, key)
        
        try:
            if self.redis_client and self._is_healthy:
                data = await self.redis_client.get(redis_key)
                if data:
                    return pickle.loads(data)
            else:
                # Fallback to in-memory cache
                cached = await self._fallback_get(redis_key)
                if cached and cached['expires_at'] > datetime.utcnow():
                    return cached['value']
                    
        except Exception as e:
            logger.error(f"Cache get error for key {key}: {e}")
            
        return None

    async def cache_set(
        self, 
        key: str, 
        value: Any, 
        ttl: int = 3600,
        namespace: RedisNamespace = RedisNamespace.CACHE
    ) -> bool:
        """Set cached value with automatic serialization"""
        redis_key = self._get_key(namespace, key)
        
        try:
            if self.redis_client and self._is_healthy:
                serialized = pickle.dumps(value)
                await self.redis_client.setex(redis_key, ttl, serialized)
                return True
            else:
                # Fallback to in-memory cache
                await self._fallback_set(redis_key, value, ttl)
                return True
                
        except Exception as e:
            logger.error(f"Cache set error for key {key}: {e}")
            return False

    async def cache_delete(self, key: str, namespace: RedisNamespace = RedisNamespace.CACHE) -> bool:
        """Delete cached value"""
        redis_key = self._get_key(namespace, key)
        
        try:
            if self.redis_client and self._is_healthy:
                result = await self.redis_client.delete(redis_key)
                return bool(result)
            else:
                self._fallback_cache.pop(redis_key, None)
                return True
                
        except Exception as e:
            logger.error(f"Cache delete error for key {key}: {e}")
            return False

    async def cache_exists(self, key: str, namespace: RedisNamespace = RedisNamespace.CACHE) -> bool:
        """Check if key exists in cache"""
        redis_key = self._get_key(namespace, key)
        
        try:
            if self.redis_client and self._is_healthy:
                return bool(await self.redis_client.exists(redis_key))
            else:
                cached = self._fallback_cache.get(redis_key)
                return cached is not None and cached['expires_at'] > datetime.utcnow()
                
        except Exception as e:
            logger.error(f"Cache exists error for key {key}: {e}")
            return False

    async def cache_invalidate_pattern(self, pattern: str, namespace: RedisNamespace = RedisNamespace.CACHE):
        """Invalidate all keys matching pattern"""
        try:
            if self.redis_client and self._is_healthy:
                redis_pattern = self._get_key(namespace, pattern)
                keys = await self.redis_client.keys(redis_pattern)
                if keys:
                    await self.redis_client.delete(*keys)
                    logger.info(f"Invalidated {len(keys)} cache keys matching {pattern}")
            else:
                # Fallback pattern matching
                prefix = self._get_key(namespace, "")
                to_delete = [k for k in self._fallback_cache.keys() if k.startswith(prefix)]
                for key in to_delete:
                    del self._fallback_cache[key]
                    
        except Exception as e:
            logger.error(f"Cache invalidate pattern error for {pattern}: {e}")

    # ====================
    # RATE LIMITING
    # ====================

    async def rate_limit_check(
        self, 
        identifier: str, 
        limit: int, 
        window_seconds: int,
        namespace: str = "default"
    ) -> Dict[str, Any]:
        """
        Check rate limit using sliding window algorithm
        Returns: {allowed: bool, remaining: int, reset_time: datetime}
        """
        key = f"{namespace}:{identifier}"
        redis_key = self._get_key(RedisNamespace.RATE_LIMIT, key)
        current_time = datetime.utcnow()
        window_start = current_time - timedelta(seconds=window_seconds)
        
        try:
            if self.redis_client and self._is_healthy:
                # Use Redis sorted sets for sliding window
                pipe = self.redis_client.pipeline()
                
                # Remove old entries
                await pipe.zremrangebyscore(redis_key, 0, window_start.timestamp())
                
                # Count current requests
                current_count = await pipe.zcard(redis_key)
                
                if current_count < limit:
                    # Add current request
                    await pipe.zadd(redis_key, {str(current_time.timestamp()): current_time.timestamp()})
                    await pipe.expire(redis_key, window_seconds)
                    await pipe.execute()
                    
                    return {
                        "allowed": True,
                        "remaining": limit - current_count - 1,
                        "reset_time": current_time + timedelta(seconds=window_seconds),
                        "limit": limit
                    }
                else:
                    return {
                        "allowed": False,
                        "remaining": 0,
                        "reset_time": current_time + timedelta(seconds=window_seconds),
                        "limit": limit
                    }
                    
        except Exception as e:
            logger.error(f"Rate limit check error for {identifier}: {e}")
            # Fail open for availability
            return {"allowed": True, "remaining": limit, "reset_time": current_time}

    # ====================
    # SESSION MANAGEMENT
    # ====================

    async def session_create(self, session_id: str, user_data: Dict[str, Any], ttl: int = 86400) -> bool:
        """Create user session"""
        try:
            session_data = {
                "user_data": user_data,
                "created_at": datetime.utcnow().isoformat(),
                "last_accessed": datetime.utcnow().isoformat()
            }
            
            return await self.cache_set(
                f"session:{session_id}", 
                session_data, 
                ttl, 
                RedisNamespace.SESSION
            )
            
        except Exception as e:
            logger.error(f"Session create error for {session_id}: {e}")
            return False

    async def session_get(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session data and update last accessed time"""
        try:
            session_data = await self.cache_get(f"session:{session_id}", RedisNamespace.SESSION)
            
            if session_data:
                # Update last accessed time
                session_data["last_accessed"] = datetime.utcnow().isoformat()
                await self.cache_set(
                    f"session:{session_id}", 
                    session_data, 
                    86400,  # Reset TTL
                    RedisNamespace.SESSION
                )
                
            return session_data
            
        except Exception as e:
            logger.error(f"Session get error for {session_id}: {e}")
            return None

    async def session_delete(self, session_id: str) -> bool:
        """Delete session"""
        return await self.cache_delete(f"session:{session_id}", RedisNamespace.SESSION)

    # ====================
    # WEBSOCKET SUPPORT
    # ====================

    async def websocket_subscribe(self, channel: str, callback: Callable):
        """Subscribe to WebSocket channel"""
        if not self.redis_client or not self._is_healthy:
            return
            
        try:
            pubsub = self.redis_client.pubsub()
            await pubsub.subscribe(self._get_key(RedisNamespace.WEBSOCKET, channel))
            
            async for message in pubsub.listen():
                if message['type'] == 'message':
                    data = json.loads(message['data'])
                    await callback(data)
                    
        except Exception as e:
            logger.error(f"WebSocket subscribe error for channel {channel}: {e}")

    async def websocket_publish(self, channel: str, data: Dict[str, Any]) -> bool:
        """Publish to WebSocket channel"""
        if not self.redis_client or not self._is_healthy:
            return False
            
        try:
            redis_key = self._get_key(RedisNamespace.WEBSOCKET, channel)
            await self.redis_client.publish(redis_key, json.dumps(data))
            return True
            
        except Exception as e:
            logger.error(f"WebSocket publish error for channel {channel}: {e}")
            return False

    # ====================
    # MONITORING & STATS
    # ====================

    async def get_stats(self) -> Dict[str, Any]:
        """Get Redis and cache statistics"""
        stats = {
            "redis_healthy": self._is_healthy,
            "fallback_cache_size": len(self._fallback_cache),
            "connection_info": None
        }
        
        try:
            if self.redis_client and self._is_healthy:
                info = await self.redis_client.info()
                stats["connection_info"] = {
                    "connected_clients": info.get("connected_clients", 0),
                    "used_memory": info.get("used_memory_human", "0"),
                    "redis_version": info.get("redis_version", "unknown"),
                    "uptime_seconds": info.get("uptime_in_seconds", 0)
                }
                
        except Exception as e:
            logger.error(f"Redis stats error: {e}")
            
        return stats

    async def cleanup_expired(self):
        """Cleanup expired entries from fallback cache"""
        current_time = datetime.utcnow()
        expired_keys = [
            key for key, data in self._fallback_cache.items()
            if data['expires_at'] <= current_time
        ]
        
        for key in expired_keys:
            del self._fallback_cache[key]
            
        if expired_keys:
            logger.info(f"Cleaned up {len(expired_keys)} expired cache entries")

    async def close(self):
        """Close Redis connections"""
        try:
            if self.redis_client:
                await self.redis_client.close()
                logger.info("Redis connections closed")
        except Exception as e:
            logger.error(f"Error closing Redis connections: {e}")


# ====================
# CACHE DECORATORS
# ====================

def cached(
    ttl: int = 3600,
    key_prefix: str = "",
    namespace: RedisNamespace = RedisNamespace.CACHE,
    strategy: CacheStrategy = CacheStrategy.TTL
):
    """
    Decorator for caching function results
    """
    def decorator(func: Callable):
        async def wrapper(*args, **kwargs):
            # Generate cache key
            key_parts = [key_prefix, func.__name__]
            if args:
                key_parts.append(str(hash(str(args))))
            if kwargs:
                key_parts.append(str(hash(str(sorted(kwargs.items())))))
            
            cache_key = ":".join(filter(None, key_parts))
            
            # Try to get from cache
            cached_result = await redis_manager.cache_get(cache_key, namespace)
            if cached_result is not None:
                return cached_result
            
            # Execute function and cache result
            result = await func(*args, **kwargs)
            await redis_manager.cache_set(cache_key, result, ttl, namespace)
            
            return result
        return wrapper
    return decorator


# Global Redis manager instance
redis_manager = EnterpriseRedisManager() 