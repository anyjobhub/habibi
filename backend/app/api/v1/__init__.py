"""
API v1 router
"""

from fastapi import APIRouter
from app.api.v1.endpoints import auth, websocket, conversations, messages, users, friends, moments, media

api_router = APIRouter()

# Include endpoint routers
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(websocket.router, tags=["WebSocket"])
api_router.include_router(conversations.router, prefix="/conversations", tags=["Conversations"])
api_router.include_router(messages.router, prefix="/messages", tags=["Messages"])
api_router.include_router(users.router, prefix="/users", tags=["Users"])
api_router.include_router(friends.router, prefix="/friends", tags=["Friends"])
api_router.include_router(moments.router, prefix="/moments", tags=["Moments"])
api_router.include_router(media.router, prefix="/media", tags=["Media"])

