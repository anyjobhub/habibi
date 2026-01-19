"""
Friends endpoints for friend requests and management
"""

from fastapi import APIRouter, HTTPException, status, Depends, Header
from datetime import datetime
from bson import ObjectId
from typing import Optional

from app.models.friendship import (
    FriendRequestCreate,
    FriendRequestRespond,
    FriendshipResponse,
    FriendListResponse,
    FriendRequestListResponse,
    FriendshipStatus
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


@router.post("/request", response_model=FriendshipResponse, status_code=status.HTTP_201_CREATED)
async def send_friend_request(
    data: FriendRequestCreate,
    current_user_id: str = Depends(get_current_user_id)
):
    """
    Send a friend request
    
    - Cannot send request to yourself
    - Cannot send if already friends
    - Cannot send if blocked
    - Can resend if previously rejected
    """
    db = await get_database()
    
    # Validate target user exists
    target_user = await db.users.find_one({"_id": ObjectId(data.user_id)})
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Cannot send request to yourself
    if data.user_id == current_user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot send friend request to yourself"
        )
    
    # Check for existing friendship
    existing = await db.friendships.find_one({
        "$or": [
            {"requester_id": current_user_id, "addressee_id": data.user_id},
            {"requester_id": data.user_id, "addressee_id": current_user_id}
        ]
    })
    
    if existing:
        if existing["status"] == FriendshipStatus.BLOCKED:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot send friend request. User may have blocked you."
            )
        elif existing["status"] == FriendshipStatus.ACCEPTED:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Already friends with this user"
            )
        elif existing["status"] == FriendshipStatus.PENDING:
            # Check who sent the original request
            if existing["requester_id"] == current_user_id:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Friend request already sent"
                )
            else:
                # The other user sent a request to us, we should accept instead
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="This user has already sent you a friend request. Please accept it instead."
                )
        elif existing["status"] == FriendshipStatus.REJECTED:
            # Allow resending after rejection
            await db.friendships.update_one(
                {"_id": existing["_id"]},
                {
                    "$set": {
                        "status": FriendshipStatus.PENDING,
                        "requested_at": datetime.utcnow(),
                        "responded_at": None,
                        "updated_at": datetime.utcnow()
                    }
                }
            )
            
            # Notify via WebSocket
            await notify_friend_request(data.user_id, current_user_id, str(existing["_id"]))
            
            return await format_friendship_response(existing, current_user_id, db, is_requester=True)
    
    # Create new friend request
    friendship = {
        "requester_id": current_user_id,
        "addressee_id": data.user_id,
        "status": FriendshipStatus.PENDING,
        "requested_at": datetime.utcnow(),
        "responded_at": None,
        "updated_at": datetime.utcnow(),
        "blocked_by": None
    }
    
    result = await db.friendships.insert_one(friendship)
    friendship["_id"] = result.inserted_id
    
    # Notify via WebSocket
    await notify_friend_request(data.user_id, current_user_id, str(result.inserted_id))
    
    return await format_friendship_response(friendship, current_user_id, db, is_requester=True)


@router.get("/requests/received", response_model=FriendRequestListResponse)
async def get_received_requests(
    status_filter: Optional[str] = None,
    limit: int = 50,
    skip: int = 0,
    current_user_id: str = Depends(get_current_user_id)
):
    """
    Get friend requests received by current user
    
    - Can filter by status (pending, accepted, rejected)
    - Sorted by most recent first
    """
    db = await get_database()
    
    query = {"addressee_id": current_user_id}
    
    if status_filter:
        query["status"] = status_filter
    
    requests = await db.friendships.find(query).sort("requested_at", -1).skip(skip).limit(limit).to_list(length=limit)
    
    total = await db.friendships.count_documents(query)
    
    formatted_requests = []
    for req in requests:
        formatted = await format_friendship_response(req, current_user_id, db, is_requester=False)
        formatted_requests.append(formatted)
    
    return FriendRequestListResponse(
        requests=formatted_requests,
        total=total
    )


@router.get("/requests/sent", response_model=FriendRequestListResponse)
async def get_sent_requests(
    status_filter: Optional[str] = None,
    limit: int = 50,
    skip: int = 0,
    current_user_id: str = Depends(get_current_user_id)
):
    """
    Get friend requests sent by current user
    
    - Can filter by status (pending, accepted, rejected, blocked)
    - Sorted by most recent first
    """
    db = await get_database()
    
    query = {"requester_id": current_user_id}
    
    if status_filter:
        query["status"] = status_filter
    
    requests = await db.friendships.find(query).sort("requested_at", -1).skip(skip).limit(limit).to_list(length=limit)
    
    total = await db.friendships.count_documents(query)
    
    formatted_requests = []
    for req in requests:
        formatted = await format_friendship_response(req, current_user_id, db, is_requester=True)
        formatted_requests.append(formatted)
    
    return FriendRequestListResponse(
        requests=formatted_requests,
        total=total
    )


@router.post("/requests/{friendship_id}/respond", response_model=FriendshipResponse)
async def respond_to_friend_request(
    friendship_id: str,
    data: FriendRequestRespond,
    current_user_id: str = Depends(get_current_user_id)
):
    """
    Respond to a friend request (accept or reject)
    
    - Only the addressee can respond
    - Cannot respond to already responded requests
    """
    db = await get_database()
    
    try:
        friendship = await db.friendships.find_one({"_id": ObjectId(friendship_id)})
    except:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid friendship ID"
        )
    
    if not friendship:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Friend request not found"
        )
    
    # Only addressee can respond
    if friendship["addressee_id"] != current_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the recipient can respond to this request"
        )
    
    # Cannot respond if not pending
    if friendship["status"] != FriendshipStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Request is already {friendship['status']}"
        )
    
    # Update status
    new_status = FriendshipStatus.ACCEPTED if data.action == "accept" else FriendshipStatus.REJECTED
    
    await db.friendships.update_one(
        {"_id": ObjectId(friendship_id)},
        {
            "$set": {
                "status": new_status,
                "responded_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }
        }
    )
    
    friendship["status"] = new_status
    friendship["responded_at"] = datetime.utcnow()
    
    # Notify requester via WebSocket
    if new_status == FriendshipStatus.ACCEPTED:
        await manager.send_to_user(
            {
                "type": "friend_request_accepted",
                "data": {
                    "friendship_id": friendship_id,
                    "user_id": current_user_id
                }
            },
            friendship["requester_id"]
        )
    
    return await format_friendship_response(friendship, current_user_id, db, is_requester=False)


@router.get("", response_model=FriendListResponse)
async def get_friends(
    limit: int = 100,
    skip: int = 0,
    current_user_id: str = Depends(get_current_user_id)
):
    """
    Get current user's friends
    
    - Returns only accepted friendships
    - Friends list is PRIVATE (only user can see their own friends)
    - Sorted by friendship date
    """
    db = await get_database()
    
    # Find accepted friendships where user is either requester or addressee
    friendships = await db.friendships.find({
        "$or": [
            {"requester_id": current_user_id, "status": FriendshipStatus.ACCEPTED},
            {"addressee_id": current_user_id, "status": FriendshipStatus.ACCEPTED}
        ]
    }).sort("responded_at", -1).skip(skip).limit(limit).to_list(length=limit)
    
    total = await db.friendships.count_documents({
        "$or": [
            {"requester_id": current_user_id, "status": FriendshipStatus.ACCEPTED},
            {"addressee_id": current_user_id, "status": FriendshipStatus.ACCEPTED}
        ]
    })
    
    # Get friend details
    friends = []
    for friendship in friendships:
        friend_id = friendship["addressee_id"] if friendship["requester_id"] == current_user_id else friendship["requester_id"]
        
        friend = await db.users.find_one({"_id": ObjectId(friend_id)})
        if friend:
            friends.append({
                "id": str(friend["_id"]),
                "username": friend["username"],
                "full_name": friend["profile"]["full_name"],
                "avatar_url": friend["profile"].get("avatar_url"),
                "bio": friend["profile"].get("bio"),
                "online": friend["status"].get("online", False),
                "last_seen": friend["status"].get("last_seen"),
                "friendship_since": friendship["responded_at"]
            })
    
    return FriendListResponse(
        friends=friends,
        total=total
    )


@router.post("/{user_id}/block", status_code=status.HTTP_200_OK)
async def block_user(
    user_id: str,
    current_user_id: str = Depends(get_current_user_id)
):
    """
    Block a user
    
    - Blocks all communication
    - Removes friendship if exists
    - User cannot send new friend requests
    """
    db = await get_database()
    
    # Validate user exists
    user = await db.users.find_one({"_id": ObjectId(user_id)})
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Cannot block yourself
    if user_id == current_user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot block yourself"
        )
    
    # Check for existing friendship
    existing = await db.friendships.find_one({
        "$or": [
            {"requester_id": current_user_id, "addressee_id": user_id},
            {"requester_id": user_id, "addressee_id": current_user_id}
        ]
    })
    
    if existing:
        # Update to blocked
        await db.friendships.update_one(
            {"_id": existing["_id"]},
            {
                "$set": {
                    "status": FriendshipStatus.BLOCKED,
                    "blocked_by": current_user_id,
                    "updated_at": datetime.utcnow()
                }
            }
        )
    else:
        # Create new blocked entry
        await db.friendships.insert_one({
            "requester_id": current_user_id,
            "addressee_id": user_id,
            "status": FriendshipStatus.BLOCKED,
            "blocked_by": current_user_id,
            "requested_at": datetime.utcnow(),
            "responded_at": None,
            "updated_at": datetime.utcnow()
        })
    
    return {"message": "User blocked successfully"}


@router.delete("/{user_id}/unblock", status_code=status.HTTP_200_OK)
async def unblock_user(
    user_id: str,
    current_user_id: str = Depends(get_current_user_id)
):
    """
    Unblock a user
    
    - Removes block
    - Deletes friendship record
    - User can send friend requests again
    """
    db = await get_database()
    
    # Find blocked friendship
    friendship = await db.friendships.find_one({
        "$or": [
            {"requester_id": current_user_id, "addressee_id": user_id, "status": FriendshipStatus.BLOCKED},
            {"requester_id": user_id, "addressee_id": current_user_id, "status": FriendshipStatus.BLOCKED}
        ],
        "blocked_by": current_user_id
    })
    
    if not friendship:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No block found for this user"
        )
    
    # Delete the friendship record
    await db.friendships.delete_one({"_id": friendship["_id"]})
    
    return {"message": "User unblocked successfully"}


async def format_friendship_response(friendship: dict, current_user_id: str, db, is_requester: bool) -> FriendshipResponse:
    """Format friendship for response"""
    
    # Get the other user's details
    other_user_id = friendship["addressee_id"] if is_requester else friendship["requester_id"]
    
    user = await db.users.find_one({"_id": ObjectId(other_user_id)})
    
    user_details = {
        "id": str(user["_id"]),
        "username": user["username"],
        "full_name": user["profile"]["full_name"],
        "avatar_url": user["profile"].get("avatar_url"),
        "bio": user["profile"].get("bio")
    } if user else None
    
    return FriendshipResponse(
        id=str(friendship["_id"]),
        user=user_details,
        status=friendship["status"],
        requested_at=friendship["requested_at"],
        responded_at=friendship.get("responded_at")
    )


async def notify_friend_request(addressee_id: str, requester_id: str, friendship_id: str):
    """Notify user of new friend request via WebSocket"""
    db = await get_database()
    
    requester = await db.users.find_one({"_id": ObjectId(requester_id)})
    
    if requester:
        await manager.send_to_user(
            {
                "type": "friend_request_received",
                "data": {
                    "friendship_id": friendship_id,
                    "requester": {
                        "id": str(requester["_id"]),
                        "username": requester["username"],
                        "full_name": requester["profile"]["full_name"],
                        "avatar_url": requester["profile"].get("avatar_url")
                    }
                }
            },
            addressee_id
        )
