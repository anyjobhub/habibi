"""
Redis connection and cache management
"""

import redis.asyncio as redis
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)


class RedisCache:
    """Redis cache connection manager"""
    
    redis_client: redis.Redis = None


cache = RedisCache()


async def connect_to_redis():
    """Connect to Redis"""
    logger.info("Connecting to Redis...")
    cache.redis_client = await redis.from_url(
        settings.REDIS_URL,
        encoding="utf-8",
        decode_responses=True
    )
    logger.info("Connected to Redis")


async def close_redis_connection():
    """Close Redis connection"""
    logger.info("Closing Redis connection...")
    await cache.redis_client.close()
    logger.info("Redis connection closed")


async def get_redis() -> redis.Redis:
    """Get Redis client instance"""
    return cache.redis_client
