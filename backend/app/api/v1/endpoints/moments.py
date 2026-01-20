from fastapi import APIRouter, HTTPException, status, Depends, Header
from app.core import decode_access_token, get_database
from app.core.websocket import manager
from app.models.moment import MomentCreate, MomentResponse, Moment
from app.models.user import UserResponse
from typing import List, Optional
from datetime import datetime
from bson import ObjectId

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

@router.post("", response_model=MomentResponse, status_code=status.HTTP_201_CREATED)
async def create_moment(
    data: MomentCreate,
    current_user_id: str = Depends(get_current_user_id)
):
    """
    Create a new moment and broadcast to friends
    """
    db = await get_database()
    
    # Create moment object
    moment = Moment(
        user_id=current_user_id,
        **data.dict()
    )
    
    result = await db.moments.insert_one(moment.dict(by_alias=True))
    moment.id = result.inserted_id
    
    # Notification Flow
    # 1. Find friends
    user = await db.users.find_one({"_id": ObjectId(current_user_id)})
    friends = [f["user_id"] for f in user.get("friends", []) if f["status"] == "accepted"]
    
    # 2. Broadcast to friends
    notification_data = {
         "type": "new_moment",
         "data": {
             "moment_id": str(moment.id),
             "user": {
                 "id": str(user["_id"]),
                 "username": user["username"],
                 "full_name": user["profile"]["full_name"],
                 "avatar_url": user["profile"].get("avatar_url")
             },
             "moment_type": moment.type,
             "created_at": moment.created_at.isoformat()
         }
    }
    
    for friend_id in friends:
        await manager.send_to_user(notification_data, friend_id)
        
    # Return formatted response
    return MomentResponse(
        id=str(moment.id),
        user={
            "id": str(user["_id"]),
            "username": user["username"],
            "full_name": user["profile"]["full_name"],
            "avatar_url": user["profile"].get("avatar_url")
        },
        type=moment.type,
        text_content=moment.text_content,
        media_url=moment.media_url,
        media_thumbnail=moment.media_thumbnail,
        duration=moment.duration,
        view_count=0,
        has_viewed=False,
        created_at=moment.created_at,
        expires_at=moment.expires_at,
        time_remaining=int((moment.expires_at - datetime.utcnow()).total_seconds())
    )


@router.get("", status_code=status.HTTP_200_OK)
async def get_moments(
    skip: int = 0,
    limit: int = 20,
    current_user_id: str = Depends(get_current_user_id)
):
    """
    Get moments feed
    """
    # ... (Actual implementation of feed logic would go here, stub for now as focus is POST)
    # For now, let's keep the user's existing logic, just replaced the file content to inject POST.
    # But wait, the previous file had a STUB for GET too. I should probably leave it as stub but ensure it returns LIST.
    
    return {
        "moments_by_user": [], # Changed key to match MomentListResponse if used
        "total_users": 0
    }
