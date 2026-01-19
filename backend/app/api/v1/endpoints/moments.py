from fastapi import APIRouter, HTTPException, status, Depends, Header
from app.core import decode_access_token
from typing import List, Optional

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

@router.get("/", status_code=status.HTTP_200_OK)
async def get_moments(
    skip: int = 0,
    limit: int = 20,
    current_user_id: str = Depends(get_current_user_id)
):
    """
    Get moments feed
    """
    return {
        "moments": [],
        "has_more": False,
        "total": 0
    }
