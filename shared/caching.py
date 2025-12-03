"""
Redis Caching Layer

This module implements caching for frequently accessed data to improve performance.

Features:
- Room data caching
- User profile caching
- Booking statistics caching
- Automatic cache invalidation
- TTL-based expiration

Author: Jad Eido
"""

import redis
import json
import pickle
from typing import Optional, Any, Callable
from functools import wraps
import hashlib
import os
from datetime import timedelta

redis_client = redis.Redis(
    host=os.getenv('REDIS_HOST', 'localhost'),
    port=int(os.getenv('REDIS_PORT', 6379)),
    db=1,
    decode_responses=False
)

CACHE_TTL = {
    "room": 300,           # 5 minutes
    "user": 600,           # 10 minutes
    "booking": 180,        # 3 minutes
    "review": 300,         # 5 minutes
    "statistics": 3600,    # 1 hour
    "search": 120,         # 2 minutes
}


def generate_cache_key(prefix: str, *args, **kwargs) -> str:
    """
    Generate unique cache key from function arguments.
    
    Args:
        prefix: Cache key prefix (e.g., "room", "user")
        *args: Positional arguments
        **kwargs: Keyword arguments
        
    Returns:
        str: Unique cache key
    """
    key_parts = [prefix]
    
    for arg in args:
        key_parts.append(str(arg))
    
    for k, v in sorted(kwargs.items()):
        key_parts.append(f"{k}={v}")
    
    key_string = ":" .join(key_parts)
    key_hash = hashlib.md5(key_string.encode()).hexdigest()[:16]
    
    return f"cache:{prefix}:{key_hash}"


def cache_response(cache_type: str = "default", ttl: Optional[int] = None):
    """
    Decorator for caching function responses.
    
    Args:
        cache_type: Type of cache (room, user, booking, etc.)
        ttl: Time to live in seconds (overrides default)
        
    Returns:
        Decorator function
        
    Example:
        @cache_response("room", ttl=300)
        def get_room(room_id: int):
            return db.query(Room).filter(Room.id == room_id).first()
    """
    def decorator(func: Callable):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            cache_key = generate_cache_key(cache_type, *args, **kwargs)
            
            try:
                cached_data = redis_client.get(cache_key)
                if cached_data:
                    return pickle.loads(cached_data)
            except Exception as e:
                print(f"Cache read error: {e}")
            
            result = await func(*args, **kwargs)
            
            try:
                cache_ttl = ttl or CACHE_TTL.get(cache_type, 300)
                redis_client.setex(
                    cache_key,
                    cache_ttl,
                    pickle.dumps(result)
                )
            except Exception as e:
                print(f"Cache write error: {e}")
            
            return result
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            cache_key = generate_cache_key(cache_type, *args, **kwargs)
            
            try:
                cached_data = redis_client.get(cache_key)
                if cached_data:
                    return pickle.loads(cached_data)
            except Exception as e:
                print(f"Cache read error: {e}")
            
            result = func(*args, **kwargs)
            
            try:
                cache_ttl = ttl or CACHE_TTL.get(cache_type, 300)
                redis_client.setex(
                    cache_key,
                    cache_ttl,
                    pickle.dumps(result)
                )
            except Exception as e:
                print(f"Cache write error: {e}")
            
            return result
        
        import inspect
        if inspect.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    
    return decorator


def invalidate_cache(cache_type: str, *args, **kwargs) -> bool:
    """
    Invalidate specific cache entry.
    
    Args:
        cache_type: Type of cache to invalidate
        *args: Arguments to identify cache entry
        **kwargs: Keyword arguments to identify cache entry
        
    Returns:
        bool: True if cache was invalidated
        
    Example:
        invalidate_cache("room", room_id=1)
    """
    try:
        cache_key = generate_cache_key(cache_type, *args, **kwargs)
        redis_client.delete(cache_key)
        return True
    except Exception as e:
        print(f"Cache invalidation error: {e}")
        return False


def invalidate_cache_pattern(pattern: str) -> int:
    """
    Invalidate all cache entries matching pattern.
    
    Args:
        pattern: Redis key pattern (e.g., "cache:room:*")
        
    Returns:
        int: Number of keys deleted
        
    Example:
        # Invalidate all room caches
        invalidate_cache_pattern("cache:room:*")
    """
    try:
        keys = redis_client.keys(f"cache:{pattern}:*")
        if keys:
            return redis_client.delete(*keys)
        return 0
    except Exception as e:
        print(f"Pattern invalidation error: {e}")
        return 0


def get_cache_stats() -> dict:
    """
    Get cache statistics.
    
    Returns:
        dict: Cache statistics including hit rate, memory usage
    """
    try:
        info = redis_client.info()
        
        # Calculate cache statistics
        total_keys = redis_client.dbsize()
        memory_used = info.get('used_memory_human', 'N/A')
        hit_rate = 0
        
        if info.get('keyspace_hits', 0) + info.get('keyspace_misses', 0) > 0:
            hit_rate = (info.get('keyspace_hits', 0) / 
                       (info.get('keyspace_hits', 0) + info.get('keyspace_misses', 0))) * 100
        
        return {
            "total_keys": total_keys,
            "memory_used": memory_used,
            "hit_rate_percent": round(hit_rate, 2),
            "hits": info.get('keyspace_hits', 0),
            "misses": info.get('keyspace_misses', 0),
            "connected_clients": info.get('connected_clients', 0)
        }
    except Exception as e:
        return {"error": str(e)}


def clear_all_cache() -> bool:
    """
    Clear all cached data (use with caution).
    
    Returns:
        bool: True if successful
    """
    try:
        redis_client.flushdb()
        return True
    except Exception as e:
        print(f"Cache clear error: {e}")
        return False


class CacheManager:
    """
    Context manager for cache operations.
    
    Example:
        with CacheManager("room") as cache:
            data = cache.get(room_id=1)
            if not data:
                data = fetch_from_db()
                cache.set(data, room_id=1)
    """
    
    def __init__(self, cache_type: str):
        """
        Initialize cache manager.
        
        Args:
            cache_type: Type of cache to manage
        """
        self.cache_type = cache_type
        self.client = redis_client
    
    def __enter__(self):
        """Enter context."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context."""
        pass
    
    def get(self, **kwargs) -> Optional[Any]:
        """
        Get data from cache.
        
        Args:
            **kwargs: Arguments to identify cache entry
            
        Returns:
            Cached data or None
        """
        try:
            cache_key = generate_cache_key(self.cache_type, **kwargs)
            cached_data = self.client.get(cache_key)
            if cached_data:
                return pickle.loads(cached_data)
        except Exception as e:
            print(f"Cache get error: {e}")
        return None
    
    def set(self, data: Any, ttl: Optional[int] = None, **kwargs) -> bool:
        """
        Set data in cache.
        
        Args:
            data: Data to cache
            ttl: Time to live in seconds
            **kwargs: Arguments to identify cache entry
            
        Returns:
            bool: True if successful
        """
        try:
            cache_key = generate_cache_key(self.cache_type, **kwargs)
            cache_ttl = ttl or CACHE_TTL.get(self.cache_type, 300)
            self.client.setex(cache_key, cache_ttl, pickle.dumps(data))
            return True
        except Exception as e:
            print(f"Cache set error: {e}")
            return False
    
    def delete(self, **kwargs) -> bool:
        """
        Delete data from cache.
        
        Args:
            **kwargs: Arguments to identify cache entry
            
        Returns:
            bool: True if successful
        """
        return invalidate_cache(self.cache_type, **kwargs)
