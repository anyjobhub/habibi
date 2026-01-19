"""
Message model and schemas
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from bson import ObjectId
from app.models.user import PyObjectId


class RecipientKey(BaseModel):
    """Encrypted key for a recipient device"""
    user_id: str
    device_id: str
    encrypted_key: str  # Symmetric key encrypted with device public key


class MessageMetadata(BaseModel):
    """Message metadata (NOT encrypted)"""
    media_url: Optional[str] = None
    media_thumbnail: Optional[str] = None
    file_size: Optional[int] = None
    duration: Optional[int] = None  # For audio/video in seconds
    reply_to: Optional[str] = None  # Message ID being replied to
    
    # Ephemeral settings
    is_ephemeral: bool = False
    ttl_seconds: Optional[int] = None  # Time to live
    expires_at: Optional[datetime] = None
    view_once: bool = False
    viewed_by: List[dict] = Field(default_factory=list)  # [{user_id, viewed_at}]


class DeliveryStatus(BaseModel):
    """Message delivery status"""
    user_id: str
    delivered_at: datetime


class ReadStatus(BaseModel):
    """Message read status"""
    user_id: str
    read_at: datetime


class MessageStatus(BaseModel):
    """Message status tracking"""
    sent_at: datetime = Field(default_factory=datetime.utcnow)
    delivered_to: List[DeliveryStatus] = Field(default_factory=list)
    read_by: List[ReadStatus] = Field(default_factory=list)


class Message(BaseModel):
    """Message model"""
    id: Optional[PyObjectId] = Field(default=None, alias="_id")
    conversation_id: str
    sender_id: str
    
    # Encrypted content
    encrypted_content: str  # Base64 encoded encrypted blob
    content_type: str = Field(..., regex=r'^(text|image|video|audio|file)$')
    
    # Per-recipient encryption (for multi-device)
    recipient_keys: List[RecipientKey]
    
    # Message metadata (NOT encrypted)
    metadata: MessageMetadata = Field(default_factory=MessageMetadata)
    
    # Delivery status
    status: MessageStatus = Field(default_factory=MessageStatus)
    
    # Soft delete
    deleted_for: List[str] = Field(default_factory=list)  # User IDs who deleted
    deleted_for_everyone: bool = False
    deleted_at: Optional[datetime] = None
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str, datetime: lambda v: v.isoformat()}


# Request/Response Schemas

class MessageCreate(BaseModel):
    """Create a new message"""
    conversation_id: str
    encrypted_content: str
    content_type: str = Field(..., regex=r'^(text|image|video|audio|file)$')
    recipient_keys: List[RecipientKey]
    
    # Optional metadata
    media_url: Optional[str] = None
    media_thumbnail: Optional[str] = None
    file_size: Optional[int] = None
    duration: Optional[int] = None
    reply_to: Optional[str] = None
    is_ephemeral: bool = False
    ttl_seconds: Optional[int] = None
    view_once: bool = False
    
    class Config:
        json_schema_extra = {
            "example": {
                "conversation_id": "507f1f77bcf86cd799439011",
                "encrypted_content": "base64_encrypted_blob",
                "content_type": "text",
                "recipient_keys": [
                    {
                        "user_id": "507f1f77bcf86cd799439012",
                        "device_id": "device-uuid",
                        "encrypted_key": "base64_encrypted_symmetric_key"
                    }
                ],
                "reply_to": None,
                "is_ephemeral": False
            }
        }


class MessageResponse(BaseModel):
    """Message response"""
    id: str
    conversation_id: str
    sender_id: str
    encrypted_content: str
    content_type: str
    recipient_keys: List[dict]
    metadata: dict
    status: dict
    created_at: datetime
    
    # Client-side decryption info
    is_deleted: bool = False
    
    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}
        json_schema_extra = {
            "example": {
                "id": "507f1f77bcf86cd799439011",
                "conversation_id": "507f1f77bcf86cd799439012",
                "sender_id": "507f1f77bcf86cd799439013",
                "encrypted_content": "base64_encrypted_blob",
                "content_type": "text",
                "recipient_keys": [],
                "metadata": {},
                "status": {
                    "sent_at": "2026-01-19T01:00:00Z",
                    "delivered_to": [],
                    "read_by": []
                },
                "created_at": "2026-01-19T01:00:00Z",
                "is_deleted": False
            }
        }


class MessageListResponse(BaseModel):
    """List of messages"""
    messages: List[MessageResponse]
    has_more: bool
    total: int
    
    class Config:
        json_schema_extra = {
            "example": {
                "messages": [],
                "has_more": True,
                "total": 100
            }
        }


class MessageStatusUpdate(BaseModel):
    """Update message status"""
    message_id: str
    status: str = Field(..., regex=r'^(delivered|read)$')
    
    class Config:
        json_schema_extra = {
            "example": {
                "message_id": "507f1f77bcf86cd799439011",
                "status": "read"
            }
        }


class MessageDelete(BaseModel):
    """Delete message"""
    delete_for_everyone: bool = False
    
    class Config:
        json_schema_extra = {
            "example": {
                "delete_for_everyone": False
            }
        }
