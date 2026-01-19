"""
User endpoints for search and discovery
"""

from fastapi import APIRouter, HTTPException, status, Depends, Header, Query, UploadFile, File, Body
from bson import ObjectId
from typing import Optional

from app.core import get_database, decode_access_token
from app.models.user import UserResponse, UserUpdate, UserDetailResponse, UserProfile, UserPrivacy
from app.utils.media import upload_image
from app.utils.sanitization import sanitize_text

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


@router.put("/me", response_model=UserDetailResponse)
async def update_user_profile(
    data: UserUpdate,
    current_user_id: str = Depends(get_current_user_id)
):
    """
    Update current user profile
    """
    db = await get_database()
    
    # Sanitize inputs
    if data.bio:
        data.bio = sanitize_text(data.bio)
        
    update_data = {}
    
    # Update profile fields
    if data.full_name:
        update_data["profile.full_name"] = data.full_name
    if data.bio is not None: # Allow clearing bio
        update_data["profile.bio"] = data.bio
    if data.address:
        update_data["profile.address"] = data.address
    if data.avatar_url:
        update_data["profile.avatar_url"] = data.avatar_url
        
    # Update privacy settings
    if data.privacy:
        if data.privacy.discoverable_by_email is not None:
            update_data["privacy.discoverable_by_email"] = data.privacy.discoverable_by_email
        if data.privacy.discoverable_by_username is not None:
            update_data["privacy.discoverable_by_username"] = data.privacy.discoverable_by_username
        if data.privacy.show_online_status is not None:
            update_data["privacy.show_online_status"] = data.privacy.show_online_status
        if data.privacy.read_receipts is not None:
            update_data["privacy.read_receipts"] = data.privacy.read_receipts
            
    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No data to update"
        )
    
    update_data["metadata.updated_at"] = datetime.utcnow()
    
    # Perform update
    result = await db.users.find_one_and_update(
        {"_id": ObjectId(current_user_id)},
        {"$set": update_data},
        return_document=True
    )
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
        
    from datetime import datetime
    
    # Return updated user
    return UserDetailResponse(
        id=str(result["_id"]),
        email=result["email"],
        username=result["username"],
        profile=UserProfile(**result["profile"]),
        privacy=UserPrivacy(**result["privacy"]),
        devices=result.get("devices", []),
        status=result.get("status", {})
    )


@router.post("/me/avatar", response_model=UserDetailResponse)
async def upload_avatar(
    file: UploadFile = File(...),
    current_user_id: str = Depends(get_current_user_id)
):
    """
    Upload and update user avatar
    """
    db = await get_database()
    
    # Upload to Cloudinary
    try:
        start_time = datetime.utcnow()
        upload_result = await upload_image(file, folder="habibti/avatars")
        avatar_url = upload_result["url"]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload avatar: {str(e)}"
        )
        
    # Update user profile
    result = await db.users.find_one_and_update(
        {"_id": ObjectId(current_user_id)},
        {
            "$set": {
                "profile.avatar_url": avatar_url,
                "metadata.updated_at": datetime.utcnow()
            }
        },
        return_document=True
    )
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
        
    return UserDetailResponse(
        id=str(result["_id"]),
        email=result["email"],
        username=result["username"],
        profile=UserProfile(**result["profile"]),
        privacy=UserPrivacy(**result["privacy"]),
        devices=result.get("devices", []),
        status=result.get("status", {})
    )


@router.get("/search", response_model=dict)
async def search_users(
    q: str = Query(..., min_length=1, description="Search query"),
    search_by: str = Query("username", regex=r'^(username|email|mobile)$'),
    limit: int = Query(20, le=50),
    current_user_id: str = Depends(get_current_user_id)
):
    """
    Search for users
    
    - Search by username (default)
    - Search by email (if user has enabled discoverability)
    - Search by mobile (if user has enabled discoverability)
    - Returns limited public profile information
    """
    db = await get_database()
    
    # Build search query based on search type
    if search_by == "username":
        # Case-insensitive username search
        query = {
            "username": {"$regex": f"^{q}", "$options": "i"},
            "privacy.discoverable_by_username": True
        }
    
    elif search_by == "email":
        # Exact email match only
        query = {
            "email": q.lower(),
            "privacy.discoverable_by_email": True
        }
    
    elif search_by == "mobile":
        # Exact mobile match only
        query = {
            "profile.mobile": q,
            "privacy.discoverable_by_email": True  # Using email privacy for mobile too
        }
    
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid search_by parameter"
        )
    
    # Exclude current user from results
    query["_id"] = {"$ne": ObjectId(current_user_id)}
    
    # Execute search
    users = await db.users.find(query).limit(limit).to_list(length=limit)
    
    # Format results (limited public info)
    results = []
    for user in users:
        results.append({
            "id": str(user["_id"]),
            "username": user["username"],
            "full_name": user["profile"]["full_name"],
            "avatar_url": user["profile"].get("avatar_url"),
            "bio": user["profile"].get("bio")
        })
    
    return {
        "results": results,
        "total": len(results),
        "search_by": search_by,
        "query": q
    }


@router.get("/{user_id}", response_model=UserResponse)
async def get_user_profile(
    user_id: str,
    current_user_id: str = Depends(get_current_user_id)
):
    """
    Get public profile of a user
    
    - Returns limited public information
    - Does not expose email, mobile, or other private data
    """
    db = await get_database()
    
    try:
        user = await db.users.find_one({"_id": ObjectId(user_id)})
    except:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid user ID"
        )
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Return limited public profile
    return UserResponse(
        id=str(user["_id"]),
        username=user["username"],
        full_name=user["profile"]["full_name"],
        avatar_url=user["profile"].get("avatar_url"),
        bio=user["profile"].get("bio")
    )


@router.get("/{user_id}/public-key", response_model=dict)
async def get_user_public_key(
    user_id: str,
    current_user_id: str = Depends(get_current_user_id)
):
    """
    Get user's public encryption key
    
    - Required for sending encrypted messages
    - Returns public key and device keys
    """
    db = await get_database()
    
    try:
        user = await db.users.find_one({"_id": ObjectId(user_id)})
    except:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid user ID"
        )
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Return encryption keys
    return {
        "user_id": str(user["_id"]),
        "public_key": user["encryption"]["public_key"],
        "key_version": user["encryption"]["key_version"],
        "devices": [
            {
                "device_id": device["device_id"],
                "device_name": device["device_name"],
                "public_key": device["public_key"]
            }
            for device in user.get("devices", [])
        ]
    }
