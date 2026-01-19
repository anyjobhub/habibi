"""
Conversation endpoints
"""

from fastapi import APIRouter, HTTPException, status, Depends, Header
from datetime import datetime
from bson import ObjectId
from typing import Optional

from app.models.conversation import (
    ConversationCreate,
    ConversationResponse,
    ConversationListResponse,
    ConversationParticipant,
    ConversationMetadata
)
from app.core import get_database, decode_access_token

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


@router.post("", response_model=ConversationResponse, status_code=status.HTTP_201_CREATED)
async def create_or_get_conversation(
    data: ConversationCreate,
    current_user_id: str = Depends(get_current_user_id)
):
    """
    Create a new conversation or get existing one
    
    - For one-to-one chats, returns existing conversation if it exists
    - Creates new conversation if it doesn't exist
    """
    db = await get_database()
    
    # Validate participant exists
    participant = await db.users.find_one({"_id": ObjectId(data.participant_id)})
    if not participant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Check if conversation already exists (one-to-one)
    participant_ids_sorted = sorted([current_user_id, data.participant_id])
    
    existing_conversation = await db.conversations.find_one({
        "type": "one_to_one",
        "participant_ids": participant_ids_sorted
    })
    
    if existing_conversation:
        # Return existing conversation
        return await format_conversation_response(existing_conversation, current_user_id, db)
    
    # Create new conversation
    conversation = {
        "type": "one_to_one",
        "participants": [
            {
                "user_id": current_user_id,
                "joined_at": datetime.utcnow(),
                "left_at": None,
                "last_read_at": None,
                "notifications_enabled": True
            },
            {
                "user_id": data.participant_id,
                "joined_at": datetime.utcnow(),
                "left_at": None,
                "last_read_at": None,
                "notifications_enabled": True
            }
        ],
        "participant_ids": participant_ids_sorted,
        "last_message": None,
        "metadata": {
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "archived_by": []
        }
    }
    
    result = await db.conversations.insert_one(conversation)
    conversation["_id"] = result.inserted_id
    
    return await format_conversation_response(conversation, current_user_id, db)


@router.get("", response_model=ConversationListResponse)
async def get_conversations(
    limit: int = 50,
    skip: int = 0,
    current_user_id: str = Depends(get_current_user_id)
):
    """
    Get all conversations for current user
    
    - Returns conversations sorted by last message timestamp
    - Includes unread count for each conversation
    """
    db = await get_database()
    
    # Find conversations where user is a participant
    conversations = await db.conversations.find({
        "participant_ids": current_user_id,
        "metadata.archived_by": {"$ne": current_user_id}  # Exclude archived
    }).sort("metadata.updated_at", -1).skip(skip).limit(limit).to_list(length=limit)
    
    # Get total count
    total = await db.conversations.count_documents({
        "participant_ids": current_user_id,
        "metadata.archived_by": {"$ne": current_user_id}
    })
    
    # Format responses
    formatted_conversations = []
    for conv in conversations:
        formatted = await format_conversation_response(conv, current_user_id, db)
        formatted_conversations.append(formatted)
    
    return ConversationListResponse(
        conversations=formatted_conversations,
        total=total
    )


@router.get("/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(
    conversation_id: str,
    current_user_id: str = Depends(get_current_user_id)
):
    """Get a specific conversation"""
    db = await get_database()
    
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
    
    # Check if user is a participant
    if current_user_id not in conversation["participant_ids"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a participant in this conversation"
        )
    
    return await format_conversation_response(conversation, current_user_id, db)


@router.delete("/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conversation(
    conversation_id: str,
    current_user_id: str = Depends(get_current_user_id)
):
    """
    Delete conversation (archive for current user)
    
    - Conversation is not actually deleted, just archived for this user
    - Messages remain accessible to other participants
    """
    db = await get_database()
    
    try:
        result = await db.conversations.update_one(
            {
                "_id": ObjectId(conversation_id),
                "participant_ids": current_user_id
            },
            {
                "$addToSet": {"metadata.archived_by": current_user_id}
            }
        )
    except:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid conversation ID"
        )
    
    if result.matched_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found"
        )
    
    return None


async def format_conversation_response(conversation: dict, current_user_id: str, db) -> ConversationResponse:
    """Format conversation for response"""
    
    # Get participant details
    participant_details = []
    for participant in conversation["participants"]:
        if participant["user_id"] != current_user_id:
            user = await db.users.find_one({"_id": ObjectId(participant["user_id"])})
            if user:
                participant_details.append({
                    "user_id": str(user["_id"]),
                    "username": user["username"],
                    "full_name": user["profile"]["full_name"],
                    "avatar_url": user["profile"].get("avatar_url"),
                    "online": user["status"].get("online", False),
                    "last_seen": user["status"].get("last_seen")
                })
    
    # Calculate unread count
    current_participant = next(
        (p for p in conversation["participants"] if p["user_id"] == current_user_id),
        None
    )
    
    unread_count = 0
    if current_participant and conversation.get("last_message"):
        last_read_at = current_participant.get("last_read_at")
        last_message_time = conversation["last_message"]["timestamp"]
        
        if not last_read_at or last_message_time > last_read_at:
            # Count unread messages
            unread_count = await db.messages.count_documents({
                "conversation_id": str(conversation["_id"]),
                "sender_id": {"$ne": current_user_id},
                "created_at": {"$gt": last_read_at} if last_read_at else {"$exists": True}
            })
    
    return ConversationResponse(
        id=str(conversation["_id"]),
        type=conversation["type"],
        participants=participant_details,
        last_message=conversation.get("last_message"),
        unread_count=unread_count,
        created_at=conversation["metadata"]["created_at"],
        updated_at=conversation["metadata"]["updated_at"]
    )
