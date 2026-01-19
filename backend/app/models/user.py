"""
User model and schemas
"""

from pydantic import BaseModel, Field, EmailStr, field_validator
from typing import Optional, List
from datetime import datetime, date
from bson import ObjectId
from enum import Enum


class PyObjectId(ObjectId):
    """Custom ObjectId type for Pydantic"""
    
    @classmethod
    def __get_validators__(cls):
        yield cls.validate
    
    @classmethod
    def validate(cls, v):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid ObjectId")
        return ObjectId(v)
    
    @classmethod
    def __modify_schema__(cls, field_schema):
        field_schema.update(type="string")


class Gender(str, Enum):
    """Gender enumeration"""
    MALE = "male"
    FEMALE = "female"
    OTHER = "other"
    PREFER_NOT_TO_SAY = "prefer_not_to_say"


class UserProfile(BaseModel):
    """User profile information"""
    full_name: str = Field(..., min_length=2, max_length=100, description="Full name (alphabets only)")
    bio: Optional[str] = Field(None, max_length=500)
    avatar_url: Optional[str] = None
    
    # Mandatory fields for signup
    mobile: str = Field(..., regex=r'^\+?[1-9]\d{9,14}$', description="Mobile number (unique, no OTP)")
    address: str = Field(..., min_length=10, max_length=500, description="Full address")
    date_of_birth: date = Field(..., description="Date of birth (age validation required)")
    gender: Gender = Field(..., description="Gender")
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    @field_validator('full_name')
    @classmethod
    def validate_full_name(cls, v):
        """Validate full name contains only alphabets and spaces"""
        if not all(c.isalpha() or c.isspace() for c in v):
            raise ValueError("Full name must contain only alphabets and spaces")
        return v.strip()
    
    @field_validator('date_of_birth')
    @classmethod
    def validate_age(cls, v):
        """Validate minimum age (13 years)"""
        today = date.today()
        age = today.year - v.year - ((today.month, today.day) < (v.month, v.day))
        if age < 13:
            raise ValueError("User must be at least 13 years old")
        if age > 120:
            raise ValueError("Invalid date of birth")
        return v


class UserPrivacy(BaseModel):
    """User privacy settings"""
    discoverable_by_email: bool = True
    discoverable_by_username: bool = True
    show_online_status: bool = True
    read_receipts: bool = True


class UserEncryption(BaseModel):
    """User encryption keys"""
    public_key: str
    key_version: int = 1


class DeviceInfo(BaseModel):
    """User device information"""
    device_id: str
    device_name: str
    public_key: str
    last_active: datetime = Field(default_factory=datetime.utcnow)
    push_token: Optional[str] = None


class UserStatus(BaseModel):
    """User online status"""
    online: bool = False
    last_seen: datetime = Field(default_factory=datetime.utcnow)


class UserMetadata(BaseModel):
    """User metadata"""
    trust_score: int = Field(default=100, ge=0, le=100)
    is_banned: bool = False
    account_status: str = Field(default="active", regex=r'^(active|suspended|deleted)$')
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class User(BaseModel):
    """Complete user model"""
    id: Optional[PyObjectId] = Field(default=None, alias="_id")
    email: EmailStr = Field(..., description="Primary identifier (unique)")
    username: str = Field(..., min_length=3, max_length=30, regex=r'^[a-zA-Z0-9_]+$', description="Unique username")
    
    profile: UserProfile
    privacy: UserPrivacy = Field(default_factory=UserPrivacy)
    encryption: UserEncryption
    devices: List[DeviceInfo] = Field(default_factory=list)
    status: UserStatus = Field(default_factory=UserStatus)
    metadata: UserMetadata = Field(default_factory=UserMetadata)
    
    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str, date: lambda v: v.isoformat()}
        json_schema_extra = {
            "example": {
                "email": "salman@example.com",
                "username": "salman_dev",
                "profile": {
                    "full_name": "Salman Ahmed",
                    "mobile": "+919876543210",
                    "address": "123 Main Street, Mumbai, Maharashtra, India",
                    "date_of_birth": "1995-05-15",
                    "gender": "male",
                    "bio": "Privacy advocate"
                },
                "encryption": {
                    "public_key": "base64_encoded_public_key"
                }
            }
        }


# Request/Response Schemas

class UserCreate(BaseModel):
    """Schema for creating a new user (after OTP verification)"""
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=30, regex=r'^[a-zA-Z0-9_]+$')
    
    # Mandatory profile fields
    full_name: str = Field(..., min_length=2, max_length=100)
    mobile: str = Field(..., regex=r'^\+?[1-9]\d{9,14}$')
    address: str = Field(..., min_length=10, max_length=500)
    date_of_birth: date
    gender: Gender
    
    # Optional
    bio: Optional[str] = Field(None, max_length=500)
    
    # Encryption
    public_key: str
    device_info: DeviceInfo
    
    @field_validator('full_name')
    @classmethod
    def validate_full_name(cls, v):
        if not all(c.isalpha() or c.isspace() for c in v):
            raise ValueError("Full name must contain only alphabets and spaces")
        return v.strip()
    
    @field_validator('date_of_birth')
    @classmethod
    def validate_age(cls, v):
        today = date.today()
        age = today.year - v.year - ((today.month, today.day) < (v.month, v.day))
        if age < 13:
            raise ValueError("User must be at least 13 years old")
        if age > 120:
            raise ValueError("Invalid date of birth")
        return v


class UserUpdate(BaseModel):
    """Schema for updating user profile"""
    full_name: Optional[str] = Field(None, min_length=2, max_length=100)
    bio: Optional[str] = Field(None, max_length=500)
    avatar_url: Optional[str] = None
    address: Optional[str] = Field(None, min_length=10, max_length=500)
    privacy: Optional[UserPrivacy] = None


class UserResponse(BaseModel):
    """Public user response (limited info)"""
    id: str
    username: str
    full_name: str
    avatar_url: Optional[str]
    bio: Optional[str]
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "507f1f77bcf86cd799439011",
                "username": "salman_dev",
                "full_name": "Salman Ahmed",
                "avatar_url": "https://...",
                "bio": "Privacy advocate"
            }
        }


class UserDetailResponse(BaseModel):
    """Detailed user response (own profile)"""
    id: str
    email: str
    username: str
    profile: UserProfile
    privacy: UserPrivacy
    devices: List[DeviceInfo]
    status: UserStatus
    
    class Config:
        json_encoders = {date: lambda v: v.isoformat()}
        json_schema_extra = {
            "example": {
                "id": "507f1f77bcf86cd799439011",
                "email": "salman@example.com",
                "username": "salman_dev",
                "profile": {
                    "full_name": "Salman Ahmed",
                    "mobile": "+919876543210",
                    "address": "123 Main Street, Mumbai",
                    "date_of_birth": "1995-05-15",
                    "gender": "male",
                    "bio": "Privacy advocate"
                },
                "privacy": {
                    "discoverable_by_email": True
                },
                "devices": [],
                "status": {
                    "online": True,
                    "last_seen": "2026-01-19T01:00:00Z"
                }
            }
        }
