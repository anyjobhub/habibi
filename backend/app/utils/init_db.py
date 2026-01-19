"""
Database initialization script
Creates indexes and initial setup
"""

import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import settings
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def create_indexes():
    """Create database indexes"""
    logger.info("Connecting to MongoDB...")
    client = AsyncIOMotorClient(settings.MONGODB_URI)
    db = client[settings.MONGODB_DB_NAME]
    
    logger.info("Creating indexes...")
    
    # Users collection indexes
    await db.users.create_index("email", unique=True)
    await db.users.create_index("username", unique=True)
    await db.users.create_index("profile.mobile", unique=True)  # Mobile must be unique
    logger.info("✓ Users indexes created")
    
    # OTP sessions collection indexes
    await db.otp_sessions.create_index("identifier")
    await db.otp_sessions.create_index("expires_at", expireAfterSeconds=0)  # TTL index
    logger.info("✓ OTP sessions indexes created")
    
    # Conversations collection indexes
    await db.conversations.create_index("participant_ids")
    await db.conversations.create_index([("participants.user_id", 1)])
    await db.conversations.create_index([("metadata.updated_at", -1)])
    await db.conversations.create_index([("type", 1), ("participant_ids", 1)], unique=True)  # Unique one-to-one conversations
    logger.info("✓ Conversations indexes created")
    
    # Messages collection indexes
    await db.messages.create_index([("conversation_id", 1), ("created_at", -1)])
    await db.messages.create_index([("sender_id", 1), ("created_at", -1)])
    await db.messages.create_index("expires_at", sparse=True)  # For ephemeral messages
    await db.messages.create_index([("status.sent_at", 1)])
    logger.info("✓ Messages indexes created")
    
    # Friendships collection indexes
    await db.friendships.create_index([("requester_id", 1), ("addressee_id", 1)], unique=True)
    await db.friendships.create_index([("requester_id", 1), ("status", 1)])
    await db.friendships.create_index([("addressee_id", 1), ("status", 1)])
    await db.friendships.create_index([("status", 1)])
    logger.info("✓ Friendships indexes created")
    
    # Moments collection indexes
    await db.moments.create_index([("user_id", 1), ("created_at", -1)])
    await db.moments.create_index([("expires_at", 1)])  # For auto-cleanup
    await db.moments.create_index([("deleted", 1), ("expires_at", 1)])
    await db.moments.create_index("expires_at", expireAfterSeconds=0)  # TTL index for auto-deletion
    logger.info("✓ Moments indexes created")
    
    logger.info("All indexes created successfully!")
    
    client.close()


async def main():
    """Main initialization function"""
    try:
        await create_indexes()
        logger.info("Database initialization complete!")
    except Exception as e:
        logger.error(f"Database initialization failed: {str(e)}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
