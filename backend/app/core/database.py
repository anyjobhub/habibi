"""
Database connection and initialization
"""

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from app.core.config import settings
import logging
import certifi

logger = logging.getLogger(__name__)


class Database:
    """MongoDB database connection manager"""
    
    client: AsyncIOMotorClient = None
    db: AsyncIOMotorDatabase = None


db = Database()


async def connect_to_mongo():
    """Connect to MongoDB"""
    logger.info(f"Connecting to MongoDB with certifi: {certifi.where()}")
    db.client = AsyncIOMotorClient(
        settings.MONGODB_URI,
        tlsCAFile=certifi.where(),
        tls=True
    )
    db.db = db.client[settings.MONGODB_DB_NAME]
    logger.info(f"Connected to MongoDB: {settings.MONGODB_DB_NAME}")
    
    # Create Indexes
    await create_indexes()


async def create_indexes():
    """Create database indexes for performance"""
    try:
        # Users
        await db.db.users.create_index("email", unique=True)
        await db.db.users.create_index("username", unique=True)
        await db.db.users.create_index("profile.mobile", sparse=True)
        
        # Friendships
        await db.db.friendships.create_index([("requester_id", 1), ("addressee_id", 1)], unique=True)
        await db.db.friendships.create_index("status")
        
        # Messages
        await db.db.messages.create_index([("conversation_id", 1), ("created_at", -1)])
        
        # Moments (TTL index for auto-expiry)
        # Note: We implement logical expiry, but TTL is good for cleanup.
        # But we soft-delete first usually. Let's just index user_id and expires_at.
        await db.db.moments.create_index("user_id")
        await db.db.moments.create_index("expires_at")
        
        logger.info("Database indexes created")
    except Exception as e:
        logger.error(f"Error creating indexes: {e}")



async def close_mongo_connection():
    """Close MongoDB connection"""
    logger.info("Closing MongoDB connection...")
    db.client.close()
    logger.info("MongoDB connection closed")


async def get_database() -> AsyncIOMotorDatabase:
    """Get database instance"""
    return db.db
