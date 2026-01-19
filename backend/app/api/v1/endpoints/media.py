"""
Media endpoints for general file uploads
"""

from fastapi import APIRouter, HTTPException, status, Depends, UploadFile, File, Query, Header
from app.core import decode_access_token
from app.utils.media import upload_image

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

@router.post("/upload", response_model=dict)
async def upload_media(
    type: str = Query(..., regex="^(image|video)$"),
    file: UploadFile = File(...),
    current_user_id: str = Depends(get_current_user_id)
):
    """
    Upload media (image or video)
    
    Returns:
        dict: {
            "url": "https://...",
            "public_id": "...",
            "type": "image"
        }
    """
    # Map type to Cloudinary resource type
    resource_type = "video" if type == "video" else "image"
    folder = "habibti/chat_media"
    
    try:
        result = await upload_image(file, folder=folder, resource_type=resource_type)
        
        return {
            "url": result["url"],
            "public_id": result.get("public_id"),
            "type": type,
            "format": result.get("format")
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
