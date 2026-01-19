from fastapi import APIRouter, HTTPException, status, Depends
from app.api.v1.endpoints import auth
from typing import List, Optional

router = APIRouter()

@router.get("/", status_code=status.HTTP_200_OK)
async def get_moments(
    skip: int = 0,
    limit: int = 20,
    current_user: dict = Depends(auth.get_current_user)
):
    """
    Get moments feed
    """
    return {
        "moments": [],
        "has_more": False,
        "total": 0
    }
