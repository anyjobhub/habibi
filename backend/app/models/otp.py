"""
OTP Session model and schemas
"""

from pydantic import BaseModel, Field, EmailStr
from typing import Optional
from datetime import datetime
from bson import ObjectId
from app.models.user import PyObjectId


class OTPMetadata(BaseModel):
    """OTP session metadata"""
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    purpose: str = Field(..., regex=r'^(signup|login|recovery)$')


class OTPSession(BaseModel):
    """OTP session model"""
    id: Optional[PyObjectId] = Field(default=None, alias="_id")
    identifier: str  # Email address
    otp_hash: str  # Hashed OTP (never store plaintext)
    
    attempts: int = 0
    max_attempts: int = 3
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: datetime
    verified: bool = False
    verified_at: Optional[datetime] = None
    
    session_token: Optional[str] = None  # Temp token after verification
    metadata: OTPMetadata
    
    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}


# Request/Response Schemas

class OTPRequest(BaseModel):
    """Request to send OTP"""
    email: EmailStr = Field(..., description="Email address to send OTP")
    purpose: str = Field(..., regex=r'^(signup|login|recovery)$')
    
    class Config:
        json_schema_extra = {
            "example": {
                "email": "salman@example.com",
                "purpose": "signup"
            }
        }


class OTPVerifyRequest(BaseModel):
    """Request to verify OTP"""
    session_id: str
    otp: str = Field(..., min_length=6, max_length=6)
    
    class Config:
        json_schema_extra = {
            "example": {
                "session_id": "507f1f77bcf86cd799439011",
                "otp": "123456"
            }
        }


class OTPResponse(BaseModel):
    """Response after sending OTP"""
    session_id: str
    expires_in: int  # Seconds
    message: str = "OTP sent successfully to your email"
    
    class Config:
        json_schema_extra = {
            "example": {
                "session_id": "507f1f77bcf86cd799439011",
                "expires_in": 300,
                "message": "OTP sent successfully to your email"
            }
        }


class OTPVerifyResponse(BaseModel):
    """Response after verifying OTP"""
    verified: bool
    temp_token: Optional[str] = None  # For completing signup
    message: str = "OTP verified successfully"
    
    class Config:
        json_schema_extra = {
            "example": {
                "verified": True,
                "temp_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "message": "OTP verified successfully. Please complete your profile."
            }
        }
