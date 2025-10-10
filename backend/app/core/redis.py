"""
Redis connection and session management
Day 1, Step 1: Redis configuration
"""
import redis.asyncio as redis
from typing import Optional
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)

# Global Redis client
redis_client: Optional[redis.Redis] = None


async def get_redis() -> redis.Redis:
    """
    Get Redis client
    Used for caching and session management
    """
    global redis_client
    
    if redis_client is None:
        redis_client = redis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
            max_connections=10
        )
    
    return redis_client


async def init_redis():
    """
    Initialize Redis connection
    Called on application startup
    """
    try:
        client = await get_redis()
        await client.ping()
        logger.info("Redis connection established")
    except Exception as e:
        logger.error(f"Failed to connect to Redis: {str(e)}")
        raise


async def close_redis():
    """
    Close Redis connection
    Called on application shutdown
    """
    global redis_client
    if redis_client:
        await redis_client.close()
        redis_client = None
        logger.info("Redis connection closed")


# Helper functions for common operations
async def set_with_expiry(key: str, value: str, expiry: int = 3600):
    """Set a key with expiration time (default 1 hour)"""
    client = await get_redis()
    await client.setex(key, expiry, value)


async def get_value(key: str) -> Optional[str]:
    """Get a value from Redis"""
    client = await get_redis()
    return await client.get(key)


async def delete_key(key: str):
    """Delete a key from Redis"""
    client = await get_redis()
    await client.delete(key)


async def exists_key(key: str) -> bool:
    """Check if a key exists"""
    client = await get_redis()
    return await client.exists(key) == 1