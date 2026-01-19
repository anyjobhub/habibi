"""Core module initialization"""

from app.core.config import settings
from app.core.database import db, connect_to_mongo, close_mongo_connection, get_database
from app.core.redis import cache, connect_to_redis, close_redis_connection, get_redis
from app.core.security import (
    create_access_token,
    decode_access_token,
    generate_otp,
    hash_otp,
    verify_otp,
    generate_session_token
)

__all__ = [
    "settings",
    "db",
    "cache",
    "connect_to_mongo",
    "close_mongo_connection",
    "get_database",
    "connect_to_redis",
    "close_redis_connection",
    "get_redis",
    "create_access_token",
    "decode_access_token",
    "generate_otp",
    "hash_otp",
    "verify_otp",
    "generate_session_token",
]
