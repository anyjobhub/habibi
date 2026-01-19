"""
Media upload utilities using Cloudinary
"""
import cloudinary
import cloudinary.uploader
from fastapi import UploadFile, HTTPException, status
from app.core import settings
import io

# Initialize Cloudinary
cloudinary.config( 
  cloud_name = settings.CLOUDINARY_CLOUD_NAME, 
  api_key = settings.CLOUDINARY_API_KEY, 
  api_secret = settings.CLOUDINARY_API_SECRET,
  secure = True
)

async def upload_image(file: UploadFile, folder: str = "habibti/avatars", resource_type: str = "image") -> dict:
    """
    Upload media to Cloudinary
    
    Args:
        file: FastAPI UploadFile object
        folder: Cloudinary folder path
        resource_type: Cloudinary resource type (image, video, auto)
        
    Returns:
        Dictionary containing url and public_id
    """
    # Validate file type if strict
    if resource_type == "image" and not file.content_type.startswith("image/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be an image"
        )
    
    # Read file content
    content = await file.read()
    
    # Check file size (limit to 10MB)
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File size exceeds 10MB limit"
        )
        
    try:
        # Upload to Cloudinary
        import asyncio
        from functools import partial
        
        loop = asyncio.get_event_loop()
        upload_func = partial(
            cloudinary.uploader.upload,
            io.BytesIO(content),
            folder=folder,
            resource_type=resource_type
        )
        
        response = await loop.run_in_executor(None, upload_func)
        
        return {
            "url": response.get("secure_url"),
            "public_id": response.get("public_id"),
            "width": response.get("width"),
            "height": response.get("height"),
            "format": response.get("format"),
            "resource_type": response.get("resource_type")
        }
        
    except Exception as e:
        print(f"Cloudinary upload error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to upload image"
        )
