"""
Message endpoints
"""

from fastapi import APIRouter, HTTPException, status, Depends, Header
from datetime import datetime, timedelta
from bson import ObjectId
from typing import Optional

from app.models.message import (
    MessageCreate,
    MessageResponse,
    MessageListResponse,
    MessageStatusUpdate,
    MessageDelete,
    MessageMetadata,
    MessageStatus
)
from app.core import get_database, decode_access_token
from app.core.websocket import manager

router = APIRouter()


async def get_current_user_id(authorization: str = Header(...)) -> str:
    """Dependency to get current user ID from token"""
    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header"
        )
    
    token = authorization.replace("Bearer ", "")
    payload = decode_access_token(token)
    
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )
    
    return payload.get("user_id")


@router.post("", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
async def send_message(
    data: MessageCreate,
    current_user_id: str = Depends(get_current_user_id)
):
    """
    Send a new message
    
    - Message content is encrypted client-side
    - Server stores encrypted blob
    - Broadcasts to recipients via WebSocket
    """
    db = await get_database()
    
    # Validate conversation exists and user is a participant
    try:
        conversation = await db.conversations.find_one({"_id": ObjectId(data.conversation_id)})
    except:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid conversation ID"
        )
    
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found"
        )
    
    if current_user_id not in conversation["participant_ids"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a participant in this conversation"
        )
    
    # Create message metadata
    metadata = {
        "media_url": data.media_url,
        "media_thumbnail": data.media_thumbnail,
        "file_size": data.file_size,
        "duration": data.duration,
        "reply_to": data.reply_to,
        "is_ephemeral": data.is_ephemeral,
        "ttl_seconds": data.ttl_seconds,
        "view_once": data.view_once,
        "viewed_by": []
    }
    
    # Calculate expiry if ephemeral
    if data.is_ephemeral and data.ttl_seconds:
        metadata["expires_at"] = datetime.utcnow() + timedelta(seconds=data.ttl_seconds)
    
    # Create message
    message = {
        "conversation_id": data.conversation_id,
        "sender_id": current_user_id,
        "content": data.content,  # Plaintext content
        "encrypted_content": data.encrypted_content,  # Encrypted content
        "content_type": data.content_type,
        "recipient_keys": [rk.model_dump() for rk in data.recipient_keys],
        "metadata": metadata,
        "status": {
            "sent_at": datetime.utcnow(),
            "delivered_to": [],
            "read_by": []
        },
        "deleted_for": [],
        "deleted_for_everyone": False,
        "deleted_at": None,
        "created_at": datetime.utcnow()
    }
    
    result = await db.messages.insert_one(message)
    message["_id"] = result.inserted_id
    
    # Update conversation's last message
    await db.conversations.update_one(
        {"_id": ObjectId(data.conversation_id)},
        {
            "$set": {
                "last_message": {
                    "message_id": str(result.inserted_id),
                    "encrypted_preview": data.encrypted_content[:50] if data.encrypted_content else data.content[:50],
                    "timestamp": datetime.utcnow(),
                    "sender_id": current_user_id
                },
                "metadata.updated_at": datetime.utcnow()
            }
        }
    )
    
    # Broadcast to recipients via WebSocket
    await manager.broadcast_to_conversation(
        {
            "type": "new_message",
            "data": {
                "message": format_message_response(message)
            }
        },
        data.conversation_id,
        conversation["participant_ids"],
        exclude_user=None  # Send to all including sender (for multi-device)
    )
    
    return format_message_response(message)


@router.get("/conversations/{conversation_id}/messages", response_model=MessageListResponse)
async def get_messages(
    conversation_id: str,
    limit: int = 50,
    before: Optional[str] = None,  # Message ID for pagination
    since: Optional[str] = None,   # ISO Timestamp for polling
    current_user_id: str = Depends(get_current_user_id)
):
    """
    Get messages in a conversation
    
    - Returns messages in reverse chronological order (newest first)
    - Supports pagination with 'before' parameter
    - Excludes messages deleted for current user
    """
    db = await get_database()
    
    # Validate conversation and user is participant
    try:
        conversation = await db.conversations.find_one({"_id": ObjectId(conversation_id)})
    except:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid conversation ID"
        )
    
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found"
        )
    
    if current_user_id not in conversation["participant_ids"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a participant in this conversation"
        )
    
    # Build query
    query = {
        "conversation_id": conversation_id,
        "deleted_for": {"$ne": current_user_id}
    }
    
    # Add pagination and polling support
    if before:
        try:
            # Pagination: Get older messages
            before_message = await db.messages.find_one({"_id": ObjectId(before)})
            if before_message:
                query["created_at"] = {"$lt": before_message["created_at"]}
        except:
            pass
            
    if since:
        try:
            # Polling: Get newer messages
            since_dt = datetime.fromisoformat(since.replace('Z', '+00:00'))
            query["created_at"] = {"$gt": since_dt}
        except:
            pass
    
    # Get messages
    messages = await db.messages.find(query).sort("created_at", -1).limit(limit).to_list(length=limit)
    
    # Get total count
    total = await db.messages.count_documents({
        "conversation_id": conversation_id,
        "deleted_for": {"$ne": current_user_id}
    })
    
    # Format responses
    formatted_messages = [format_message_response(msg) for msg in messages]
    
    return MessageListResponse(
        messages=formatted_messages,
        has_more=len(messages) == limit,
        total=total
    )


@router.post("/{message_id}/read", status_code=status.HTTP_200_OK)
async def mark_message_read(
    message_id: str,
    current_user_id: str = Depends(get_current_user_id)
):
    """
    Mark message as read
    
    - Updates read status
    - Sends read receipt to sender via WebSocket
    """
    db = await get_database()
    
    try:
        message = await db.messages.find_one({"_id": ObjectId(message_id)})
    except:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid message ID"
        )
    
    if not message:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Message not found"
        )
    
    # Check if already read by this user
    already_read = any(r["user_id"] == current_user_id for r in message["status"].get("read_by", []))
    
    if not already_read:
        # Update read status
        await db.messages.update_one(
            {"_id": ObjectId(message_id)},
            {
                "$push": {
                    "status.read_by": {
                        "user_id": current_user_id,
                        "read_at": datetime.utcnow()
                    }
                }
            }
        )
        
        # Send read receipt to sender
        if message["sender_id"] != current_user_id:
            await manager.send_to_user(
                {
                    "type": "message_status_update",
                    "data": {
                        "message_id": message_id,
                        "status": "read",
                        "user_id": current_user_id,
                        "timestamp": datetime.utcnow().isoformat()
                    }
                },
                message["sender_id"]
            )
    
    # Update conversation last_read_at
    await db.conversations.update_one(
        {
            "_id": ObjectId(message["conversation_id"]),
            "participants.user_id": current_user_id
        },
        {
            "$set": {
                "participants.$.last_read_at": datetime.utcnow()
            }
        }
    )
    
    return {"message": "Message marked as read"}


@router.delete("/{message_id}", status_code=status.HTTP_200_OK)
async def delete_message(
    message_id: str,
    data: MessageDelete,
    current_user_id: str = Depends(get_current_user_id)
):
    """
    Delete message
    
    - delete_for_everyone: Delete for all participants (only sender can do this within 1 hour)
    - delete_for_me: Delete only for current user
    """
    db = await get_database()
    
    try:
        message = await db.messages.find_one({"_id": ObjectId(message_id)})
    except:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid message ID"
        )
    
    if not message:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Message not found"
        )
    
    if data.delete_for_everyone:
        # Only sender can delete for everyone
        if message["sender_id"] != current_user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only sender can delete message for everyone"
            )
        
        # Check if message is within 1 hour
        message_age = datetime.utcnow() - message["created_at"]
        if message_age > timedelta(hours=1):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Can only delete for everyone within 1 hour of sending"
            )
        
        # Mark as deleted for everyone
        await db.messages.update_one(
            {"_id": ObjectId(message_id)},
            {
                "$set": {
                    "deleted_for_everyone": True,
                    "deleted_at": datetime.utcnow()
                }
            }
        )
        
        # Notify all participants
        conversation = await db.conversations.find_one({"_id": ObjectId(message["conversation_id"])})
        if conversation:
            await manager.broadcast_to_conversation(
                {
                    "type": "message_deleted",
                    "data": {
                        "message_id": message_id,
                        "deleted_for_everyone": True
                    }
                },
                message["conversation_id"],
                conversation["participant_ids"]
            )
        
        return {"message": "Message deleted for everyone"}
    
    else:
        # Delete for current user only
        await db.messages.update_one(
            {"_id": ObjectId(message_id)},
            {
                "$addToSet": {"deleted_for": current_user_id}
            }
        )
        
        return {"message": "Message deleted for you"}


def format_message_response(message: dict) -> MessageResponse:
    """Format message for response"""
    return MessageResponse(
        id=str(message["_id"]),
        conversation_id=message["conversation_id"],
        sender_id=message["sender_id"],
        encrypted_content=message["encrypted_content"],
        content_type=message["content_type"],
        recipient_keys=message["recipient_keys"],
        metadata=message["metadata"],
        status=message["status"],
        created_at=message["created_at"],
        is_deleted=message.get("deleted_for_everyone", False)
    )
