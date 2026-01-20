"""
Moment model and schemas (24-hour stories/feeds)
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime, timedelta, timezone
from bson import ObjectId
from app.models.user import PyObjectId
from enum import Enum


class MomentType(str, Enum):
    """Moment content type"""
    TEXT = "text"
    PHOTO = "photo"
    VIDEO = "video"


class MomentView(BaseModel):
    """Moment view tracking"""
    user_id: str
    viewed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Moment(BaseModel):
    """Moment model (24-hour story)"""
    id: Optional[PyObjectId] = Field(default=None, alias="_id")
    user_id: str  # Creator
    
    # Content
    type: MomentType
    text_content: Optional[str] = Field(None, max_length=500)  # For text moments
    media_url: Optional[str] = None  # Photo or video URL
    media_thumbnail: Optional[str] = None  # Thumbnail for videos
    duration: Optional[int] = None  # Video duration in seconds
    
    # Privacy
    visible_to: str = Field(default="friends", pattern=r'^(friends|public)$')  # Only friends for now
    
    # Tracking
    views: List[MomentView] = Field(default_factory=list)
    view_count: int = 0
    
    # Timestamps
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: datetime  # Auto-calculated as created_at + 24 hours
    
    # Soft delete
    deleted: bool = False
    deleted_at: Optional[datetime] = None
    
    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str, datetime: lambda v: v.isoformat()}
    
    def __init__(self, **data):
        if 'expires_at' not in data:
            data['expires_at'] = datetime.now(timezone.utc) + timedelta(hours=24)
        super().__init__(**data)


# Request/Response Schemas

class MomentCreate(BaseModel):
    """Create a new moment"""
    type: MomentType
    text_content: Optional[str] = Field(None, max_length=500)
    media_url: Optional[str] = None
    media_thumbnail: Optional[str] = None
    duration: Optional[int] = None
    visible_to: str = Field(default="friends", pattern=r'^(friends|public)$')
    
    class Config:
        json_schema_extra = {
            "example": {
                "type": "photo",
                "text_content": "Beautiful sunset!",
                "media_url": "https://cloudinary.com/...",
                "visible_to": "friends"
            }
        }


class MomentResponse(BaseModel):
    """Moment response"""
    id: str
    user: dict  # User details
    type: str
    text_content: Optional[str]
    media_url: Optional[str]
    media_thumbnail: Optional[str]
    duration: Optional[int]
    view_count: int
    has_viewed: bool  # Whether current user has viewed
    created_at: datetime
    expires_at: datetime
    time_remaining: int  # Seconds until expiry
    
    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}
        json_schema_extra = {
            "example": {
                "id": "507f1f77bcf86cd799439011",
                "user": {
                    "id": "507f1f77bcf86cd799439012",
                    "username": "janedoe",
                    "full_name": "Jane Doe",
                    "avatar_url": "https://..."
                },
                "type": "photo",
                "text_content": "Beautiful sunset!",
                "media_url": "https://...",
                "view_count": 15,
                "has_viewed": False,
                "created_at": "2026-01-19T02:00:00Z",
                "expires_at": "2026-01-20T02:00:00Z",
                "time_remaining": 82800
            }
        }


class MomentListResponse(BaseModel):
    """List of moments grouped by user"""
    moments_by_user: List[dict]
    total_users: int
    
    class Config:
        json_schema_extra = {
            "example": {
                "moments_by_user": [
                    {
                        "user": {
                            "id": "507f1f77bcf86cd799439012",
                            "username": "janedoe",
                            "full_name": "Jane Doe",
                            "avatar_url": "https://..."
                        },
                        "moments": [],
                        "total_moments": 3,
                        "has_unviewed": True,
                        "latest_moment_at": "2026-01-19T02:00:00Z"
                    }
                ],
                "total_users": 10
            }
        }


class MomentViewersResponse(BaseModel):
    """List of users who viewed a moment"""
    viewers: List[dict]
    total: int
    
    class Config:
        json_schema_extra = {
            "example": {
                "viewers": [
                    {
                        "user_id": "507f1f77bcf86cd799439013",
                        "username": "salman_dev",
                        "full_name": "Salman Ahmed",
                        "avatar_url": "https://...",
                        "viewed_at": "2026-01-19T02:05:00Z"
                    }
                ],
                "total": 15
            }
        }
