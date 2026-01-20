"""
Conversation model and schemas
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime, timezone
from bson import ObjectId
from app.models.user import PyObjectId


class ConversationParticipant(BaseModel):
    """Participant in a conversation"""
    user_id: str
    joined_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    left_at: Optional[datetime] = None
    last_read_at: Optional[datetime] = None
    notifications_enabled: bool = True


class LastMessage(BaseModel):
    """Last message preview in conversation"""
    message_id: str
    encrypted_preview: str  # First 50 chars encrypted
    timestamp: datetime
    sender_id: str


class ConversationMetadata(BaseModel):
    """Conversation metadata"""
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    archived_by: List[str] = Field(default_factory=list)  # User IDs who archived


class Conversation(BaseModel):
    """Conversation model"""
    id: Optional[PyObjectId] = Field(default=None, alias="_id")
    type: str = Field(default="one_to_one", pattern=r'^(one_to_one|group)$')
    
    participants: List[ConversationParticipant]
    participant_ids: List[str]  # Sorted array for quick lookup
    
    last_message: Optional[LastMessage] = None
    metadata: ConversationMetadata = Field(default_factory=ConversationMetadata)
    
    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}


# Request/Response Schemas

class ConversationCreate(BaseModel):
    """Create or get conversation"""
    participant_id: str  # Other user's ID
    
    class Config:
        json_schema_extra = {
            "example": {
                "participant_id": "507f1f77bcf86cd799439011"
            }
        }


class ConversationResponse(BaseModel):
    """Conversation response"""
    id: str
    type: str
    participants: List[dict]  # User info for each participant
    last_message: Optional[dict]
    unread_count: int = 0
    created_at: datetime
    updated_at: datetime
    
    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}
        json_schema_extra = {
            "example": {
                "id": "507f1f77bcf86cd799439011",
                "type": "one_to_one",
                "participants": [
                    {
                        "user_id": "507f1f77bcf86cd799439011",
                        "username": "salman_dev",
                        "full_name": "Salman Ahmed",
                        "avatar_url": "https://..."
                    }
                ],
                "last_message": {
                    "message_id": "507f1f77bcf86cd799439012",
                    "encrypted_preview": "...",
                    "timestamp": "2026-01-19T01:00:00Z",
                    "sender_id": "507f1f77bcf86cd799439011"
                },
                "unread_count": 3,
                "created_at": "2026-01-19T01:00:00Z",
                "updated_at": "2026-01-19T01:05:00Z"
            }
        }


class ConversationListResponse(BaseModel):
    """List of conversations"""
    conversations: List[ConversationResponse]
    total: int
    
    class Config:
        json_schema_extra = {
            "example": {
                "conversations": [],
                "total": 10
            }
        }
