"""
WebSocket endpoint for real-time messaging
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, status
from datetime import datetime
from bson import ObjectId
import logging

from app.core.websocket import manager
from app.core import decode_access_token, get_database, get_redis

logger = logging.getLogger(__name__)

router = APIRouter()


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    token: str = Query(..., description="JWT session token")
):
    """
    WebSocket endpoint for real-time messaging
    
    Connection URL: ws://localhost:8000/api/v1/ws?token=<session_token>
    
    Client -> Server Events:
    - typing_start: User started typing
    - typing_stop: User stopped typing
    - message_delivered: Message delivered to device
    - message_read: Message read by user
    
    Server -> Client Events:
    - authenticated: Connection established
    - new_message: New message received
    - message_status_update: Message delivery/read status changed
    - typing_indicator: Other user typing status
    - user_online: User came online
    - user_offline: User went offline
    - error: Error occurred
    """
    
    # Authenticate user
    payload = decode_access_token(token)
    if not payload:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return
    
    user_id = payload.get("user_id")
    if not user_id:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return
    
    # Connect user
    await manager.connect(websocket, user_id)
    
    # Update user online status in database
    db = await get_database()
    await db.users.update_one(
        {"_id": ObjectId(user_id)},
        {
            "$set": {
                "status.online": True,
                "status.last_seen": datetime.utcnow()
            }
        }
    )
    
    # Store online status in Redis (for quick lookup)
    redis = await get_redis()
    await redis.setex(f"user:online:{user_id}", 3600, "1")  # 1 hour expiry
    
    # Notify contacts that user is online
    await notify_contacts_status(user_id, True)
    
    try:
        while True:
            # Receive message from client
            data = await websocket.receive_json()
            
            event_type = data.get("type")
            event_data = data.get("data", {})
            
            logger.info(f"Received event from {user_id}: {event_type}")
            
            # Handle different event types
            if event_type == "typing_start":
                await handle_typing_start(user_id, event_data)
            
            elif event_type == "typing_stop":
                await handle_typing_stop(user_id, event_data)
            
            elif event_type == "message_delivered":
                await handle_message_delivered(user_id, event_data)
            
            elif event_type == "message_read":
                await handle_message_read(user_id, event_data)
            
            elif event_type == "ping":
                # Heartbeat
                await manager.send_personal_message(
                    {"type": "pong", "timestamp": datetime.utcnow().isoformat()},
                    websocket
                )
            
            else:
                logger.warning(f"Unknown event type: {event_type}")
                await manager.send_personal_message(
                    {
                        "type": "error",
                        "data": {"message": f"Unknown event type: {event_type}"}
                    },
                    websocket
                )
    
    except WebSocketDisconnect:
        logger.info(f"User {user_id} disconnected")
    
    except Exception as e:
        logger.error(f"WebSocket error for user {user_id}: {e}")
    
    finally:
        # Disconnect user
        manager.disconnect(websocket)
        
        # Update user offline status
        is_still_online = manager.is_user_online(user_id)
        
        if not is_still_online:
            await db.users.update_one(
                {"_id": ObjectId(user_id)},
                {
                    "$set": {
                        "status.online": False,
                        "status.last_seen": datetime.utcnow()
                    }
                }
            )
            
            # Remove from Redis
            await redis.delete(f"user:online:{user_id}")
            
            # Notify contacts that user is offline
            await notify_contacts_status(user_id, False)


async def handle_typing_start(user_id: str, data: dict):
    """Handle typing start event"""
    conversation_id = data.get("conversation_id")
    
    if not conversation_id:
        return
    
    # Get conversation participants
    db = await get_database()
    conversation = await db.conversations.find_one({"_id": ObjectId(conversation_id)})
    
    if not conversation:
        return
    
    # Broadcast typing indicator to other participants
    participant_ids = [p["user_id"] for p in conversation["participants"]]
    
    await manager.broadcast_to_conversation(
        {
            "type": "typing_indicator",
            "data": {
                "conversation_id": conversation_id,
                "user_id": user_id,
                "is_typing": True
            }
        },
        conversation_id,
        participant_ids,
        exclude_user=user_id
    )


async def handle_typing_stop(user_id: str, data: dict):
    """Handle typing stop event"""
    conversation_id = data.get("conversation_id")
    
    if not conversation_id:
        return
    
    # Get conversation participants
    db = await get_database()
    conversation = await db.conversations.find_one({"_id": ObjectId(conversation_id)})
    
    if not conversation:
        return
    
    # Broadcast typing stopped to other participants
    participant_ids = [p["user_id"] for p in conversation["participants"]]
    
    await manager.broadcast_to_conversation(
        {
            "type": "typing_indicator",
            "data": {
                "conversation_id": conversation_id,
                "user_id": user_id,
                "is_typing": False
            }
        },
        conversation_id,
        participant_ids,
        exclude_user=user_id
    )


async def handle_message_delivered(user_id: str, data: dict):
    """Handle message delivered event"""
    message_id = data.get("message_id")
    
    if not message_id:
        return
    
    db = await get_database()
    
    # Update message delivery status
    await db.messages.update_one(
        {"_id": ObjectId(message_id)},
        {
            "$push": {
                "status.delivered_to": {
                    "user_id": user_id,
                    "delivered_at": datetime.utcnow()
                }
            }
        }
    )
    
    # Get message to find sender
    message = await db.messages.find_one({"_id": ObjectId(message_id)})
    
    if message:
        # Notify sender about delivery
        await manager.send_to_user(
            {
                "type": "message_status_update",
                "data": {
                    "message_id": message_id,
                    "status": "delivered",
                    "user_id": user_id,
                    "timestamp": datetime.utcnow().isoformat()
                }
            },
            message["sender_id"]
        )


async def handle_message_read(user_id: str, data: dict):
    """Handle message read event"""
    message_id = data.get("message_id")
    
    if not message_id:
        return
    
    db = await get_database()
    
    # Update message read status
    await db.messages.update_one(
        {"_id": ObjectId(message_id)},
        {
            "$push": {
                "status.read_by": {
                    "user_id": user_id,
                    "read_at": datetime.utcnow()
                }
            }
        }
    )
    
    # Get message to find sender
    message = await db.messages.find_one({"_id": ObjectId(message_id)})
    
    if message:
        # Notify sender about read receipt
        await manager.send_to_user(
            {
                "type": "message_status_update",
                "data": {
                    "message_id": message_id,
                    "status": "read",
                    "user_id": user_id,
                    "timestamp": datetime.utcnow().isoformat()
                }
            },
            message["sender_id"]
        )


async def notify_contacts_status(user_id: str, is_online: bool):
    """Notify user's contacts about online status change"""
    try:
        db = await get_database()
        
        # Find confirmed friends
        user = await db.users.find_one(
            {"_id": ObjectId(user_id)},
            {"friends": 1}
        )
        
        if not user or "friends" not in user:
            return
            
        friend_ids = [f["user_id"] for f in user["friends"] if f["status"] == "accepted"]
        
        # Broadcast status content
        status_event = {
            "type": "user_online" if is_online else "user_offline",
            "data": {
                "user_id": user_id,
                "timestamp": datetime.utcnow().isoformat()
            }
        }
        
        # Notify each online friend
        for friend_id in friend_ids:
            if manager.is_user_online(friend_id):
                await manager.send_to_user(status_event, friend_id)
                
    except Exception as e:
        logger.error(f"Error notifying contacts: {e}")
