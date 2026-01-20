"""
Friendship model and schemas
"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime, timezone
from bson import ObjectId
from app.models.user import PyObjectId
from enum import Enum


class FriendshipStatus(str, Enum):
    """Friendship status enumeration"""
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    BLOCKED = "blocked"


class Friendship(BaseModel):
    """Friendship model"""
    id: Optional[PyObjectId] = Field(default=None, alias="_id")
    requester_id: str  # User who sent the request
    addressee_id: str  # User who receives the request
    
    status: FriendshipStatus = FriendshipStatus.PENDING
    
    # Timestamps
    requested_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    responded_at: Optional[datetime] = None
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    # For blocking
    blocked_by: Optional[str] = None  # User ID who blocked
    
    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str, datetime: lambda v: v.isoformat()}


# Request/Response Schemas

class FriendRequestCreate(BaseModel):
    """Send a friend request"""
    user_id: str  # User to send request to
    
    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "507f1f77bcf86cd799439011"
            }
        }


class FriendRequestRespond(BaseModel):
    """Respond to a friend request"""
    action: str = Field(..., pattern=r'^(accept|reject)$')
    
    class Config:
        json_schema_extra = {
            "example": {
                "action": "accept"
            }
        }


class FriendshipResponse(BaseModel):
    """Friendship response with user details"""
    id: str
    user: dict  # User details (requester or addressee depending on context)
    status: str
    requested_at: datetime
    responded_at: Optional[datetime]
    
    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}
        json_schema_extra = {
            "example": {
                "id": "507f1f77bcf86cd799439011",
                "user": {
                    "id": "507f1f77bcf86cd799439012",
                    "username": "janedoe",
                    "full_name": "Jane Doe",
                    "avatar_url": "https://...",
                    "bio": "Hello!"
                },
                "status": "pending",
                "requested_at": "2026-01-19T02:00:00Z",
                "responded_at": None
            }
        }


class FriendListResponse(BaseModel):
    """List of friends"""
    friends: list
    total: int
    
    class Config:
        json_schema_extra = {
            "example": {
                "friends": [],
                "total": 10
            }
        }


class FriendRequestListResponse(BaseModel):
    """List of friend requests"""
    requests: list
    total: int
    
    class Config:
        json_schema_extra = {
            "example": {
                "requests": [],
                "total": 5
            }
        }
