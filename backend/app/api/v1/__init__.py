"""
API v1 router
"""

from fastapi import APIRouter
from app.api.v1.endpoints.auth import router as auth_router
from app.api.v1.endpoints.websocket import router as websocket_router
from app.api.v1.endpoints.conversations import router as conversations_router
from app.api.v1.endpoints.messages import router as messages_router
from app.api.v1.endpoints.users import router as users_router
from app.api.v1.endpoints.friends import router as friends_router
from app.api.v1.endpoints.moments import router as moments_router
from app.api.v1.endpoints.media import router as media_router

api_router = APIRouter()

# Include endpoint routers
api_router.include_router(auth_router, prefix="/auth", tags=["Authentication"])
api_router.include_router(websocket_router, tags=["WebSocket"])
api_router.include_router(conversations_router, prefix="/conversations", tags=["Conversations"])
api_router.include_router(messages_router, prefix="/messages", tags=["Messages"])
api_router.include_router(users_router, prefix="/users", tags=["Users"])
api_router.include_router(friends_router, prefix="/friends", tags=["Friends"])
api_router.include_router(moments_router, prefix="/moments", tags=["Moments"])
api_router.include_router(media_router, prefix="/media", tags=["Media"])

