"""
Redis Cache Service
High-performance caching layer for classification results
"""

import os
import json
import hashlib
from typing import Optional, Any
import redis.asyncio as redis

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
CACHE_TTL = 60 * 60 * 24 * 7  # 7 days

client: Optional[redis.Redis] = None


async def init_cache():
    """Initialize Redis connection"""
    global client
    try:
        client = redis.from_url(REDIS_URL, decode_responses=True)
        await client.ping()
    except Exception as e:
        print(f"⚠️ Redis init failed: {e} (caching disabled)")
        client = None


async def close_cache():
    """Close Redis connection"""
    global client
    if client:
        await client.close()


def make_cache_key(text: str) -> str:
    """Generate deterministic cache key from text"""
    normalized = " ".join(text.lower().split())
    return f"classify:{hashlib.sha256(normalized.encode()).hexdigest()[:32]}"


async def get_cached(key: str) -> Optional[dict]:
    """Get cached classification result"""
    if not client:
        return None
    try:
        data = await client.get(key)
        return json.loads(data) if data else None
    except:
        return None


async def set_cached(key: str, value: Any, ttl: int = CACHE_TTL) -> bool:
    """Cache classification result"""
    if not client:
        return False
    try:
        await client.setex(key, ttl, json.dumps(value, default=str))
        return True
    except:
        return False


async def invalidate_cached(key: str) -> bool:
    """Invalidate cached result"""
    if not client:
        return False
    try:
        await client.delete(key)
        return True
    except:
        return False


async def get_cache_stats() -> dict:
    """Get cache statistics"""
    if not client:
        return {"connected": False}
    
    try:
        info = await client.info("stats")
        keyspace = await client.info("keyspace")
        
        hits = info.get("keyspace_hits", 0)
        misses = info.get("keyspace_misses", 0)
        total = hits + misses
        
        return {
            "connected": True,
            "hits": hits,
            "misses": misses,
            "hit_rate": round((hits / total) * 100, 1) if total > 0 else 0,
            "keys": keyspace.get("db0", {}).get("keys", 0) if keyspace else 0
        }
    except:
        return {"connected": False}


async def check_connection() -> bool:
    """Check Redis connection"""
    if not client:
        return False
    try:
        await client.ping()
        return True
    except:
        return False
